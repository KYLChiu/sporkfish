from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import chess


class Board(ABC):
    """
    Abstract base class representing a chess board.
    """

    # --- Board mutators ---
    @abstractmethod
    def push(self, move: chess.Move) -> None:
        """
        Apply the given move to the board.

        :param move: The move to be applied.
        :type move: Move
        """
        pass

    @abstractmethod
    def push_uci(self, move: str) -> None:
        """
        Apply the move specified in Universal Chess Interface (UCI) format to the board.

        :param move: UCI-formatted move string.
        :type move: str
        """
        pass

    @abstractmethod
    def pop(self) -> None:
        """
        Undo the last move on the board.
        """
        pass

    @abstractmethod
    def reset(self) -> None:
        """
        Reset the board to its initial state.
        """
        pass

    @abstractmethod
    def set_fen(self, fen: str) -> None:
        """
        Set the position based on the input FEN string.

        :param fen: FEN string.
        :type fen: str
        """
        pass

    @abstractmethod
    def set_epd(self, epd: str) -> Dict[str, Any]:
        """
        Set the position based on the input EPD string.

        :param epd: EPD string.
        :type epd: str
        :return: The epd info (e.g. containing best move) for the board.
        :rtype: Dict[str, Any]
        """
        pass

    # --- Board information ---
    @property
    @abstractmethod
    def turn(self) -> chess.Color:
        """
        The side to move.

        :return: WHITE if white to move else BLACK.
        :rtype: chess.Color
        """
        pass

    @property
    @abstractmethod
    def ep_square(self) -> Optional[chess.Square]:
        """
        Returns the potential en passant square if available, else None.

        :return: The en passant square.
        :rtype: Optional[chess.Square]
        """
        pass

    @property
    @abstractmethod
    # NB: this returns any because we don't have a set type for legal moves in our own board implementation.
    # We will revisit this after it's been implemented.
    def legal_moves(self) -> Any:
        """
        Get a collection of all legal moves for the current position.

        :return: A collection of legal moves.
        :rtype: Any
        """
        pass

    @abstractmethod
    def piece_at(self, square: chess.Square) -> Optional[chess.Piece]:
        """
        Get the piece at the specified square.

        :param square: The target square.
        :type square: Square
        :return: The piece at the specified square, or None if the square is empty.
        :rtype: Optional[Piece]
        """
        pass

    @abstractmethod
    def piece_map(self) -> Dict[chess.Square, chess.Piece]:
        pass

    @abstractmethod
    def is_capture(self, move: chess.Move) -> bool:
        """
        Check if a given move is a capture.

        :param move: The move to check.
        :type move: chess.Move
        :return: True if it is a capture, false otherwise.
        :rtype: bool
        """
        pass

    @abstractmethod
    def is_check(self) -> bool:
        """
        Check if the current side to move is in check.

        :return: True if is the current side to move is in check, false otherwise.
        :rtype: bool
        """
        pass

    @abstractmethod
    def fen(self) -> str:
        """
        Get the Forsyth-Edwards Notation (FEN) of the current board position.

        :return: FEN string representing the current board position.
        :rtype: str
        """
        pass

    @abstractmethod
    def has_queenside_castling_rights(self, color: chess.Color) -> bool:
        """
        Check if the specified color has queenside castling rights.

        :param color: The color to check.
        :type color: chess.Color
        :return: True if the color has queenside castling rights, False otherwise.
        :rtype: bool
        """
        pass

    @abstractmethod
    def has_kingside_castling_rights(self, color: chess.Color) -> bool:
        """
        Check if the specified color has kingside castling rights.

        :param color: The color to check.
        :type color: chess.Color
        :return: True if the color has kingside castling rights, False otherwise.
        :rtype: bool
        """
        pass
