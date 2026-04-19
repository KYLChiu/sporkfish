import chess

from benchmarks.benchmark_utils import EPDSuiteScore, score_epd_suite


def test_score_epd_suite_respects_limit_and_timeout(monkeypatch) -> None:
    epds = (
        "8/8/8/8/8/8/8/K6k w - - bm Ka2;",
        "8/8/8/8/8/8/8/K6k w - - bm Kb2;",
        "8/8/8/8/8/8/8/K6k w - - bm Kb1;",
    )

    moves = [
        chess.Move.from_uci("a1a2"),
        chess.Move.from_uci("a1b2"),
        chess.Move.from_uci("a1b1"),
    ]
    observed_timeouts = []

    class _FakeSearcher:
        def __init__(self, move: chess.Move) -> None:
            self._move = move

        def search(self, board, timeout=None):
            observed_timeouts.append(timeout)
            return 0.0, self._move

    def _fake_create(*args, **kwargs):
        return _FakeSearcher(moves.pop(0))

    monkeypatch.setattr(
        "benchmarks.benchmark_utils.SearcherFactory.create", _fake_create
    )

    score = score_epd_suite(
        epds,
        max_depth=3,
        evaluator_factory=lambda: object(),
        max_positions=2,
        per_position_timeout_s=0.25,
    )

    assert isinstance(score, EPDSuiteScore)
    assert score.hits == 2
    assert score.total == 2
    assert score.timed_out == 0
    assert observed_timeouts == [0.25, 0.25]


def test_score_epd_suite_counts_null_move_as_timeout(monkeypatch) -> None:
    epds = ("8/8/8/8/8/8/8/K6k w - - bm Ka2;",)

    class _FakeSearcher:
        def search(self, board, timeout=None):
            return 0.0, chess.Move.null()

    monkeypatch.setattr(
        "benchmarks.benchmark_utils.SearcherFactory.create",
        lambda *args, **kwargs: _FakeSearcher(),
    )

    score = score_epd_suite(
        epds,
        max_depth=3,
        evaluator_factory=lambda: object(),
        per_position_timeout_s=0.1,
    )

    assert score.hits == 0
    assert score.total == 1
    assert score.timed_out == 1
    assert score.elapsed_s >= 0.0
