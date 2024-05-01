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
        """
        Outline of the basic strategy for time management in chess.

        The strategy involves allocating tw * time + iw * increment for searching the move.
        By default, time_weight (tw) is set to 0.1, and increment_weight (iw) is set to 0.01.

        Quick analysis without increment:
        We get to make (1.0 - 0.1)^n * S number of (half) moves, where S = start_time in seconds.
        To reach 1 second:
        (0.9)^n * S < 1
        n > ln (1/S) / ln 0.9

        Assuming a blitz game of 5 mins (S = 300), we can make 54 half moves before reaching 1 second.
        Assuming a bullet game of 1 min (S = 60), we can make 38 half moves before reaching 1 second.

        In the future, more sophisticated methods can be investigated.
        """
        return (
            self._config.time_weight * time + self._config.increment_weight * increment
        )
