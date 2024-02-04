import copy
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Optional, Tuple

import chess
import stopit

from ..board.board import Board
from ..evaluator import Evaluator
from ..transposition_table import TranspositionTable
from ..zobrist_hasher import ZobristHasher
from .move_ordering import MoveOrder
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
        pass

    def __init__(
        self,
        evaluator: Evaluator,
        move_order: MoveOrder,
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
        self._move_order = move_order

    @property
    def evaluator(self) -> Evaluator:
        return self._evaluator

    def _ordered_moves(self, board: Board, legal_moves: Any) -> Any:
        # order moves from best to worse
        return sorted(
            legal_moves,
            key=lambda move: (self._move_order.evaluate(board, move),),
            reverse=True,
        )

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
            # Aspiration window size: 50 centipawn is worth about 1/2 of a pawn in our eval function
            # We leave configuration for this to another PR
            window_size = 50
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

    def _quiescence(self, board: Board, depth: int, alpha: float, beta: float) -> float:
        """
        Quiescence search to help the horizon effect (improving checking of tactical possibilities).

        Parameters:
            board (Board): The chess board.
            alpha (float): The lower bound of the search window.
            beta (float): The upper bound of the search window.
            depth (int): max recursion limit

        Returns:
            int: The evaluated score after quiescence search.
        """

        self._statistics.increment()

        stand_pat = self._evaluator.evaluate(board)

        if depth == 0:
            return stand_pat

        if stand_pat >= beta:
            return beta

        if alpha < stand_pat:
            alpha = stand_pat

        legal_moves = (move for move in board.legal_moves if board.is_capture(move))
        legal_moves = self._ordered_moves(board, legal_moves)

        # Assuming the input move is a capturing move, returns the captured piece
        def captured_piece(board: Board, move: chess.Move) -> chess.PieceType:
            return (
                chess.PAWN
                if board.is_en_passant(move)
                else board.piece_at(move.to_square).piece_type  # type: ignore
            )

        for move in legal_moves:
            # Delta pruning
            # Rationale: if our position is such that:
            # evaluation + captured piece value + safety margin (delta) doesn't exceed what I can already guarantee,
            # then there is no point to continue the search for this branch.
            # The safety margin leaves some room for searching for sacrifices,
            # i.e. taking a pawn down a rook usually will not help but taking a bishop down a rook may help.
            # The delta value should be tuned based on piece values of the evaluator.
            # TODO: consider add check for late endgame - it should not be enabled there because
            # transitions into won endgames made at the expense of some material will no longer be considered
            # However we might remedy this directly with endgame tablebases.
            if (
                self._searcher_config.enable_delta_pruning
                and stand_pat
                + self.evaluator.MG_PIECE_VALUES[captured_piece(board, move)]
                + self.evaluator.DELTA
                < alpha
            ):
                continue

            board.push(move)
            score = -self._quiescence(board, depth - 1, -beta, -alpha)
            board.pop()

            if score >= beta:
                return beta

            if score > alpha:
                alpha = score

        return alpha

    @stopit.threading_timeoutable(default=(float("-inf"), chess.Move.null(), 0.0, 1))
    def _do_search_with_info(
        self,
        board_to_search: Board,
        depth: int,
        start_time: float,
        prev_score: float,
    ) -> Tuple[float, chess.Move, float, int]:
        """
        Perform an aspiration windows search on the given chess board up to the specified depth.

        Parameters:
        - board_to_search (Board): The chess board to search.
        - depth (int): The depth of the search.
        - start_time (float): The start time of the search.
        - prev_score (float): The previous score from a shallower search.

        Returns:
        Tuple[float, chess.Move, float, int]: A tuple containing the following:
        - float: The score of the best move found during the search.
        - chess.Move: The best move found.
        - float: The elapsed time of the search.
        - int: A flag indicating whether the search was terminated due to a timeout (1 for timeout, 0 otherwise).

        Raises:
        - Exception: If an unexpected error occurs during the search.
        """
        try:
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

    def _iterative_deepening(
        self, board: Board, timeout: Optional[float]
    ) -> Tuple[float, chess.Move]:
        """
        Iterative deepening
        This conducts a fixed-depth search for depths ranging from 1 to max_depth.
        1) It enables the transposition table (cache) to be easily utilized.
        2) If time constraints prevent a complete search, the function can return the best move found up to the previous depth.
        3) It facilitates the use of aspiration windows, as implemented in the _aspiration_windows_search function.
        """
        score = -float("inf")
        move = chess.Move.null()

        for depth in range(1, self._searcher_config.max_depth + 1):
            new_board = copy.deepcopy(board)

            -float("inf")
            float("inf")

            self._statistics.reset()
            start_time = time.time()

            time_left = timeout
            new_score, new_move, elapsed, error_code = self._do_search_with_info(
                timeout=time_left,
                board_to_search=new_board,
                depth=depth,
                start_time=start_time,
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
        pass
