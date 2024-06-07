from enum import Enum, auto


class GameTerminationReason(Enum):
    """
    Enumeration of termination reasons.
    """

    RESIGNATION = auto()
    OPPONENT_LEFT = auto()
    UNKNOWN = auto()
