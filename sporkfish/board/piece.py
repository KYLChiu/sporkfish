from . import Color, PieceType


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

    def __eq__(self, other: object) -> bool:
        """
        Check equivalence of this piece against another.

        :return: True if the piece type and color are equal, otherwise.
        :rtype: bool
        """
        if isinstance(other, Piece):
            return self.piece_type == other.piece_type and self.color == other.color
        raise NotImplementedError

    def __hash__(self) -> int:
        """
        Calculate the hash value of the piece.

        :return: The hash value.
        :rtype: int
        """
        return self.piece_type + (-1 if self.color else 5)
