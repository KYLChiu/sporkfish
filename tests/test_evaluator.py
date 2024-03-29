from init_board_helper import board_setup, score_fen

from sporkfish.evaluator.evaluator import Evaluator
from sporkfish.evaluator.evaluator_config import EvaluatorConfig, EvaluatorMode
from sporkfish.evaluator.evaluator_factory import EvaluatorFactory
from sporkfish.evaluator.pesto import Pesto


def _evaluator(
    evaluator_cfg: EvaluatorConfig = EvaluatorConfig(
        evaluator_mode=EvaluatorMode.PESTO
    ),
) -> Evaluator:
    return EvaluatorFactory.create(evaluator_cfg)


class TestEvaluator:
    def _eval_kings_pos(self) -> list[float, float]:
        ev = _evaluator()

        white_mg_score = ev.MG_KING[44]
        white_eg_score = ev.EG_KING[44]
        black_mg_score = ev.MG_KING[26 ^ 56]
        black_eg_score = ev.EG_KING[26 ^ 56]

        mg_score = white_mg_score - black_mg_score
        eg_score = white_eg_score - black_eg_score
        return [mg_score, eg_score]

    def _eval_kings_pawn_pos(self) -> list[float, float]:
        ev = _evaluator()

        white_mg_score = ev.MG_KING[44]
        white_eg_score = ev.EG_KING[44]
        black_mg_score = ev.MG_KING[34 ^ 56]
        black_eg_score = ev.EG_KING[34 ^ 56]
        black_mg_score += ev.MG_PAWN[26 ^ 56]
        black_eg_score += ev.EG_PAWN[26 ^ 56]

        mg_score = white_mg_score - black_mg_score
        eg_score = white_eg_score - black_eg_score
        return [mg_score, eg_score]

    def test_evaluation_two_kings_white_to_move(self) -> None:
        """
        Testing evaluate function for a simple board (after flipping vertically, i.e. XOR 56):
        black king at 44 (c4)
        white king at 34 (e6)
        white to move
        """
        fen_string = board_setup["white"]["two_kings"]
        score = score_fen(fen_string)

        phase = 0
        mg_phase = min(24, phase)
        eg_phase = 24 - mg_phase

        [mg_score, eg_score] = self._eval_kings_pos()
        expected = ((mg_score * mg_phase) + (eg_score * eg_phase)) / 24

        assert score == expected

    def test_evaluation_two_kings_black_to_move(self) -> None:
        """
        Testing evaluate function for a simple board (after XOR 56):
        black king at 44 (c4)
        white king at 34 (e6)
        black to move
        """
        fen_string = board_setup["black"]["two_kings"]
        score = score_fen(fen_string)

        phase = 0
        mg_phase = min(24, phase)
        eg_phase = 24 - mg_phase

        [mg_score, eg_score] = self._eval_kings_pos()
        mg_score, eg_score = -mg_score, -eg_score
        expected = ((mg_score * mg_phase) + (eg_score * eg_phase)) / 24

        assert score == expected

    def test_evaluation_two_kings_one_pawn_white_to_move(self) -> None:
        """
        Testing evaluate function for a simple board:
        black king at 44
        black pawn at 26
        white king at 34
        white to move
        """
        fen_string = board_setup["white"]["two_kings_one_pawn"]
        score = score_fen(fen_string)

        phase = 0
        mg_phase = min(24, phase)
        eg_phase = 24 - mg_phase

        [mg_score, eg_score] = self._eval_kings_pawn_pos()
        expected = ((mg_score * mg_phase) + (eg_score * eg_phase)) / 24

        assert score == expected

    def test_evaluation_two_kings_one_pawn_black_to_move(self) -> None:
        """
        Testing evaluate function for a simple board:
        black king at 44
        black pawn at 26
        white king at 34
        black to move
        """
        fen_string = board_setup["black"]["two_kings_one_pawn"]
        score = score_fen(fen_string)

        phase = 0
        mg_phase = min(24, phase)
        eg_phase = 24 - mg_phase

        [mg_score, eg_score] = self._eval_kings_pawn_pos()
        mg_score, eg_score = -mg_score, -eg_score
        expected = ((mg_score * mg_phase) + (eg_score * eg_phase)) / 24

        assert score == expected


class TestEvaluatorFactory:
    def test_create_default(self) -> None:
        evaluator = EvaluatorFactory.create(EvaluatorConfig())
        assert isinstance(evaluator, Pesto)


class TestScore:
    # NB: static evaluation function must return a score relative to the side to being evaluated, e.g. the simplest score evaluation could be:
    # score = materialWeight * (numWhitePieces - numBlackPieces) * who2move
    def test_black_winning_black_to_move(self) -> None:
        score = score_fen("6r1/pNkb4/Pp2p3/2p1np1p/8/1PP4P/R5B1/5K2 b - - 1 34")
        assert score > 0

    def test_black_winning_white_to_move(self) -> None:
        score = score_fen("8/pNkb4/Pp2p3/2p1np1p/8/1PP3rP/R5B1/5K2 w - - 2 35")
        assert score < 0

    def test_white_winning_white_to_move(self) -> None:
        score = score_fen("8/2Q5/8/8/1k1K4/8/8/8 w - - 15 74")
        assert score > 0

    def test_white_winning_black_to_move(self) -> None:
        score = score_fen("8/1Q6/8/8/1k1K4/8/8/8 b - - 16 74")
        assert score < 0
