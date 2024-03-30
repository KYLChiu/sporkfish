import pytest
from init_board_helper import board_setup, init_board, score_fen

from sporkfish.board.board_factory import BoardFactory, BoardPyChess
from sporkfish.evaluator.evaluator_config import EvaluatorConfig, EvaluatorMode
from sporkfish.evaluator.evaluator_factory import EvaluatorFactory
from sporkfish.evaluator.pesto import Pesto as Evaluator
from sporkfish.searcher.move_ordering.move_order_config import (
    MoveOrderConfig,
    MoveOrderMode,
)
from sporkfish.searcher.move_ordering.move_orderer import MoveOrderer
from sporkfish.searcher.move_ordering.mvv_lva_heuristic import MvvLvaHeuristic
from sporkfish.searcher.searcher import Searcher
from sporkfish.searcher.searcher_config import SearcherConfig
from sporkfish.searcher.searcher_factory import SearcherFactory


def _evaluator(
    evaluator_cfg: EvaluatorConfig = EvaluatorConfig(
        evaluator_mode=EvaluatorMode.PESTO
    ),
) -> Evaluator:
    return EvaluatorFactory.create(evaluator_cfg)


def _searcher_with_fen(
    fen: str,
    max_depth: int = 3,
    enable_null_move_pruning=False,
    enable_futility_pruning=False,
    enable_delta_pruning=False,
    enable_transposition_table=False,
    enable_aspiration_windows=False,
    move_order_config=MoveOrderConfig(move_order_mode=MoveOrderMode.MVV_LVA),
):
    board = BoardFactory.create(board_type=BoardPyChess)
    s = SearcherFactory.create(
        SearcherConfig(
            max_depth,
            enable_null_move_pruning=enable_null_move_pruning,
            enable_futility_pruning=enable_futility_pruning,
            enable_delta_pruning=enable_delta_pruning,
            enable_transposition_table=enable_transposition_table,
            enable_aspiration_windows=enable_aspiration_windows,
            move_order_config=move_order_config,
        ),
        evaluator=_evaluator(),
    )
    board.set_fen(fen)
    score, move = s.search(board)
    return score, move


@pytest.mark.parametrize(
    ("fen_string"),
    [
        (board_setup["white"]["mid"]),
        (board_setup["white"]["two_kings"]),
        (board_setup["black"]["end"]),
    ],
)
class TestValidMove:
    # This is a fairly slow test
    def test_valid_moves(self, fen_string: str):
        """
        Tests if no exceptions are thrown and no null moves made
        """
        _searcher_with_fen(fen_string)


