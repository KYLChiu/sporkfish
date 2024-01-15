from .configurable import Configurable
from .lichess_bot.lichess_bot_berserk import LichessBotBerserk
from .uci_client import UCIClient

from enum import Enum
import logging


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


def run_uci() -> None:
    """Run the UCI (Universal Chess Interface) client."""
    logging.info("Running UCI...")
    client = UCIClient(UCIClient.UCIProtocol.ResponseMode.PRINT)
    while True:
        message = input()
        client.send_command(message)


def run_lichess() -> None:
    """Run the Lichess bot using the Berserk API."""
    logging.info("Running Lichess...")
    with open("api_token.txt") as f:
        lichess_client = LichessBotBerserk(token=f.read())
    lichess_client.run()
