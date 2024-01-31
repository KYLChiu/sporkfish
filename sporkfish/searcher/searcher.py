import logging
from abc import ABC, abstractmethod
from typing import Optional, Tuple

import chess

# should be absolute paths - amend in next PR
from ..board.board import Board
from ..evaluator import Evaluator
from ..statistics import Statistics
from .searcher_config import SearcherConfig

# _manager = Manager()
# We explicitly do not lock these and let race conditions happen
# Locks are too slow, need to consider atomic maps / values later
# This might cause underestimation of statistics.
# _dict = _manager.dict()
# _stats = _manager.Value("i", 0)


class Searcher(ABC):
    """
    Dynamic best move searching class.
    """

    def __init__(self, config: SearcherConfig = SearcherConfig()) -> None:
        """
        Initialize the Searcher instance with mutable statistics.

        :param config: Config to use for searching.
        :type config: SearcherConfig
        :return: None
        """

        self._config = config
        self._stats = 0
        self._statistics = Statistics(self._stats)
        self._dict: dict = dict()

    def _log_info(
        self, elapsed: float, score: float, move: chess.Move, depth: int
    ) -> None:
        fields = {
            "depth": depth,
            # time in ms
            "time": int(1000 * elapsed),
            "nodes": self._statistics.nodes_visited,
            "nps": int(self._statistics.nodes_visited / elapsed) if elapsed > 0 else 0,
            "score cp": int(score)
            if score not in {float("inf"), -float("inf")}
            else float("nan"),
            "pv": move,  # Incorrect but will do for now
        }
        info_str = " ".join(f"{k} {v}" for k, v in fields.items())
        logging.info(f"info {info_str}")

    @abstractmethod
    def search(
        self, board: Board, timeout: Optional[float] = None
    ) -> Tuple[float, chess.Move]:
        pass
