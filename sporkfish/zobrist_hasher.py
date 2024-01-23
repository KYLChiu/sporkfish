import chess
import numpy as np
from numba import njit
from typing import Tuple

from .board.board import Board


class BoardInfoExtractor:

    """
    Extracts information about a chess board used for hashing.
    """

    @staticmethod
    def full_hash_info(board: Board) -> Tuple[np.ndarray, bool, np.int8, np.ndarray]:
        colored_piece_types = np.array(
            [
                # This won't have hash collisions as all the piece indices are > 0
                [
                    square,
                    hash(piece) if (piece := board.piece_at(square)) else np.uint8(255),
                ]
                for square in chess.SQUARES
            ],
            dtype=np.uint8,
        )
        board_turn: bool = board.turn
        en_passant_file: np.uint8 = (
            chess.square_file(board.ep_square) if board.ep_square else np.uint8(255)
        )
        castling_rights = np.array(  # type: ignore
            [
                board.has_kingside_castling_rights(chess.WHITE),
                board.has_queenside_castling_rights(chess.WHITE),
                board.has_kingside_castling_rights(chess.BLACK),
                board.has_queenside_castling_rights(chess.BLACK),
            ],
            dtype=bool,
        )
        return colored_piece_types, board_turn, en_passant_file, castling_rights

    @staticmethod
    def incremental_hash_info(board: Board):
        color_piece_type = 255
        from_sq, to_sq = 255, 255
        colored_piece_types = np.array([[np.uint8(255), np.uint8(255)]], dtype=np.uint8)
        # TODO: what happens when no moves?
        try:
            last_move = board.peek()
            from_sq = last_move.from_square
            to_sq = last_move.to_square
            color_piece_type = hash(board.piece_at(to_sq))
            colored_piece_types = np.array(
                [[from_sq, color_piece_type], [to_sq, color_piece_type]],
                dtype=np.uint8,
            )
            # I really don't like this but don't see another way to do it atm
            if board.is_capture(last_move):
                board.pop()
                np.append(
                    colored_piece_types,
                    [[to_sq, hash(board.piece_at(to_sq))]],
                )
                board.push(last_move)
        except:
            pass
        # TODO: what about promotion...?

        board_turn: bool = board.turn
        en_passant_file: np.uint8 = (
            chess.square_file(board.ep_square) if board.ep_square else 255
        )
        castling_rights = np.array(  # type: ignore
            [
                board.has_kingside_castling_rights(chess.WHITE),
                board.has_queenside_castling_rights(chess.WHITE),
                board.has_kingside_castling_rights(chess.BLACK),
                board.has_queenside_castling_rights(chess.BLACK),
            ],
            dtype=bool,
        )
        return colored_piece_types, board_turn, en_passant_file, castling_rights


@njit(cache=True, nogil=True)
def _compute_aggregate_piece_hash(
    board_hash: np.uint64, colored_piece_types: np.ndarray, piece_hashes: np.ndarray
) -> np.uint64:
    new_board_hash = board_hash
    for square, color_piece_type in colored_piece_types:
        # Get rid of the squares which don't have pieces
        if color_piece_type != np.uint8(255):
            new_board_hash ^= piece_hashes[square, color_piece_type]  # type: ignore
    return new_board_hash


@njit(cache=True, nogil=True)
def _compute_turn_hash(board_hash: np.uint64, board_turn: bool, turn_hash: np.uint64):
    if board_turn:
        new_board_hash = board_hash ^ turn_hash
        return new_board_hash
    return board_hash


@njit(cache=True, nogil=True)
def _compute_en_passant_hash(
    board_hash: np.uint64, en_passant_file: np.uint64, en_passant_hashes: np.ndarray
):
    if en_passant_file != 255:
        new_board_hash = board_hash ^ en_passant_hashes[en_passant_file]  # type: ignore
        return new_board_hash
    return board_hash


@njit(cache=True, nogil=True)
def _compute_castling_hash(
    board_hash: np.uint64, castling_rights: np.uint64, castling_hashes: np.ndarray
):
    new_board_hash = board_hash
    for i, castling_right in enumerate(castling_rights):
        if castling_right:
            new_board_hash ^= castling_hashes[i]  # type: ignore
    return new_board_hash


@njit(cache=True, nogil=True)
def _compute_hash(
    initial_hash: np.uint64,
    colored_piece_types: np.ndarray,
    piece_hashes: np.ndarray,
    board_turn: bool,
    turn_hash: np.int64,
    en_passant_file: np.int64,
    en_passant_hashes: np.ndarray,
    castling_rights: np.ndarray,
    castling_hashes: np.ndarray,
) -> np.uint64:
    board_hash = _compute_aggregate_piece_hash(
        initial_hash, colored_piece_types, piece_hashes
    )
    board_hash = _compute_turn_hash(board_hash, board_turn, turn_hash)
    board_hash = _compute_en_passant_hash(
        board_hash, en_passant_file, en_passant_hashes
    )
    board_hash = _compute_castling_hash(board_hash, castling_rights, castling_hashes)
    return board_hash


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
        # TODO: we may revisit this in future as people claim this can affect collision chances greatly
        np.random.seed(10101010)

        self._piece_hashes = np.random.randint(
            0, 2**64, size=(64, 12), dtype=np.uint64
        )
        self._turn_hash = np.random.randint(0, 2**64, dtype=np.uint64)
        self._en_passant_hashes = np.random.randint(0, 2**64, size=8, dtype=np.uint64)
        self._castling_hashes = np.random.randint(0, 2**64, size=4, dtype=np.uint64)

    def hash(self, board: Board) -> np.uint64:
        """
        Hashes the given chess board using Zobrist hashing.

        Parameters:
        - board (Board): The chess board.

        Returns:
        - int: The computed Zobrist hash value for the board.
        """

        (
            colored_piece_types,
            board_turn,
            en_passant_file,
            castling_rights,
        ) = BoardInfoExtractor.full_hash_info(board)

        return _compute_hash(  # type: ignore
            np.uint64(0),
            colored_piece_types,
            self._piece_hashes,
            board_turn,
            self._turn_hash,
            en_passant_file,
            self._en_passant_hashes,
            castling_rights,
            self._castling_hashes,
        )

    def incremental_hash(self, initial_hash: np.uint64, board: Board):
        try:
            (
                colored_piece_types,
                board_turn,
                en_passant_file,
                castling_rights,
            ) = BoardInfoExtractor.incremental_hash_info(board)
        except:
            return initial_hash

        return _compute_hash(  # type: ignore
            np.uint64(initial_hash),
            colored_piece_types,
            self._piece_hashes,
            board_turn,
            self._turn_hash,
            en_passant_file,
            self._en_passant_hashes,
            castling_rights,
            self._castling_hashes,
        )
