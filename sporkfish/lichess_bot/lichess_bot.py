from abc import ABC, abstractmethod
from typing import Optional

import sporkfish.uci_client as uci_client


class LichessBot(ABC):
    """
    An abstract base class representing a Lichess bot.
    This can be extended for different variants, warranting the base class.

    Methods:
    - run():
        Start the Lichess bot, listening to incoming events and playing games accordingly.
    """

    _ACCEPTED_VARIANTS = ["standard"]
    _ACCEPTED_TIME_CONTROLS = {"rapid", "bullet", "blitz"}
    _GAME_FINISHED_MESSAGE = "GGWP, hope you had fun playing with Sporkfish!"

    def __init__(self, bot_id: str) -> None:
        """
        Initialize the LichessBot with UCIClient.
        """
        self._sporkfish = uci_client.UCIClient(
            response_mode=uci_client.UCIClient.UCIProtocol.ResponseMode.RETURN
        )
        self._bot_id = bot_id

    def _get_best_move(
        self,
        color: int,
        time: Optional[float] = None,
        increment: Optional[float] = None,
    ) -> str:
        """
        Get the best move for the bot using the Sporkfish engine.

        :param color: Player color. 0 for white and 1 for black.
        :type color: int
        :param time: Time (in ms) left for player.
        :type time: Optional[float]
        :param increment: Increment (in ms) for player.
        :type increment: Optional[float]

        :return: The UCI command to send but without the best move.
        :rtype: str
        """
        command = "go"

        if time is not None and increment is not None:
            time_ms = time * 1000
            inc_ms = increment * 1000
            time_command = (
                f" wtime {time_ms} winc {inc_ms}"
                if not bool(color)
                else f" btime {time_ms} binc {inc_ms}"
            )
            command += time_command

        response = self._sporkfish.send_command(command)

        # Remove "bestmove" from the start
        return response.split()[1]

    def _set_position(self, moves: str) -> None:
        """
        Set the chess position based on a sequence of UCI moves (space delimited).

        :param moves: A sequence of chess moves.
        :type moves: str
        """
        self._sporkfish.send_command(f"position startpos moves {moves}")

    @abstractmethod
    def run(self) -> None:
        """
        Start the Lichess bot, listening to incoming events and playing games accordingly.

        :param timeout: seconds until the bot stops running.
        :type float
        """
        pass
