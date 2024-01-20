from dataclasses import dataclass
from typing import Optional

from . import PIECE_SYMBOLS, SQUARE_NAMES, PieceType, Square


@dataclass(frozen=True)
class Move:
    """
    Represents a chess move.

    Attributes:
    - from_square (int): The square from which the move originates.
    - to_square (int): The destination square of the move.
    - promotion (Optional[int]): The piece type to which a pawn is promoted (if applicable).
    """

    from_square: Square
    to_square: Square
    promotion: Optional[PieceType] = None

    def uci(self) -> str:
        """
        Get the move in Universal Chess Interface (UCI) format.

        :return: UCI-formatted move string.
        :rtype: str
        """
        from_to = self.from_square and self.to_square
        if self.promotion is not None and from_to:
            return (
                SQUARE_NAMES[self.from_square]
                + SQUARE_NAMES[self.to_square]
                + PIECE_SYMBOLS[self.promotion]
            )
        elif from_to:
            return SQUARE_NAMES[self.from_square] + SQUARE_NAMES[self.to_square]
        else:
            return "0000"

    def __str__(self) -> str:
        """
        Get a string representation of the move.

        :return: String representation of the move.
        :rtype: str
        """
        return self.uci()

    @staticmethod
    def null() -> "Move":
        """
        Create a null move.

        :return: Null Move instance.
        :rtype: Move
        """
        return Move(0, 0, None)

    @staticmethod
    def from_uci(uci: str) -> "Move":
        """
        Create a Move instance from a UCI-formatted string.

        :param uci: UCI-formatted move string.
        :type uci: str
        :return: Move instance.
        :rtype: Move
        :raises ValueError: If the UCI string is invalid.
        """
        if uci == "0000":
            return Move(0, 0, None)
        elif 4 <= len(uci) <= 5:
            try:
                from_square = SQUARE_NAMES.index(uci[0:2])
                to_square = SQUARE_NAMES.index(uci[2:4])
                promotion = PIECE_SYMBOLS.index(uci[4]) if len(uci) == 5 else None
            except IndexError:
                raise ValueError("Invalid uci: " + str(uci))
            if from_square == to_square:
                raise ValueError(
                    "From move and to move are the same in this UCI string: " + str(uci)
                )
            return Move(from_square, to_square, promotion=promotion)
        else:
            raise ValueError("Expected uci string to be of length 4 or 5: " + str(uci))
