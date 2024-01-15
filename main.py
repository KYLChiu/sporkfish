import multiprocessing
import logging.config
import logging

from config import load_config
from sporkfish.runner import RunConfig, RunMode, run_lichess, run_uci


if __name__ == "__main__":
    config = load_config()

    logging_config = config.get("LoggingConfig")
    run_config = RunConfig.from_dict(config.get("RunConfig"))

    multiprocessing.freeze_support()

    logging.config.dictConfig(logging_config)

    logging.info("----- Sporkfish -----")

    if run_config.mode == RunMode.LICHESS:
        run_lichess()
    else:
        run_uci()
