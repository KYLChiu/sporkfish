from enum import Enum

from sporkfish.searcher.move_ordering import MoveOrderMode

from ..configurable import Configurable


class SearchMode(Enum):
    SINGLE_PROCESS = "SINGLE_PROCESS"
    LAZY_SMP = "LAZY_SMP"


class SearcherConfig(Configurable):
    """Configuration class for the searcher.

    :param max_depth: Maximum depth for the search (default: 5).
    :type max_depth: int
    :param mode: Search mode (default: SearchMode.SINGLE_PROCESS).
    :type mode: SearchMode
    :param enable_null_move_pruning: Enable null-move pruning (default: True).
    :type enable_null_move_pruning: bool
    :param enable_transposition_table: Enable transposition table (default: True).
    :type enable_transposition_table: bool
    """

    def __init__(
        self,
        max_depth: int = 5,
        search_mode: SearchMode = SearchMode.SINGLE_PROCESS,
        move_order_mode: MoveOrderMode = MoveOrderMode.MVV_LVA,
        enable_null_move_pruning: bool = True,
        enable_delta_pruning: bool = True,
        enable_transposition_table: bool = False,
        enable_aspiration_windows: bool = True,
    ) -> None:
        self.max_depth = max_depth
        # TODO: register the constructor function in yaml loader instead.
        self.search_mode = (
            search_mode
            if isinstance(search_mode, SearchMode)
            else SearchMode(search_mode)
        )
        self.move_order_mode = (
            move_order_mode
            if isinstance(move_order_mode, MoveOrderMode)
            else MoveOrderMode(move_order_mode)
        )
        self.enable_null_move_pruning = enable_null_move_pruning
        self.enable_delta_pruning = enable_delta_pruning
        self.enable_transposition_table = enable_transposition_table
        self.enable_aspiration_windows = enable_aspiration_windows
