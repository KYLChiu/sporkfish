import math

from benchmarks.selfplay_runner import _parse_override, _score_to_elo, _set_nested


def test_set_nested_creates_path() -> None:
    cfg = {}
    _set_nested(cfg, "SearcherConfig.max_depth", 7)
    assert cfg == {"SearcherConfig": {"max_depth": 7}}


def test_parse_override_parses_yaml_values() -> None:
    key, value = _parse_override("SearcherConfig.enable_lmr=false")
    assert key == "SearcherConfig.enable_lmr"
    assert value is False


def test_score_to_elo_symmetric_cases() -> None:
    assert _score_to_elo(0.5) == 0.0
    assert _score_to_elo(0.75) > 0
    assert _score_to_elo(0.25) < 0
    assert math.isinf(_score_to_elo(1.0))
    assert math.isinf(_score_to_elo(0.0))
