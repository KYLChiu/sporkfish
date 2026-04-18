from enum import Enum, auto


class GameTerminationReason(Enum):
    """
    Enumeration of termination reasons, mapping to Lichess gameState status values.

    See: https://lichess.org/api#tag/Bot/operation/botGameStream
    """

    # Normal game conclusions
    CHECKMATE = auto()
    STALEMATE = auto()
    DRAW = auto()  # covers 50-move, insufficient material, repetition, agreement
    OUTOFTIME = auto()  # flag fall
    TIMEOUT = auto()  # disconnection timeout

    # Explicit forfeit
    RESIGNATION = auto()
    OPPONENT_LEFT = auto()  # claimed via board.claim_victory

    # Fallback for any unrecognised status
    UNKNOWN = auto()


# Map Lichess API status strings to GameTerminationReason values.
LICHESS_STATUS_MAP: dict = {
    "mate": GameTerminationReason.CHECKMATE,
    "stalemate": GameTerminationReason.STALEMATE,
    "draw": GameTerminationReason.DRAW,
    "outoftime": GameTerminationReason.OUTOFTIME,
    "timeout": GameTerminationReason.TIMEOUT,
    "resign": GameTerminationReason.RESIGNATION,
    "aborted": GameTerminationReason.UNKNOWN,
}