@pytest.mark.parametrize(
    ("fen_string", "max_depth"),
    [
        (board_setup["white"]["mid"], 4),
        (board_setup["white"]["open"], 5),
        (board_setup["black"]["mid"], 6),
        (board_setup["black"]["end"], 6),
    ],
)
class TestPerformance:
    """
    Tests only for performance analysis - skipped by marked as slow
    To run perf tests:
    python3 -m pytest tests/test_searcher.py::TestPerformance -sv --runslow
    """

    @pytest.fixture
    def request_fixture(self, request):
        return request

    def _run_perf_analytics(
        self,
        test_name: str,
        fen: str,
        max_depth: int,
        enable_null_move_pruning: bool = False,
        enable_futility_pruning: bool = False,
        enable_delta_pruning: bool = False,
        enable_transposition_table: bool = False,
        enable_aspiration_windows: bool = False,
        move_order_config: MoveOrderConfig = MoveOrderConfig(
            move_order_mode=MoveOrderMode.MVV_LVA
        ),
    ) -> None:
        import cProfile
        import pstats

        profiler = cProfile.Profile()
        profiler.enable()
        _searcher_with_fen(
            fen,
            max_depth,
            enable_null_move_pruning=enable_null_move_pruning,
            enable_futility_pruning=enable_futility_pruning,
            enable_delta_pruning=enable_delta_pruning,
            enable_transposition_table=enable_transposition_table,
            enable_aspiration_windows=enable_aspiration_windows,
            move_order_config=move_order_config,
        )
        profiler.disable()
        stats = pstats.Stats(profiler)

        import os
        import sys

        test_name = (
            test_name.replace("[", "_")
            .replace("]", "_")
            .replace(" ", "_")
            .replace("/", "_")
        )
        perf_test_folder = "perf/"

        if not os.path.exists(perf_test_folder):
            os.mkdir(perf_test_folder)

        with open(
            os.path.join(perf_test_folder, f"{test_name}.txt"),
            "w",
        ) as f:
            sys.stdout = f
            print(
                "------------------------------------------------------------------------------------------------"
            )
            print(f"FEN: {fen}")
            stats = pstats.Stats(profiler)
            stats.strip_dirs().sort_stats("tottime").print_stats()
            print(
                "------------------------------------------------------------------------------------------------"
            )

        sys.stdout = sys.__stdout__

    @pytest.mark.slow
    def test_perf_base(self, request_fixture, fen_string: str, max_depth: int) -> None:
        self._run_perf_analytics(
            request_fixture.node.name,
            fen=fen_string,
            max_depth=max_depth,
        )

    @pytest.mark.slow
    def test_perf_transposition_table(
        self, request_fixture, fen_string: str, max_depth: int
    ) -> None:
        self._run_perf_analytics(
            request_fixture.node.name,
            fen=fen_string,
            max_depth=max_depth,
            enable_transposition_table=True,
        )

    @pytest.mark.slow
    def test_perf_null_move_pruning(
        self, request_fixture, fen_string: str, max_depth: int
    ) -> None:
        self._run_perf_analytics(
            request_fixture.node.name,
            fen=fen_string,
            max_depth=max_depth,
            enable_null_move_pruning=True,
        )

    @pytest.mark.slow
    def test_perf_aspiration_windows(
        self, request_fixture, fen_string: str, max_depth: int
    ) -> None:
        self._run_perf_analytics(
            request_fixture.node.name,
            fen=fen_string,
            max_depth=max_depth,
            enable_aspiration_windows=True,
        )

    @pytest.mark.slow
    def test_perf_futility_pruning(
        self, request_fixture, fen_string: str, max_depth: int
    ) -> None:
        self._run_perf_analytics(
            request_fixture.node.name,
            fen=fen_string,
            max_depth=max_depth,
            enable_futility_pruning=True,
        )

    @pytest.mark.slow
    def test_perf_delta_pruning(
        self, request_fixture, fen_string: str, max_depth: int
    ) -> None:
        self._run_perf_analytics(
            request_fixture.node.name,
            fen=fen_string,
            max_depth=max_depth,
            enable_delta_pruning=True,
        )

    @pytest.mark.slow
    def test_combined_move_order(
        self, request_fixture, fen_string: str, max_depth: int
    ) -> None:
        self._run_perf_analytics(
            request_fixture.node.name,
            fen=fen_string,
            max_depth=max_depth,
            enable_delta_pruning=True,
            move_order_config=MoveOrderConfig(move_order_mode=MoveOrderMode.COMPOSITE),
        )

    @pytest.mark.slow
    def test_perf_combined(
        self, request_fixture, fen_string: str, max_depth: int
    ) -> None:
        """Performance test with combined general performance config on"""
        self._run_perf_analytics(
            request_fixture.node.name,
            fen=fen_string,
            max_depth=max_depth,
            enable_null_move_pruning=True,
            enable_delta_pruning=True,
            enable_aspiration_windows=True,
        )


@pytest.mark.parametrize(
    ("fen_string", "max_depth"),
    [
        (board_setup["white"]["open"], 3),
        (board_setup["white"]["mid"], 3),
        (board_setup["white"]["end"], 3),
        (board_setup["white"]["two_kings"], 3),
        (board_setup["black"]["open"], 3),
        (board_setup["black"]["mid"], 3),
        (board_setup["black"]["end"], 3),
        # (board_setup["black"]["two_kings"], 3) TODO: (kchiu) Issue #63
    ],
)
class TestConsistency:
    """Tests consistency across configs"""

    def _run_consistency_test(
        self,
        fen: str,
        max_depth: int,
        enable_null_move_pruning: bool = False,
        enable_futility_pruning: bool = False,
        enable_delta_pruning: bool = False,
        enable_transposition_table: bool = False,
        enable_aspiration_windows: bool = False,
    ):
        score, move = _searcher_with_fen(fen, max_depth)
        score_2, move_2 = _searcher_with_fen(
            fen,
            max_depth,
            enable_null_move_pruning=enable_null_move_pruning,
            enable_futility_pruning=enable_futility_pruning,
            enable_delta_pruning=enable_delta_pruning,
            enable_transposition_table=enable_transposition_table,
            enable_aspiration_windows=enable_aspiration_windows,
        )
        assert score == score_2
        assert move == move_2

    def test_transposition_table_consistency(self, fen_string: str, max_depth: int):
        "Tests base searcher and transposition table on return the same score and bestmove"
        self._run_consistency_test(
            fen=fen_string, max_depth=max_depth, enable_transposition_table=True
        )

    def test_null_move_pruning_consistency(self, fen_string: str, max_depth: int):
        "Tests base searcher and null move pruning on return the same score and bestmove"
        self._run_consistency_test(
            fen=fen_string, max_depth=max_depth, enable_null_move_pruning=True
        )

    def test_delta_pruning_consistency(self, fen_string: str, max_depth: int):
        "Tests base searcher and delta pruning on return the same score and bestmove"
        self._run_consistency_test(
            fen=fen_string, max_depth=max_depth, enable_delta_pruning=True
        )

    def test_aspiration_windows_consistency(self, fen_string: str, max_depth: int):
        "Tests base searcher and null move pruning on return the same score and bestmove"
        self._run_consistency_test(
            fen=fen_string, max_depth=max_depth, enable_aspiration_windows=True
        )


