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
        self,
        time_weight: float = 0.1,
        increment_weight: float = 0.01,
        min_move_time: float = 0.01,
        max_time_fraction: float = 0.6,
        reserve_fraction: float = 0.05,
    ) -> None:
        self.time_weight = time_weight
        self.increment_weight = increment_weight
        self.min_move_time = min_move_time
        self.max_time_fraction = max_time_fraction
        self.reserve_fraction = reserve_fraction


class TimeManager:
    """Class for managing time in a chess game."""

    def __init__(self, config: TimeManagerConfig = TimeManagerConfig()) -> None:
        """Initialize TimeManager.

        :param config: Configuration for TimeManager (default: TimeManagerConfig()).
        :type config: TimeManagerConfig
        """
        self._config = config

    def get_timeout(
        self,
        time: float,
        increment: float,
        ply: int | None = None,
    ) -> float:
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

        # Defensive handling for edge cases from GUI / bot inputs.
        if time <= 0:
            return self._config.min_move_time

        # Base budget from the legacy linear model.
        weighted_budget = (
            self._config.time_weight * time
            + self._config.increment_weight * max(0.0, increment)
        )

        # Moves-to-go estimate gives more stable allocations than fixed percentages.
        # Keep estimate in a practical band to avoid extreme budgets.
        if ply is None:
            estimated_moves_to_go = 24
        else:
            # Early game tends to be longer; simplify to a bounded linear estimate.
            estimated_moves_to_go = max(12, min(32, 32 - ply // 6))

        base_budget = time / estimated_moves_to_go
        increment_budget = 0.75 * max(0.0, increment)

        # Blend both strategies and mildly adapt by game phase.
        timeout = max(weighted_budget, base_budget + increment_budget)
        if ply is not None:
            if ply < 20:
                timeout *= 1.1
            elif ply > 70:
                timeout *= 0.9

        # Keep a reserve so we avoid flagging after a few expensive moves.
        reserve = max(self._config.min_move_time, time * self._config.reserve_fraction)
        hard_cap = min(time * self._config.max_time_fraction, max(0.0, time - reserve))

        timeout = min(timeout, hard_cap) if hard_cap > 0 else self._config.min_move_time
        return max(self._config.min_move_time, timeout)
