from types import SimpleNamespace

import chess
import pytest
from init_board_helper import (
    board_setup,
    evaluator,
    init_board,
    score_fen,
    searcher_with_fen,
)

from sporkfish.evaluator.pesto import Pesto as Evaluator
from sporkfish.searcher.move_ordering.move_order_config import (
    MoveOrderConfig,
    MoveOrderMode,
)
from sporkfish.searcher.move_ordering.move_orderer import MoveOrderer
from sporkfish.searcher.move_ordering.mvv_lva_heuristic import MvvLvaHeuristic
from sporkfish.searcher.searcher import Searcher
from sporkfish.searcher.searcher_config import SearcherConfig, SearchMode
from sporkfish.searcher.searcher_factory import SearcherFactory
from sporkfish.statistics import PruningTypes
from sporkfish.transposition_table import TranspositionTable
from sporkfish.zobrist_hasher import ZobristStateInfo


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
        searcher_with_fen(fen_string)


CONSISTENCY_FAST_CASES = [
    (board_setup["white"]["open"], 2),
    (board_setup["white"]["mid"], 2),
    (board_setup["white"]["two_kings"], 2),
    (board_setup["black"]["open"], 2),
    (board_setup["black"]["end"], 2),
]

CONSISTENCY_SLOW_CASES = [
    (board_setup["white"]["end"], 3),
    (board_setup["black"]["mid"], 3),
    (board_setup["white"]["mid"], 3),
    # (board_setup["black"]["two_kings"], 3) TODO: (kchiu) Issue #63
]


