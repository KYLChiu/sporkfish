from enum import Enum

from ..configurable import Configurable


class SearchMode(Enum):
    SINGLE_PROCESS = "SINGLE_PROCESS"
    LAZY_SMP = "LAZY_SMP"


class MoveOrdering(Enum):
    MVV_LVA = "MVV_LVA"


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
        mode: SearchMode = SearchMode.SINGLE_PROCESS,
        order: MoveOrdering = MoveOrdering.MVV_LVA,
        enable_null_move_pruning: bool = True,
        enable_transposition_table: bool = False,
    ) -> None:
        self.max_depth = max_depth
        # TODO: register the constructor function in yaml loader instead.
        self.mode = mode if isinstance(mode, SearchMode) else SearchMode(mode)
        self.order = order
        self.enable_null_move_pruning = enable_null_move_pruning
        self.enable_transposition_table = enable_transposition_table
