from abc import ABC, abstractmethod
from typing import Optional, Tuple

import chess

# should be absolute paths - amend in next PR
from sporkfish.board.board import Board
from sporkfish.searcher.searcher_config import SearcherConfig
from sporkfish.statistics import Statistics


class Searcher(ABC):
    """
    Dynamic best move searching class.
    """

    def __init__(self, searcher_config: SearcherConfig = SearcherConfig()) -> None:
        """
        Initialize the Searcher instance with mutable statistics.

        :param searcher_config: Config to use for searching.
        :type searcher_config: SearcherConfig
        """

        self._searcher_config = searcher_config
        self._statistics = Statistics()
        self._dict: dict = dict()

    def _log_info(
        self, elapsed: float, score: float, move: chess.Move, depth: int
    ) -> None:
        """
        Log information about the search process.

        This method logs various statistics and details about the search process.

        :param elapsed: The time elapsed for the search process, in seconds.
        :type elapsed: float
        :param score: The evaluation score of the best move found.
        :type score: float
        :param move: The best move found during the search.
        :type move: chess.Move
        :param depth: The depth of the search.
        :type depth: int
        """
        self._statistics.log_info(elapsed, score, move, depth)

    @abstractmethod
    def search(
        self, board: Board, timeout: Optional[float] = None
    ) -> Tuple[float, chess.Move]:
        """
        Abstract method to search for the best move in a given board position.

        :param board: The current state of the chess board.
        :type board: Board
        :param timeout: Optional timeout value for the search operation.
                       If provided, the search should terminate after the specified time.
        :type timeout: Optional[float]

        :return: A tuple containing the evaluation score of the best move found
                 and the corresponding move itself.
        :rtype: Tuple[float, chess.Move]
        """
        pass
