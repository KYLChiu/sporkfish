from typing import Any, Dict, Optional

import chess

from .board import Board


class BoardPyChess(Board):
    """
    This class implements the abstract methods defined in the Board ABC using python-chess.
    """

    def __init__(self) -> None:
        """
        Initialize a new chess board using the python-chess library.
        """
        self.board = chess.Board()

    def push(self, move: chess.Move) -> None:
        """
        Apply the given move to the board.

        :param move: The move to be applied.
        :type move: chess.Move
        """
        self.board.push(move)

    def pop(self) -> None:
        """
        Undo the last move on the board.
        """
        self.board.pop()

    def reset(self) -> None:
        """
        Reset the board to its initial state.
        """
        self.board.reset()

    def push_uci(self, move: str) -> None:
        """
        Apply the move specified in Universal Chess Interface (UCI) format to the board.

        :param move: UCI-formatted move string.
        :type move: str
        """
        self.board.push_uci(move)

    @property
    def turn(self) -> chess.Color:
        """
        Returns which turn it is to play a move.

        :return: WHITE if white to move else BLACK.
        :rtype: chess.Color
        """
        return self.board.turn

    def set_fen(self, fen: str) -> None:
        """
        Set the position based on the input FEN string.

        :param fen: FEN string.
        :type fen: str
        """
        self.board.set_fen(fen)

    def set_epd(self, epd: str) -> Dict[str, Any]:
        """
        Set the position based on the input EPD string.

        :param epd: EPD string.
        :type epd: str
        :return: The epd info (e.g. containing best move) for the board.
        :rtype: Dict[str, Any]
        """
        return self.board.set_epd(epd)

    @property
    def ep_square(self) -> Optional[chess.Square]:
        """
        Returns the potential en passant square if available, else None.

        :return: The en passant square.
        :rtype: Optional[chess.Square]
        """
        return self.board.ep_square

    @property
    def legal_moves(self) -> Any:
        """
        Get a collection of all legal moves for the current position.

        :return: A collection of legal moves.
        :rtype: Any
        """
        return self.board.legal_moves

    def peek(self) -> chess.Move:
        return self.board.peek()

    def piece_at(self, square: chess.Square) -> Optional[chess.Piece]:
        """
        Get the piece at the specified square.

        :param square: The target square.
        :type square: chess.Square
        :return: The piece at the specified square, or None if the square is empty.
        :rtype: Optional[chess.Piece]
        """
        return self.board.piece_at(square)

    def is_capture(self, move: chess.Move) -> bool:
        """
        Check if a given move is a capture.

        :param move: The move to check.
        :type move: chess.Move
        :return: True if it is a capture, false otherwise.
        :rtype: bool
        """
        return self.board.is_capture(move)

    def is_check(self) -> bool:
        """
        Check if the current side to move is in check.

        :return: True if is the current side to move is in check, false otherwise.
        :rtype: bool
        """
        return self.board.is_check()

    def fen(self) -> str:
        """
        Get the Forsyth-Edwards Notation (FEN) of the current board position.

        :return: FEN string representing the current board position.
        :rtype: str
        """
        return self.board.fen()

    def has_queenside_castling_rights(self, color: chess.Color) -> bool:
        """
        Check if the specified color has queenside castling rights.

        :param color: The color to check.
        :type color: chess.Color
        :return: True if the color has queenside castling rights, False otherwise.
        :rtype: bool
        """
        return self.board.has_queenside_castling_rights(color)

    def has_kingside_castling_rights(self, color: chess.Color) -> bool:
        """
        Check if the specified color has kingside castling rights.

        :param color: The color to check.
        :type color: chess.Color
        :return: True if the color has kingside castling rights, False otherwise.
        :rtype: bool
        """
        return self.board.has_kingside_castling_rights(color)
