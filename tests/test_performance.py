from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

import pytest
from benchmark_utils import (
    run_profile_analytics,
    run_search_once,
    score_epd_suite,
    write_csv_report,
)
from init_board_helper import board_setup, searcher_with_fen
from test_bratko_kopec import epds as BK_EPDS_ALL

from sporkfish.evaluator.pesto import Pesto
from sporkfish.evaluator.simple import SimpleEval
from sporkfish.searcher.move_ordering.move_order_config import (
    MoveOrderConfig,
    MoveOrderMode,
)
from sporkfish.searcher.searcher_config import SearchMode

# Subset of Bratko-Kopec (12/24) to keep this reproducible test reasonably fast.
BK_EPDS_SUBSET = tuple(epd for epd in BK_EPDS_ALL.split("\n") if epd.strip())[:12]


@dataclass(frozen=True)
class BenchmarkResult:
    label: str
    depth: int
    elapsed_s: float
    score: float
    best_move: str
    bk_hits: int
    bk_total: int


def _search_once(depth: int, evaluator) -> Tuple[float, float, str]:
    fen = board_setup["black"]["mid"]
    return run_search_once(fen, depth, evaluator)


def _bk_score(depth: int, evaluator_cls, epds: Sequence[str]) -> Tuple[int, int]:
    return score_epd_suite(epds, depth, evaluator_cls)


def _write_perf_report(results: Iterable[BenchmarkResult], file_name: str) -> None:
    rows = []
    for row in results:
        pct = 100.0 * row.bk_hits / row.bk_total if row.bk_total else 0.0
        rows.append(
            f"{row.label},{row.depth},{row.elapsed_s:.3f},{row.score:.2f},"
            f"{row.best_move},{row.bk_hits},{row.bk_total},{pct:.1f}"
        )
    write_csv_report(
        file_name,
        "Evaluator depth tradeoff benchmark\n"
        "label,depth,elapsed_s,score,best_move,bk_hits,bk_total,bk_pct",
        rows,
    )


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
        run_profile_analytics(
            test_name,
            searcher_with_fen,
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
            search_mode=SearchMode.PVS_SINGLE_PROCESS,
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


@pytest.mark.slow
def test_perf_simple_vs_pesto_depth_tradeoff() -> None:
    """
    Persistent slow benchmark for evaluator-depth tradeoff.

    Goal:
    - Compare runtime and tactical quality (BK subset) between PeSTO and Simple eval.
    - Answer whether running Simple much deeper gives a large practical gain.

    Run with:
    pytest -q tests/test_performance.py -k simple_vs_pesto_depth_tradeoff --runslow -s
    """
    scenarios = [
        ("pesto", 7, Pesto()),
        ("simple", 8, SimpleEval()),
        ("simple", 9, SimpleEval()),
    ]

    results: List[BenchmarkResult] = []

    for label, depth, evaluator in scenarios:
        elapsed_s, score, best_move = _search_once(depth, evaluator)
        bk_hits, bk_total = _bk_score(depth, evaluator.__class__, BK_EPDS_SUBSET)

        row = BenchmarkResult(
            label=label,
            depth=depth,
            elapsed_s=elapsed_s,
            score=score,
            best_move=best_move,
            bk_hits=bk_hits,
            bk_total=bk_total,
        )
        results.append(row)

    _write_perf_report(results, "test_perf_simple_vs_pesto_depth_tradeoff.txt")

    for row in results:
        bk_pct = 100.0 * row.bk_hits / row.bk_total if row.bk_total else 0.0
        print(
            f"{row.label}@d{row.depth}: {row.elapsed_s:.3f}s "
            f"mid-score={row.score:.2f} move={row.best_move} "
            f"BK={row.bk_hits}/{row.bk_total} ({bk_pct:.1f}%)"
        )

    # Keep assertions robust/non-flaky: verify benchmark executed and produced sane values.
    assert len(results) == 3
    assert all(r.elapsed_s > 0 for r in results)
    assert all(0 <= r.bk_hits <= r.bk_total for r in results)
