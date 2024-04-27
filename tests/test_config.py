from config import load_config
from sporkfish.searcher.move_ordering.move_order_config import MoveOrderMode
from sporkfish.searcher.searcher_config import SearcherConfig, SearchMode
import pytest


def test_load_config():
    cfg = load_config()
    assert "RunConfig" in cfg


def test_create_from_yaml_config():
    cfg = load_config()
    searcher_cfg = SearcherConfig.from_dict(cfg.get("SearcherConfig"))
    assert isinstance(searcher_cfg.max_depth, int)


@pytest.mark.parametrize(
    ("max_depth", "search_mode", "enable_tt", "move_order_config"),
    [
        (10, SearchMode.NEGA_MAX_SINGLE_PROCESS, False, {"move_order_mode": MoveOrderMode.KILLER_MOVE, "mvv_lva_weight": 100}),
        (3, SearchMode.NEGA_MAX_LAZY_SMP, False, {"move_order_mode": MoveOrderMode.MVV_LVA, "mvv_lva_weight": 20}),
        (32, SearchMode.NEGA_MAX_LAZY_SMP, False, {"move_order_mode": MoveOrderMode.HISTORY, "mvv_lva_weight": 0.3}),
    ],
)
class TestCreateFromDict:
    def test_create_from_dict(
        self, max_depth, search_mode, enable_tt, move_order_config
    ) -> None:
        cfg = {
            "max_depth": max_depth,
            "search_mode": search_mode.value,
            "enable_transposition_table": enable_tt,
            "move_order_config": move_order_config,
        }
        searcher_cfg = SearcherConfig.from_dict(cfg)
        assert searcher_cfg.max_depth == max_depth
        assert searcher_cfg.search_mode == search_mode
        assert searcher_cfg.enable_transposition_table is False
        assert searcher_cfg.move_order_config
        assert searcher_cfg.move_order_config.move_order_mode == move_order_config["move_order_mode"]
        assert searcher_cfg.move_order_config.mvv_lva_weight == move_order_config["mvv_lva_weight"]

