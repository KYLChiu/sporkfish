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
        wtime: Optional[float] = None,
        btime: Optional[float] = None,
        winc: Optional[float] = None,
        binc: Optional[float] = None,
    ) -> str:
        """
        Get the best move for the bot using the Sporkfish engine.

        :param wtime: White time remaining in seconds.
        :param btime: Black time remaining in seconds.
        :param winc: White increment in seconds.
        :param binc: Black increment in seconds.

        :return: The best move in UCI notation.
        :rtype: str
        """
        command = "go"

        if wtime is not None and btime is not None:
            command += f" wtime {wtime * 1000} btime {btime * 1000}"
            if winc is not None:
                command += f" winc {winc * 1000}"
            if binc is not None:
                command += f" binc {binc * 1000}"

        response = self._sporkfish.send_command(command)

        # Remove "bestmove" from the start
        return response.split()[1]

    def _set_position(self, moves: str) -> None:
        """
        Set the chess position based on a sequence of UCI moves (space delimited).

        :param moves: A sequence of chess moves.
        :type moves: str
        """
        if moves.strip():
            self._sporkfish.send_command(f"position startpos moves {moves}")
        else:
            self._sporkfish.send_command("position startpos")

    @abstractmethod
    def run(self) -> None:
        """
        Start the Lichess bot, listening to incoming events and playing games accordingly.

        :param timeout: seconds until the bot stops running.
        :type float
        """
        pass