class _ConsistencyBase:
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
        score, move = searcher_with_fen(fen, max_depth)
        score_2, move_2 = searcher_with_fen(
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
        """TT search must find an equally good best move as non-TT search.

        Note: hash-move ordering (added alongside the TT) may cause the TT search to
        select a *different* move when multiple moves are tied for best. In that case
        we verify both moves have the same minimax value by re-evaluating each child
        position at depth-1 with a fresh non-TT searcher.
        """
        _, move_no_tt = searcher_with_fen(fen_string, max_depth)
        _, move_tt = searcher_with_fen(
            fen_string, max_depth, enable_transposition_table=True
        )
        if move_no_tt == move_tt:
            return  # moves agree — no further check needed

        # Moves differ: verify they are tied by searching each child position at
        # depth-1 with a plain non-TT negamax. Equal opponent scores means both
        # parent moves are equally good for the side to move.
        board_a = init_board(fen_string)
        board_a.push(move_no_tt)
        board_b = init_board(fen_string)
        board_b.push(move_tt)
        score_a, _ = searcher_with_fen(board_a.fen(), max(1, max_depth - 1))
        score_b, _ = searcher_with_fen(board_b.fen(), max(1, max_depth - 1))
        assert score_a == score_b, (
            f"TT found a non-equivalent move: {move_tt} (score={score_b}) "
            f"vs non-TT {move_no_tt} (score={score_a})"
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


@pytest.mark.parametrize(("fen_string", "max_depth"), CONSISTENCY_FAST_CASES)
class TestConsistency(_ConsistencyBase):
    pass


@pytest.mark.slow
@pytest.mark.parametrize(("fen_string", "max_depth"), CONSISTENCY_SLOW_CASES)
class TestConsistencySlow(_ConsistencyBase):
    pass


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
    def test_quiescence_depth_0(self, init_searcher: Searcher, fen_string: str) -> None:
        """
        Test for quiescence base case (depth 0)
        """
        board = init_board(fen_string)
        s = init_searcher

        alpha, beta = 1.1, 2.3
        result = s._quiescence(board, 0, alpha, beta, None)
        assert result == score_fen(fen_string)

    def test_quiescence_depth_2_beta(
        self, init_searcher: Searcher, fen_string: str
    ) -> None:
        """
        Test quiescence returns beta
        if beta is sufficiently negative
        """
        board = init_board(fen_string)
        s = init_searcher
        alpha, beta = 0, -1e8
        result = s._quiescence(board, 2, alpha, beta, None)
        assert result == beta

    def test_quiescence_depth_1_alpha(
        self, init_searcher: Searcher, fen_string: str
    ) -> None:
        """
        Test quiescence behaviour with depth 1
        when both alpha and beta are sufficiently large
        """
        board = init_board(fen_string)
        s = init_searcher
        alpha, beta = 1e8, 1e9
        result = s._quiescence(board, 1, alpha, beta, None)

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
def init_searcher(
    max_depth: int = 4,
    search_mode: SearchMode = SearchMode.NEGAMAX_SINGLE_PROCESS,
    move_order_mode: MoveOrderMode = MoveOrderMode.MVV_LVA,
) -> Searcher:
    """Initialise searcher.
    Check extensions and LMR are disabled so that scores are deterministic and
    comparable between negamax and PVS in unit tests.
    """
    return SearcherFactory.create(
        SearcherConfig(
            max_depth=max_depth,
            search_mode=search_mode,
            enable_check_extensions=False,
            enable_lmr=False,
            move_order_config=MoveOrderConfig(move_order_mode=move_order_mode),
        ),
        evaluator=evaluator(),
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
        self, init_searcher: Searcher, fen_string: str, param: list[float, float]
    ) -> None:
        """
        Testing negamax base case (depth 0)
        Checks that negamax devolve to quiescence search
        """
        board = init_board(fen_string)
        s = init_searcher

        alpha, beta = param[0], param[1]
        result = s._negamax(board, 0, alpha, beta, None)
        assert result == s._quiescence(board, 4, alpha, beta, None)

    def test_negamax_depth_1(
        self, init_searcher: Searcher, fen_string: str, param: list[float, float]
    ) -> None:
        """
        Testing negamax depth 1
        """
        board = init_board(fen_string)
        s = init_searcher

        alpha, beta = param[0], param[1]
        result = s._negamax(board, 1, alpha, beta, None)

        mo_heuristic = MvvLvaHeuristic(board)
        legal_moves = MoveOrderer.order_moves(mo_heuristic, board.legal_moves)

        value = -float("inf")

        for move in legal_moves:
            board.push(move)
            child_value = -s._quiescence(board, 4, -beta, -alpha, None)
            board.pop()

            value = max(value, child_value)

            alpha = max(alpha, value)

            # Mirror negamax: stop searching once we exceed the upper bound.
            if alpha >= beta:
                break

        assert result == value


@pytest.fixture
def init_pvs_searcher(
    max_depth: int = 4, move_order_mode: MoveOrderMode = MoveOrderMode.MVV_LVA
) -> Searcher:
    """Initialise searcher.
    LMR and check extensions are disabled so that PVS returns the exact same
    minimax score as negamax, making the two-searcher comparison test valid.
    """
    return SearcherFactory.create(
        SearcherConfig(
            max_depth,
            search_mode=SearchMode.PVS_SINGLE_PROCESS,
            enable_lmr=False,
            enable_check_extensions=False,
            move_order_config=MoveOrderConfig(move_order_mode=move_order_mode),
        ),
        evaluator=evaluator(),
    )


PVS_FAST_FENS = [
    board_setup["white"]["open"],
    board_setup["white"]["mid"],
    board_setup["white"]["two_kings"],
    board_setup["black"]["open"],
    board_setup["black"]["end"],
]

PVS_SLOW_FENS = [
    board_setup["white"]["end"],
    board_setup["black"]["mid"],
    board_setup["black"]["two_kings"],
]


@pytest.mark.parametrize(
    ("fen_string"),
    PVS_FAST_FENS,
)
class TestPVS:
    def test_pvs_depth(
        self, init_searcher: Searcher, init_pvs_searcher: Searcher, fen_string: str
    ) -> None:
        """
        Fast PVS parity check for regular unit-test runs.
        """
        s_nega = init_searcher
        s_pvs = init_pvs_searcher

        for depth in range(1, 4):
            board = init_board(fen_string)

            alpha, beta = float("-inf"), float("inf")
            result_nega = s_nega._negamax(board, depth, alpha, beta, None)
            result_pvs = s_pvs._pvs(board, depth, alpha, beta, None)
            assert result_pvs == result_nega


@pytest.mark.slow
@pytest.mark.parametrize(("fen_string"), PVS_SLOW_FENS)
class TestPVSSlow:
    def test_pvs_depth_4(
        self, init_searcher: Searcher, init_pvs_searcher: Searcher, fen_string: str
    ) -> None:
        """Exhaustive depth-4 parity checks kept under --runslow."""
        s_nega = init_searcher
        s_pvs = init_pvs_searcher

        board = init_board(fen_string)
        alpha, beta = float("-inf"), float("inf")
        result_nega = s_nega._negamax(board, 4, alpha, beta, None)
        result_pvs = s_pvs._pvs(board, 4, alpha, beta, None)
        assert result_pvs == result_nega


class TestNegamaxPruningCoverage:
    def test_negamax_null_move_pruning_branch(
        self, init_searcher: Searcher, monkeypatch
    ) -> None:
        board = init_board(board_setup["white"]["mid"])
        s = init_searcher

        # Force the null-move pruning branch to trigger so we validate that early return path.
        monkeypatch.setattr(s, "_null_move_pruning", lambda *_args, **_kwargs: True)

        beta = 7.0
        result = s._negamax(board, 3, -10.0, beta, None)

        assert result == beta
        assert s._statistics.visited[PruningTypes.NULL_MOVE] >= 1

    def test_negamax_futility_pruning_branch(
        self, init_searcher: Searcher, monkeypatch
    ) -> None:
        board = init_board(board_setup["white"]["mid"])
        s = init_searcher

        # Enable futility pruning and disable earlier exits so we can force
        # and observe the futility-continue path in the main negamax loop.
        s._searcher_config.enable_futility_pruning = True
        monkeypatch.setattr(s, "_null_move_pruning", lambda *_args, **_kwargs: False)
        monkeypatch.setattr(
            s, "_reverse_futility_pruning", lambda *_args, **_kwargs: False
        )
        monkeypatch.setattr(s, "_razoring", lambda *_args, **_kwargs: None)
        monkeypatch.setattr(s, "_futility_pruning", lambda *_args, **_kwargs: True)

        result = s._negamax(board, 2, -50.0, 50.0, None)

        # Branch-coverage goal: ensure the futility path is hit.
        # If all moves are skipped as futile, fail-soft value can remain -inf.
        assert result == float("-inf")
        assert s._statistics.visited[PruningTypes.FUTILITY] >= 1


class TestPVSBranchCoverage:
    def test_pvs_tt_exact_hit_branch(
        self, init_pvs_searcher: Searcher, monkeypatch
    ) -> None:
        board = init_board(board_setup["white"]["mid"])
        s = init_pvs_searcher
        zobrist_state = ZobristStateInfo(
            zobrist_hash=1234, ep_file=127, castling_rights=0
        )
        s._searcher_config.enable_transposition_table = True
        s._transposition_table = SimpleNamespace(
            probe=lambda *_args, **_kwargs: (2, 42.0, TranspositionTable.EXACT, None)
        )

        result = s._pvs(board, 2, -100.0, 100.0, zobrist_state)

        assert result == 42.0

    def test_pvs_null_move_pruning_branch(
        self, init_pvs_searcher: Searcher, monkeypatch
    ) -> None:
        board = init_board(board_setup["white"]["mid"])
        s = init_pvs_searcher

        monkeypatch.setattr(s, "_null_move_pruning", lambda *_args, **_kwargs: True)

        beta = 9.0
        result = s._pvs(board, 3, -10.0, beta, None)

        assert result == beta
        assert s._statistics.visited[PruningTypes.NULL_MOVE] >= 1

    def test_pvs_futility_pruning_branch(
        self, init_pvs_searcher: Searcher, monkeypatch
    ) -> None:
        board = init_board(board_setup["white"]["mid"])
        s = init_pvs_searcher

        s._searcher_config.enable_futility_pruning = True
        monkeypatch.setattr(s, "_null_move_pruning", lambda *_args, **_kwargs: False)
        monkeypatch.setattr(
            s, "_reverse_futility_pruning", lambda *_args, **_kwargs: False
        )
        monkeypatch.setattr(s, "_razoring", lambda *_args, **_kwargs: None)
        monkeypatch.setattr(s, "_futility_pruning", lambda *_args, **_kwargs: True)

        result = s._pvs(board, 2, -50.0, 50.0, None)

        assert result == float("-inf")
        assert s._statistics.visited[PruningTypes.FUTILITY] >= 1

    def test_pvs_terminal_positions(self, init_pvs_searcher: Searcher) -> None:
        s = init_pvs_searcher

        # No legal moves while in check should be scored as a forced loss.
        checkmate_board = init_board("7k/6Q1/6K1/8/8/8/8/8 b - - 0 1")
        checkmate_score = s._pvs(checkmate_board, 1, -100.0, 100.0, None)
        assert checkmate_score < -90000

        # No legal moves while not in check is stalemate (draw).
        stalemate_board = init_board("7k/5Q2/7K/8/8/8/8/8 b - - 0 1")
        stalemate_score = s._pvs(stalemate_board, 1, -100.0, 100.0, None)
        assert stalemate_score == 0


class TestIterativeDeepeningTimeBudget:
    def test_iterative_deepening_passes_remaining_timeout(
        self, init_searcher: Searcher, monkeypatch
    ) -> None:
        s = init_searcher
        board = init_board(board_setup["white"]["open"])

        observed_timeouts = []

        def fake_timeoutable_search(*, timeout, board_to_search, depth, prev_score):
            observed_timeouts.append(timeout)
            return 0.0, chess.Move.null(), 0.1, 0

        monkeypatch.setattr(s, "_timeoutable_search", fake_timeoutable_search)
        monkeypatch.setattr(s._statistics, "reset_visited", lambda: None)

        s._iterative_deepening_search(board, timeout=0.25)

        assert len(observed_timeouts) >= 2
        assert observed_timeouts[0] == pytest.approx(0.25)
        assert observed_timeouts[1] == pytest.approx(0.15, abs=1e-6)

    def test_iterative_deepening_stops_when_budget_exhausted(
        self, init_searcher: Searcher, monkeypatch
    ) -> None:
        s = init_searcher
        board = init_board(board_setup["white"]["open"])

        calls = {"count": 0}

        def fake_timeoutable_search(*, timeout, board_to_search, depth, prev_score):
            calls["count"] += 1
            # Simulate a single over-budget depth iteration.
            return 0.0, chess.Move.null(), 0.3, 0

        monkeypatch.setattr(s, "_timeoutable_search", fake_timeoutable_search)
        monkeypatch.setattr(s._statistics, "reset_visited", lambda: None)

        s._iterative_deepening_search(board, timeout=0.1)

        assert calls["count"] == 1
