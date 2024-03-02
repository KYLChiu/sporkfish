from config import load_config
from sporkfish.searcher.move_ordering.move_order_config import MoveOrderMode
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
        "enable_transposition_table": False,
        "move_order_config": {"move_order_mode": "KILLER_MOVE", "mvv_lva_weight": 100},
    }
    searcher_cfg = SearcherConfig.from_dict(cfg)
    assert searcher_cfg.max_depth == 10
    assert searcher_cfg.search_mode == SearchMode.SINGLE_PROCESS
    assert searcher_cfg.enable_transposition_table is False
    assert searcher_cfg.move_order_config
    assert searcher_cfg.move_order_config.move_order_mode is MoveOrderMode.KILLER_MOVE
    assert searcher_cfg.move_order_config.mvv_lva_weight == 100
