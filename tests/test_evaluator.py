from typing import Any

import chess
import pytest
from init_board_helper import board_setup, score_fen

from sporkfish import evaluator

# NB: static evaluation function must return a score relative to the side to being evaluated, e.g. the simplest score evaluation could be:
# score = materialWeight * (numWhitePieces - numBlackPieces) * who2move


class TestScore:
    def test_black_winning_black_to_move(self):
        score = score_fen("6r1/pNkb4/Pp2p3/2p1np1p/8/1PP4P/R5B1/5K2 b - - 1 34")
        assert score > 0

    def test_black_winning_white_to_move(self):
        score = score_fen("8/pNkb4/Pp2p3/2p1np1p/8/1PP3rP/R5B1/5K2 w - - 2 35")
        assert score < 0

    def test_white_winning_white_to_move(self):
        score = score_fen("8/2Q5/8/8/1k1K4/8/8/8 w - - 15 74")
        assert score > 0

    def test_white_winning_black_to_move(self):
        score = score_fen("8/1Q6/8/8/1k1K4/8/8/8 b - - 16 74")
        assert score < 0


class TestEvaluator:
    def eval_kings_pos(self) -> list[float, float]:
        ev = evaluator.Evaluator()

        white_mg_score = ev.MG_KING[44] + ev.MG_PIECE_VALUES[chess.KING]
        white_eg_score = ev.EG_KING[44] + ev.EG_PIECE_VALUES[chess.KING]
        black_mg_score = ev.MG_KING[43 ^ 56] + ev.MG_PIECE_VALUES[chess.KING]
        black_eg_score = ev.EG_KING[43 ^ 56] + ev.EG_PIECE_VALUES[chess.KING]

        mg_score = white_mg_score - black_mg_score
        eg_score = white_eg_score - black_eg_score
        return [mg_score, eg_score]

    def test_evaluation_two_kings_white_to_move(self):
        """
        Testing evaluate function for a simple board:
        black king at 43 (d6)
        white king at 44 (e6)
        white to move
        """
        fen_string = board_setup["white"]["two_kings"]
        score = score_fen(fen_string)

        [mg_score, eg_score] = self.eval_kings_pos()

        phase = 0
        mg_phase = min(24, phase)
        eg_phase = 24 - mg_phase

        expected = ((mg_score * mg_phase) + (eg_score * eg_phase)) / 24

        assert score == expected

    def test_evaluation_two_kings_black_to_move(self):
        """
        Testing evaluate function for a simple board:
        black king at 43 (d6)
        white king at 44 (e6)
        black to move
        """
        fen_string = board_setup["black"]["two_kings"]
        score = score_fen(fen_string)

        [mg_score, eg_score] = self.eval_kings_pos()
        mg_score, eg_score = -mg_score, -eg_score

        phase = 0
        mg_phase = min(24, phase)
        eg_phase = 24 - mg_phase

        expected = ((mg_score * mg_phase) + (eg_score * eg_phase)) / 24

        assert score == expected
