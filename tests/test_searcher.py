from sporkfish.searcher import SearcherConfig, Searcher
from sporkfish.evaluator import Evaluator
import chess
from typing import Any


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


def run_perft(fen: str, max_depth: int, enable_transposition_table: bool):
    import cProfile
    import pstats

    profiler = cProfile.Profile()
    profiler.enable()
    searcher_with_fen(fen, max_depth, enable_transposition_table)
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
        max_depth=6,
        enable_transposition_table=False,
    )


# Performance test with transposition table
def test_pos2_tt_perf():
    run_perft(
        fen="r1r3k1/1ppp1ppp/p7/8/1P1nPPn1/3B1RP1/P1PP3q/R1BQ2K1 w - - 2 18",
        max_depth=6,
        enable_transposition_table=True,
    )


def test_negamax_base_case():
    """
    testing negamax base case (depth 0)
    """
    fen_string = "8/8/3kK3/8/8/8/8/8 w - - 1 34"
    board = chess.Board()
    board.set_fen(fen_string)
    e = Evaluator()
    s = Searcher(e, 5)

    alpha, beta = 1.1, 43.2
    result = s._negamax(board, 0, alpha, beta)
    assert result == s._quiescence(board, 4, alpha, beta)
