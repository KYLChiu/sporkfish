import datetime
import logging
from typing import Any, Optional, Tuple

import berserk
import berserk.exceptions
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from sporkfish.lichess_bot.lichess_bot import LichessBot


class LichessBotBerserk(LichessBot):
    """
    A class representing a Lichess bot powered by the Sporkfish chess engine.
    Powered by the synchronous berserk lichess API.
    Not thread-safe (do not use with multithreading, might exceed rate limit of Lichess).

    Attributes:
    - _session (berserk.TokenSession): The session object for interacting with the Lichess API.
    - _berserk (berserk.Client): The client for making requests to the Lichess API.
    - _bot_id (str): The identifier for the bot on Lichess.
    - _sporkfish (uci_berserk.UCIClient): The UCI client using the Sporkfish chess engine.

    Methods:
    - __init__(token: str, bot_id: str = "sporkfish", max_concurrent_games: int = 4):
        Initialize the LichessBot with a Lichess API token and a bot identifier.

    - _make_bot_move(game_id: str) -> None:
        Make a move for the bot using the Sporkfish engine.

    - _set_position(moves: str) -> None:
        Set the chess position based on a sequence of UCI moves (space delimited).

    - _play_game(game_id: str, test: bool = False) -> None:
        Play a game on Lichess by streaming game states, setting positions, and making moves.

    - run() -> None:
        Start the Lichess bot, listening to incoming events sequentially and playing games accordingly.

    """

    class Berserk:
        def __init__(self, token: str) -> None:
            """
            Initialize the Berserk class with a Lichess API token.

            :param token: The Lichess API token.
            :type token: str
            """
            self._session = berserk.TokenSession(token)
            self._client = berserk.Client(session=self._session)

    def __init__(self, token: str, bot_id: str = "sporkfish") -> None:
        """
        Initialize the LichessBot with a Lichess API token.

        :param token: The Lichess API token.
        :type token: str
        :param bot_id: The identifier for the bot on Lichess. Default is "sporkfish".
        :type bot_id: str
        """
        super().__init__(bot_id)
        self._berserk = LichessBotBerserk.Berserk(token)

    @property
    def client(self) -> berserk.Client:
        """
        Get the berserk client.

        :return: The berserk client.
        :rtype: berserk.Client
        """
        return self._berserk._client

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_fixed(60 * 1000),  # 1 min, to adhere to lichess rate limiting
        retry=retry_if_exception_type(berserk.exceptions.ResponseError),
    )
    def _play_game(self, game_id: str) -> None:
        """
        Play a game on Lichess by streaming game states, setting positions, and making moves.

        :param game_id: The ID of the game on Lichess.
        :type game_id: str
        """

        def get_time_and_inc(
            color: int, state: Any
        ) -> Tuple[Optional[float], Optional[float]]:
            if (
                state.get("perf", None)
                and state.get("perf").get("name", None) == "Correspondence"
            ):
                return None, None

            game_state = state["state"] if state["type"] == "gameFull" else state

            def extract_second(obj: Any) -> Optional[float]:
                if isinstance(obj, datetime.datetime):
                    return obj.timestamp()
                elif isinstance(obj, int):
                    return obj / 1000
                else:
                    return None

            time_str = "wtime" if not bool(color) else "btime"
            inc_str = "winc" if not bool(color) else "binc"
            time_obj = game_state.get(time_str, None)
            inc_obj = game_state.get(inc_str, None)
            time = extract_second(time_obj)
            inc = extract_second(inc_obj)
            return time, inc

        def set_pos_and_play_move(
            num_moves: int, color: int, prev_moves: str, game_id: str, state: Any
        ) -> None:
            if num_moves & 1 == color:
                self._set_position(prev_moves)
                time, inc = get_time_and_inc(color, state)
                best_move = self._get_best_move(color, time, inc)
                self.client.bots.make_move(game_id, best_move)

        states = self.client.bots.stream_game_state(game_id)
        game_full = next(states)
        logging.debug(f"Full game data: {game_full}")
        color = 0 if game_full["white"].get("id") == self._bot_id else 1
        prev_moves_start = game_full["state"]["moves"] or ""
        num_moves_start = len(prev_moves_start.split())

        if num_moves_start > 0:
            logging.info(f"Restarting game with id: {game_id}")
        else:
            logging.info(f"Starting game with id: {game_id}")

        # If white (and playing a new game), we need to play a move to get new states
        set_pos_and_play_move(
            num_moves_start, color, prev_moves_start, game_id, game_full
        )

        for state in states:
            logging.debug(f"Game state: {state}")
            if state["type"] == "gameState":
                num_moves = len(state["moves"].split())
                prev_moves = state["moves"]
                set_pos_and_play_move(num_moves, color, prev_moves, game_id, state)

    def run(self) -> None:
        """
        Start the Lichess bot, listening to incoming events sequentially and playing games accordingly.
        """

        events = self.client.bots.stream_incoming_events()
        for event in events:
            if event.get("type") == "gameStart":
                self._play_game(event["game"]["fullId"])
