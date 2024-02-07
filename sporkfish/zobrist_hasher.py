from dataclasses import dataclass
from typing import Optional

import chess
import numpy as np
from numba import njit

from .board.board import Board

_int64_min_val = np.iinfo(np.int64).min
_int64_max_val = np.iinfo(np.int64).max
_int8_max_val = np.iinfo(np.int8).max

# TODO: we may revisit this in future as people claim this can affect collision chances
# We set these globally as we want these to be shared across all Zobrist hashers
np.random.seed(10101010)
_piece_keys = np.random.randint(
    _int64_min_val, _int64_max_val, size=(64, 12), dtype=np.int64
)
_turn_key = np.random.randint(_int64_min_val, _int64_max_val, dtype=np.int64)
_en_passant_keys = np.random.randint(
    _int64_min_val, _int64_max_val, size=8, dtype=np.int64
)
_castling_keys = np.random.randint(
    _int64_min_val, _int64_max_val, size=16, dtype=np.int64
)


@njit(cache=True, nogil=True)
def _aggregate_piece_hash(
    board_hash: np.int64, squares: np.ndarray, colored_piece_types: np.ndarray
) -> np.int64:
    num_pieces = len(squares)
    assert (
        num_pieces == len(colored_piece_types)
    ), f"Expected the same number of squares and colored_piece_types but got length {num_pieces}, {len(colored_piece_types)} respectively."
    new_board_hash = board_hash
    for idx in range(num_pieces):
        new_board_hash ^= _piece_keys[squares[idx], colored_piece_types[idx]]  # type: ignore
    return new_board_hash


@njit(cache=True, nogil=True)
def _turn_hash(board_hash: np.int64) -> np.int64:
    return board_hash ^ _turn_key


@njit(cache=True, nogil=True)
def _conditional_turn_hash(board_hash: np.int64, board_turn: bool) -> np.int64:
    return board_hash ^ _turn_key if board_turn else board_hash


@njit(cache=True, nogil=True)
def _en_passant_hash(board_hash: np.int64, en_passant_file: np.int8) -> np.int64:
    return (  # type: ignore
        board_hash ^ _en_passant_keys[en_passant_file]
        if en_passant_file != _int8_max_val
        else board_hash
    )


@njit(cache=True, nogil=True)
def _castling_hash(board_hash: np.int64, castling_rights: np.ndarray) -> np.int64:
    num_castle_rights = len(castling_rights)
    assert (
        num_castle_rights == 4
    ), "There should only be 4 castling rights to check, 2 for black, 2 for white."

    # This transforms the castling rights from an array of 4 bools
    # into an int from [0, 15].
    castling_keys_idx = 0
    for idx in range(num_castle_rights):
        if castling_rights[idx]:
            castling_keys_idx += 1 << idx
    return board_hash ^ _castling_keys[castling_keys_idx]  # type: ignore


@njit(cache=True, nogil=True)
def _full_zobrist_hash(
    squares: np.ndarray,
    colored_piece_types: np.ndarray,
    board_turn: bool,
    en_passant_file: np.int64,
    castling_rights: np.ndarray,
) -> np.int64:
    # Here we send all the colored_piece types
    board_hash = _aggregate_piece_hash(np.int64(0), squares, colored_piece_types)
    board_hash = _conditional_turn_hash(board_hash, board_turn)
    board_hash = _en_passant_hash(board_hash, en_passant_file)
    board_hash = _castling_hash(board_hash, castling_rights)
    return board_hash


