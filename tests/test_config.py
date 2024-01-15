from config import load_config
from sporkfish.searcher import SearcherConfig


def test_load_config():
    cfg = load_config()
    assert "RunConfig" in cfg


def test_create_from_yaml_config():
    cfg = load_config()
    searcher_cfg = SearcherConfig.from_dict(cfg.get("SearcherConfig"))
    assert isinstance(searcher_cfg.max_depth, int)


def test_create_from_dict():
    cfg = {
        "max_depth": 10,
        "mode": "SINGLE_PROCESS",
        "enable_transposition_table": False,
    }
    searcher_cfg = SearcherConfig.from_dict(cfg)
    assert searcher_cfg.max_depth == 10
