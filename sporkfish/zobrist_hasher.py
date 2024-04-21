from dataclasses import dataclass
from typing import Optional

import chess
import numpy as np
from numba import njit

from sporkfish.board.board import Board

_INT64_MIN_VAL = np.iinfo(np.int64).min
_INT64_MAX_VAL = np.iinfo(np.int64).max
_INT8_MAX_VAL = np.iinfo(np.int8).max

# TODO: we may revisit this in future as people claim this can affect collision chances
np.random.seed(10101010)
_PIECE_KEYS = np.random.randint(
    _INT64_MIN_VAL, _INT64_MAX_VAL, size=(64, 12), dtype=np.int64
)
_TURN_KEY = np.random.randint(_INT64_MIN_VAL, _INT64_MAX_VAL, dtype=np.int64)
_EN_PASSANT_KEYS = np.random.randint(
    _INT64_MIN_VAL, _INT64_MAX_VAL, size=8, dtype=np.int64
)
_CASTLING_KEYS = np.random.randint(
    _INT64_MIN_VAL, _INT64_MAX_VAL, size=16, dtype=np.int64
)


@njit(cache=True, nogil=True)
def _aggregate_piece_hash(
    board_hash: np.int64, squares: np.ndarray, colored_piece_types: np.ndarray
) -> np.int64:
    num_pieces = len(squares)
    assert num_pieces == len(
        colored_piece_types
    ), f"Expected the same number of squares and colored_piece_types but got length {num_pieces}, {len(colored_piece_types)} respectively."
    new_board_hash = board_hash
    for idx in range(num_pieces):
        new_board_hash ^= _PIECE_KEYS[squares[idx], colored_piece_types[idx]]  # type: ignore
    return new_board_hash


@njit(cache=True, nogil=True)
def _turn_hash(board_hash: np.int64) -> np.int64:
    return board_hash ^ _TURN_KEY


@njit(cache=True, nogil=True)
def _conditional_turn_hash(board_hash: np.int64, board_turn: bool) -> np.int64:
    return board_hash ^ _TURN_KEY if board_turn else board_hash


@njit(cache=True, nogil=True)
def _en_passant_hash(board_hash: np.int64, en_passant_file: np.int8) -> np.int64:
    return (  # type: ignore
        board_hash ^ _EN_PASSANT_KEYS[en_passant_file]
        if en_passant_file != _INT8_MAX_VAL
        else board_hash
    )


@njit(cache=True, nogil=True)
def _castling_hash(board_hash: np.int64, castling_rights: np.ndarray) -> np.int64:
    num_castle_rights = len(castling_rights)
    assert (
        num_castle_rights == 4
    ), f"There should only be 4 castling rights to check, 2 for black, 2 for white, but got {num_castle_rights}."

    # This transforms the castling rights from an array of 4 bools
    # into an int from [0, 15].
    castling_keys_idx = 0
    for idx in range(num_castle_rights):
        if castling_rights[idx]:
            castling_keys_idx += 1 << idx
    return board_hash ^ _CASTLING_KEYS[castling_keys_idx]  # type: ignore


@njit(cache=True, nogil=True)
def _full_zobrist_hash(
    squares: np.ndarray,
    colored_piece_types: np.ndarray,
    board_turn: bool,
    en_passant_file: np.int64,
    castling_rights: np.ndarray,
) -> np.int64:
    # Here we send all the colored_piece types for all pieces which exist on all the board
    board_hash = _aggregate_piece_hash(np.int64(0), squares, colored_piece_types)
    board_hash = _conditional_turn_hash(board_hash, board_turn)
    board_hash = _en_passant_hash(board_hash, en_passant_file)
    board_hash = _castling_hash(board_hash, castling_rights)
    return board_hash  # type: ignore


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
    # Here we send in only the colored_piece_types for the input move
    # If capturing, the original piece is sent in to be XOR'd out
    # Promotions are included already as part of the colored_piece_type for the new move
    board_hash = _aggregate_piece_hash(initial_hash, squares, colored_piece_types)

    # We hash on every turn, to XOR out the previous turn hash.
    board_hash = _turn_hash(board_hash)

    # We do pairwise hashes for en passant and castling, based on the previous and current rights.
    # The first one XOR's away the previous rights and the second adds the current rights.
    # If previous_rights == current_rights then we obtain the same result as before.
    # This is likely faster than checking if both arrays are the same (to be tested).
    board_hash = _en_passant_hash(board_hash, prev_en_passant_file)
    board_hash = _en_passant_hash(board_hash, curr_en_passant_file)

    board_hash = _castling_hash(board_hash, prev_castling_rights)
    board_hash = _castling_hash(board_hash, curr_castling_rights)

    return board_hash  # type: ignore


