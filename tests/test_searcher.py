from typing import Any
import logging

import pytest
from init_board_helper import board_setup, init_board, score_fen

from sporkfish.board.board_factory import BoardFactory, BoardPyChess
from sporkfish.evaluator import Evaluator
from sporkfish.searcher import Searcher, SearcherConfig
from sporkfish.zobrist_hasher import ZobristHasher


def _searcher_with_fen(
    fen: str,
    max_depth: int = 3,
    enable_null_move_pruning=False,
    enable_transposition_table=False,
):
    board = BoardFactory.create(board_type=BoardPyChess)
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
        ("r1r3k1/1ppp1ppp/p7/8/1P1nPPn1/3B1RP1/P1PP3q/R1BQ2K1 w - - 2 18", 4),
        ("r1r3k1/1ppp1ppp/p7/8/1P1nPPn1/3B1RP1/P1PP3q/R1BQ2K1 w - - 2 18", 5),
        ("r1r3k1/1ppp1ppp/p7/8/1P1nPPn1/3B1RP1/P1PP3q/R1BQ2K1 w - - 2 18", 6),
    ],
)
class TestPerformance:
    """
    Tests only for performance analysis - skipped by marked as slow
    To run perf tests:
    python3 -m pytest tests/test_searcher.py::TestPerformance -sv --runslow
    """

    def _run_perf_analytics(
        self,
        fen: str,
        max_depth: int,
        enable_null_move_pruning: bool = False,
        enable_transposition_table: bool = False,
    ) -> None:
        import cProfile
        import pstats

        profiler = cProfile.Profile()
        profiler.enable()
        _searcher_with_fen(
            fen, max_depth, enable_null_move_pruning, enable_transposition_table
        )
        profiler.disable()
        stats = pstats.Stats(profiler)

        stats.strip_dirs().sort_stats("tottime").print_stats(10)

    # @pytest.mark.slow
    # def test_perf_base(self, fen_string: str, max_depth: int) -> None:
    #     """Performance test base"""
    #     self._run_perf_analytics(
    #         fen=fen_string,
    #         max_depth=max_depth,
    #     )

    # @pytest.mark.slow
    # def test_perf_transposition_table(self, fen_string: str, max_depth: int) -> None:
    #     """Performance test with transposition table"""
    #     self._run_perf_analytics(
    #         fen=fen_string,
    #         max_depth=max_depth,
    #         enable_transposition_table=True,
    #     )

    @pytest.mark.slow
    def test_perf_null_move_pruning(self, fen_string: str, max_depth: int) -> None:
        """Performance test with null move pruning"""
        self._run_perf_analytics(
            fen=fen_string,
            max_depth=max_depth,
            enable_null_move_pruning=True,
        )

    @pytest.mark.slow
    def test_perf_all(self, fen_string: str, max_depth: int) -> None:
        """Performance test with null move pruning and transposition table"""
        self._run_perf_analytics(
            fen=fen_string,
            max_depth=max_depth,
            enable_null_move_pruning=True,
            enable_transposition_table=True,
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
        enable_transposition_table: bool = False,
    ):
        score, move = _searcher_with_fen(fen, max_depth)
        score_2, move_2 = _searcher_with_fen(
            fen,
            max_depth,
            enable_null_move_pruning=enable_null_move_pruning,
            enable_transposition_table=enable_transposition_table,
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
    def test_quiescence_depth_0(
        self, _init_searcher: Searcher, fen_string: str
    ) -> None:
        """
        Test for quiescence base case (depth 0)
        """
        board = init_board(fen_string)
        zh = ZobristHasher()
        hash = zh.hash(board)
        s = _init_searcher

        alpha, beta = 1.1, 2.3
        result = s._quiescence(board, 0, alpha, beta)
        assert result == score_fen(fen_string)

    def test_quiescence_depth_2_beta(
        self, _init_searcher: Searcher, fen_string: str
    ) -> None:
        """
        Test quiescence returns beta
        if beta is sufficiently negative
        """
        board = init_board(fen_string)
        s = _init_searcher
        alpha, beta = 0, -1e8
        result = s._quiescence(board, -2, alpha, beta)
        assert result == beta

    def test_quiescence_depth_1_alpha(
        self, _init_searcher: Searcher, fen_string: str
    ) -> None:
        """
        Test quiescence behaviour with depth 1
        when both alpha and beta are sufficiently large
        """
        board = init_board(fen_string)
        s = _init_searcher
        alpha, beta = 1e8, 1e9
        result = s._quiescence(board, -1, alpha, beta)

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

    def test_quiescence_depth_2(
        self, _init_searcher: Searcher, fen_string: str
    ) -> None:
        """
        Test quiescence behaviour with depth 2
        with both low alpha and high beta
        """
        board = init_board(fen_string)
        s = _init_searcher
        alpha, beta = -1e8, 1e9
        result = s._quiescence(board, 2, alpha, beta)

        e = Evaluator()
        stand_pat = e.evaluate(board)
        if alpha < stand_pat:
            alpha = stand_pat

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
                alpha = beta
                break

            if score > alpha:
                alpha = score

        assert result == alpha


@pytest.fixture
def _init_searcher(max_depth: int = 4) -> Searcher:
    """Initialise searcher"""
    e = Evaluator()
    return Searcher(e, SearcherConfig(max_depth))


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
        result = s._negamax(board, 0, alpha, beta)
        assert result == s._quiescence(board, 4, alpha, beta)

    def test_negamax_depth_1(
        self, _init_searcher: Searcher, fen_string: str, param: list[float, float]
    ) -> None:
        """
        Testing negamax depth 1
        """
        board = init_board(fen_string)
        s = _init_searcher

        alpha, beta = param[0], param[1]
        result = s._negamax(board, 1, alpha, beta)

        legal_moves = sorted(
            board.legal_moves,
            key=lambda move: (s._mvv_lva_heuristic(board, move),),
            reverse=True,
        )

        value = -float("inf")

        for move in legal_moves:
            board.push(move)
            child_value = -s._quiescence(board, 4, -beta, -alpha)
            board.pop()

            value = max(value, child_value)

            alpha = max(alpha, value)

        assert result == value


@pytest.mark.parametrize(
    ("fen_string", "move_scores"),
    [
        ("k7/8/8/8/8/8/7K/6qR w - - 1 34", [0, 50, 52]),
    ],
)
class TestMvvLvvHeuristic:
    def test_mvv_lva_heuristic_end_game(
        self, _init_searcher: Searcher, fen_string: str, move_scores: list[int]
    ) -> None:
        """
        Test mvv lva heuistic on an end game board
        """
        board = init_board(fen_string)
        s = _init_searcher

        all_moves = board.legal_moves
        num_moves = len(move_scores)
        assert len(list(all_moves)) == num_moves

        for i, move in enumerate(all_moves):
            score = s._mvv_lva_heuristic(board, move)
            assert score == move_scores[i]

    def test_sorting_legal_moves(
        self, _init_searcher: Searcher, fen_string: str, move_scores: list[int]
    ) -> None:
        """
        Test sorting of legal moves by mvv_lva_heuristic
        """
        board = init_board(fen_string)
        s = _init_searcher

        legal_moves = sorted(
            board.legal_moves,
            key=lambda move: (s._mvv_lva_heuristic(board, move),),
            reverse=True,
        )
        num_moves = len(move_scores)
        for i, move in enumerate(legal_moves):
            score = s._mvv_lva_heuristic(board, move)
            assert score == move_scores[num_moves - i - 1]
