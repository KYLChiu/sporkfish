import cProfile
import os
import pstats
import sys
from typing import Any, Callable


def run_perf_analytics(test_name: str, f: Callable[..., Any], *args, **kwargs) -> None:
    """
    Run performance analytics on a given function.

    :param test_name: Name of the test.
    :type test_name: str
    :param f: Function to analyze performance for.
    :type f: Callable[..., Any]
    :param args: Positional arguments to pass to the function.
    :param kwargs: Additional keyword arguments to pass to the function.
    :type kwargs: dict
    """

    profiler = cProfile.Profile()
    profiler.enable()
    f(*args, **kwargs)
    profiler.disable()
    stats = pstats.Stats(profiler)

    test_name = (
        test_name.replace("[", "_")
        .replace("]", "_")
        .replace(" ", "_")
        .replace("/", "_")
    )
    perf_test_folder = "perf/"

    if not os.path.exists(perf_test_folder):
        os.mkdir(perf_test_folder)

    with open(
        os.path.join(perf_test_folder, f"{test_name}.txt"),
        "w",
    ) as file:
        sys.stdout = file
        print(
            "------------------------------------------------------------------------------------------------"
        )
        stats = pstats.Stats(profiler)
        stats.strip_dirs().sort_stats("tottime").print_stats()
        print(
            "------------------------------------------------------------------------------------------------"
        )

    sys.stdout = sys.__stdout__
