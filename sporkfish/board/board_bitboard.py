from dataclasses import dataclass
from typing import Any, Dict, Optional

import chess


@dataclass(frozen=True)
class _BitboardSnapshot:
    """Cached bitboards for fast read access in evaluation/search hot paths."""

    pawns: int
    knights: int
    bishops: int
    rooks: int
    queens: int
    kings: int
    white_occ: int
    black_occ: int
    all_occ: int


class BoardBitboard(chess.Board):
    """Board implementation with explicit cached bitboards.

    This keeps a lightweight snapshot of piece and occupancy bitboards and updates
    it incrementally on `push`/`pop`/position reset operations. Move legality and
    rule handling are still delegated to python-chess.
    """

    def __init__(self, fen: str = chess.STARTING_FEN, chess960: bool = False) -> None:
        self._bb = _BitboardSnapshot(0, 0, 0, 0, 0, 0, 0, 0, 0)
        self._bb_history = [self._bb]
        super().__init__(fen=fen, chess960=chess960)
        self._refresh_cache()
        self._bb_history = [self._bb]

    def _refresh_cache(self) -> None:
        self._bb = _BitboardSnapshot(
            pawns=int(self.pawns),
            knights=int(self.knights),
            bishops=int(self.bishops),
            rooks=int(self.rooks),
            queens=int(self.queens),
            kings=int(self.kings),
            white_occ=int(self.occupied_co[chess.WHITE]),
            black_occ=int(self.occupied_co[chess.BLACK]),
            all_occ=int(self.occupied),
        )

    @staticmethod
    def _bit(square: chess.Square) -> int:
        return 1 << square

    def _incremental_push_snapshot(self, move: chess.Move) -> _BitboardSnapshot | None:
        """Return next snapshot via move deltas, or None when fallback is safer."""
        moving_piece = self.piece_type_at(move.from_square)
        if moving_piece is None:
            return None

        stm = self.turn
        from_bb = self._bit(move.from_square)
        to_bb = self._bit(move.to_square)
        is_castling = self.is_castling(move)
        is_capture = self.is_capture(move)
        is_ep = self.is_en_passant(move)

        captured_piece: Optional[chess.PieceType] = None
        captured_square: Optional[chess.Square] = None
        if is_capture:
            if is_ep:
                captured_piece = chess.PAWN
                captured_square = (
                    move.to_square - 8 if stm == chess.WHITE else move.to_square + 8
                )
            else:
                captured_piece = self.piece_type_at(move.to_square)
                captured_square = move.to_square
            if captured_piece is None or captured_square is None:
                return None

        pawns = self._bb.pawns
        knights = self._bb.knights
        bishops = self._bb.bishops
        rooks = self._bb.rooks
        queens = self._bb.queens
        kings = self._bb.kings

        # Remove moving piece from origin.
        if moving_piece == chess.PAWN:
            pawns &= ~from_bb
        elif moving_piece == chess.KNIGHT:
            knights &= ~from_bb
        elif moving_piece == chess.BISHOP:
            bishops &= ~from_bb
        elif moving_piece == chess.ROOK:
            rooks &= ~from_bb
        elif moving_piece == chess.QUEEN:
            queens &= ~from_bb
        elif moving_piece == chess.KING:
            kings &= ~from_bb

        # Remove captured piece from destination/captured square.
        if is_capture and captured_square is not None and captured_piece is not None:
            cap_bb = self._bit(captured_square)
            if captured_piece == chess.PAWN:
                pawns &= ~cap_bb
            elif captured_piece == chess.KNIGHT:
                knights &= ~cap_bb
            elif captured_piece == chess.BISHOP:
                bishops &= ~cap_bb
            elif captured_piece == chess.ROOK:
                rooks &= ~cap_bb
            elif captured_piece == chess.QUEEN:
                queens &= ~cap_bb
            elif captured_piece == chess.KING:
                kings &= ~cap_bb

        # Add moving/promoted piece at destination.
        promoted_piece = move.promotion
        placed_piece = promoted_piece if promoted_piece else moving_piece
        if placed_piece == chess.PAWN:
            pawns |= to_bb
        elif placed_piece == chess.KNIGHT:
            knights |= to_bb
        elif placed_piece == chess.BISHOP:
            bishops |= to_bb
        elif placed_piece == chess.ROOK:
            rooks |= to_bb
        elif placed_piece == chess.QUEEN:
            queens |= to_bb
        elif placed_piece == chess.KING:
            kings |= to_bb

        rook_from_bb = 0
        rook_to_bb = 0
        if is_castling:
            if stm == chess.WHITE and move.to_square == chess.G1:
                rook_from_bb = self._bit(chess.H1)
                rook_to_bb = self._bit(chess.F1)
            elif stm == chess.WHITE and move.to_square == chess.C1:
                rook_from_bb = self._bit(chess.A1)
                rook_to_bb = self._bit(chess.D1)
            elif stm == chess.BLACK and move.to_square == chess.G8:
                rook_from_bb = self._bit(chess.H8)
                rook_to_bb = self._bit(chess.F8)
            elif stm == chess.BLACK and move.to_square == chess.C8:
                rook_from_bb = self._bit(chess.A8)
                rook_to_bb = self._bit(chess.D8)
            else:
                return None

            rooks = (rooks & ~rook_from_bb) | rook_to_bb

        # Update occupancy deltas.
        if stm == chess.WHITE:
            white_occ = (self._bb.white_occ & ~from_bb) | to_bb
            black_occ = self._bb.black_occ
            if rook_from_bb:
                white_occ = (white_occ & ~rook_from_bb) | rook_to_bb
            if is_capture and captured_square is not None:
                black_occ &= ~self._bit(captured_square)
        else:
            black_occ = (self._bb.black_occ & ~from_bb) | to_bb
            white_occ = self._bb.white_occ
            if rook_from_bb:
                black_occ = (black_occ & ~rook_from_bb) | rook_to_bb
            if is_capture and captured_square is not None:
                white_occ &= ~self._bit(captured_square)

        all_occ = white_occ | black_occ
        return _BitboardSnapshot(
            pawns=pawns,
            knights=knights,
            bishops=bishops,
            rooks=rooks,
            queens=queens,
            kings=kings,
            white_occ=white_occ,
            black_occ=black_occ,
            all_occ=all_occ,
        )

    def push(self, move: chess.Move) -> None:
        next_snapshot = self._incremental_push_snapshot(move)
        super().push(move)
        if next_snapshot is not None:
            self._bb = next_snapshot
        else:
            self._refresh_cache()
        self._bb_history.append(self._bb)

    def pop(self) -> chess.Move:
        move = super().pop()
        # Restore previous cached snapshot in O(1) after unmake.
        if len(self._bb_history) > 1:
            self._bb_history.pop()
            self._bb = self._bb_history[-1]
        else:
            self._refresh_cache()
            self._bb_history = [self._bb]
        return move

    def reset(self) -> None:
        super().reset()
        self._refresh_cache()
        self._bb_history = [self._bb]

    def clear(self) -> None:
        super().clear()
        self._refresh_cache()
        self._bb_history = [self._bb]

    def set_fen(self, fen: str) -> None:
        super().set_fen(fen)
        self._refresh_cache()
        self._bb_history = [self._bb]

    def set_epd(self, epd: str) -> Dict[str, object]:
        parsed = super().set_epd(epd)
        self._refresh_cache()
        self._bb_history = [self._bb]
        return parsed

    def push_uci(self, move: str) -> None:
        # chess.Board.push_uci delegates to self.push(move), which already updates
        # the cache and snapshot history in this subclass.
        super().push_uci(move)

    def copy(self, *, stack: bool = True) -> "BoardBitboard":
        """Clone board state while keeping bitboard cache coherent."""
        cloned = super().copy(stack=stack)
        if not isinstance(cloned, BoardBitboard):
            raise TypeError("BoardBitboard.copy() did not return BoardBitboard")

        # Keep cached snapshot consistent with copied python-chess internals.
        cloned._refresh_cache()

        # Preserve history when stack is requested; otherwise keep a single root snapshot.
        if stack:
            cloned._bb_history = list(self._bb_history)
            if not cloned._bb_history:
                cloned._bb_history = [cloned._bb]
            cloned._bb = cloned._bb_history[-1]
        else:
            cloned._bb_history = [cloned._bb]
        return cloned

    def __deepcopy__(self, memo: Dict[int, Any]) -> "BoardBitboard":
        cloned = self.copy(stack=True)
        memo[id(self)] = cloned
        return cloned

    def __copy__(self) -> "BoardBitboard":
        return self.copy(stack=True)

    def pieces_mask(self, piece_type: chess.PieceType, color: chess.Color) -> int:
        if piece_type == chess.PAWN:
            piece_bb = self._bb.pawns
        elif piece_type == chess.KNIGHT:
            piece_bb = self._bb.knights
        elif piece_type == chess.BISHOP:
            piece_bb = self._bb.bishops
        elif piece_type == chess.ROOK:
            piece_bb = self._bb.rooks
        elif piece_type == chess.QUEEN:
            piece_bb = self._bb.queens
        elif piece_type == chess.KING:
            piece_bb = self._bb.kings
        else:
            return 0
        side_occ = self._bb.white_occ if color == chess.WHITE else self._bb.black_occ
        return piece_bb & side_occ

    def piece_bitboards(self) -> _BitboardSnapshot:
        """Expose cached bitboards for callers that need all masks together."""
        return self._bb

    def king(self, color: chess.Color) -> Optional[chess.Square]:
        king_bb = self.pieces_mask(chess.KING, color)
        if not king_bb:
            return None
        return chess.msb(king_bb)
