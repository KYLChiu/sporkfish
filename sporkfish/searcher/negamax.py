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
from sporkfish.zobrist_hasher import ZobristStateInfo

# A score large enough to represent checkmate but below infinity, so aspiration
# windows and TT comparisons behave correctly. The engine subtracts `depth` from
# this value so it prefers mating in 1 over mating in 3, etc.
MATE_SCORE = 100_000


class NegamaxSp(MiniMaxVariants):
    def __init__(
        self,
        evaluator: Evaluator,
        searcher_config: SearcherConfig = SearcherConfig(),
    ) -> None:
        super().__init__(evaluator, searcher_config)

    def _negamax(
        self,
        board: Board,
        depth: int,
        alpha: float,
        beta: float,
        zobrist_state: Optional[ZobristStateInfo],
    ) -> float:
        """
        Negamax with fail-soft alpha-beta pruning. Called for all non-root nodes.

        Negamax is a variant of minimax that exploits the zero-sum property of chess:
        the score from one player's perspective is the negation of the score from the
        other player's perspective. This allows a single function to handle both sides.

        Alpha-beta pruning cuts branches that cannot possibly affect the final result:
        - alpha: the best score the current player is guaranteed so far (lower bound).
                 Raised whenever a child returns a better score.
        - beta:  the best score the opponent is guaranteed so far (upper bound).
                 If our value exceeds beta, the opponent will avoid this line entirely,
                 so we can stop searching (beta cutoff).

        Fail-soft means we return the actual `value` even if it falls outside [alpha, beta],
        which gives more information for aspiration windows and TT bound types.

        :param board: The current state of the chess board.
        :type board: Board
        :param depth: Remaining plies to search. 0 = leaf, devolves to quiescence.
        :type depth: int
        :param alpha: Lower bound: best score already secured by the current player.
        :type alpha: float
        :param beta: Upper bound: best score already secured by the opponent.
        :type beta: float
        :param zobrist_state: Carries the incremental Zobrist hash and castling/ep info
                              for transposition table lookups. None if TT is disabled.
        :type zobrist_state: Optional[ZobristStateInfo]

        :returns: The evaluation score of the current board position (from current player's POV).
        :rtype: float
        """
        # best score seen so far at this node; starts at -inf (no move seen yet)
        value = -float("inf")

        # --- Base case ---
        # At depth 0 we switch to quiescence search instead of returning a static eval.
        # Quiescence extends the search on captures only, resolving tactical sequences
        # so we don't evaluate a position mid-capture ("horizon effect").
        if depth == 0:
            return self._quiescence(board, 4, alpha, beta, zobrist_state)

        # --- Transposition table (TT) probe ---
        # The TT maps Zobrist hashes → previously computed scores.
        # A hit may let us avoid re-searching this position entirely, or at least
        # tighten the alpha/beta window so we prune more aggressively below.
        # We also extract the stored best move for hash-move ordering.
        tt_best_move = None
        if zobrist_state and (
            tt_entry := self._transposition_table.probe(
                zobrist_state.zobrist_hash, depth
            )
        ):
            # add test
            self._statistics.increment_visited(
                TranspositionTableNodeType.TRANSPOSITITON_TABLE
            )
            # Tuple layout: (depth, score, flag, best_move) — see TranspositionTable constants
            tt_score = tt_entry[TranspositionTable._SCORE]  # type: ignore
            tt_flag = tt_entry[TranspositionTable._FLAG]
            if tt_flag == TranspositionTable.EXACT:
                # Score is reliable within the full window — return immediately.
                return tt_score
            elif tt_flag == TranspositionTable.LOWER_BOUND:
                # Search failed high (beta cutoff occurred). Score is a lower bound.
                # Raise alpha — we know we can do at least this well.
                alpha = max(alpha, tt_score)
            elif tt_flag == TranspositionTable.UPPER_BOUND:
                # Search failed low (never exceeded alpha). Score is an upper bound.
                # Lower beta — the opponent can hold us to at most this.
                beta = min(beta, tt_score)
            # After tightening the window, check if it collapsed (alpha >= beta).
            # If so, the TT score is sufficient — no need to search further.
            if alpha >= beta:
                return tt_score
            # Extract best move for hash-move ordering even when we can't cut off.
            tt_best_move = tt_entry[TranspositionTable._BEST_MOVE]  # type: ignore

        # Capture alpha AFTER TT probe, because the probe may have raised alpha via
        # a LOWER_BOUND hit. original_alpha is used at the end to determine the
        # correct TT flag for this node's result.
        original_alpha = alpha

        self._statistics.increment_visited(NodeTypes.NEGAMAX)

        # --- Null move pruning ---
        # Try passing (making no move). If the resulting position is still so good that
        # beta is exceeded, the current position is likely too good for the opponent to
        # allow — prune this branch. Disabled in zugzwang-prone endgames.
        if self._searcher_config.enable_null_move_pruning and self._null_move_pruning(
            board, depth, alpha, beta, self._negamax
        ):
            # add test
            self._statistics.increment_visited(PruningTypes.NULL_MOVE)
            return beta

        # --- Move ordering ---
        # Searching the best moves first dramatically improves pruning efficiency.
        # A good move found early raises alpha quickly, causing more beta cutoffs later.
        mo_heuristic = self._build_move_order_heuristic(board, depth)
        legal_moves = MoveOrderer.order_moves(mo_heuristic, board.legal_moves)
        # Hash move: prepend the TT best move so it is always searched first.
        if tt_best_move is not None and tt_best_move in legal_moves:
            legal_moves = [tt_best_move] + [m for m in legal_moves if m != tt_best_move]

        # --- Checkmate / stalemate detection ---
        # If there are no legal moves the loop below will never run, leaving `value`
        # at -inf and causing the engine to mis-score forced-mate positions.
        # - Checkmate: the side to move is in check with no escape → large loss.
        #   Scaling by `depth` makes the engine prefer faster mates over slower ones.
        # - Stalemate: no legal moves but not in check → draw (0).
        if not legal_moves:
            return -MATE_SCORE + depth if board.is_check() else 0

        # --- Check extension ---
        # If the side to move is currently in check, search 1 ply deeper at this node.
        in_check = board.is_check()
        extension = (
            1 if (self._searcher_config.enable_check_extensions and in_check) else 0
        )

        # Tracks the move that raised value the most; stored to TT for hash-move ordering.
        best_move_for_tt = None

        # --- Main search loop ---
        for move in legal_moves:
            # Snapshot board state BEFORE pushing the move.
            # The TT hash is updated incrementally: we need the piece that was on
            # from_square (the moving piece) and any piece on to_square (the capture).
            previous_piece_from_square = (
                board.piece_at(move.from_square) if zobrist_state else None
            )
            capture = (
                board.is_capture(move)
                if self._searcher_config.enable_futility_pruning or zobrist_state
                else False
            )
            captured_piece = (
                board.piece_at(move.to_square) if zobrist_state and capture else None
            )

            board.push(move)

            # --- Futility pruning ---
            # Near the leaves (depth 1-2), if a quiet move's static eval is so far
            # below alpha that even a large material swing can't recover, skip it.
            if self._searcher_config.enable_futility_pruning and self._futility_pruning(
                board, depth, capture, move, alpha
            ):
                board.pop()
                # add test
                self._statistics.increment_visited(PruningTypes.FUTILITY)
                continue

            # Compute the child's Zobrist hash incrementally (XOR out moved/captured
            # pieces, XOR in new piece positions, update castling/ep rights).
            child_zobrist_state = (
                self._zobrist_hash.incremental_zobrist_hash(
                    board,
                    move,
                    zobrist_state,
                    previous_piece_from_square,  # type: ignore
                    captured_piece,
                )
                if zobrist_state
                else None
            )

            # Recurse. Negate child's score because the child evaluates from the
            # opponent's perspective. Flip the window: our beta becomes child's alpha,
            # and our alpha becomes child's beta (both negated).
            child_value = -self._negamax(
                board, depth - 1 + extension, -beta, -alpha, child_zobrist_state
            )

            board.pop()

            if child_value > value:
                value = child_value
                best_move_for_tt = move
            # Raise alpha if we found a better move for the current player.
            alpha = max(alpha, value)

            if alpha >= beta:
                # Beta cutoff: this position is too good — the opponent won't allow it.
                # Record the move in killer/history tables to prioritise it in sibling
                # nodes (where the same refutation likely applies).
                self._statistics.increment_visited(PruningTypes.ALPHA_BETA)
                self._update_killer_moves(move, depth)
                self._update_history_table(move, depth)
                break

        # --- TT store ---
        # Determine what kind of bound the returned `value` represents:
        #   LOWER_BOUND: we hit beta — value is a lower bound (could be higher).
        #   UPPER_BOUND: value never exceeded original_alpha — it's an upper bound.
        #   EXACT:       value is within [original_alpha, beta] — it's exact.
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
        Entry point for negamax: searches the root position and returns (score, best_move).

        Unlike _negamax, this also tracks the best move, since non-root nodes only need
        to return scores (the move is implicit from the caller's loop).

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

        # Compute the full Zobrist hash for the root position (TT enabled).
        # Child nodes update this hash incrementally.
        zobrist_state = (
            self._zobrist_hash.full_zobrist_hash(board)
            if self._searcher_config.enable_transposition_table
            else None
        )
        original_alpha = alpha
        mo_heuristic = self._build_move_order_heuristic(board, depth)
        legal_moves = MoveOrderer.order_moves(mo_heuristic, board.legal_moves)
        # At the root, use the TT best move from the previous ID iteration for ordering.
        if zobrist_state:
            root_tt_move = self._transposition_table.get_best_move(
                zobrist_state.zobrist_hash
            )
            if root_tt_move is not None and root_tt_move in legal_moves:
                legal_moves = [root_tt_move] + [
                    m for m in legal_moves if m != root_tt_move
                ]

        for move in legal_moves:
            # Snapshot the moving piece and any captured piece before pushing,
            # so the incremental Zobrist hash can XOR them in/out correctly.
            previous_piece_from_square = (
                board.piece_at(move.from_square) if zobrist_state else None
            )
            captured_piece = (
                board.piece_at(move.to_square)
                if zobrist_state and board.is_capture(move)
                else None
            )

            board.push(move)

            # Update the Zobrist hash incrementally for the child position.
            child_zobrist_state = (
                self._zobrist_hash.incremental_zobrist_hash(
                    board,
                    move,
                    zobrist_state,
                    previous_piece_from_square,  # type: ignore
                    captured_piece,
                )
                if zobrist_state
                else None
            )
            # Recurse with negated window (child sees the opponent's perspective).
            child_value = -self._negamax(
                board, depth - 1, -beta, -alpha, child_zobrist_state
            )

            board.pop()

            if value < child_value:
                value = child_value
                best_move = move

            alpha = max(alpha, value)
            if alpha >= beta:
                self._update_killer_moves(move, depth)
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

    def search(
        self, board: Board, timeout: Optional[float] = None
    ) -> Tuple[float, chess.Move]:
        """
        Finds the best move (and associated score) via negamax and iterative deepening.

        :param board: The current chess board position.
        :type board: Board
        :param timeout: Time in seconds until we stop the search, returning the best depth if we timeout.
        :type timeout: Optional[float]

        :return: The best score and associated move based on the search.
        :rtype: Tuple[float, Move]
        """
        score, move = self._iterative_deepening_search(board, timeout)
        return score, move
