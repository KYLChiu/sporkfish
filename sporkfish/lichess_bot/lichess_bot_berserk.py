import datetime
import logging
import time
from typing import Any, Dict, Iterator, Optional, Tuple, Union

import berserk

from sporkfish.lichess_bot.berserk_retriable import BerserkRetriable
from sporkfish.lichess_bot.game_termination_reason import GameTerminationReason
from sporkfish.lichess_bot.lichess_bot import LichessBot


class GameHandler:
    """
    A class representing a game handler for a Lichess game.
    It contains the game state and methods to interact with the game.
    """

    @property
    def client(self) -> berserk.Client:
        return self._berserk._client

    def __init__(self, game_id, _berserk):
        """
        Initialize the GameHandler with a game ID and a BerserkRetriable instance.

        :param game_id: The ID of the game provided by Lichess.
        :type game_id: str
        :param _berserk: The BerserkRetriable instance to interact with the Lichess API.
        :type _berserk: BerserkRetriable
        """
        self.game_id = game_id
        self._berserk = _berserk
        # Initialize game state

    def stream_game_state(self):
        return self.client.bots.stream_game_state(self.game_id)

    def make_move(self, best_move):
        self.client.bots.make_move(self.game_id, best_move)


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
        self.active_games = {}  # Store active games

    @property
    def client(self) -> berserk.Client:
        return self._berserk._client

    def _extract_second(
        self, obj: Union[datetime.datetime, int, Any]
    ) -> Optional[float]:
        """
        Extracts the second from the given object.

        :param obj: The object from which to extract the second.
        :type obj: Union[datetime.datetime, int, Any]
        :return: The second extracted from the object, or None if the object is not of the expected types.
        :rtype: Optional[float]
        """
        return (
            obj.timestamp()
            if isinstance(obj, datetime.datetime)
            else obj / 1000.0
            if isinstance(obj, int)
            else None
        )

    def _get_time(
        self, color: int, state: Dict[str, Any]
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Extracts the time and increment given the color and game state.

        :param color: The color of the player (0 for white, 1 for black)
        :type color: int
        :param state: The game state containing time and increment information
        :type state: Any

        :return: A tuple containing the time and increment for the specified color, or None if the game is correspondence
        :rtype: Tuple[Optional[float], Optional[float]]
        """
        if state.get("perf", {}).get("name") == "Correspondence":  # type: ignore
            return None, None

        game_state: Dict[str, Any] = state.get("state", state)

        color_str = "w" if not color else "b"
        time_obj = game_state.get(f"{color_str}time")
        inc_obj = game_state.get(f"{color_str}inc")
        return self._extract_second(time_obj), self._extract_second(inc_obj)

    def _play_move(
        self, game_handler: GameHandler, color: int, prev_moves: str, state: Any
    ) -> None:
        """
        Set the position and play a move based on the number of moves, color, previous moves, game ID, and state.

        :param game_handler: The game handler for the current game.
        :type game_handler: GameHandler
        :param color: The color of the player (0 for white, 1 for black).
        :type color: int
        :param prev_moves: The previous moves made in the game.
        :type prev_moves: str
        :param state: The current state of the game.
        :type state: Any
        """
        # Check if it's the player's turn based on the number of moves and color
        if len(prev_moves.split()) & 1 == color:
            self._set_position(prev_moves)
            time, inc = self._get_time(color, state)
            best_move = self._get_best_move(color, time, inc)
            game_handler.make_move(best_move)

    def _handle_states(
        self, game_id: str, states: Iterator[Dict[str, Any]]
    ) -> GameTerminationReason:
        """
        Look for a game with the specified ID and play it. If the game is not found, create a new game.
        If a game is found, play the game based on the given game states.

        :param game_id: The ID of the game on Lichess.
        :type game_id: str
        :param states: The game states to play the game from.
        :type states: Iterator[Dict[str, Any]]

        :return: The reason for the game termination.
        :rtype: GameTerminationReason
        """
        if game_id not in self.active_games:
            self.active_games[game_id] = GameHandler(game_id, self._berserk)
        game_handler = self.active_games[game_id]

        # Get game states and process initial state
        states = game_handler.stream_game_state()
        game_full = next(states)
        logging.debug(f"Full game data: {game_full}")

        color = 0 if game_full["white"].get("id") == self._bot_id else 1
        prev_moves_start: str = game_full["state"].get("moves", "")

        # Log game status
        game_status = "Restarting" if prev_moves_start else "Starting"
        logging.info(f"{game_status} game with id: {game_id}")

        # Play initial move to receive updated game states
        # This occurs if:
        # 1) We are starting a new game and playing white
        # 2) We are restarting the game and it's our turn to play, i.e.
        #    prev_num_moves & 1 == color (0 for white, 1 for black)
        self._play_move(game_handler, color, prev_moves_start, game_full)

        # Loop through subsequent game states
        for state in states:
            logging.debug(f"Game state: {state}")
            if state["type"] == "gameState":
                self._play_move(game_handler, color, state["moves"], state)
            elif state["type"] == "gameStateResign":
                return GameTerminationReason.RESIGNATION
            elif state["type"] == "opponentGone":
                # Busy polling is fine, nothing else to do
                # Alternative is to asynchronously wait while finding the PV, if PV is the same as opponents move then play
                # But this is more complex and not necessary for now
                can_claim_win = state["claimWinInSeconds"]
                start = time.time()
                while True:
                    if state["gone"]:
                        # Claim victory if opponent is gone for more than the claimWinInSeconds
                        if time.time() - start > can_claim_win:
                            try:
                                self.client.board.claim_victory(game_id)
                                return GameTerminationReason.OPPONENT_LEFT
                            except Exception as e:
                                logging.error(f"Error claiming victory: {e}")
                                break
                        # Otherwise, keep polling
                    else:
                        break

        return GameTerminationReason.UNKNOWN

    def _play_game(self, game_id: str) -> GameTerminationReason:
        """
        Stream game states and pass to function handling game states.

        :param game_id: The ID of the game on Lichess.
        :type game_id: str

        :return: The reason for the game termination.
        :rtype: GameTerminationReason
        """
        states = self.client.bots.stream_game_state(game_id)
        return self._handle_states(game_id, states)

    @classmethod
    def _should_accept_challenge(cls, event: Dict[str, Any]) -> bool:
        """
        Determines whether the bot should accept a challenge based on the event details.

        :param event: The event details containing the challenge information.
        :type event: Dict[str, Any]

        :return: True if the bot should accept the challenge, False otherwise.
        :rtype: bool
        """
        variant_key = event["challenge"]["variant"]["key"]
        speed = event["challenge"]["speed"]
        if (variant_key in cls._ACCEPTED_VARIANTS) and (
            speed in cls._ACCEPTED_TIME_CONTROLS
        ):
            logging.debug(
                f"Accecpting challenge with variant: {variant_key} and speed: {speed}"
            )
            return True
        logging.debug(
            f"Declining challenge with variant: {variant_key} and speed: {speed}"
        )
        return False

    # --- Event handlers ---
    def _event_action_accept_challenge(self, event: Dict[str, Any]) -> bool:
        """
        Accepts or declines a challenge based on certain conditions.

        :param event: The event containing information about the challenge.
        :type event: Dict[str, Any]

        :return: True if the challenge is accepted, False if it is declined.
        :rtype: bool
        """
        if self._should_accept_challenge(event):
            self.client.bots.accept_challenge(event["challenge"]["id"])
            return True
        else:
            self.client.bots.decline_challenge(event["challenge"]["id"])
            return False

    def _event_action_play_game(self, event: Dict[str, Any]) -> GameTerminationReason:
        """
        Initiates gameplay for the specified game.

        :param event: The event containing information about the game.
        :type event: Dict[str, Any]

        :return: The reason for the game termination.
        :rtype: GameTerminationReason
        """
        return self._play_game(event["game"]["fullId"])

    def _event_action_game_finish(self, event: Dict[str, Any]) -> None:
        """
        Posts a chat message in response to a game event.

        :param event: The event containing information about the game.
        :type event: Dict[str, Any]
        """
        self.client.bots.post_message(
            event["game"]["fullId"],
            LichessBot._GAME_FINISHED_MESSAGE,
        )

    _event_actions = {
        "challenge": _event_action_accept_challenge,
        "gameStart": _event_action_play_game,
        "gameFinish": _event_action_game_finish,
    }

    def run(self) -> None:
        """
        Start the Lichess bot, listening to incoming events sequentially and playing games accordingly.
        """
        for event in self.client.bots.stream_incoming_events():
            if action := self._event_actions.get(event.get("type", "")):
                action(self, event)
