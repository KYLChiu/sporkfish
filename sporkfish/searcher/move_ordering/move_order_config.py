from enum import Enum

from sporkfish.configurable import Configurable


class MoveOrderMode(Enum):
    MVV_LVA = "MVV_LVA"
    KILLER_MOVE = "KILLER_MOVE"
    HISTORY = "HISTORY"
    COMPOSITE = "COMPOSITE"


class MoveOrderConfig(Configurable):
    """
    Configuration class for move ordering.
    """

    def __init__(
        self,
        move_order_mode: MoveOrderMode = MoveOrderMode.COMPOSITE,
        mvv_lva_weight: float = 3.0,
        killer_moves_weight: float = 2.0,
        history_weight: float = 1.0,
    ):
        """
        Initializes MoveOrderConfig with specified parameters.

        :param move_order_mode: The mode for move ordering. Default is MoveOrderMode.COMPOSITE.
        :type move_order_mode: MoveOrderMode, optional
        :param mvv_lva_weight: The weight for Most Valuable Victim/Least Valuable Aggressor heuristic. Default is 2.0.
        :type mvv_lva_weight: float, optional
        :param killer_moves_weight: The weight for killer moves heuristic. Default is 1.0.
        :type killer_moves_weight: float, optional
        """
        self.move_order_mode = (
            move_order_mode
            if isinstance(move_order_mode, MoveOrderMode)
            else MoveOrderMode(move_order_mode)
        )
        self.mvv_lva_weight = mvv_lva_weight
        self.killer_moves_weight = killer_moves_weight
        self.history_weight = history_weight
