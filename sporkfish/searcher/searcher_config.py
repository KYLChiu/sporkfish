from enum import Enum

from sporkfish.searcher.move_ordering.move_ordering import MoveOrderMode

from ..configurable import Configurable


class SearchMode(Enum):
    SINGLE_PROCESS = "SINGLE_PROCESS"
    LAZY_SMP = "LAZY_SMP"


class SearcherConfig(Configurable):
    """
    Configuration class for the searcher.

    :param max_depth: Maximum depth for the search (default: 5).
                      Controls how deeply the search algorithm explores the game tree.
    :type max_depth: int
    :param search_mode: Search mode (default: SearchMode.SINGLE_PROCESS).
                        Determines the search mode used by the searcher.
    :type search_mode: SearchMode
    :param move_order_mode: Move order mode (default: MoveOrderMode.MVV_LVA).
                            Specifies the move order mode used by the searcher.
    :type move_order_mode: MoveOrderMode
    :param enable_null_move_pruning: Enable null-move pruning (default: True).
                                     Enables or disables null-move pruning, a technique used
                                     in game tree search algorithms to improve efficiency by
                                     pruning parts of the tree where a null move is made.
    :type enable_null_move_pruning: bool
    :param enable_futility_pruning: Enable futility pruning (default: False).
                                    This is a technique used
                                    to prune search branches that are deemed unlikely to lead
                                    to a good outcome.
    :type enable_futility_pruning: bool
    :param enable_delta_pruning: Enable delta pruning (default: True).
                                 This is a technique used to prune branches of the search tree
                                 based on the evaluation function's delta value.
    :type enable_delta_pruning: bool
    :param enable_transposition_table: Enable transposition table (default: False).
                                       Enables or disables the transposition table, a cache
                                       of previously computed positions to avoid redundant
                                       computation.
    :type enable_transposition_table: bool
    :param enable_aspiration_windows: Enable aspiration windows (default: True).
                                      Enables or disables aspiration windows, a technique
                                      used to focus the search around promising moves.
    :type enable_aspiration_windows: bool
    """

    def __init__(
        self,
        max_depth: int = 5,
        search_mode: SearchMode = SearchMode.SINGLE_PROCESS,
        move_order_mode: MoveOrderMode = MoveOrderMode.MVV_LVA,
        enable_null_move_pruning: bool = True,
        enable_futility_pruning: bool = False,
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
        self.enable_futility_pruning = enable_futility_pruning
        self.enable_delta_pruning = enable_delta_pruning
        self.enable_transposition_table = enable_transposition_table
        self.enable_aspiration_windows = enable_aspiration_windows
