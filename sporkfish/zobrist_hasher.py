from dataclasses import dataclass

import chess
import numpy as np

from sporkfish.board.board import Board

_INT64_MIN_VAL = np.iinfo(np.int64).min
_INT64_MAX_VAL = np.iinfo(np.int64).max

# Sentinel for "no en-passant file" — plain Python int (faster than np.int8 in hot path).
_NO_EP_FILE = 127


def zobrist_piece_index(piece_type: int, color: bool) -> int:
    """
    Compute the Zobrist table index for a piece, matching chess.Piece.__hash__
    but without creating a Piece object.

    White: piece_type - 1  (0-5)
    Black: piece_type + 5  (6-11)
    """
    return (piece_type - 1) if color else (piece_type + 5)


# TODO: we may revisit this in future as people claim this can affect collision chances
np.random.seed(10101010)

# Numpy arrays are kept for the vectorised full-hash path.
_PIECE_KEYS_NP = np.random.randint(
    _INT64_MIN_VAL, _INT64_MAX_VAL, size=(64, 12), dtype=np.int64
)
_TURN_KEY_NP = np.random.randint(_INT64_MIN_VAL, _INT64_MAX_VAL, dtype=np.int64)
_EN_PASSANT_KEYS_NP = np.random.randint(
    _INT64_MIN_VAL, _INT64_MAX_VAL, size=8, dtype=np.int64
)
_CASTLING_KEYS_NP = np.random.randint(
    _INT64_MIN_VAL, _INT64_MAX_VAL, size=16, dtype=np.int64
)

# Pure-Python int tables for the incremental hash hot path.
# List-of-list lookup avoids numpy scalar construction overhead on every move.
_PIECE_KEYS: list[list[int]] = [
    [int(_PIECE_KEYS_NP[sq, pt]) for pt in range(12)] for sq in range(64)
]
_TURN_KEY: int = int(_TURN_KEY_NP)
_EP_KEYS: list[int] = [int(x) for x in _EN_PASSANT_KEYS_NP]
_CASTLING_KEYS: list[int] = [int(x) for x in _CASTLING_KEYS_NP]


@dataclass
class ZobristStateInfo:
    """
    Stores the information from the current state of the board.

    :param zobrist_hash: The Zobrist hash value representing the current board state
    :type zobrist_hash: int
    :param ep_file: The file where en passant is possible, or _NO_EP_FILE (127) if none.
    :type ep_file: int
    :param castling_rights: 4-bit integer encoding castling rights (0–15).
        bit 0 = white kingside, bit 1 = white queenside,
        bit 2 = black kingside, bit 3 = black queenside.
    :type castling_rights: int
    """

    zobrist_hash: int
    ep_file: int
    castling_rights: int


class ZobristHasher:
    """
    Incremental Zobrist hashing for the transposition table.

    Two methods are provided:
    - ``full_zobrist_hash``: hashes the entire board from scratch (slow, called once
      per search at the root).
    - ``incremental_zobrist_hash``: updates the hash after a single move (fast, called
      at every node).

    All Numba / JIT dependencies have been removed.  The hot incremental path operates
    entirely in Python-int space (no numpy scalar allocation) to minimise overhead.
    """

    @staticmethod
    def _parse_ep_file(board: Board) -> int:
        """
        Return the en-passant file as a plain Python int, or _NO_EP_FILE if none.
        """
        return (
            int(chess.square_file(board.ep_square)) if board.ep_square else _NO_EP_FILE
        )

    @staticmethod
    def _parse_castling_rights(board: Board) -> int:
        """
        Return a 4-bit integer encoding the four castling rights.

        Bit layout: bit 0 = white kingside, bit 1 = white queenside,
                    bit 2 = black kingside, bit 3 = black queenside.
        """
        return (
            int(board.has_kingside_castling_rights(chess.WHITE))
            | (int(board.has_queenside_castling_rights(chess.WHITE)) << 1)
            | (int(board.has_kingside_castling_rights(chess.BLACK)) << 2)
            | (int(board.has_queenside_castling_rights(chess.BLACK)) << 3)
        )

    def full_zobrist_hash(self, board: Board) -> ZobristStateInfo:
        """
        Compute the Zobrist hash value for the entire board from scratch.

        Uses vectorised numpy XOR reduction over all occupied squares.

        :param board: The chess board.
        :type board: Board
        :return: ZobristStateInfo for the current position.
        :rtype: ZobristStateInfo
        """
        piece_map = board.piece_map()
        if piece_map:
            squares = np.array(list(piece_map.keys()), dtype=np.int32)
            colored_piece_types = np.array(
                [hash(p) for p in piece_map.values()], dtype=np.int32
            )
            board_hash = int(
                np.bitwise_xor.reduce(_PIECE_KEYS_NP[squares, colored_piece_types])
            )
        else:
            board_hash = 0

        if board.turn:
            board_hash ^= int(_TURN_KEY_NP)

        ep_file = ZobristHasher._parse_ep_file(board)
        if ep_file != _NO_EP_FILE:
            board_hash ^= int(_EN_PASSANT_KEYS_NP[ep_file])

        castling_rights = ZobristHasher._parse_castling_rights(board)
        board_hash ^= int(_CASTLING_KEYS_NP[castling_rights])

        return ZobristStateInfo(board_hash, ep_file, castling_rights)

    def incremental_zobrist_hash(
        self,
        board: Board,
        move: chess.Move,
        prev_state: ZobristStateInfo,
        from_cpt: int,
        captured_cpt: int,
    ) -> ZobristStateInfo:
        """
        Compute the Zobrist hash incrementally after a move.

        All arithmetic is done with plain Python ints to avoid numpy scalar
        allocation on every call.

        :param board: The chess board *after* the move has been applied.
        :param move: The move that was just made.
        :param prev_state: Zobrist state *before* the move.
        :param from_cpt: Colored piece type index (0-11) of the moving piece,
                         matching chess.Piece.__hash__: (piece_type - 1) for white,
                         (piece_type + 5) for black.
        :param captured_cpt: Colored piece type index of the captured piece,
                             or -1 if no capture.
        :return: Updated ZobristStateInfo.
        :rtype: ZobristStateInfo
        """
        from_sq = move.from_square
        to_sq = move.to_square

        # For promotions the piece type on to_sq differs from the moving piece.
        if move.promotion:
            from_color = from_cpt < 6  # True if white
            to_cpt = (move.promotion - 1) if from_color else (move.promotion + 5)
        else:
            to_cpt = from_cpt

        ep_file = ZobristHasher._parse_ep_file(board)
        castling_rights = ZobristHasher._parse_castling_rights(board)

        pk = _PIECE_KEYS
        h = int(prev_state.zobrist_hash)
        h ^= pk[from_sq][from_cpt]  # remove piece from source square
        h ^= pk[to_sq][to_cpt]  # place piece on destination square
        if captured_cpt >= 0:
            h ^= pk[to_sq][captured_cpt]  # remove captured piece

        h ^= _TURN_KEY  # flip side to move

        # En-passant: XOR out previous file, XOR in new file.
        prev_ep = prev_state.ep_file
        if prev_ep != _NO_EP_FILE:
            h ^= _EP_KEYS[prev_ep]
        if ep_file != _NO_EP_FILE:
            h ^= _EP_KEYS[ep_file]

        # Castling rights: XOR out previous rights, XOR in new rights.
        h ^= _CASTLING_KEYS[prev_state.castling_rights]
        h ^= _CASTLING_KEYS[castling_rights]

        return ZobristStateInfo(h, ep_file, castling_rights)
