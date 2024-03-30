from enum import Enum, auto


class GameTerminationReason(Enum):
    """
    Enumeration of termination reasons.
    """

    RESIGNATION = auto()
    UNKNOWN = auto()
