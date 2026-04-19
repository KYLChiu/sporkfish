import pytest

from sporkfish.time_manager import TimeManager, TimeManagerConfig


class TestTimeManager:
    def test_timeout_has_minimum_floor(self) -> None:
        tm = TimeManager(TimeManagerConfig(min_move_time=0.02))
        assert tm.get_timeout(0.0, 0.0) == pytest.approx(0.02)

    def test_timeout_respects_reserve_and_cap(self) -> None:
        tm = TimeManager(
            TimeManagerConfig(
                time_weight=0.5,
                increment_weight=0.5,
                min_move_time=0.01,
                max_time_fraction=0.6,
                reserve_fraction=0.05,
            )
        )

        timeout = tm.get_timeout(time=10.0, increment=0.0, ply=10)

        # Must never exceed max_time_fraction * time.
        assert timeout <= 6.0
        # Must also leave at least reserve_fraction * time in the clock.
        assert timeout <= 9.5

    def test_opening_phase_gets_more_time_than_late_phase(self) -> None:
        tm = TimeManager(TimeManagerConfig())

        early = tm.get_timeout(time=60.0, increment=1.0, ply=8)
        late = tm.get_timeout(time=60.0, increment=1.0, ply=90)

        assert early > late

    def test_increment_never_hurts_budget(self) -> None:
        tm = TimeManager(TimeManagerConfig())

        without_inc = tm.get_timeout(time=30.0, increment=0.0, ply=30)
        with_inc = tm.get_timeout(time=30.0, increment=2.0, ply=30)

        assert with_inc >= without_inc
