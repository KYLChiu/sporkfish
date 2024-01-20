import chess
import numpy as np
from numba import njit

from .board.board import Board


from .board.board import Board
from .board import SQUARES


class BoardInfo:

    """
    Represents information about a chess board used for hashing.

    Attributes:
    - colored_piece_types (numpy.ndarray): Array of colored piece types on each square.
    - board_turn (bool): True if it's black's turn, False otherwise.
    - en_passant_file (int): File index of the en passant square or -1 if not an en passant square.
    - castling_rights (numpy.ndarray): Array indicating castling rights.
    """

    def __init__(self, board: Board) -> None:
        self.colored_piece_types = np.array(
            [
                # This won't have hash collisions as all the piece indices are > 0
                hash(piece) if (piece := board.piece_at(square)) else -1
                for square in SQUARES
            ],
            dtype=np.int8,
        )
        self.board_turn: bool = board.turn
        self.en_passant_file: int = (
            chess.square_file(board.ep_square) if board.ep_square else -1
        )
        self.castling_rights = np.array(  # type: ignore
            [
                board.has_kingside_castling_rights(chess.WHITE),
                board.has_queenside_castling_rights(chess.WHITE),
                board.has_kingside_castling_rights(chess.BLACK),
                board.has_queenside_castling_rights(chess.BLACK),
            ],
            dtype=bool,
        )


@njit
def _hash(
    colored_piece_types: np.ndarray,
    piece_hashes: np.ndarray,
    board_turn: bool,
    turn_hash: np.int64,
    en_passant_file: np.int64,
    en_passant_hashes: np.ndarray,
    castling_rights: np.ndarray,
    castling_hashes: np.ndarray,
) -> int:
    board_hash = np.int64(0)
    for square, color_piece_type in enumerate(colored_piece_types):
        # Get rid of the squares which don't have pieces
        if color_piece_type != -1:
            board_hash ^= piece_hashes[square, color_piece_type]  # type: ignore

    if board_turn == chess.BLACK:
        board_hash ^= turn_hash

    if en_passant_file >= 0:
        board_hash ^= en_passant_hashes[en_passant_file]  # type: ignore

    for i, castling_right in enumerate(castling_rights):
        if castling_right:
            board_hash ^= castling_hashes[i]  # type: ignore

    return int(board_hash)


class ZobristHasher:
    def __init__(self) -> None:
        """
        Initialize the Zobrist Hasher object, used to hash board positions.
        This allows caching via the transposition table, so we don't have to evaluate positions twice.

        Attributes:
        - _piece_hashes (numpy.ndarray): Zobrist hash values for each piece on each square.
        - _turn_hash (np.uint64): Zobrist hash value for the side to move.
        - _en_passant_hashes (numpy.ndarray): Zobrist hash values for en passant squares.
        - _castling_hashes (numpy.ndarray): Zobrist hash values for castling rights.

        Methods:
        - __init__(): Initialize the Zobrist Hasher object.
        - hash(board) -> int: Hashes the given chess board using Zobrist hashing.
        """
        # Sporkfish's lucky number
        np.random.seed(10101010)

        self._piece_hashes = np.random.randint(
            0, 2**64, size=(64, 12), dtype=np.uint64
        )
        self._turn_hash = np.random.randint(0, 2**64, dtype=np.uint64)

        self._en_passant_hashes = np.random.randint(0, 2**64, size=8, dtype=np.uint64)
        self._castling_hashes = np.random.randint(0, 2**64, size=4, dtype=np.uint64)

    def hash(self, board: Board) -> int:
        """
        Hashes the given chess board using Zobrist hashing.

        Parameters:
        - board (Board): The chess board.

        Returns:
        - int: The computed Zobrist hash value for the board.
        """

        board_info = BoardInfo(board)

        return _hash(  # type: ignore
            board_info.colored_piece_types,
            self._piece_hashes,
            board_info.board_turn,
            self._turn_hash,
            board_info.en_passant_file,
            self._en_passant_hashes,
            board_info.castling_rights,
            self._castling_hashes,
        )
