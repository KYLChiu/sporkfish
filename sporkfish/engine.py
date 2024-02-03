from typing import Optional

import chess

from .board.board import Board
from .opening_book import OpeningBook
from .endgame_tablebase import EndgameTablebase
from .searcher.searcher import Searcher


class Engine:
    """
    Class wrapping the opening book and searcher into a convenient interface.

    Attributes:
    - _searcher (Searcher): The chess move searcher.
    - _opening_book (OpeningBook): The opening book for initial moves.
    """

    def __init__(self, searcher: Searcher, opening_book: OpeningBook, endgame_tablebase: EndgameTablebase) -> None:
        """
        Initialize the Engine with a searcher and an opening book.

        :param searcher: The chess move searcher.
        :type searcher: Searcher
        :param opening_book: The opening book for initial moves.
        :type opening_book: OpeningBook
        """
        self._searcher = searcher
        self._opening_book = opening_book
        self._endgame_tablebase = endgame_tablebase

    def best_move(self, board: Board, timeout: Optional[float] = None) -> chess.Move:
        """
        Return the best move based on opening book queries and searcher.

        :param board: The current chess board position.
        :type board: Board
        :param timeout: Time in seconds until the engine stops searching.
        :type timeout: Optional[float]
        :return: The selected chess move.
        :rtype: chess.Move
        """
        opening_move = self._opening_book.query(board)
        end_move = self._endgame_tablebase.query(board)
        return opening_move or end_move or self._searcher.search(board, timeout)[1]

    def score(self, board: Board, timeout: Optional[float] = None) -> float:
        """
        Returns the dynamic search score, useful for testing.

        :param board: The current chess board position.
        :type board: Board
        :return: The score of the searcher.
        :param timeout: Time in seconds until the engine stops searching.
        :type timeout: Optional[float]
        :rtype: float
        """
        return self._searcher.search(board, timeout)[0]