@pytest.mark.parametrize(
    ("fen_string"),
    [
        (board_setup["white"]["open"]),
        (board_setup["white"]["mid"]),
        (board_setup["white"]["end"]),
        (board_setup["white"]["two_kings"]),
        (board_setup["black"]["open"]),
        (board_setup["black"]["mid"]),
        (board_setup["black"]["end"]),
        (board_setup["black"]["two_kings"]),
    ],
)
class TestQuiescence:
    def test_quiescence_search_depth_0(
        self, _init_searcher: Searcher, fen_string: str
    ) -> None:
        """
        Test for quiescence base case (depth 0)
        """
        board = init_board(fen_string)
        s = _init_searcher

        alpha, beta = 1.1, 2.3
        result = s._quiescence_search(board, 0, alpha, beta, None)
        assert result == score_fen(fen_string)

    def test_quiescence_search_depth_2_beta(
        self, _init_searcher: Searcher, fen_string: str
    ) -> None:
        """
        Test quiescence returns beta
        if beta is sufficiently negative
        """
        board = init_board(fen_string)
        s = _init_searcher
        alpha, beta = 0, -1e8
        result = s._quiescence_search(board, 2, alpha, beta, None)
        assert result == beta

    def test_quiescence_search_depth_1_alpha(
        self, _init_searcher: Searcher, fen_string: str
    ) -> None:
        """
        Test quiescence behaviour with depth 1
        when both alpha and beta are sufficiently large
        """
        board = init_board(fen_string)
        s = _init_searcher
        alpha, beta = 1e8, 1e9
        result = s._quiescence_search(board, 1, alpha, beta, None)

        legal_moves = (move for move in board.legal_moves if board.is_capture(move))
        mo_heuristic = MvvLvaHeuristic(board)
        legal_moves = MoveOrderer.order_moves(mo_heuristic, board.legal_moves)
        e = Evaluator()
        for move in legal_moves:
            board.push(move)
            score = -e.evaluate(board)
            board.pop()

            if score > alpha:
                alpha = score

        assert result == alpha


@pytest.fixture
def _init_searcher(
    max_depth: int = 4, move_order_mode: MoveOrderMode = MoveOrderMode.MVV_LVA
) -> Searcher:
    """Initialise searcher"""
    return SearcherFactory.create(
        SearcherConfig(
            max_depth,
            move_order_config=MoveOrderConfig(move_order_mode=move_order_mode),
        ),
        evaluator=_evaluator(),
    )


@pytest.mark.parametrize(
    ("fen_string", "param"),
    [
        (board_setup["white"]["open"], [20, 0]),
        (board_setup["white"]["mid"], [20, 0]),
        (board_setup["white"]["end"], [20, 0]),
        (board_setup["white"]["two_kings"], [20, 0]),
        (board_setup["black"]["open"], [20, 0]),
        (board_setup["black"]["mid"], [20, 0]),
        (board_setup["black"]["end"], [20, 0]),
        (board_setup["black"]["two_kings"], [20, 0]),
        (board_setup["white"]["open"], [0, -90]),
        (board_setup["white"]["mid"], [0, -90]),
        (board_setup["white"]["end"], [0, -90]),
        (board_setup["white"]["two_kings"], [0, -90]),
        (board_setup["black"]["open"], [0, -90]),
        (board_setup["black"]["mid"], [0, -90]),
        (board_setup["black"]["end"], [0, -90]),
        # (board_setup["black"]["two_kings"], [0, -90]) # Discussed with Jeremy to temp disable this,
    ],
)
class TestNegamax:
    def test_negamax_depth_0(
        self, _init_searcher: Searcher, fen_string: str, param: list[float, float]
    ) -> None:
        """
        Testing negamax base case (depth 0)
        Checks that negamax devolve to quiescence search
        """
        board = init_board(fen_string)
        s = _init_searcher

        alpha, beta = param[0], param[1]
        result = s._negamax(board, 0, alpha, beta, None)
        assert result == s._quiescence_search(board, 4, alpha, beta, None)

    def test_negamax_depth_1(
        self, _init_searcher: Searcher, fen_string: str, param: list[float, float]
    ) -> None:
        """
        Testing negamax depth 1
        """
        board = init_board(fen_string)
        s = _init_searcher

        alpha, beta = param[0], param[1]
        result = s._negamax(board, 1, alpha, beta, None)

        mo_heuristic = MvvLvaHeuristic(board)
        legal_moves = MoveOrderer.order_moves(mo_heuristic, board.legal_moves)

        value = -float("inf")

        for move in legal_moves:
            board.push(move)
            child_value = -s._quiescence_search(board, 4, -beta, -alpha, None)
            board.pop()

            value = max(value, child_value)

            alpha = max(alpha, value)

        assert result == value
