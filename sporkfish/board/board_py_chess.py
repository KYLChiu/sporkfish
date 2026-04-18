import chess


class BoardPyChess(chess.Board):
    """
    Board implementation that subclasses chess.Board directly, eliminating
    all wrapper overhead. Every method call (push, pop, piece_at, is_capture,
    is_check, legal_moves, etc.) goes straight to the C-optimized python-chess
    implementation with zero intermediate Python dispatch.

    Satisfies the Board Protocol structurally (no inheritance needed - Protocol
    uses structural typing via isinstance checks at runtime).
    """

    def push_uci(self, move: str) -> None:
        """chess.Board.push_uci returns the Move; our Protocol returns None."""
        super().push_uci(move)
