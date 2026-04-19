import copy
import logging
import time
from abc import ABC, abstractmethod
from typing import Callable, Optional, Tuple

import chess
import stopit

from sporkfish.board.board import Board
from sporkfish.evaluator.evaluator import Evaluator
from sporkfish.searcher.move_ordering.composite_heuristic import CompositeHeuristic
from sporkfish.searcher.move_ordering.history_heuristic import HistoryHeuristic
from sporkfish.searcher.move_ordering.killer_move_heuristic import KillerMoveHeuristic
from sporkfish.searcher.move_ordering.move_order_config import MoveOrderMode
from sporkfish.searcher.move_ordering.move_order_heuristic import MoveOrderHeuristic
from sporkfish.searcher.move_ordering.move_orderer import MoveOrderer
from sporkfish.searcher.move_ordering.mvv_lva_heuristic import MvvLvaHeuristic
from sporkfish.searcher.searcher import Searcher
from sporkfish.searcher.searcher_config import SearcherConfig
from sporkfish.statistics import AspirationTypes, NodeTypes, PruningTypes
from sporkfish.statistics import TranspositionTable as TranspositionTableNodeType
from sporkfish.transposition_table import TranspositionTable
from sporkfish.zobrist_hasher import (
    ZobristHasher,
    ZobristStateInfo,
    zobrist_piece_index,
)


