import pytest
from init_board_helper import board_setup, searcher_with_fen

from sporkfish.searcher.move_ordering.move_order_config import (
    MoveOrderConfig,
    MoveOrderMode,
)
from sporkfish.searcher.searcher_config import SearchMode


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
        search_mode: SearchMode = SearchMode.NEGAMAX_SINGLE_PROCESS,
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
        searcher_with_fen(
            fen,
            max_depth,
            search_mode=search_mode,
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
    def test_perf_base_pvs(
        self, request_fixture, fen_string: str, max_depth: int
    ) -> None:
        self._run_perf_analytics(
            request_fixture.node.name,
            search_mode=SearchMode.PVS,
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
