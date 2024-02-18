import datetime
import logging
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple, Union

import berserk
import berserk.exceptions
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from sporkfish.lichess_bot.lichess_bot import LichessBot


# TODO: I can't get this to work with metaclasses. Maybe in a future PR.
# The goal is to automatically wrap all functions in berserk.Client so they are retriable.
class BerserkRetriable:
    """
    Interface to interact with Lichess API with retry logic.
    Wraps the berserk.Client API.
    """

    # Retry configuration parameters
    num_retries = 2
    time_to_wait_seconds = 1

    def __init__(self, token: str):
        """
        Initialize the Berserk instance with the Lichess API token.

        :param token: The Lichess API token.
        :type token: str
        """
        self._client = berserk.Client(berserk.TokenSession(token))

    @retry(
        stop=stop_after_attempt(num_retries),
        wait=wait_fixed(time_to_wait_seconds),
        retry=retry_if_exception_type(berserk.exceptions.ResponseError),
    )
    def send(
        self,
        attribute_name: str,
        *args: Sequence[Any],
        **kwargs: Mapping[str, Any],
    ) -> Any:
        """
        Execute a method on the Lichess API with retry logic.

        :param attribute_name: The name of the method to execute, in the format "module.method", e.g. bots.make_move or bots.stream_incoming_events.
        :type attribute_name: str
        :param args: Positional arguments to be passed to the method.
        :type args: Sequence[Any]
        :param kwargs: Keyword arguments to be passed to the method.
        :type kwargs: Mapping[str, Any]
        :return: The result of the method call.
        :rtype: Any
        :raises AssertionError: If the attribute name is not in the correct format.
        """
        module_func_name = attribute_name.split(".")
        assert (
            len(module_func_name) == 2
        ), f"Expected to send module.func_name (i.e. attribute name of length 2), but got attribute name {attribute_name} of length {len(attribute_name)}."
        module_name, func_name = module_func_name
        module = getattr(self._client, module_name)
        fn = getattr(module, func_name)
        return fn(*args, **kwargs)


class LichessBotBerserk(LichessBot):
    """
    A class representing a Lichess bot powered by the Sporkfish chess engine.
    Powered by the synchronous berserk lichess API.
    Not thread-safe (do not use with multithreading, might exceed rate limit of Lichess).
    """

    def __init__(self, token: str, bot_id: str = "sporkfish") -> None:
        """
        Initialize the LichessBot with a Lichess API token.

        :param token: The Lichess API token.
        :type token: str
        :param bot_id: The identifier for the bot on Lichess. Default is "sporkfish".
        :type bot_id: str
        """
        super().__init__(bot_id)
        self._berserk = BerserkRetriable(token)

    @property
    def client(self) -> BerserkRetriable:
        return self._berserk

    def _get_time_and_inc(
        self, color: int, state: Dict[str, Any]
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Extracts the time and increment given the color and game state.

        :param color: The color of the player (0 for white, 1 for black), defaults to None
        :type color: int, optional
        :param state: The game state containing time and increment information
        :type state: Any

        :return: A tuple containing the time and increment for the specified color, or None if the game is correspondence
        :rtype: Tuple[Optional[float], Optional[float]]
        """
        if state.get("perf", {}).get("name") == "Correspondence":  # type: ignore
            return None, None

        game_state: Dict[str, Any] = state.get("state", state)

        # Extracts the second from a datetime object or converts milliseconds to seconds
        def _extract_second(obj: Union[datetime.datetime, int, Any]) -> Optional[float]:
            return (
                obj.timestamp()
                if isinstance(obj, datetime.datetime)
                else obj / 1000.0
                if isinstance(obj, int)
                else None
            )

        color_str = "w" if not color else "b"
        time_obj = game_state.get(f"{color_str}time")
        inc_obj = game_state.get(f"{color_str}inc")
        return _extract_second(time_obj), _extract_second(inc_obj)

    def _set_pos_and_play_move(
        self, color: int, prev_moves: str, game_id: str, state: Any
    ) -> None:
        """
        Set the position and play a move based on the number of moves, color, previous moves, game ID, and state.

        :param color: The color of the player (0 for white, 1 for black).
        :type color: int
        :param prev_moves: The previous moves made in the game.
        :type prev_moves: str
        :param game_id: The ID of the game.
        :type game_id: str
        :param state: The current state of the game.
        :type state: Any
        :return: None
        """
        # Check if it's the player's turn based on the number of moves and color
        if len(prev_moves.split()) & 1 == color:
            self._set_position(prev_moves)
            time, inc = self._get_time_and_inc(color, state)
            best_move = self._get_best_move(color, time, inc)
            self._berserk.send("bots.make_move", game_id, best_move)

    def _play_game(self, game_id: str) -> None:
        """
        Play a game on Lichess by streaming game states, setting positions, and making moves.

        :param game_id: The ID of the game on Lichess.
        :type game_id: str
        """
        # Get game states and process initial state
        states = self._berserk.send("bots.stream_game_state", game_id)
        game_full = next(states)
        logging.debug(f"Full game data: {game_full}")

        color = 0 if game_full["white"].get("id") == self._bot_id else 1
        prev_moves_start: str = game_full["state"].get("moves", "")

        # Log game status
        game_status = "Restarting" if len(prev_moves_start.split()) > 0 else "Starting"
        logging.info(f"{game_status} game with id: {game_id}")

        # Play initial move to receive updated game states
        # This occurs if:
        # 1) We are starting a new game and playing white
        # 2) We are restarting the game and it's our turn to play, i.e.
        #    prev_num_moves & 1 == color (0 for white, 1 for black)
        self._set_pos_and_play_move(color, prev_moves_start, game_id, game_full)

        # Loop through subsequent game states
        for state in states:
            logging.debug(f"Game state: {state}")
            if state["type"] == "gameState":
                self._set_pos_and_play_move(color, state["moves"], game_id, state)

    def run(self) -> None:
        """
        Start the Lichess bot, listening to incoming events sequentially and playing games accordingly.
        """
        events = self._berserk.send("bots.stream_incoming_events")
        for event in events:
            if event.get("type") == "gameStart":
                self._play_game(event["game"]["fullId"])