@njit(cache=True, nogil=True)
def _incremental_zobrist_hash(
    initial_hash: np.int64,
    squares: np.ndarray,
    colored_piece_types: np.ndarray,
    prev_en_passant_file: np.int8,
    curr_en_passant_file: np.int8,
    prev_castling_rights: np.ndarray,
    curr_castling_rights: np.ndarray,
) -> np.int64:
    # Here we send in only the colored_piece_types for the new move
    # If capturing, the original piece is sent in to be XOR'd out
    # Promotions are included already as part of the colored_piece_type for the new move
    board_hash = _aggregate_piece_hash(initial_hash, squares, colored_piece_types)

    # We hash on every turn, to XOR out the previous turn hash.
    board_hash = _turn_hash(board_hash)

    # We do pairwise hashes for en en passant and castling, based on the previous and current rights.
    # The first one XOR's away the previous rights and the second adds the current rights.
    # If previous_rights == current_rights then we obtain the same result as before.
    # This is likely faster than checking if both arrays are the same (to be tested).
    board_hash = _en_passant_hash(board_hash, prev_en_passant_file)
    board_hash = _en_passant_hash(board_hash, curr_en_passant_file)

    board_hash = _castling_hash(board_hash, prev_castling_rights)
    board_hash = _castling_hash(board_hash, curr_castling_rights)

    return board_hash


@dataclass
class ZobristStateInfo:
    """
    Store the information from the current state of the board.
    It contains board level information be used in computation of the Zobrist incremental hash.
    """

    zobrist_hash: np.int64
    ep_file: np.int8
    castling_rights: np.ndarray


class ZobristHasher:
    def _init_(self) -> None:
        """
        Initialize the Zobrist Hasher object, used to hash board positions.
        This allows caching via the transposition table, so we don't have to evaluate positions twice.
        """

    @staticmethod
    def _parse_ep_file(board: Board) -> np.int8:
        return (
            np.int8(chess.square_file(board.ep_square))
            if board.ep_square
            else _int8_max_val
        )

    @staticmethod
    def _parse_castling_rights(board: Board) -> np.ndarray:
        return np.array(  # type: ignore
            [
                board.has_kingside_castling_rights(chess.WHITE),
                board.has_queenside_castling_rights(chess.WHITE),
                board.has_kingside_castling_rights(chess.BLACK),
                board.has_queenside_castling_rights(chess.BLACK),
            ],
            dtype=bool,
        )

    def full_zobrist_hash(self, board: Board) -> ZobristStateInfo:
        """
        Hashes the given a static chess board using Zobrist hashing.

        Parameters:
        - board (Board): The chess board.

        Returns:
        - int: The computed Zobrist hash value for the board.
        """
        squares_colored_piece_types = np.array(
            [
                [square, hash(piece)]
                for square in chess.SQUARES
                if (piece := board.piece_at(square))
            ],
            dtype=np.int8,
        )
        squares = squares_colored_piece_types[:, 0]
        colored_piece_types = squares_colored_piece_types[:, 1]

        ep_file = ZobristHasher._parse_ep_file(board)
        castling_rights = ZobristHasher._parse_castling_rights(board)

        zobrist_hash = _full_zobrist_hash(  # type: ignore
            squares, colored_piece_types, board.turn, ep_file, castling_rights
        )
        return ZobristStateInfo(zobrist_hash, ep_file, castling_rights)

    def incremental_zobrist_hash(
        self,
        board: Board,
        move: chess.Move,
        prev_state: ZobristStateInfo,
        captured_piece: Optional[chess.Piece],
    ) -> ZobristStateInfo:
        # This isn't right, it should use the piece type before the move
        to_color_piece_type = hash(board.piece_at(move.to_square))
        squares = [move.from_square]
        colored_piece_types = [to_color_piece_type]

        if move.promotion:
            squares.append(move.to_square)
            colored_piece_types.append(hash(board.piece_at(move.to_square)))
        else:
            squares.append(move.to_square)
            colored_piece_types.append(to_color_piece_type)

        if captured_piece:
            squares.append(move.to_square)
            colored_piece_types.append(hash(captured_piece))

        squares = np.array(squares, dtype=np.int8)
        colored_piece_types = np.array(colored_piece_types, dtype=np.int8)

        ep_file = ZobristHasher._parse_ep_file(board)
        castling_rights = ZobristHasher._parse_castling_rights(board)
        zobrist_hash = _incremental_zobrist_hash(
            prev_state.zobrist_hash,
            squares,
            colored_piece_types,
            prev_state.ep_file,
            ep_file,
            prev_state.castling_rights,
            castling_rights,
        )
        return ZobristStateInfo(zobrist_hash, ep_file, castling_rights)
