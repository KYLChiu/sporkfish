import os
from typing import Tuple

import chess
from pathos.multiprocessing import ProcessPool

from sporkfish.board.board import Board
from sporkfish.evaluator.evaluator import Evaluator
from sporkfish.searcher.negamax import NegamaxSp
from sporkfish.searcher.searcher_config import SearcherConfig


# This doesn't really work yet. Don't use.
class NegaMaxLazySmp(NegamaxSp):
    def __init__(
        self,
        evaluator: Evaluator,
        searcher_config: SearcherConfig = SearcherConfig(),
    ) -> None:
        super().__init__(evaluator, searcher_config)

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

        def task() -> Tuple[float, chess.Move]:
            return NegamaxSp._start_search_from_root(self, board, depth, alpha, beta)

        # Let processes race down lazily and see who completes first
        # We need to add more asymmetry but a task for later
        futures = []
        for i in range(self._num_processes):  # type: ignore
            futures.append(self._pool.apipe(task))

        while True:
            for future in futures:
                if future.ready():
                    res: Tuple[float, chess.Move] = future.get()
                    return res
            else:
                # Continue the loop if no result is ready yet
                # Busy waiting is fine here because in principle, nothing else needs to be done
                continue
