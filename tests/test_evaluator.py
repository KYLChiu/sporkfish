import pytest
from init_board_helper import board_setup, score_fen

from sporkfish.board.board_factory import BoardFactory, BoardPyChess
from sporkfish.evaluator.evaluator import Evaluator
from sporkfish.evaluator.evaluator_config import EvaluatorConfig, EvaluatorMode
from sporkfish.evaluator.evaluator_factory import EvaluatorFactory
from sporkfish.evaluator.pesto import Pesto
from sporkfish.evaluator.simple import SimpleEval


def _evaluator(
    evaluator_cfg: EvaluatorConfig = EvaluatorConfig(
        evaluator_mode=EvaluatorMode.PESTO
    ),
) -> Evaluator:
    return EvaluatorFactory.create(evaluator_cfg)


class TestEvaluator:
    def _eval_kings_pos(self) -> list[float, float]:
        ev = _evaluator()

        # White king at e6 = chess square 44, PSQT index = 44 ^ 56 = 20
        white_mg_score = ev.MG_KING[44 ^ 56]
        white_eg_score = ev.EG_KING[44 ^ 56]

        # Black king at c4 = chess square 26, PSQT index = 26
        black_mg_score = ev.MG_KING[26]
        black_eg_score = ev.EG_KING[26]

        mg_score = white_mg_score - black_mg_score
        eg_score = white_eg_score - black_eg_score
        return [mg_score, eg_score]

    def _eval_kings_pawn_pos(self) -> list[float, float]:
        ev = _evaluator()

        # White king at e6 = chess square 44, PSQT index = 44 ^ 56 = 20
        white_mg_score = ev.MG_KING[44 ^ 56]
        white_eg_score = ev.EG_KING[44 ^ 56]

        # Black king at c5 = chess square 34, PSQT index = 34
        black_mg_score = ev.MG_KING[34]
        black_eg_score = ev.EG_KING[34]

        # Black pawn at c4 = chess square 26, PSQT index = 26
        black_mg_score += ev.MG_PAWN[26]
        black_eg_score += ev.EG_PAWN[26]

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
        pesto = ((mg_score * mg_phase) + (eg_score * eg_phase)) / 24
        # Black pawn on c4 is passed (rank 3, bonus index 4 = 35cp)
        pp_bonus = -35  # negative because it's opponent's passed pawn
        # Black c4 pawn is isolated (no adjacent pawns), opponent's weakness = +12cp for white
        ps_bonus = 12.0
        expected = pesto + pp_bonus * (0.5 + 0.5 * eg_phase / 24) + ps_bonus

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
        pesto = ((mg_score * mg_phase) + (eg_score * eg_phase)) / 24
        # Black pawn on c4 is passed (rank 3, bonus index 4 = 35cp)
        pp_bonus = 35  # positive because it's own passed pawn for black
        # Black c4 pawn is isolated (no adjacent pawns), own weakness = -12cp for black
        ps_bonus = -12.0
        expected = pesto + pp_bonus * (0.5 + 0.5 * eg_phase / 24) + ps_bonus

        assert score == expected


class TestEvaluatorFactory:
    def test_create_default(self) -> None:
        evaluator = EvaluatorFactory.create(EvaluatorConfig())
        assert isinstance(evaluator, Pesto)

    def test_create_unsupported_mode_raises(self) -> None:
        cfg = EvaluatorConfig()
        cfg.evaluator_mode = object()

        with pytest.raises(
            TypeError, match="does not support the creation of Evaluator"
        ):
            EvaluatorFactory.create(cfg)


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


class TestSimpleEvaluator:
    def test_material_only_sign_flips_with_turn(self) -> None:
        ev = SimpleEval()
        board = BoardFactory.create(BoardPyChess)
        board.set_fen("4k3/8/8/8/8/8/8/3QK3 w - - 0 1")

        # White to move with an extra queen should be +1025 by pure material.
        assert ev.evaluate(board) == 1025.0

        # Same board, black to move should negate the side-to-move perspective.
        board.set_fen("4k3/8/8/8/8/8/8/3QK3 b - - 0 1")
        assert ev.evaluate(board) == -1025.0

    def test_passed_pawn_bonus_for_white_side_to_move(self) -> None:
        ev = SimpleEval()
        board = BoardFactory.create(BoardPyChess)
        board.set_fen("4k3/8/8/4P3/8/8/8/4K3 w - - 0 1")

        # White pawn on e5: material 82 + passed-pawn bonus on rank 4 => 35.
        assert ev.evaluate(board) == 117.0

    def test_passed_pawn_bonus_for_black_side_to_move(self) -> None:
        ev = SimpleEval()
        board = BoardFactory.create(BoardPyChess)
        board.set_fen("4k3/8/8/8/8/8/4p3/4K3 b - - 0 1")

        # Black pawn on e2 from black POV: material 82 + near-promotion bonus (index 6) => 100.
        assert ev.evaluate(board) == 182.0

    def test_simple_eval_api_methods(self) -> None:
        ev = SimpleEval()
        board = BoardFactory.create(BoardPyChess)
        board.set_fen(board_setup["white"]["open"])

        # No-op incremental hooks should be callable and stable.
        ev.init_from_board(board)
        move = next(iter(board.legal_moves))
        ev.on_push(board, move)
        ev.on_pop()

        assert ev.piece_values() == SimpleEval.MG_PIECE_VALUES
        assert ev.delta() == SimpleEval.DELTA
