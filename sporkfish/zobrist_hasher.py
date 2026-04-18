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
    assert (
        num_pieces == len(colored_piece_types)
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
def _castling_hash(board_hash: np.int64, castling_rights_int: np.int8) -> np.int64:
    # castling_rights_int is a pre-computed 4-bit integer (0–15):
    #   bit 0 = white kingside, bit 1 = white queenside,
    #   bit 2 = black kingside, bit 3 = black queenside.
    # Indexing directly avoids the array-iteration loop in the original version.
    return board_hash ^ _CASTLING_KEYS[castling_rights_int]  # type: ignore


@njit(cache=True, nogil=True)
def _full_zobrist_hash(
    squares: np.ndarray,
    colored_piece_types: np.ndarray,
    board_turn: bool,
    en_passant_file: np.int64,
    castling_rights_int: np.int8,
) -> np.int64:
    board_hash = _aggregate_piece_hash(np.int64(0), squares, colored_piece_types)
    board_hash = _conditional_turn_hash(board_hash, board_turn)
    board_hash = _en_passant_hash(board_hash, en_passant_file)
    board_hash = _castling_hash(board_hash, castling_rights_int)
    return board_hash  # type: ignore


# Scalar variants of _aggregate_piece_hash to avoid np.array() construction
# in the hot incremental_zobrist_hash path.  Profile showed np.array() was
# called ~18k times; replacing it with direct XOR eliminates that overhead.
@njit(cache=True, nogil=True)
def _xor_pieces_2(
    h: np.int64,
    sq0: np.int8,
    pt0: np.int8,
    sq1: np.int8,
    pt1: np.int8,
) -> np.int64:
    return h ^ _PIECE_KEYS[sq0, pt0] ^ _PIECE_KEYS[sq1, pt1]  # type: ignore


@njit(cache=True, nogil=True)
def _xor_pieces_3(
    h: np.int64,
    sq0: np.int8,
    pt0: np.int8,
    sq1: np.int8,
    pt1: np.int8,
    sq2: np.int8,
    pt2: np.int8,
) -> np.int64:
    return h ^ _PIECE_KEYS[sq0, pt0] ^ _PIECE_KEYS[sq1, pt1] ^ _PIECE_KEYS[sq2, pt2]  # type: ignore


@njit(cache=True, nogil=True)
def _incremental_zobrist_hash(
    initial_hash: np.int64,
    squares: np.ndarray,
    colored_piece_types: np.ndarray,
    prev_en_passant_file: np.int8,
    curr_en_passant_file: np.int8,
    prev_castling_rights_int: np.int8,
    curr_castling_rights_int: np.int8,
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
    board_hash = _en_passant_hash(board_hash, prev_en_passant_file)
    board_hash = _en_passant_hash(board_hash, curr_en_passant_file)

    board_hash = _castling_hash(board_hash, prev_castling_rights_int)
    board_hash = _castling_hash(board_hash, curr_castling_rights_int)

    return board_hash  # type: ignore


@dataclass
class ZobristStateInfo:
    """
    Stores the information from the current state of the board.

    :param zobrist_hash: The Zobrist hash value representing the current board state
    :type zobrist_hash: np.int64
    :param ep_file: The file where en passant is possible
    :type ep_file: np.int8
    :param castling_rights: 4-bit integer encoding castling rights (0–15).
        bit 0 = white kingside, bit 1 = white queenside,
        bit 2 = black kingside, bit 3 = black queenside.
        Stored as an int rather than np.ndarray to avoid array allocation on every
        incremental hash update.
    :type castling_rights: int
    """

    zobrist_hash: np.int64
    ep_file: np.int8
    castling_rights: int


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
    def _parse_castling_rights(board: Board) -> int:
        """
        Parse the castling rights from the given board as a 4-bit integer (0–15).

        Encoding: bit 0 = white kingside, bit 1 = white queenside,
                  bit 2 = black kingside, bit 3 = black queenside.

        Returning a plain int instead of np.ndarray eliminates one np.array()
        allocation per incremental hash call (profile showed ~12k np.array calls
        just from castling rights).

        :param board: The chess board.
        :type board: Board

        :return: 4-bit integer encoding the four castling rights.
        :rtype: int
        """
        return (
            int(board.has_kingside_castling_rights(chess.WHITE))
            | (int(board.has_queenside_castling_rights(chess.WHITE)) << 1)
            | (int(board.has_kingside_castling_rights(chess.BLACK)) << 2)
            | (int(board.has_queenside_castling_rights(chess.BLACK)) << 3)
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
        from_color_piece_type = np.int8(hash(previous_from_square_piece))
        to_sq = np.int8(move.to_square)
        from_sq = np.int8(move.from_square)

        # Determine the piece type XOR'd into to_square.
        to_color_piece_type = (
            np.int8(hash(board.piece_at(move.to_square)))
            if move.promotion
            else from_color_piece_type
        )

        ep_file = ZobristHasher._parse_ep_file(board)
        castling_rights = ZobristHasher._parse_castling_rights(board)

        # Use scalar numba helpers (_xor_pieces_2 / _xor_pieces_3) to avoid
        # building np.array([...]) lists for just 2-3 elements.
        # Profile showed np.array() was called ~12k times from this path alone.
        if captured_piece:
            # 3 XORs: remove from_sq piece, add to_sq piece, remove captured piece.
            zobrist_hash = _xor_pieces_3(
                prev_state.zobrist_hash,
                from_sq,
                from_color_piece_type,
                to_sq,
                to_color_piece_type,
                to_sq,
                np.int8(hash(captured_piece)),
            )
        else:
            # 2 XORs: remove from_sq piece, add to_sq piece.
            zobrist_hash = _xor_pieces_2(
                prev_state.zobrist_hash,
                from_sq,
                from_color_piece_type,
                to_sq,
                to_color_piece_type,
            )

        # XOR turn, en-passant and castling rights (pairwise to XOR out old and in new).
        zobrist_hash = np.int64(zobrist_hash) ^ _TURN_KEY
        zobrist_hash = _en_passant_hash(zobrist_hash, prev_state.ep_file)
        zobrist_hash = _en_passant_hash(zobrist_hash, ep_file)
        zobrist_hash = _castling_hash(zobrist_hash, np.int8(prev_state.castling_rights))
        zobrist_hash = _castling_hash(zobrist_hash, np.int8(castling_rights))

        return ZobristStateInfo(zobrist_hash, ep_file, castling_rights)
