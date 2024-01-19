from . import Color, PieceType


# Adapted from python-chess
class Piece:
    """
    Represents a chess piece.

    :param piece_type: The type of the chess piece (e.g., Pawn, Rook).
    :type piece_type: PieceType
    :param color: The color of the chess piece (e.g., White, Black).
    :type color: Color
    """

    def __init__(self, piece_type: PieceType, color: Color):
        """
        Initialize a new chess piece.

        :param piece_type: The type of the chess piece.
        :type piece_type: PieceType
        :param color: The color of the chess piece.
        :type color: Color
        """
        self.piece_type = piece_type
        self.color = color

    def __hash__(self) -> int:
        """
        Calculate the hash value of the piece.

        :return: The hash value.
        :rtype: int
        """
        return self.piece_type + (-1 if self.color else 5)
