from typing import Dict

import chess

from sporkfish.board.board import Board
from sporkfish.evaluator.evaluator import Evaluator


class SimpleEval(Evaluator):
    """
    Minimal evaluator: material only.

    Used as a baseline to compare against PeSTO. Shows whether improving
    evaluation quality (PeSTO's PST tables, king safety, pawn structure)
    helps more than simply searching deeper with a simpler eval.
    """

    MG_PIECE_VALUES = {
        chess.PAWN: 82.0,
        chess.KNIGHT: 337.0,
        chess.BISHOP: 365.0,
        chess.ROOK: 477.0,
        chess.QUEEN: 1025.0,
        chess.KING: 12000.0,
    }

    DELTA = 200.0

    def __init__(self) -> None:
        pass

    def evaluate(self, board: Board) -> float:
        """
        Evaluate position: material only.

        No piece-square tables, no king safety, no pawn structure.
        Extremely fast for comparison.
        """
        stm = board.turn
        score = 0.0

        # Material count for all pieces.
        for piece_type in chess.PIECE_TYPES:
            own_count = len(board.pieces(piece_type, stm))
            opp_count = len(board.pieces(piece_type, not stm))

            # Use midgame piece values for material.
            piece_val = self.MG_PIECE_VALUES[piece_type]
            score += (own_count - opp_count) * piece_val

        return score

    def init_from_board(self, board: Board) -> None:
        """No incremental tracking needed for simple eval."""
        pass

    def on_push(self, board: Board, move: chess.Move) -> None:
        """No incremental tracking needed for simple eval."""
        pass

    def on_pop(self) -> None:
        """No incremental tracking needed for simple eval."""
        pass

    def piece_values(self) -> Dict[chess.PieceType, float]:
        """Return piece values for pruning margins."""
        return self.MG_PIECE_VALUES

    def delta(self) -> float:
        """Return delta threshold for futility pruning."""
        return self.DELTA
