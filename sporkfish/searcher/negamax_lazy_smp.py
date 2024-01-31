import os
from typing import Tuple

import chess
from pathos.multiprocessing import ProcessPool

from ..board.board import Board
from ..evaluator import Evaluator
from .move_ordering import MoveOrder
from .negamax import NegamaxSp
from .searcher_config import SearcherConfig


# This doesn't really work yet. Don't use.
class NegaMaxLazySmp(NegamaxSp):
    def __init__(
        self,
        evaluator: Evaluator,
        order: MoveOrder,
        searcher_config: SearcherConfig = SearcherConfig(),
    ) -> None:
        super().__init__(evaluator, order, searcher_config)

        self._num_processes = os.cpu_count()
        self._pool = ProcessPool(nodes=self._num_processes)

    # This doesn't really work yet. Don't use.
    def _start_search_from_root(
        self,
        board: Board,
        depth: int,
        alpha: float,
        beta: float,
    ) -> Tuple[float, chess.Move]:
        """
        Entry point for negamax search with fail-soft alpha-beta pruning with lazy symmetric multiprocessing.

        :param board: The current chess board position.
        :type board: Board
        :param depth: The current search depth.
        :type depth: int
        :param alpha: Alpha value for alpha-beta pruning.
        :type alpha: float
        :param beta: Beta value for alpha-beta pruning.
        :type beta: float
        :return: Tuple containing the best move and its value.
        :rtype: Tuple[float, chess.Move]
        """

        # Let processes race down lazily and see who completes first
        # We need to add more asymmetry but a task for later
        def task() -> Tuple[float, chess.Move]:
            return self._start_search_from_root(board, depth, alpha, beta)

        futures = []
        for i in range(self._num_processes):  # type: ignore
            futures.append(self._pool.apipe(task, i))

        while True:
            for future in futures:
                if future.ready():
                    res: Tuple[float, chess.Move] = future.get()
                    return res
            else:
                continue  # Continue the loop if no result is ready yet
