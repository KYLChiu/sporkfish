import inspect
import logging
from enum import Enum

from .configurable import Configurable
from .lichess_bot.lichess_bot_berserk import LichessBotBerserk
from .uci_client import UCIClient


class RunMode(Enum):
    """Enumeration for different run modes."""

    LICHESS = "LICHESS"
    UCI = "UCI"


class RunConfig(Configurable):
    """Configuration class for the run mode.

    :param mode: The run mode (default: RunMode.LICHESS).
    :type mode: RunMode
    """

    def __init__(self, mode: RunMode = RunMode.LICHESS) -> None:
        self.mode = mode if isinstance(mode, RunMode) else RunMode(mode)


class Runner:
    """Class responsible for running the appropriate client based on the run configuration."""

    def __init__(self, run_config: RunConfig):
        """
        Initialize the Runner object.

        :param run_config: The run configuration specifying the mode of operation.
        :type run_config: RunConfig
        """
        self._run_config = run_config

    @staticmethod
    def _run_uci() -> None:
        """
        Run the UCI (Universal Chess Interface) client.

        This method initializes a UCI client and sends user input as commands to the client.
        """
        logging.info("Running in UCI mode...")
        client = UCIClient(UCIClient.UCIProtocol.ResponseMode.PRINT)
        while True:
            message = input()
            client.send_command(message)

    @staticmethod
    def _run_lichess() -> None:
        """
        Run the Lichess bot using the Berserk API.

        This method initializes a Lichess bot using the Berserk API and runs it.
        """
        logging.info("Running in Lichess mode...")
        with open("api_token.txt") as f:
            lichess_client = LichessBotBerserk(token=f.read())
        lichess_client.run()

    _mode_actions = {RunMode.LICHESS: _run_lichess, RunMode.UCI: _run_uci}

    def run(self) -> None:
        """
        Run the appropriate client based on the run configuration.

        If the run mode is set to LICHESS, it runs the Lichess bot, otherwise, it runs the UCI client.
        """
        action = self._mode_actions.get(self._run_config.mode)
        assert action, f"Run mode '{self._run_config.mode}' is not supported."
        assert callable(action), f"Function '{action.__name__}' is not callable."
        assert (
            len(inspect.signature(action).parameters) == 0
        ), f"Function '{action.__name__}' does not accept zero arguments."
        action()
