from sporkfish.searcher import SearcherConfig, Searcher
from sporkfish.evaluator import Evaluator
import chess
from typing import Any


def searcher_with_fen(
    fen: str,
    max_depth=5,
    enable_null_move_pruning=True,
    enable_transposition_table=False,
):
    board = chess.Board()
    e = Evaluator()
    s = Searcher(
        e,
        SearcherConfig(
            max_depth,
            enable_null_move_pruning=enable_null_move_pruning,
            enable_transposition_table=enable_transposition_table,
        ),
    )
    board.set_fen(fen)
    score, move = s.search(board)
    return score, move


def run_perft(
    fen: str,
    max_depth: int,
    enable_null_move_pruning: bool,
    enable_transposition_table: bool,
):
    import cProfile
    import pstats

    profiler = cProfile.Profile()

    profiler.enable()

    searcher_with_fen(
        fen, max_depth, enable_null_move_pruning, enable_transposition_table
    )

    profiler.disable()

    stats = pstats.Stats(profiler)

    stats.strip_dirs().sort_stats("tottime").print_stats(10)


# Performance test without transposition table and without null-move pruning
def test_perf():
    run_perft(
        fen="r1r3k1/1ppp1ppp/p7/8/1P1nPPn1/3B1RP1/P1PP3q/R1BQ2K1 w - - 2 18",
        max_depth=6,
        enable_null_move_pruning=False,
        enable_transposition_table=False,
    )


# Performance test without transposition table and with null-move pruning
def test_null_move_pruning_perf():
    run_perft(
        fen="r1r3k1/1ppp1ppp/p7/8/1P1nPPn1/3B1RP1/P1PP3q/R1BQ2K1 w - - 2 18",
        max_depth=6,
        enable_null_move_pruning=True,
        enable_transposition_table=False,
    )


# Performance test with transposition table
def test_transposition_table_perf():
    run_perft(
        fen="r1r3k1/1ppp1ppp/p7/8/1P1nPPn1/3B1RP1/P1PP3q/R1BQ2K1 w - - 2 18",
        max_depth=6,
        enable_null_move_pruning=False,
        enable_transposition_table=True,
    )
