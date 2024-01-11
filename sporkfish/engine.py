import chess
from .searcher import Searcher
from .opening_book import OpeningBook


class Engine:
    """
    Class wrapping the opening book and searcher into a convenient interface.

    Attributes:
    - _searcher (Searcher): The chess move searcher.
    - _opening_book (OpeningBook): The opening book for initial moves.
    """

    def __init__(self, searcher: Searcher, opening_book: OpeningBook):
        """
        Initialize the Engine with a searcher and an opening book.

        :param searcher: The chess move searcher.
        :type searcher: Searcher
        :param opening_book: The opening book for initial moves.
        :type opening_book: OpeningBook
        """
        self._searcher = searcher
        self._opening_book = opening_book

    def best_move(self, board: chess.Board, timeout: int = None) -> chess.Move:
        """
        Return the best move based on opening book queries and searcher.

        :param board: The current chess board position.
        :type board: chess.Board
        :param timeout: Time in seconds until the engine stops searching.
        :type timeout: int
        :return: The selected chess move.
        :rtype: chess.Move
        """
        opening_move = self._opening_book.query(board)
        return opening_move or self._searcher.search(board, timeout)[1]

    def score(self, board: chess.Board, timeout: int = None) -> float:
        """
        Returns the dynamic search score, useful for testing.

        :param board: The current chess board position.
        :type board: chess.Board
        :return: The score of the searcher.
        :param timeout: Time in seconds until the engine stops searching.
        :type timeout: int
        :rtype: float
        """
        return self._searcher.search(board, timeout)[0]

    def evaluate(self, board: chess.Board) -> float:
        """
        Returns the (static) leaf evaluation score, useful for testing.

        :param board: The current chess board position.
        :type board: chess.Board
        :return: The score of the evaluator.
        :rtype: float
        """
        score = self._searcher.evaluator.evaluate(board)
        return score
