from sporkfish.searcher import SearcherConfig, Searcher
from sporkfish.evaluator import Evaluator
from test_evaluator import score_fen
from init_board_helper import board_setup, init_board
import chess
from typing import Any
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
def test_valid_moves():

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


@pytest.fixture
def init_searcher():
    e = Evaluator()
    return Searcher(e, SearcherConfig(4))


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

    def test_quiescence_depth_0(self, init_searcher, fen_string):
        """
        Test for quiescence base case (depth 0)
        """
        board = init_board(fen_string)
        s = init_searcher

        alpha, beta = 1.1, 2.3
        result = s._quiescence(board, 0, alpha, beta)
        assert result == score_fen(fen_string)

    def test_quiescence_depth_2_beta(self, init_searcher, fen_string):
        """
        Test quiescence returns beta if beta is sufficiently negative
        """
        board = init_board(fen_string)
        s = init_searcher
        alpha, beta = 0, -1e8
        result = s._quiescence(board, 2, alpha, beta)
        assert result == beta

    def test_quiescence_depth_1_alpha(self, init_searcher, fen_string):
        board = init_board(fen_string)
        s = init_searcher
        alpha, beta = -1e8, 1e8
        result = s._quiescence(board, 1, alpha, beta)

        legal_moves = sorted(
            (move for move in board.legal_moves if board.is_capture(move)),
            key=lambda move: (s._mvv_lva_heuristic(board, move),),
            reverse=True,
        )
        e = Evaluator()
        for move in legal_moves:
            board.push(move)
            score = -e.evaluate(board)
            board.pop()

            if score > alpha:
                alpha = score

        assert result == alpha

    def test_quiescence_depth_2(self, init_searcher, fen_string):
        board = init_board(fen_string)
        s = init_searcher
        alpha, beta = 0, -1e8
        result = s._quiescence(board, 2, alpha, beta)

        legal_moves = sorted(
            (move for move in board.legal_moves if board.is_capture(move)),
            key=lambda move: (s._mvv_lva_heuristic(board, move),),
            reverse=True,
        )
        for move in legal_moves:
            board.push(move)
            score = -s._quiescence(board, 1, -beta, -alpha)
            board.pop()

            if score >= beta:
                score = beta
                break

            if score > alpha:
                alpha = score
        assert result == score


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
class TestNegamax:

    def test_negamax_depth_0(self, init_searcher, fen_string):
        """
        Testing negamax base case (depth 0)
        Checks that negamax devolve to quiescence search
        """
        board = init_board(fen_string)
        s = init_searcher

        alpha, beta = 12.3, 1.2
        result = s._negamax(board, 0, alpha, beta)
        score = score_fen(fen_string)
        assert result == s._quiescence(board, 4, alpha, beta)

    def test_negamax_depth_1(self, init_searcher, fen_string):
        assert True
