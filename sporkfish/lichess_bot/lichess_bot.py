from abc import ABC, abstractmethod


class LichessBot(ABC):
    """
    An abstract base class representing a Lichess bot.

    Methods:
    - run():
        Start the Lichess bot, listening to incoming events and playing games accordingly.
    """

    @abstractmethod
    def run(self, timeout=None):
        """
        Start the Lichess bot, listening to incoming events and playing games accordingly.
        """
        pass
