import logging
import logging.config
import multiprocessing

from config import load_config
from sporkfish.runner import Runner, RunConfig

if __name__ == "__main__":
    config = load_config()

    logging_config = config.get("LoggingConfig")

    multiprocessing.freeze_support()

    logging.config.dictConfig(logging_config)

    logging.info("----- Sporkfish -----")

    runner = Runner(RunConfig.from_dict(config.get("RunConfig")))
    runner.run()