@dataclass
class ZobristStateInfo:
    """
    Stores the information from the current state of the board.

    :param zobrist_hash: The Zobrist hash value representing the current board state
    :type zobrist_hash: np.int64
    :param ep_file: The file where en passant is possible
    :type ep_file: np.int8
    :param castling_rights: An array representing castling rights.
    :type castling_rights: np.ndarray
    """

    zobrist_hash: np.int64
    ep_file: np.int8
    castling_rights: np.ndarray


class ZobristHasher:
    """
    This allows caching via the transposition table, so we don't have to evaluate positions twice.
    Two methods are provided:
    - One hashes the board statically, doing this by retrieving the full board and hence is slow.
    - The other hashes the board after a move is made (i.e. incrementally), and is designed to be faster.
    """

    @staticmethod
    def _parse_ep_file(board: Board) -> np.int8:
        """
        Parse the en passant file from the given board.

        :param board: The chess board.
        :type board: Board

        :return: The file where en passant is possible.
        :rtype: np.int8
        """
        return (
            np.int8(chess.square_file(board.ep_square))  # type: ignore
            if board.ep_square
            else _INT8_MAX_VAL
        )

    @staticmethod
    def _parse_castling_rights(board: Board) -> np.ndarray:
        """
        Parse the castling rights from the given board.

        :param board: The chess board.
        :type board: Board

        :return: An array representing castling rights.
        :rtype: np.ndarray
        """
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
        Compute the Zobrist hash value for the entire board.

        :param board: The chess board.
        :type board: Board

        :return: An object containing the Zobrist hash value and other board state information.
        :rtype: ZobristStateInfo
        """
        # colored_piece_types for all pieces that exist on the board
        squares_colored_piece_types = np.array(
            [
                [square, hash(piece)]
                for square in chess.SQUARES
                if (piece := board.piece_at(square))
            ],
            dtype=np.int8,
        )
        # Splice into two arrays
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
        previous_from_square_piece: chess.Piece,
        captured_piece: Optional[chess.Piece],
    ) -> ZobristStateInfo:
        """
        Compute the Zobrist hash value incrementally after a move.

        :param board: The chess board.
        :type board: Board
        :param move: The move being made.
        :type move: chess.Move
        :param prev_state: The previous Zobrist state information.
        :type prev_state: ZobristStateInfo
        :param previous_from_square_piece: The piece from the originating square of move.
        :type previous_from_square_piece: chess.Piece
        :param captured_piece: The piece captured, if any, defaults to None
        :type captured_piece: Optional[chess.Piece]

        :return: An object containing the updated Zobrist hash value and other board state information.
        :rtype: ZobristStateInfo
        """
        from_color_piece_type = hash(previous_from_square_piece)

        # XOR out the previous from square piece
        squares_list = [move.from_square]
        colored_piece_types_list = [from_color_piece_type]

        # XOR in the to square piece, piece type depending on if promoted or not
        squares_list.append(move.to_square)
        if move.promotion:
            colored_piece_types_list.append(hash(board.piece_at(move.to_square)))
        else:
            colored_piece_types_list.append(from_color_piece_type)

        # XOR out the captured piece if exists
        if captured_piece:
            squares_list.append(move.to_square)
            colored_piece_types_list.append(hash(captured_piece))

        squares = np.array(squares_list, dtype=np.int8)
        colored_piece_types = np.array(colored_piece_types_list, dtype=np.int8)

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
