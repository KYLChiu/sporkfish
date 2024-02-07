from dataclasses import dataclass
from typing import Optional

import chess
import numpy as np
from numba import njit

from .board.board import Board

# TODO: we may revisit this in future as people claim this can affect collision chances
# We set these globally as we want these to be shared across all Zobrist hashers
np.random.seed(10101010)
_piece_keys = np.random.randint(0, 2**64, size=(64, 12), dtype=np.uint64)
_turn_key = np.random.randint(0, 2**64, dtype=np.uint64)
_en_passant_keys = np.random.randint(0, 2**64, size=8, dtype=np.uint64)
_castling_keys = np.random.randint(0, 2**64, size=16, dtype=np.uint64)


@njit(cache=True, nogil=True)
def _aggregate_piece_hash(
    board_hash: np.uint64, colored_piece_types: np.ndarray
) -> np.uint64:
    new_board_hash = board_hash
    for square, color_piece_type in colored_piece_types:
        new_board_hash ^= _piece_keys[square, color_piece_type]  # type: ignore
    return new_board_hash


@njit(cache=True, nogil=True)
def _turn_hash(board_hash: np.uint64) -> np.uint64:
    return board_hash ^ _turn_key


@njit(cache=True, nogil=True)
def _conditional_turn_hash(board_hash: np.uint64, board_turn: bool) -> np.uint64:
    return board_hash ^ _turn_key if board_turn else board_hash


@njit(cache=True, nogil=True)
def _en_passant_hash(board_hash: np.uint64, en_passant_file: np.uint8) -> np.uint64:
    return (  # type: ignore
        board_hash ^ _en_passant_keys[en_passant_file]
        if en_passant_file != np.uint8(-1)
        else board_hash
    )


@njit(cache=True, nogil=True)
def _castling_hash(board_hash: np.uint64, castling_rights: np.ndarray) -> np.uint64:
    # This transforms the castling rights from an array of 4 bools
    # into an int from [0, 15].
    assert (
        len(castling_rights) == 4
    ), "There should only be 4 castling rights to check, 2 for black, 2 for white."

    castling_keys_idx = 0
    for idx in range(len(castling_rights)):
        if castling_rights[idx]:
            castling_keys_idx += 1 << idx
    return board_hash ^ _castling_keys[castling_keys_idx]  # type: ignore


@njit(cache=True, nogil=True)
def full_zobrist_hash(
    colored_piece_types: np.ndarray,
    board_turn: bool,
    en_passant_file: np.uint64,
    castling_rights: np.ndarray,
) -> np.uint64:
    # Here we send all the colored_piece types
    board_hash = _aggregate_piece_hash(np.uint64(0), colored_piece_types)
    board_hash = _conditional_turn_hash(board_hash, board_turn)
    board_hash = _en_passant_hash(board_hash, en_passant_file)
    board_hash = _castling_hash(board_hash, castling_rights)
    return board_hash


@njit(cache=True, nogil=True)
def incremental_zobrist_hash(
    initial_hash: np.uint64,
    colored_piece_types: np.ndarray,
    prev_en_passant_file: np.uint8,
    curr_en_passant_file: np.uint8,
    prev_castling_rights: np.uint8,
    curr_castling_rights: np.uint8,
) -> np.uint64:
    # Here we send in only the colored_piece_types for the new move
    # If capturing, the original piece is sent in to be XOR'd out
    # Promotions are included already as part of the colored_piece_type for the new move
    board_hash = _aggregate_piece_hash(initial_hash, colored_piece_types)

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

    zobrist_hash: np.uint64
    ep_file: np.uint64
    castling_rights: np.ndarray


class ZobristHasher:
    def _init_(self) -> None:
        """
        Initialize the Zobrist Hasher object, used to hash board positions.
        This allows caching via the transposition table, so we don't have to evaluate positions twice.
        """

    @staticmethod
    def _parse_ep_file(board: Board) -> np.uint8:
        return (
            np.uint8(chess.square_file(board.ep_square))
            if board.ep_square
            else np.uint8(-1)
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

        colored_piece_types = np.array(
            [
                # TODO: consider more cache friendly of doing this
                [square, hash(piece)]
                for square in chess.SQUARES
                if (piece := board.piece_at(square))
            ],
            dtype=np.uint8,
        )
        ep_file = ZobristHasher._parse_ep_file(board)
        castling_rights = ZobristHasher._parse_castling_rights(board)

        zobrist_hash = full_zobrist_hash(  # type: ignore
            colored_piece_types, board.turn, ep_file, castling_rights
        )
        return ZobristStateInfo(zobrist_hash, ep_file, castling_rights)

    def incremental_zobrist_hash(
        self,
        board: Board,
        move: chess.Move,
        prev_state: ZobristStateInfo,
        captured_piece: Optional[chess.Piece],
    ) -> ZobristStateInfo:
        colored_piece_types = np.array(
            [
                [move.from_square, hash(board.piece_at(move.from_square))],
                [move.to_square, hash(board.piece_at(move.to_square))],
            ],
            dtype=np.uint8,
        )
        if captured_piece:
            np.append(
                colored_piece_types,
                [[move.to_square, hash(captured_piece)]],
            )
        ep_file = ZobristHasher._parse_ep_file(board)
        castling_rights = ZobristHasher._parse_castling_rights(board)
        zobrist_hash = incremental_zobrist_hash(
            prev_state.zobrist_hash,
            colored_piece_types,
            prev_state.ep_file,
            ep_file,
            prev_state.castling_rights,
            castling_rights,
        )
        return ZobristStateInfo(zobrist_hash, ep_file, castling_rights)
