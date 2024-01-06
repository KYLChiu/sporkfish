import chess
from . import searcher
from . import opening_book


class Engine:
    """
    Class responsible for making moves based on the opening book and searcher.

    Attributes:
    - searcher (searcher.Searcher): The chess move searcher.
    - opening_book (opening_book.OpeningBook): The opening book for initial moves.

    Methods:
    - make_move(depth: int, board: chess.Board, searcher: searcher.Searcher) -> chess.Move:
        Make a chess move based on the opening book and searcher.

    """

    def __init__(
        self, searcher: searcher.Searcher, opening_book: opening_book.OpeningBook
    ) -> None:
        """
        Initialize the Engine instance.

        :param searcher: The chess move searcher.
        :type searcher: searcher.Searcher
        :param opening_book: The opening book for initial moves.
        :type opening_book: opening_book.OpeningBook
        :return: None
        """
        self.searcher = searcher
        self.opening_book = opening_book

    def make_move(self, board: chess.Board) -> chess.Move:
        """
        Make a chess move based on the opening book queries and searcher.

        :param board: The current chess board position.
        :type board: chess.Board
        :return: The selected chess move.
        :rtype: chess.Move
        """
        opening_move = self.opening_book.query(board)
        move_choice = opening_move if opening_move else self.searcher.search(board)
        move = chess.Move.from_uci(str(move_choice))
        board.push(move)
        return move
