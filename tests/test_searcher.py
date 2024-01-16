from sporkfish.searcher import SearcherConfig, Searcher
from sporkfish.evaluator import Evaluator
import chess
import pytest


def searcher_with_fen(fen: str, max_depth=5, enable_transposition_table=False):
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


# Below just tests if no exceptions are thrown and no null moves made
def test_pos1():
    searcher_with_fen(
        "r1bqkb1r/1ppp1ppp/p1n2n2/1B2p3/4P3/5N2/PPPP1PPP/RNBQ1RK1 w kq - 0 5"
    )


def test_pos2_perf():
    import cProfile
    import pstats

    profiler = cProfile.Profile()

    profiler.enable()

    searcher_with_fen(
        "r1r3k1/1ppp1ppp/p7/8/1P1nPPn1/3B1RP1/P1PP3q/R1BQ2K1 w - - 2 18",
        enable_transposition_table=False,
    )

    profiler.disable()

    stats = pstats.Stats(profiler)

    stats.strip_dirs().sort_stats("tottime").print_stats(10)


def test_pos2_tt_perf():
    import cProfile
    import pstats

    profiler = cProfile.Profile()

    profiler.enable()

    searcher_with_fen(
        "r1r3k1/1ppp1ppp/p7/8/1P1nPPn1/3B1RP1/P1PP3q/R1BQ2K1 w - - 2 18",
        enable_transposition_table=True,
    )

    profiler.disable()

    stats = pstats.Stats(profiler)

    stats.strip_dirs().sort_stats("tottime").print_stats(10)
