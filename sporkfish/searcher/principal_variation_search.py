import math
from typing import Optional, Tuple

import chess

from sporkfish.board.board import Board
from sporkfish.evaluator.evaluator import Evaluator
from sporkfish.searcher.minimax import MiniMaxVariants
from sporkfish.searcher.move_ordering.move_orderer import MoveOrderer
from sporkfish.searcher.searcher_config import SearcherConfig
from sporkfish.statistics import NodeTypes, PruningTypes
from sporkfish.statistics import TranspositionTable as TranspositionTableNodeType
from sporkfish.transposition_table import TranspositionTable
from sporkfish.zobrist_hasher import (
    ZobristStateInfo,
    zobrist_piece_index,
)

# A score large enough to represent checkmate but below infinity, so aspiration
# windows and TT comparisons behave correctly. The engine subtracts `depth` from
# this value so it prefers mating in 1 over mating in 3, etc.
MATE_SCORE = 100_000

# Late Move Reduction (LMR) thresholds.
# After the first LMR_FULL_DEPTH_MOVES have been searched at full depth, subsequent
# *quiet* moves are searched at a reduced depth to save time.
# Only applies when the remaining depth is at least LMR_MIN_DEPTH.
LMR_FULL_DEPTH_MOVES = 4
LMR_MIN_DEPTH = 3


