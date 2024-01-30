import copy
import logging
import os
import time
from abc import ABC, abstractmethod
from typing import Optional, Tuple

import chess
import stopit
from pathos.multiprocessing import ProcessPool

from ..board.board import Board
from ..evaluator import Evaluator
from ..statistics import Statistics
from ..transposition_table import TranspositionTable
from ..zobrist_hasher import ZobristHasher
from .move_ordering import MoveOrder, MvvLvaHeuristic
from .searcher import Searcher
from .searcher_config import MoveOrdering, SearcherConfig, SearchMode

_dict: dict = dict()


class MiniMaxVariants(Searcher):
    """
    Abstract base class for minimax like searchers
    """

    @abstractmethod
    def _searcher(self, board_to_search, depth, alpha, beta):
        pass

    def __init__(
        self,
        evaluator: Evaluator,
        move_order: MoveOrder,
        config: SearcherConfig = SearcherConfig(),
    ) -> None:
        super().__init__(evaluator, config)

        if self._config.enable_transposition_table:
            self._zobrist_hash = ZobristHasher()
            self._transposition_table = TranspositionTable(_dict)
            logging.info("Enabled transposition table in search.")
        else:
            logging.info("Disabled transposition table in search.")

        if self._config.order == MoveOrdering.MVV_LVA:
            self._move_order = MvvLvaHeuristic()
        else:
            raise Exception("Only support MVV_LVA move ordering at the moment")

    def _ordered_moves(self, board: Board, legal_moves):
        # order moves from best to worse
        return sorted(
            legal_moves,
            key=lambda move: (self._move_order.evaluate(board, move),),
            reverse=True,
        )

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
        for move in legal_moves:
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
        alpha: float,
        beta: float,
    ) -> Tuple[float, chess.Move, float, int]:
        try:
            score, move = self._searcher(board_to_search, depth, alpha, beta)

            elapsed = time.time() - start_time
            self._logging(elapsed, score, move, depth)

            return score, move, elapsed, 0
        except stopit.utils.TimeoutException:
            return float("-inf"), chess.Move.null(), 0.0, 1
        except Exception:
            raise

    def _null_move_pruning(
        self, depth: int, board: Board, alpha: float, beta: float
    ) -> bool:
        """
        Null move pruning - reduce the search space by trying a null move,
        then seeing if the score of the subtree search is still high enough to cause a beta cutoff
        """
        # TODO: add zugzwang check
        depth_reduction_factor = 3
        in_check = board.is_check()
        if depth >= depth_reduction_factor and not in_check:
            null_move_depth = depth - depth_reduction_factor
            board.push(chess.Move.null())
            value = -self._negamax(board, null_move_depth, -beta, -alpha)
            board.pop()
            if value >= beta:
                return True
        return False

    def _iterative_deepening(self, board, timeout):
        """
        Iterative deepening
        This conducts a fixed-depth search for depths ranging from 1 to max_depth.
        1) It enables the transposition table (cache) to be easily utilized.
        2) If time constraints prevent a complete search, the function can return the best move found up to the previous depth.
        3) It facilitates the use of aspiration windows, as implemented in the _aspiration_windows_search function.
        """
        score = -float("inf")
        move = chess.Move.null()

        for depth in range(1, self._config.max_depth + 1):
            new_board = copy.deepcopy(board)

            alpha = -float("inf")
            beta = float("inf")

            self._statistics.reset()
            start_time = time.time()

            time_left = timeout
            new_score, new_move, elapsed, error_code = self._do_search_with_info(
                timeout=time_left,
                board_to_search=new_board,
                depth=depth,
                start_time=start_time,
                alpha=alpha,
                beta=beta,
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
    def search():
        pass
