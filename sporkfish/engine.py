from typing import Optional

import chess
import logging

from .board.board import Board
from .endgame_tablebase import EndgameTablebase
from .opening_book import OpeningBook
from .searcher.searcher import Searcher


class Engine:
    """
    Class wrapping the opening book and searcher into a convenient interface.

    Attributes:
    - _searcher (Searcher): The chess move searcher.
    - _opening_book (OpeningBook): The opening book for initial moves.
    """

    def __init__(
        self,
        searcher: Searcher,
        opening_book: OpeningBook,
        endgame_tablebase: EndgameTablebase,
    ) -> None:
        """
        Initialize the Engine with a searcher, an opening book and an endgame tablebase.

        :param searcher: The chess move searcher.
        :type searcher: Searcher
        :param opening_book: The opening book for initial moves.
        :type opening_book: OpeningBook
        :param endgame_tablebase: The endgame tablebase for final moves.
        :type endgame_tablebase: EndgameTablebase
        """
        self._searcher = searcher
        self._opening_book = opening_book
        self._endgame_tablebase = endgame_tablebase

    def best_move(self, board: Board, timeout: Optional[float] = None) -> chess.Move:
        """
        Return the best move based on opening book, endgame tablebase and searcher.

        :param board: The current chess board position.
        :type board: Board
        :param timeout: Time in seconds until the engine stops searching.
        :type timeout: Optional[float]
        :return: The selected chess move.
        :rtype: chess.Move
        """
        if opening_move := self._opening_book.query(board):
            logging.info(f"Best move {opening_move.uci()} found in opening book.")
            return opening_move
        elif end_move := self._endgame_tablebase.query(board):
            logging.info(f"Best move {end_move.uci()} found in endgame tablebase.")
            return end_move

        logging.info(
            f"No move found in opening book or endgame searcher or they are not configured. Delegating to searcher."
        )
        _, searched_move = self._searcher.search(board, timeout)
        return searched_move

    def score(self, board: Board, timeout: Optional[float] = None) -> float:
        """
        Returns the dynamic search score, useful for testing.

        :param board: The current chess board position.
        :type board: Board
        :param timeout: Time in seconds until the engine stops searching.
        :type timeout: Optional[float]
        :return: The score of the searcher.
        :rtype: float
        """
        return self._searcher.search(board, timeout)[0]
