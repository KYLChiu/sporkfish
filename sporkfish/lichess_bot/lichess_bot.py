from abc import ABC, abstractmethod
import sporkfish.uci_client as uci_client


class LichessBot(ABC):
    """
    An abstract base class representing a Lichess bot.

    Methods:
    - run():
        Start the Lichess bot, listening to incoming events and playing games accordingly.
    """

    def __init__(self, bot_id: str) -> None:
        """
        Initialize the LichessBot with UCIClient.
        """
        self._sporkfish = uci_client.UCIClient(
            response_mode=uci_client.UCIClient.UCIProtocol.ResponseMode.RETURN
        )
        self._bot_id = bot_id

    def _get_best_move(self) -> str:
        """
        Get the best move for the bot using the Sporkfish engine.

        :param game_id: The ID of the game on Lichess.
        :type game_id: str
        """
        return self._sporkfish.send_command("go").split()[1]

    def _set_position(self, moves: str) -> None:
        """
        Set the chess position based on a sequence of UCI moves (space delimited).

        :param moves: A sequence of chess moves.
        :type moves: str
        """
        self._sporkfish.send_command(f"position startpos moves {moves}")

    @abstractmethod
    def run(self, timeout: float = None):
        """
        Start the Lichess bot, listening to incoming events and playing games accordingly.

        :param timeout: seconds until the bot stops running.
        :type float
        """
        pass
