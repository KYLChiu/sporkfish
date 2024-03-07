import copy
import logging
import time
from abc import ABC, abstractmethod
from typing import Optional, Tuple

import chess
import stopit


from ..board.board import Board
from ..evaluator import Evaluator
from ..transposition_table import TranspositionTable
from ..zobrist_hasher import ZobristHasher, ZobristStateInfo
from .move_ordering.composite_heuristic import CompositeHeuristic
from .move_ordering.killer_move_heuristic import KillerMoveHeuristic
from .move_ordering.move_order_heuristic import MoveOrderHeuristic
from .move_ordering.move_order_config import MoveOrderMode
from .move_ordering.move_orderer import MoveOrderer
from .move_ordering.mvv_lva_heuristic import MvvLvaHeuristic
from .searcher import Searcher
from .searcher_config import SearcherConfig


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
        :type board_to_search: chess.Board
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

        # Killer move table - storing quiet beta-cut off moves
        self._killer_moves = (
            [
                [chess.Move.null(), chess.Move.null()]
                for _ in range(self._searcher_config.max_depth + 1)
            ]
            if self._searcher_config.move_order_config.move_order_mode
            == MoveOrderMode.KILLER_MOVE
            or self._searcher_config.move_order_config.move_order_mode
            == MoveOrderMode.COMPOSITE
            else None
        )

    @property
    def evaluator(self) -> Evaluator:
        return self._evaluator

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
        elif order_type is MoveOrderMode.COMPOSITE:
            return CompositeHeuristic(
                board,
                self._killer_moves,  # type: ignore
                depth,
                self._searcher_config.move_order_config,
            )
        else:
            raise TypeError(
                f"MoveOrderingHeuristic does not support the creation of MoveOrdering type: \
                {type(order_type).__name__}."
            )

    def _update_killer_moves(self, move: chess.Move, depth: int) -> None:
        """
        Updates the killer move table.
        To be used inside a beta cutoff.

        :param move: The beta cutoff move.
        :type move: chess.Move
        :param depth: The depth of the search.
        :type depth: int

        """
        # TODO: do we need to check if captures here too?
        if self._killer_moves:
            self._killer_moves[depth].pop()
            self._killer_moves[depth].insert(0, move)

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
        if self._searcher_config.enable_aspiration_windows and depth > 1:
            # We leave configuration for window_size to another PR
            window_size = self.evaluator.MG_PIECE_VALUES[chess.PAWN] // 2
            alpha = prev_score - window_size
            beta = prev_score + window_size
            score, move = self._start_search_from_root(
                board_to_search, depth, alpha, beta
            )
            if score <= alpha or score >= beta:
                logging.info(
                    "Search score outside aspiration window bounds, doing a full search."
                )
                score, move = self._start_search_from_root(
                    board_to_search, depth, -float("inf"), float("inf")
                )
        else:
            score, move = self._start_search_from_root(
                board_to_search, depth, -float("inf"), float("inf")
            )
        return score, move

    def _quiescence_search(
        self,
        board: Board,
        depth: int,
        alpha: float,
        beta: float,
        zobrist_state: Optional[ZobristStateInfo],
    ) -> float:
        """
        Perform a quiescence search to help alleviate the horizon effect and improve checking of tactical possibilities.

        Quiescence search is a variation of the standard search algorithm used in chess engines.
        It is specifically designed to handle positions where the board state is highly dynamic, such as positions
        with captures, checks, or threats. In such positions, the standard evaluation function may not accurately
        reflect the true value of the position, leading to the horizon effect, where the search terminates prematurely
        due to missing important tactical moves.

        :param board: The current state of the chess board.
        :type board: chess.Board
        :param depth: The maximum recursion limit.
        :type depth: int
        :param alpha: The lower bound of the search window.
        :type alpha: float
        :param beta: The upper bound of the search window.
        :type beta: float

        :return: The evaluated score after quiescence search.
        :rtype: float
        """

        # Probe the transposition table for an existing entry
        # We treat all cases as depth 0, so essentially as an static evaluation
        if zobrist_state and (
            tt_entry := self._transposition_table.probe(zobrist_state.zobrist_hash, 0)
        ):
            return tt_entry["score"]  # type: ignore

        self._statistics.increment()

        stand_pat = self._evaluator.evaluate(board)

        if depth == 0:
            return stand_pat

        if stand_pat >= beta:
            return beta

        if alpha < stand_pat:
            alpha = stand_pat

        mo_heuristic = self._build_move_order_heuristic(board, depth)
        legal_moves = MoveOrderer.order_moves(
            mo_heuristic, (move for move in board.legal_moves if board.is_capture(move))
        )

        for move in legal_moves:
            if self._searcher_config.enable_delta_pruning and self._delta_pruning(
                board, move, stand_pat, alpha
            ):
                continue

            # Get the piece from the originating square and the captured piece
            # Existence of captured piece is guaranteed in quiescence search
            previous_piece_from_square = (
                board.piece_at(move.from_square) if zobrist_state else None
            )
            captured_piece = board.piece_at(move.to_square) if zobrist_state else None

            board.push(move)

            # Update the Zobrist hash
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
            score = -self._quiescence_search(
                board, depth - 1, -beta, -alpha, child_zobrist_state
            )
            board.pop()

            if score >= beta:
                return beta

            if score > alpha:
                alpha = score

            if zobrist_state:
                self._transposition_table.store(zobrist_state.zobrist_hash, 0, score)

        return alpha

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
        :type board: chess.Board
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
            if (
                self._evaluator.evaluate(board)
                + depth * self.evaluator.MG_PIECE_VALUES[chess.PAWN] // 2
                <= alpha
            ):
                return True
        return False

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
        :type board: chess.Board
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
            else board.piece_at(move.to_square).piece_type  # type: ignore
        )
        return (
            True
            if stand_pat
            + self.evaluator.MG_PIECE_VALUES[captured_piece]
            + self.evaluator.DELTA
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
        :type board_to_search: chess.Board
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
        :type board: chess.Board
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

        for depth in range(1, self._searcher_config.max_depth + 1):
            new_board = copy.deepcopy(board)

            self._statistics.reset()

            time_left = timeout
            new_score, new_move, elapsed, error_code = self._timeoutable_search(
                timeout=time_left,
                board_to_search=new_board,
                depth=depth,
                prev_score=score,
            )

            # Timed out, return best move from previous depth.
            if error_code:
                logging.warning(
                    (
                        f"Search for position {board.fen()}"
                        f"timed out after {timeout:.1f} seconds, "
                        f"returning best move from depth {depth - 1}."
                    )
                )
                break
            # Else move onto next depth, unless we have no more time already.
            else:
                score, move = new_score, new_move
                if time_left is not None:
                    time_left -= elapsed
                    if time_left <= 0:  # type: ignore
                        break

        logging.info(f"End search for FEN {board.fen()}.")
        return score, move

    @abstractmethod
    def search(
        self, board: Board, timeout: Optional[float] = None
    ) -> Tuple[float, chess.Move]:
        """
        Abstract method to search for the best move in a given board position.

        :param board: The current state of the chess board.
        :type board: chess.Board
        :param timeout: Optional timeout value for the search operation.
                       If provided, the search should terminate after the specified time.
        :type timeout: Optional[float]

        :return: A tuple containing the evaluation score of the best move found
                 and the corresponding move itself.
        :rtype: Tuple[float, chess.Move]
        """
        pass