class MiniMaxVariants(Searcher, ABC):
    """
    Abstract base class for minimax like searchers
    """

    @abstractmethod
    def _start_search_from_root(
        self, board_to_search: Board, depth: int, alpha: float, beta: float
    ) -> Tuple[float, chess.Move]:
        """
        Abstract method to start the search from the root of the game tree.

        :param board_to_search: The current state of the chess board to search.
        :type board_to_search: Board
        :param depth: The depth of the search.
        :type depth: int
        :param alpha: The lower bound of the search window.
        :type alpha: float
        :param beta: The upper bound of the search window.
        :type beta: float

        :return: A tuple containing the evaluation score of the best move found
                 and the corresponding move itself.
        :rtype: Tuple[float, chess.Move]
        """
        pass

    def __init__(
        self,
        evaluator: Evaluator,
        searcher_config: SearcherConfig = SearcherConfig(),
    ) -> None:
        super().__init__(searcher_config)

        if self._searcher_config.enable_transposition_table:
            self._zobrist_hash = ZobristHasher()
            self._transposition_table = TranspositionTable(self._dict)
            logging.info("Enabled transposition table in search.")
        else:
            logging.info("Disabled transposition table in search.")

        self._evaluator = evaluator
        self._max_depth = searcher_config.max_depth

        # Killer move table - storing quiet beta-cut off moves
        self._killer_moves = (
            [[chess.Move.null(), chess.Move.null()] for _ in range(self._max_depth + 1)]
            if self._searcher_config.move_order_config.move_order_mode
            == MoveOrderMode.KILLER_MOVE
            or self._searcher_config.move_order_config.move_order_mode
            == MoveOrderMode.COMPOSITE
            else None
        )

        self._history_table = (
            dict()  # type: ignore
            if self._searcher_config.move_order_config.move_order_mode
            == MoveOrderMode.HISTORY
            or self._searcher_config.move_order_config.move_order_mode
            == MoveOrderMode.COMPOSITE
            else None
        )

        self._counter_move_table = (
            dict() if self._searcher_config.enable_counter_move_heuristic else None
        )

        # Cache pawn value to avoid repeated dict lookups in hot paths.
        self._pawn_value = evaluator.piece_values()[chess.PAWN]
        self._pawn_value_half = self._pawn_value // 2

    @property
    def evaluator(self) -> Evaluator:
        return self._evaluator

    def _push(self, board: Board, move: chess.Move) -> None:
        """Notify the evaluator then apply the move."""
        self._evaluator.on_push(board, move)
        board.push(move)

    def _pop(self, board: Board) -> None:
        """Undo the move then notify the evaluator."""
        board.pop()
        self._evaluator.on_pop()

    def _build_move_order_heuristic(
        self, board: Board, depth: int
    ) -> MoveOrderHeuristic:
        """
        Build and return an instance of MoveOrderHeuristic based on the specified order type.

        :param board: The current state of the chess board.
        :type board: Board
        :param depth: The depth of the search.
        :type depth: int

        :return: An instance of MoveOrderHeuristic.
        :rtype: MoveOrderHeuristic

        :raises TypeError: If the specified order type is not supported.
        """
        order_type = self._searcher_config.move_order_config.move_order_mode
        if order_type is MoveOrderMode.MVV_LVA:
            return MvvLvaHeuristic(board)
        elif order_type is MoveOrderMode.KILLER_MOVE:
            return KillerMoveHeuristic(board, self._killer_moves, depth)  # type: ignore
        elif order_type is MoveOrderMode.HISTORY:
            return HistoryHeuristic(board, self._history_table)  # type: ignore
        elif (
            order_type is MoveOrderMode.COMPOSITE
            and self._searcher_config.enable_counter_move_heuristic
            and self._counter_move_table is not None
        ):
            return CompositeHeuristic(
                board,
                self._killer_moves,  # type: ignore
                self._history_table,  # type: ignore
                self._counter_move_table,
                depth,
                self._searcher_config.move_order_config,
            )
        elif order_type is MoveOrderMode.COMPOSITE:
            return CompositeHeuristic(
                board,
                self._killer_moves,  # type: ignore
                self._history_table,  # type: ignore
                None,
                depth,
                self._searcher_config.move_order_config,
            )
        else:
            raise TypeError(
                f"MoveOrderingHeuristic does not support the creation of MoveOrdering type: \
                {type(order_type).__name__}."
            )

    def _update_killer_moves(
        self, move: chess.Move, depth: int, capture: bool = False
    ) -> None:
        """
        Updates the killer move table.
        To be used inside a beta cutoff.

        :param move: The beta cutoff move.
        :type move: chess.Move
        :param depth: The depth of the search.
        :type depth: int
        :param capture: Whether the move is a capture. Captures are skipped because
                        MVV-LVA already orders them; polluting killers with captures
                        reduces the table's effectiveness for quiet-move ordering.
        :type capture: bool
        """
        # Only store quiet (non-capture) moves; captures are handled by MVV-LVA ordering.
        if self._killer_moves and not capture:
            self._killer_moves[depth].pop()
            self._killer_moves[depth].insert(0, move)

    def _update_history_table(self, move: chess.Move, depth: int) -> None:
        """
        Update the history table by incrementing the score of a move. This should
        be called when a move causes an alpha-beta cutoff.

        :param move: The move that caused an alpha-beta cutoff.
        :type move: chess.Move
        :param depth: The depth at which the move caused the cutoff
        :type depth: int
        """
        ply = self._max_depth - depth
        increment = ply * ply

        if self._history_table:
            # Increment score for moves that cause cutoff
            if move in self._history_table:
                self._history_table[move] += increment

            # Initialize score for new moves
            else:
                self._history_table[move] = increment

    def _decay_history_table(self) -> None:
        """
        Decay history scores between iterative-deepening iterations.

        Without decay, early-iteration cutoffs can dominate ordering even when
        deeper searches disagree. A mild decay keeps useful signal while letting
        newer evidence take precedence.
        """
        if not self._history_table:
            return

        # Keep integer arithmetic and prune dead entries to avoid unbounded growth.
        stale_moves = []
        for move, score in self._history_table.items():
            decayed = (score * 9) // 10
            if decayed > 0:
                self._history_table[move] = decayed
            else:
                stale_moves.append(move)

        for move in stale_moves:
            del self._history_table[move]

    def _update_counter_move_table(
        self, board: Board, move: chess.Move, capture: bool = False
    ) -> None:
        if (
            not self._searcher_config.enable_counter_move_heuristic
            or self._counter_move_table is None
            or capture
            or not board.move_stack
        ):
            return

        self._counter_move_table[board.move_stack[-1]] = move

    def _aspiration_windows_search(
        self,
        board_to_search: Board,
        depth: int,
        prev_score: float,
    ) -> Tuple[float, chess.Move]:
        """
        Perform an aspiration windows search.

        Aspiration windows are used to optimize the search process by narrowing the search window based on
        previous search results.

        :param board_to_search: The chess board to search.
        :type board_to_search: Board
        :param depth: The search depth.
        :type depth: int
        :param prev_score: The score of the previous depth in a iterative deepening search.
        :type prev_score: float

        :return: A tuple containing the score and the best move found during the search.
        :rtype: Tuple[float, chess.Move]
        """
        if not (self._searcher_config.enable_aspiration_windows and depth > 1):
            return self._start_search_from_root(
                board_to_search, depth, -float("inf"), float("inf")
            )

        # Start with a moderate window around the previous iteration's score and
        # progressively widen on fail-low / fail-high. This avoids the expensive
        # immediate fallback to a full-width re-search in the common near-miss case.
        window_size = self._pawn_value
        alpha = prev_score - window_size
        beta = prev_score + window_size

        # Keep retries bounded so pathological positions still terminate quickly.
        for _ in range(3):
            self._statistics.increment_visited(AspirationTypes.ATTEMPT)
            score, move = self._start_search_from_root(
                board_to_search, depth, alpha, beta
            )
            if score <= alpha:
                self._statistics.increment_visited(AspirationTypes.FAIL_LOW)
                alpha -= window_size
                window_size *= 2
                continue
            if score >= beta:
                self._statistics.increment_visited(AspirationTypes.FAIL_HIGH)
                beta += window_size
                window_size *= 2
                continue
            self._statistics.increment_visited(AspirationTypes.IN_WINDOW)
            return score, move

        logging.info(
            "Search score outside widened aspiration bounds, doing a full search."
        )
        self._statistics.increment_visited(AspirationTypes.FULL_FALLBACK)
        return self._start_search_from_root(
            board_to_search, depth, -float("inf"), float("inf")
        )

    def _quiescence(
        self,
        board: Board,
        depth: int,
        alpha: float,
        beta: float,
        zobrist_state: Optional[ZobristStateInfo],
    ) -> float:
        """
        Quiescence search: resolves tactical sequences before applying the static evaluator.

        The *horizon effect* arises when the main search stops at a fixed depth mid-capture:
        e.g. we see a queen capture but don't see the recapture on the next ply, making the
        position look falsely great. Quiescence search fixes this by extending the search
        only on captures (and checks in some engines) until the position is "quiet" --
        i.e. no more captures are available - before calling the static evaluator.

        *Stand-pat pruning*: Before searching captures, we compute the static eval
        (`stand_pat`). If even without making any capture we already beat beta, we prune
        immediately (the opponent wouldn't allow this position). If stand_pat > alpha,
        we raise alpha - we can always "stand pat" and accept the current score.

        :param board: The current state of the chess board.
        :type board: Board
        :param depth: Maximum recursion depth for quiescence (limits capture chains).
                      We cap at 4 to prevent rare infinite loops on mutually recapturable positions.
        :type depth: int
        :param alpha: Lower bound: best score secured by the current player.
        :type alpha: float
        :param beta: Upper bound: best score secured by the opponent.
        :type beta: float
        :param zobrist_state: Incremental Zobrist hash state for TT lookups. None if TT is disabled.
        :type zobrist_state: Optional[ZobristStateInfo]

        :return: The evaluated score after resolving all captures (from current player's POV).
        :rtype: float
        """

        # --- Transposition table probe ---
        # Quiescence results are cached at depth=0 (they represent a "quiet" eval).
        # The same bound-type logic as the main search applies here.
        if zobrist_state and (
            tt_entry := self._transposition_table.probe(zobrist_state.zobrist_hash, 0)
        ):
            self._statistics.increment_visited(
                TranspositionTableNodeType.TRANSPOSITITON_TABLE
            )

            # Tuple layout: (depth, score, flag) - see TranspositionTable._DEPTH/SCORE/FLAG
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

        # Capture alpha AFTER TT probe (which may have raised it).
        original_alpha = alpha

        self._statistics.increment_visited(NodeTypes.QUIESCENSE)

        # --- Stand-pat score ---
        # Static evaluation of the current position without making any move.
        # The current player can always "do nothing" - so this is a guaranteed lower bound.
        stand_pat = self._evaluator.evaluate(board)

        # Hit the depth cap: return static eval without searching captures.
        if depth == 0:
            return stand_pat

        # --- Stand-pat pruning ---
        # If stand_pat already beats beta, the opponent won't allow this line.
        if stand_pat >= beta:
            self._statistics.increment_visited(PruningTypes.ALPHA_BETA)
            return beta

        # Raise alpha if the current position (without any capture) is already
        # better than what we've assumed as our lower bound.
        if alpha < stand_pat:
            alpha = stand_pat

        # --- Search captures only ---
        # Filter legal moves to captures and order them (e.g. MVV-LVA: capture large
        # pieces with small pieces first, as those are most likely to be good).
        # generate_legal_captures() is faster than filtering board.legal_moves because
        # python-chess generates captures directly from bitboards, skipping quiet moves entirely.
        mo_heuristic = self._build_move_order_heuristic(board, depth)
        legal_moves = MoveOrderer.order_moves(
            mo_heuristic, board.generate_legal_captures()
        )

        for move in legal_moves:
            # --- Delta pruning ---
            # If even capturing the most valuable piece on the board can't bring the
            # score close to alpha, skip the move. Avoids searching hopeless captures.
            if self._searcher_config.enable_delta_pruning and self._delta_pruning(
                board, move, stand_pat, alpha
            ):
                self._statistics.increment_visited(PruningTypes.DELTA)
                continue

            # Snapshot the moving piece and captured piece BEFORE pushing the move,
            # so the incremental Zobrist hash can XOR them out and in correctly.
            # Uses piece_type_at + color_at to avoid chess.Piece object creation.
            if zobrist_state:
                from_pt = board.piece_type_at(move.from_square)
                from_color = board.color_at(move.from_square)
                from_cpt = zobrist_piece_index(from_pt, from_color)
                # In quiescence we only search captures, so a captured piece usually exists.
                cap_pt = board.piece_type_at(move.to_square)
                captured_cpt = (
                    zobrist_piece_index(cap_pt, board.color_at(move.to_square))
                    if cap_pt
                    else -1
                )
            else:
                from_cpt = -1
                captured_cpt = -1

            self._push(board, move)

            # Compute the child's incremental Zobrist hash.
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

            # Recurse into the child. Negate because child evaluates from opponent's POV.
            score = -self._quiescence(
                board, depth - 1, -beta, -alpha, child_zobrist_state
            )
            self._pop(board)

            if score >= beta:
                # Beta cutoff: store as LOWER_BOUND (actual value may be higher).
                if zobrist_state:
                    self._transposition_table.store(
                        zobrist_state.zobrist_hash,
                        0,
                        score,
                        TranspositionTable.LOWER_BOUND,
                    )
                return beta

            if score > alpha:
                alpha = score

        # --- TT store ---
        # If alpha was never raised above original_alpha, every move failed low:
        # the score is an upper bound. Otherwise it's exact (best capture was found).
        if zobrist_state:
            if alpha <= original_alpha:
                flag = TranspositionTable.UPPER_BOUND
            else:
                flag = TranspositionTable.EXACT
            self._transposition_table.store(zobrist_state.zobrist_hash, 0, alpha, flag)

        return alpha

    def _null_move_pruning(
        self, board: Board, depth: int, alpha: float, beta: float, search_func: Callable
    ) -> bool:
        """
        Implements null move pruning, a technique to reduce the search space by attempting a 'null move'.
        It evaluates whether skipping a move (null move) would still allow achieving a beta cutoff,
        thereby avoiding unnecessary exploration of certain branches of the game tree.

        :param board: The current state of the chess board.
        :type board: chess.Board
        :param depth: The current depth in the search tree.
        :type depth: int
        :param alpha: The current best score for the maximizing player.
        :type alpha: float
        :param beta: The current best score for the minimizing player.
        :type beta: float
        :param search_func: The search function to be used (e.g. negamax, PVS).
        :type search_func: Callable

        :return: True if the null move leads to a beta cutoff, indicating a possible pruning opportunity.
        :rtype: bool
        """

        # TODO: add zugzwang check
        # Adaptive R: use R=4 at deeper nodes where the extra reduction saves
        # significantly more work, and R=3 at shallower nodes for safety.
        depth_reduction_factor = 4 if depth >= 6 else 3
        in_check = board.is_check()
        if depth >= depth_reduction_factor and not in_check:
            null_move_depth = depth - depth_reduction_factor
            self._push(board, chess.Move.null())

            # TODO: check if too expensive to calculate Zobrist state here
            value = -search_func(board, null_move_depth, -beta, -alpha, None)
            self._pop(board)
            if value >= beta:
                return True
        return False

    def _futility_pruning(
        self,
        board: Board,
        depth: int,
        was_capture: bool,
        move: chess.Move,
        alpha: float,
    ) -> bool:
        """
        Implements futility pruning.

        If the evaluation of the current position, when extended by a margin, falls below the minimum score
        we can guarantee, then it's not worthwhile to continue the search.
        However, it's important to note that we still need to consider tactical possibilities due to captures,
        promotions, and checks.

        :param board: The current board state.
        :type board: Board
        :param depth: The current depth in the search tree.
        :type depth: int
        :param was_capture: Indicates if the previous move was a capture.
        :type was_capture: bool
        :param move: The move that was made.
        :type move: chess.Move
        :param alpha: The current best score for the maximizing player.
        :type alpha: float

        :return: True if the position can be pruned due to futility margin checks, False otherwise.
        :rtype: bool
        """
        if (
            depth <= 3
            and not was_capture
            and not board.is_check()
            and not move.promotion
        ):
            # TODO: consider using different futility margins
            # Half a pawn margin is very aggressive
            if self._evaluator.evaluate(board) + depth * self._pawn_value_half <= alpha:
                return True
        return False

    def _reverse_futility_pruning(
        self,
        board: Board,
        depth: int,
        beta: float,
        in_check: bool,
    ) -> bool:
        """
        Reverse futility pruning (static null-move pruning).

        At shallow depths, if the static eval exceeds beta by a depth-scaled margin,
        the position is so good that a full search is very unlikely to drop below beta.
        Prune immediately without any recursive search call.

        Disabled when the side to move is in check (eval is unreliable there).

        :param board: The current board state.
        :param depth: Remaining search depth.
        :param beta: The upper bound of the search window.
        :param in_check: Whether the side to move is in check.
        :return: True if the position should be pruned.
        """
        rfp_max_depth = 3
        if depth >= 2 and depth <= rfp_max_depth and not in_check:
            static_eval = self._evaluator.evaluate(board)
            margin = depth * self._pawn_value
            if self._searcher_config.enable_conservative_rfp_margin:
                margin += self._pawn_value_half
            if static_eval - margin >= beta:
                return True
        return False

    def _razoring(
        self,
        board: Board,
        depth: int,
        alpha: float,
        in_check: bool,
        zobrist_state,
    ) -> Optional[float]:
        """
        Razoring: at shallow depths, if static eval + margin is below alpha,
        drop directly into quiescence search. If qsearch still fails low,
        return the qsearch score immediately. Otherwise return None to
        continue with the full search.

        :param board: The current board state.
        :param depth: Remaining search depth.
        :param alpha: The lower bound of the search window.
        :param in_check: Whether the side to move is in check.
        :param zobrist_state: Zobrist hash state for TT (passed to quiescence).
        :return: The qsearch score if razoring succeeds, None otherwise.
        """
        razor_max_depth = 2
        if depth <= razor_max_depth and not in_check:
            static_eval = self._evaluator.evaluate(board)
            margin = depth * self._pawn_value
            if static_eval + margin < alpha:
                q_score = self._quiescence(board, 4, alpha, alpha + 1, zobrist_state)
                if q_score < alpha:
                    return q_score
        return None

    def _delta_pruning(
        self, board: Board, move: chess.Move, stand_pat: float, alpha: float
    ) -> bool:
        """
        Implementes delta pruning.

        Rationale: If our position is such that the evaluation value plus the captured piece value plus a safety margin (delta)
                    doesn't exceed what we can already guarantee, then there is no point to continue the search for this branch.
                    The safety margin allows for searching for sacrifices; for example, taking a pawn down a rook usually will not help,
                    but taking a bishop down a rook may help. The delta value should be tuned based on the piece values of the evaluator.

        TODO: Consider adding a check for the late endgame - it should not be enabled there because transitions into won endgames made at the
                expense of some material will no longer be considered. However, we might remedy this directly with endgame tablebases.

        :param board: The current board state.
        :type board: Board
        :param move: The move to be considered.
        :type move: chess.Move
        :param stand_pat: The stand pat score for the current position.
        :type stand_pat: float
        :param alpha: The alpha value representing the minimum score needed.
        :type alpha: float
        :return: True if the position can be pruned due to delta margin checks, False otherwise.
        :rtype: bool
        """

        # Assumes the input move is already a capturing move
        # This is valid when called in quiescence search
        captured_piece = (
            chess.PAWN
            if board.is_en_passant(move)
            else board.piece_type_at(move.to_square)
        )
        return (
            True
            if stand_pat
            + self.evaluator.piece_values()[captured_piece]
            + self.evaluator.delta()
            < alpha
            else False
        )

    @stopit.threading_timeoutable(default=(float("-inf"), chess.Move.null(), 0.0, 1))
    def _timeoutable_search(
        self,
        board_to_search: Board,
        depth: int,
        prev_score: float,
    ) -> Tuple[float, chess.Move, float, int]:
        """
        Creates a search function wrapper with timeout argument, in seconds.
        If search time exceeds the timeout argument, this function immediately returns.

        :param board_to_search: The chess board to search.
        :type board_to_search: Board
        :param depth: The depth of the search.
        :type depth: int
        :param prev_score: The previous score from a shallower search.
        :type prev_score: float

        :return: A tuple containing the following:
                 - The score of the best move found during the search.
                 - The best move found.
                 - The elapsed time of the search.
                 - A flag indicating whether the search was terminated due to a timeout (1 for timeout, 0 otherwise).
        :rtype: tuple[float, chess.Move, float, int]

        :raises Exception: If an unexpected error occurs during the search.
        """
        try:
            start_time = time.time()
            score, move = self._aspiration_windows_search(
                board_to_search, depth, prev_score
            )
            elapsed = time.time() - start_time
            self._log_info(elapsed, score, move, depth)
            return score, move, elapsed, 0
        except stopit.utils.TimeoutException:
            return float("-inf"), chess.Move.null(), 0.0, 1
        except Exception:
            raise

    def _iterative_deepening_search(
        self, board: Board, timeout: Optional[float]
    ) -> Tuple[float, chess.Move]:
        """
        Conduct an iterative deepening search on the given chess board.

        This method conducts a fixed-depth search for depths ranging from 1 to the maximum depth specified in the configuration.
        It enables the transposition table (cache) to be easily utilized.
        If time constraints prevent a complete search, the function can return the best move found up to the previous depth.
        It facilitates the use of aspiration windows, as implemented in the _aspiration_windows_search function.

        :param board: The chess board to search.
        :type board: Board
        :param timeout: Optional timeout for the search operation, in seconds.
                        If specified, the search will stop after the timeout has elapsed.
                        If None, the search will continue until the maximum depth is reached.
        :type timeout: Optional[float]

        :return: A tuple containing the score of the best move found during the search
                 and the corresponding best move.
        :rtype: Tuple[float, chess.Move]
        """
        score = -float("inf")
        move = chess.Move.null()

        # Deep-copy the board once before the ID loop. Each depth iteration
        # reuses the same copy - push/pop guarantees the board is restored to
        # the root position at the end of every search, so re-copying per depth
        # is unnecessary and was paying deepcopy cost O(max_depth) times.
        search_board = copy.deepcopy(board)
        self._evaluator.init_from_board(search_board)
        time_left = timeout

        for depth in range(1, self._max_depth + 1):
            self._statistics.reset_visited()
            # Allow newer cutoff evidence to outweigh stale history from shallow depths.
            self._decay_history_table()

            # When timed, pass the remaining budget into each deeper iteration.
            if time_left is not None and time_left <= 0:
                break

            new_score, new_move, elapsed, error_code = self._timeoutable_search(
                timeout=time_left,
                board_to_search=search_board,
                depth=depth,
                prev_score=score,
            )

            # Timed out, return best move from previous depth.
            if error_code:
                timeout_display = time_left if time_left is not None else 0.0
                logging.warning(
                    (
                        f"Search for position {board.fen()}"
                        f"timed out after {timeout_display:.1f} seconds, "
                        f"returning best move from depth {depth - 1}."
                    )
                )
                break

            # Else move onto next depth, unless we have no more time already.
            else:
                score, move = new_score, new_move
                if time_left is not None:
                    time_left -= elapsed
                    if time_left <= 0:
                        break

        logging.info(f"End search for FEN {board.fen()}.")
        return score, move

    def search(
        self, board: Board, timeout: Optional[float] = None
    ) -> Tuple[float, chess.Move]:
        """
        Finds the best move (and associated score) via iterative deepening.

        :param board: The current chess board position.
        :type board: Board
        :param timeout: Time in seconds until we stop the search, returning the best
                        result from the deepest completed depth.
        :type timeout: Optional[float]

        :return: The best score and associated move based on the search.
        :rtype: Tuple[float, chess.Move]
        """
        score, move = self._iterative_deepening_search(board, timeout)
        return score, move
