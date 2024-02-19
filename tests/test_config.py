from config import load_config
from sporkfish.searcher.move_ordering.move_ordering import MoveOrderMode
from sporkfish.searcher.searcher_config import SearcherConfig, SearchMode


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
        "search_mode": "SINGLE_PROCESS",
        "move_order_mode": "MVV_LVA",
        "enable_transposition_table": False,
    }
    searcher_cfg = SearcherConfig.from_dict(cfg)
    assert searcher_cfg.max_depth == 10
    assert searcher_cfg.search_mode == SearchMode.SINGLE_PROCESS
    assert searcher_cfg.move_order_mode == MoveOrderMode.MVV_LVA
    assert searcher_cfg.enable_transposition_table is False
