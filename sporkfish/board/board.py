from typing import Any, Dict, Optional, Protocol, runtime_checkable

import chess


@runtime_checkable
class Board(Protocol):
    """
    Protocol defining the chess board interface. Using Protocol instead of ABC
    allows BoardPyChess to subclass chess.Board directly (zero wrapper overhead)
    while still providing type-safe structural checking at call sites.
    """

    # --- Board mutators ---
    def push(self, move: chess.Move) -> None:
        ...

    def push_uci(self, move: str) -> None:
        ...

    def pop(self) -> chess.Move:
        ...

    def reset(self) -> None:
        ...

    def set_fen(self, fen: str) -> None:
        ...

    def set_epd(self, epd: str) -> Dict[str, Any]:
        ...

    # --- Board information ---
    @property
    def turn(self) -> chess.Color:
        ...

    @property
    def ep_square(self) -> Optional[chess.Square]:
        ...

    @property
    def legal_moves(self) -> Any:
        ...

    def piece_at(self, square: chess.Square) -> Optional[chess.Piece]:
        ...

    def piece_type_at(self, square: chess.Square) -> Optional[chess.PieceType]:
        ...

    def color_at(self, square: chess.Square) -> Optional[chess.Color]:
        ...

    def is_capture(self, move: chess.Move) -> bool:
        ...

    def is_en_passant(self, move: chess.Move) -> bool:
        ...

    def is_check(self) -> bool:
        ...

    def is_game_over(self, *, claim_draw: bool = False) -> bool:
        ...

    def outcome(self, *, claim_draw: bool = False) -> Optional[chess.Outcome]:
        ...

    def fen(self) -> str:
        ...

    def has_queenside_castling_rights(self, color: chess.Color) -> bool:
        ...

    def has_kingside_castling_rights(self, color: chess.Color) -> bool:
        ...

    def piece_map(self) -> Dict[chess.Square, chess.Piece]:
        ...

    def pieces(self, piece_type: chess.PieceType, color: chess.Color) -> Any:
        ...

    def pieces_mask(self, piece_type: chess.PieceType, color: chess.Color) -> int:
        ...

    def king(self, color: chess.Color) -> Optional[chess.Square]:
        ...

    @property
    def move_stack(self) -> Any:
        ...

    def generate_legal_captures(self) -> Any:
        ...

    def copy(self, *, stack: bool = True) -> Any:
        ...
