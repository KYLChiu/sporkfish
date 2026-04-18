from sporkfish.configurable import Configurable


class TimeManagerConfig(Configurable):
    """
    Configuration class for TimeManager.

    :param time_weight: Weight for time allocation (default: 0.1).
    :type time_weight: float
    :param increment_weight: Weight for increment allocation (default: 0.01).
    :type increment_weight: float
    """

    def __init__(
        self, time_weight: float = 0.1, increment_weight: float = 0.01
    ) -> None:
        self.time_weight = time_weight
        self.increment_weight = increment_weight


class TimeManager:
    """Class for managing time in a chess game."""

    def __init__(self, config: TimeManagerConfig = TimeManagerConfig()) -> None:
        """Initialize TimeManager.

        :param config: Configuration for TimeManager (default: TimeManagerConfig()).
        :type config: TimeManagerConfig
        """
        self._config = config

    def get_timeout(self, time: float, increment: float) -> float:
        """
        Calculate the timeout for a move based on time and increment.

        The timeout is calculated as tw * time + iw * increment.

        :param time: Total time available for the move.
        :type time: float
        :param increment: Time increment for the move.
        :type increment: float

        :return: Calculated timeout for the move.
        :rtype: float
        """

        # -------------------------- Basic strategy for time management --------------------------
        # Allocate tw * time + iw * increment per move.
        # By default, time_weight (tw) = 0.1, increment_weight (iw) = 0.01.
        #
        # Quick analysis without increment (assuming tw=0.1):
        #   Time remaining after n half-moves: (1 - 0.1)^n * S = 0.9^n * S
        #   Half-moves before reaching 1 second: n > ln(1/S) / ln(0.9)
        #
        #   Blitz (S=300s): ~54 half-moves before reaching 1 second.
        #   Bullet (S=60s):  ~38 half-moves before reaching 1 second.
        #
        # More sophisticated time management (e.g. volatility-based allocation) can
        # be investigated in future.
        return (
            self._config.time_weight * time + self._config.increment_weight * increment
        )
