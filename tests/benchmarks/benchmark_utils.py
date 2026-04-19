import cProfile
import os
import pstats
import sys
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Optional, Sequence, Tuple

import chess

from sporkfish.board.board_factory import BoardFactory, BoardPyChess
from sporkfish.searcher.move_ordering.move_order_config import (
    MoveOrderConfig,
    MoveOrderMode,
)
from sporkfish.searcher.searcher_config import SearcherConfig, SearchMode
from sporkfish.searcher.searcher_factory import SearcherFactory


@dataclass(frozen=True)
class EPDSuiteScore:
    hits: int
    total: int
    elapsed_s: float
    timed_out: int


def run_profile_analytics(
    test_name: str, f: Callable[..., Any], *args, **kwargs
) -> None:
    """
    Run profiling analytics on a given function and write cProfile output to perf/.

    :param test_name: Name of the test.
    :type test_name: str
    :param f: Function to profile.
    :type f: Callable[..., Any]
    :param args: Positional arguments to pass to the function.
    :param kwargs: Additional keyword arguments to pass to the function.
    :type kwargs: dict
    """

    profiler = cProfile.Profile()
    profiler.enable()
    f(*args, **kwargs)
    profiler.disable()

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
    ) as file:
        sys.stdout = file
        print(
            "------------------------------------------------------------------------------------------------"
        )
        stats = pstats.Stats(profiler)
        stats.strip_dirs().sort_stats("tottime").print_stats()
        print(
            "------------------------------------------------------------------------------------------------"
        )

    sys.stdout = sys.__stdout__


def default_move_order_config() -> MoveOrderConfig:
    return MoveOrderConfig(
        move_order_mode=MoveOrderMode.COMPOSITE,
        mvv_lva_weight=2.0,
        killer_moves_weight=1.0,
    )


def build_pvs_perf_config(
    max_depth: int,
    move_order_config: MoveOrderConfig | None = None,
) -> SearcherConfig:
    return SearcherConfig(
        max_depth=max_depth,
        search_mode=SearchMode.PVS_SINGLE_PROCESS,
        enable_null_move_pruning=True,
        enable_futility_pruning=True,
        enable_delta_pruning=True,
        enable_transposition_table=True,
        enable_aspiration_windows=False,
        enable_check_extensions=True,
        enable_lmr=True,
        move_order_config=move_order_config or default_move_order_config(),
    )


def run_search_once(
    fen: str,
    max_depth: int,
    evaluator,
    move_order_config: MoveOrderConfig | None = None,
) -> Tuple[float, float, str]:
    board = BoardFactory.create(BoardPyChess)
    board.set_fen(fen)

    searcher = SearcherFactory.create(
        build_pvs_perf_config(max_depth, move_order_config), evaluator=evaluator
    )

    t0 = time.time()
    score, move = searcher.search(board)
    return time.time() - t0, float(score), str(move)


def score_epd_suite(
    epds: Sequence[str],
    max_depth: int,
    evaluator_factory,
    move_order_config: MoveOrderConfig | None = None,
    max_positions: Optional[int] = None,
    per_position_timeout_s: Optional[float] = None,
) -> EPDSuiteScore:
    config = build_pvs_perf_config(max_depth, move_order_config)

    selected_epds = epds[:max_positions] if max_positions is not None else epds

    hits = 0
    timed_out = 0
    t0 = time.time()
    for epd in selected_epds:
        board = chess.Board()
        epd_info = board.set_epd(epd)
        expected_moves = epd_info.get("bm", [])

        searcher = SearcherFactory.create(config, evaluator=evaluator_factory())
        _, move = searcher.search(board, timeout=per_position_timeout_s)
        if move == chess.Move.null():
            timed_out += 1
        if move in expected_moves:
            hits += 1

    return EPDSuiteScore(
        hits=hits,
        total=len(selected_epds),
        elapsed_s=time.time() - t0,
        timed_out=timed_out,
    )


def write_csv_report(
    file_name: str,
    header: str,
    rows: Iterable[str],
    out_dir: str = "perf",
) -> None:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, file_name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(header)
        if not header.endswith("\n"):
            fh.write("\n")
        for row in rows:
            fh.write(row)
            if not row.endswith("\n"):
                fh.write("\n")
