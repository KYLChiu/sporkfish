from sporkfish.searcher import SearcherConfig, Searcher
from sporkfish.evaluator import Evaluator
import chess
import pytest
from typing import Any


def searcher_with_fen(fen: str, max_depth=6, enable_transposition_table=False):
    board = chess.Board()
    e = Evaluator()
    s = Searcher(
        e,
        SearcherConfig(
            max_depth, enable_transposition_table=enable_transposition_table
        ),
    )
    board.set_fen(fen)
    score, move = s.search(board)
    return score, move


def run_perft(kwargs: Any):
    import cProfile
    import pstats

    profiler = cProfile.Profile()

    profiler.enable()

    searcher_with_fen(**kwargs)

    profiler.disable()

    stats = pstats.Stats(profiler)

    stats.strip_dirs().sort_stats("tottime").print_stats(10)


# Below just tests if no exceptions are thrown and no null moves made
def test_pos1():
    searcher_with_fen(
        "r1bqkb1r/1ppp1ppp/p1n2n2/1B2p3/4P3/5N2/PPPP1PPP/RNBQ1RK1 w kq - 0 5"
    )


# Performance test without transposition table
def test_pos2_perf():
    run_perft(
        fen="r1r3k1/1ppp1ppp/p7/8/1P1nPPn1/3B1RP1/P1PP3q/R1BQ2K1 w - - 2 18",
        enable_transposition_table=False,
    )


# Performance test with transposition table
def test_pos2_tt_perf():
    run_perft(
        fen="r1r3k1/1ppp1ppp/p7/8/1P1nPPn1/3B1RP1/P1PP3q/R1BQ2K1 w - - 2 18",
        enable_transposition_table=True,
    )
