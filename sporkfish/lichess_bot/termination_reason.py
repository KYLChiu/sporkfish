from enum import Enum, auto


class TerminationReason(Enum):
    """
    Enumeration of termination reasons.
    """

    RESIGNATION = auto()
    UNKNOWN = auto()
