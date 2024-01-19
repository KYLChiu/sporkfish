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

    def __eq__(self, other: "Piece") -> bool:
        """
        Check equivalence of this piece against another.

        :return: True if the piece type and color are equal, otherwise.
        :rtype: bool
        """
        return (
            self.piece_type == other.piece_type and self.color == other.color
            if isinstance(other, Piece)
            else False
        )

    def __hash__(self) -> int:
        """
        Calculate the hash value of the piece.

        :return: The hash value.
        :rtype: int
        """
        return self.piece_type + (-1 if self.color else 5)
