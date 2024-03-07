import os
import sys

import pytest

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def pytest_addoption(parser):
    parser.addoption(
        "--runslow", action="store_true", default=False, help="run slow tests"
    )
    parser.addoption(
        "--ci",
        action="store_true",
        default=False,
        help="indicate running in CI environment",
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: mark test as slow to run")
    config.addinivalue_line("markers", "ci: mark test to run only in CI environment")


def pytest_collection_modifyitems(config, items):
    config_runslow = config.getoption("--runslow")
    config_ci = config.getoption("--ci")
    for item in items:
        if not config_runslow and "slow" in item.keywords:
            skip_slow = pytest.mark.skip(reason="need --runslow option to run")
            item.add_marker(skip_slow)
        elif not config_ci and "ci" in item.keywords:
            skip_ci = pytest.mark.skip(reason="need --ci option to run")
            item.add_marker(skip_ci)
