from typing import Dict, Optional

import chess

from sporkfish.board.board import Board
from sporkfish.evaluator.evaluator import Evaluator


class SimpleEval(Evaluator):
    """
    Minimal evaluator: material only + basic passed pawn bonus.

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

    EG_PIECE_VALUES = {
        chess.PAWN: 94.0,
        chess.KNIGHT: 281.0,
        chess.BISHOP: 297.0,
        chess.ROOK: 512.0,
        chess.QUEEN: 936.0,
        chess.KING: 12000.0,
    }

    # Delta pruning margin for searcher
    DELTA = 200.0

    # Per-rank passed pawn bonus (index = rank 0-7).
    _PASSED_PAWN_BONUS = (0, 5, 10, 20, 35, 60, 100, 0)

    def __init__(self) -> None:
        pass

    def evaluate(self, board: Board) -> float:
        """
        Evaluate position: material only + passed pawn bonus.

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

        # Passed pawn bonus: scaled down slightly vs PeSTO to keep simple.
        score += self._passed_pawns_bonus(board, stm)

        return score

    @staticmethod
    def _passed_pawns_bonus(board: Board, stm: bool) -> float:
        """Passed pawn bonus from side to move perspective."""
        own_pawns = board.pieces(chess.PAWN, stm)
        opp_pawns = board.pieces(chess.PAWN, not stm)
        opp_bb = int(board.pieces_mask(chess.PAWN, not stm))

        bonus = 0.0
        pp_bonus = SimpleEval._PASSED_PAWN_BONUS

        for sq in own_pawns:
            f = chess.square_file(sq)
            r = chess.square_rank(sq)

            # Check if passed: no opponent pawn on same or adjacent files ahead.
            is_passed = True
            for opp_sq in opp_pawns:
                opp_f = chess.square_file(opp_sq)
                opp_r = chess.square_rank(opp_sq)
                # Opponent pawn blocks if on adjacent file and ahead.
                if abs(opp_f - f) <= 1:
                    if (stm and opp_r > r) or (not stm and opp_r < r):
                        is_passed = False
                        break

            if is_passed:
                # Normalize rank for stm (0 = own back rank, 7 = promotion).
                norm_r = r if stm else (7 - r)
                bonus += pp_bonus[norm_r]

        return bonus

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