class PVSSp(MiniMaxVariants):
    def __init__(
        self,
        evaluator: Evaluator,
        searcher_config: SearcherConfig = SearcherConfig(),
    ) -> None:
        super().__init__(evaluator, searcher_config)

    def _pvs(
        self,
        board: Board,
        depth: int,
        alpha: float,
        beta: float,
        zobrist_state: Optional[ZobristStateInfo],
    ) -> float:
        """
        Principal Variation Search (PVS) with fail-soft alpha-beta pruning. Non-root nodes.

        PVS is an enhancement over plain negamax that exploits the assumption that the
        first move (after good move ordering) is likely the best. The strategy is:

        1. Search the first move with a full [alpha, beta] window.
        2. For all subsequent moves, do a cheap *null window* search: [-alpha-1, -alpha].
           A null window has zero width - it can only confirm the move is worse than
           alpha (fail low) or reveal that it beats alpha (fail high).
        3. If a subsequent move unexpectedly beats alpha (step 2 failed high), re-search
           it with the full window to get the exact score.

        This reduces the number of full-window re-searches, saving significant time
        when move ordering is good (which it usually is after the first iteration of
        iterative deepening).

        :param board: The current state of the chess board.
        :type board: Board
        :param depth: Remaining plies to search. 0 = leaf, devolves to quiescence.
        :type depth: int
        :param alpha: Lower bound: best score already secured by the current player.
        :type alpha: float
        :param beta: Upper bound: best score already secured by the opponent.
        :type beta: float
        :param zobrist_state: Carries the incremental Zobrist hash for TT lookups.
                              None if TT is disabled.
        :type zobrist_state: Optional[ZobristStateInfo]

        :returns: The evaluation score of the current board position (current player's POV).
        :rtype: float
        """

        # best score seen so far at this node; starts at -inf (no move seen yet)
        value = -float("inf")

        # --- Base case ---
        # Switch to quiescence search at depth 0 to resolve captures before evaluating.
        if depth == 0:
            return self._quiescence(board, 4, alpha, beta, zobrist_state)

        # --- Transposition table probe ---
        # Identical logic to negamax: an EXACT hit returns immediately; LOWER/UPPER
        # hits tighten the window, potentially causing an early cutoff.
        # We also extract the stored best move for hash-move ordering.
        tt_best_move = None
        if zobrist_state and (
            tt_entry := self._transposition_table.probe(
                zobrist_state.zobrist_hash, depth
            )
        ):
            self._statistics.increment_visited(
                TranspositionTableNodeType.TRANSPOSITITON_TABLE
            )

            # Tuple layout: (depth, score, flag, best_move) - see TranspositionTable constants
            tt_score = tt_entry[TranspositionTable._SCORE]  # type: ignore
            tt_flag = tt_entry[TranspositionTable._FLAG]
            if tt_flag == TranspositionTable.EXACT:
                return tt_score
            elif tt_flag == TranspositionTable.LOWER_BOUND:
                alpha = max(alpha, tt_score)
            elif tt_flag == TranspositionTable.UPPER_BOUND:
                beta = min(beta, tt_score)
            if alpha >= beta:
                return tt_score

            # Extract best move for hash-move ordering even when we can't cut off.
            tt_best_move = tt_entry[TranspositionTable._BEST_MOVE]  # type: ignore

        # Capture alpha AFTER TT probe so the TT flag stored at the end is computed
        # relative to the (possibly tightened) window, not the original one.
        original_alpha = alpha

        self._statistics.increment_visited(NodeTypes.NEGAMAX)

        # --- Null move pruning ---
        # Pass the turn. If the resulting score still causes a beta cutoff, the current
        # position is likely too strong for the opponent - prune the branch.
        if self._searcher_config.enable_null_move_pruning and self._null_move_pruning(
            board, depth, alpha, beta, self._pvs
        ):
            self._statistics.increment_visited(PruningTypes.NULL_MOVE)
            return beta

        # Cache is_check() - used by stalemate detection, check extension,
        # and reverse futility pruning guard.
        in_check = board.is_check()

        # --- Reverse futility pruning ---
        # At shallow depths, if the static eval already exceeds beta by a margin,
        # a full search is very unlikely to drop below beta - prune immediately.
        if (
            self._searcher_config.enable_reverse_futility_pruning
            and self._reverse_futility_pruning(board, depth, beta, in_check)
        ):
            self._statistics.increment_visited(PruningTypes.REVERSE_FUTILITY)
            return beta

        # --- Razoring ---
        # At shallow depths, if the static eval is far below alpha, verify with
        # a quiescence search. If qsearch confirms, return immediately.
        razor_score = self._razoring(board, depth, alpha, in_check, zobrist_state)
        if razor_score is not None:
            return razor_score

        # --- Move ordering ---
        # Good move ordering is essential for PVS - if the first move isn't the best,
        # we'll waste many re-searches in step 3.
        mo_heuristic = self._build_move_order_heuristic(board, depth)
        legal_moves = MoveOrderer.order_moves(mo_heuristic, board.legal_moves)

        # Hash move: move the TT best move to the front so it is searched first.
        # Searching the previously-best move first is the single most effective
        # move-ordering technique - it reliably raises alpha early, causing more
        # beta cutoffs and dramatically shrinking the search tree.
        if tt_best_move is not None:
            try:
                idx = legal_moves.index(tt_best_move)
                legal_moves[0], legal_moves[idx] = legal_moves[idx], legal_moves[0]
            except ValueError:
                pass

        # --- Checkmate / stalemate detection ---
        # If there are no legal moves the loop below will never run, leaving `value`
        # at -inf and causing the engine to mis-score forced-mate positions.
        # - Checkmate: the side to move is in check with no escape -> large loss.
        #   Scaling by `depth` makes the engine prefer faster mates over slower ones.
        # - Stalemate: no legal moves but not in check -> draw (0).
        if not legal_moves:
            return -MATE_SCORE + depth if in_check else 0

        # --- Check extension ---
        # If the side to move is currently in check, search 1 ply deeper at this node.
        # Check positions are tactically critical and typically have very few legal
        # replies, so the extra ply costs little but prevents missing forced mates.
        extension = (
            1 if (self._searcher_config.enable_check_extensions and in_check) else 0
        )

        # Tracks the move that raised value the most; stored to TT for future hash-move ordering.
        best_move_for_tt = None

        # --- Main search loop (PVS logic) ---
        for idx, move in enumerate(legal_moves):
            # Snapshot board state BEFORE pushing, for incremental Zobrist hashing.
            # Use piece_type_at + color_at and compute the Zobrist index directly,
            # avoiding chess.Piece object creation (~600K __init__ calls eliminated).
            if zobrist_state:
                from_pt = board.piece_type_at(move.from_square)
                from_color = board.color_at(move.from_square)
                from_cpt = zobrist_piece_index(from_pt, from_color)
            else:
                from_cpt = -1
            capture = (
                board.is_capture(move)
                if self._searcher_config.enable_futility_pruning or zobrist_state
                else False
            )
            if zobrist_state and capture:
                cap_pt = board.piece_type_at(move.to_square)
                if cap_pt:
                    captured_cpt = zobrist_piece_index(
                        cap_pt, board.color_at(move.to_square)
                    )
                else:
                    captured_cpt = -1  # en passant: captured pawn not on to_square
            else:
                captured_cpt = -1

            self._push(board, move)

            # --- Futility pruning ---
            # Skip quiet moves near the leaves that can't possibly raise alpha.
            if self._searcher_config.enable_futility_pruning and self._futility_pruning(
                board, depth, capture, move, alpha
            ):
                self._pop(board)
                self._statistics.increment_visited(PruningTypes.FUTILITY)
                continue

            # Compute incremental Zobrist hash for the child position.
            child_zobrist_state = (
                self._zobrist_hash.incremental_zobrist_hash(
                    board,
                    move,
                    zobrist_state,
                    from_cpt,
                    captured_cpt,
                )
                if zobrist_state
                else None
            )

            # --- Late Move Reduction (LMR) ---
            # Moves ordered late in the list are statistically unlikely to be best.
            # For quiet moves beyond LMR_FULL_DEPTH_MOVES, search at a reduced depth
            # using a null window first. If that raises alpha, upgrade to full depth.
            # We skip LMR when:
            #   - The move is a capture (tactical, could be a winning exchange)
            #   - The move gives check (gives check to opponent - verify with board.is_check() after push)
            #   - The move is a promotion (potentially very strong)
            #   - We're near the leaves (depth < LMR_MIN_DEPTH) - too shallow to reduce safely
            lmr_reduction = 0
            if (
                self._searcher_config.enable_lmr
                and idx >= LMR_FULL_DEPTH_MOVES
                and depth >= LMR_MIN_DEPTH
                and not capture
                and not board.is_check()  # move gives check after push
                and not move.promotion
            ):
                # Reduction grows with depth and move index (deeper / later = more reduction).
                # Reduction grows with both remaining depth and move index using a
                # logxlog formula (standard in modern engines like Stockfish/Ethereal).
                # Later moves at greater depth are reduced more aggressively.
                lmr_reduction = max(1, int(math.log(depth) * math.log(idx + 1) / 2.0))

            if idx == 0:
                # First move: full-window search at (possibly extended) depth.
                # We assume this is the best move (due to move ordering) and use it
                # to establish the alpha baseline.
                child_value = -self._pvs(
                    board, depth - 1 + extension, -beta, -alpha, child_zobrist_state
                )
            else:
                # Subsequent moves: null-window search, optionally at reduced depth.
                # A null window [-alpha-1, -alpha] can only confirm fail-low (<= alpha)
                # or detect fail-high (> alpha), not the exact score.
                child_value = -self._pvs(
                    board,
                    depth - 1 + extension - lmr_reduction,
                    -alpha - 1,
                    -alpha,
                    child_zobrist_state,
                )
                if lmr_reduction > 0 and child_value > alpha:
                    # LMR failed high: the move looks promising - re-search at full depth
                    # with a null window to confirm before doing an expensive full-window search.
                    child_value = -self._pvs(
                        board,
                        depth - 1 + extension,
                        -alpha - 1,
                        -alpha,
                        child_zobrist_state,
                    )
                if alpha < child_value < beta:
                    # Null window failed high - this move might actually be the best.
                    # Re-search with the full window to get the exact score.
                    child_value = -self._pvs(
                        board, depth - 1 + extension, -beta, -alpha, child_zobrist_state
                    )

            self._pop(board)

            if child_value > value:
                value = child_value
                best_move_for_tt = move
            alpha = max(alpha, value)

            if alpha >= beta:
                # Beta cutoff: opponent won't allow this line.
                # Update move ordering heuristics so this refutation is tried first
                # in sibling nodes of future searches.
                self._statistics.increment_visited(PruningTypes.ALPHA_BETA)
                self._update_killer_moves(move, depth)
                self._update_history_table(move, depth)
                break

        # --- TT store ---
        # Store with the correct bound type so future probes know what the score means.
        if zobrist_state:
            if value >= beta:
                flag = TranspositionTable.LOWER_BOUND
            elif value <= original_alpha:
                flag = TranspositionTable.UPPER_BOUND
            else:
                flag = TranspositionTable.EXACT
            self._transposition_table.store(
                zobrist_state.zobrist_hash, depth, value, flag, best_move_for_tt
            )

        return value

    def _start_search_from_root(
        self,
        board: Board,
        depth: int,
        alpha: float,
        beta: float,
    ) -> Tuple[float, chess.Move]:
        """
        Entry point for PVS: searches the root position and returns (score, best_move).

        Unlike _pvs, this also tracks the best_move, since non-root nodes only need scores.

        :param board: The current chess board position.
        :type board: Board
        :param depth: The search depth for this iteration of iterative deepening.
        :type depth: int
        :param alpha: Lower bound of the search window (typically -inf at root).
        :type alpha: float
        :param beta: Upper bound of the search window (typically +inf at root).
        :type beta: float

        :return: (best_score, best_move) from the root position.
        :rtype: Tuple[float, chess.Move]
        """
        value = -float("inf")
        best_move = chess.Move.null()
        self._statistics.increment_visited(NodeTypes.NEGAMAX)

        # Compute the full Zobrist hash for the root position.
        zobrist_state = (
            self._zobrist_hash.full_zobrist_hash(board)
            if self._searcher_config.enable_transposition_table
            else None
        )
        original_alpha = alpha
        mo_heuristic = self._build_move_order_heuristic(board, depth)
        legal_moves = MoveOrderer.order_moves(mo_heuristic, board.legal_moves)

        # At the root, use the TT best move from the previous ID iteration for
        # ordering. This ensures the hash move is tried first even at depth 1
        # of each new iteration, where no TT probe score can cut off.
        if zobrist_state:
            root_tt_move = self._transposition_table.get_best_move(
                zobrist_state.zobrist_hash
            )
            if root_tt_move is not None:
                try:
                    idx = legal_moves.index(root_tt_move)
                    legal_moves[0], legal_moves[idx] = legal_moves[idx], legal_moves[0]
                except ValueError:
                    pass

        for idx, move in enumerate(legal_moves):
            # Snapshot before push for incremental Zobrist hashing.
            if zobrist_state:
                from_pt = board.piece_type_at(move.from_square)
                from_color = board.color_at(move.from_square)
                from_cpt = zobrist_piece_index(from_pt, from_color)
                if board.is_capture(move):
                    cap_pt = board.piece_type_at(move.to_square)
                    captured_cpt = (
                        zobrist_piece_index(cap_pt, board.color_at(move.to_square))
                        if cap_pt
                        else -1
                    )
                else:
                    captured_cpt = -1
            else:
                from_cpt = -1
                captured_cpt = -1

            self._push(board, move)

            child_zobrist_state = (
                self._zobrist_hash.incremental_zobrist_hash(
                    board,
                    move,
                    zobrist_state,
                    from_cpt,
                    captured_cpt,
                )
                if zobrist_state
                else None
            )

            # Apply PVS: full window for the first move, null window + re-search for rest.
            if idx == 0:
                child_value = -self._pvs(
                    board, depth - 1, -beta, -alpha, child_zobrist_state
                )
            else:
                child_value = -self._pvs(
                    board, depth - 1, -alpha - 1, -alpha, child_zobrist_state
                )
                if alpha < child_value < beta:
                    child_value = -self._pvs(
                        board, depth - 1, -beta, -alpha, child_zobrist_state
                    )

            self._pop(board)

            if value < child_value:
                value = child_value
                best_move = move

            alpha = max(alpha, value)
            if alpha >= beta:
                self._update_killer_moves(move, depth)
                self._update_history_table(move, depth)
                self._statistics.increment_visited(PruningTypes.ALPHA_BETA)
                break

        if zobrist_state:
            if value >= beta:
                flag = TranspositionTable.LOWER_BOUND
            elif value <= original_alpha:
                flag = TranspositionTable.UPPER_BOUND
            else:
                flag = TranspositionTable.EXACT
            self._transposition_table.store(
                zobrist_state.zobrist_hash, depth, value, flag, best_move
            )

        return value, best_move
