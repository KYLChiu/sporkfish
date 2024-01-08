import berserk
import sporkfish.uci_client as uci_client
import logging


class LichessBot:
    """
    A class representing a Lichess bot powered by the Sporkfish chess engine.

    Attributes:
    - _session (berserk.TokenSession): The session object for interacting with the Lichess API.
    - _client (berserk.Client): The client for making requests to the Lichess API.
    - _bot_id (str): The identifier for the bot on Lichess.
    - _sporkfish (uci_client.UCIClient): The UCI client using the Sporkfish chess engine.

    Methods:
    - __init__(token: str, bot_id: str = "sporkfish"):
        Initialize the LichessBot with a Lichess API token and a bot identifier.

    - _make_bot_move(game_id: str):
        Make a move for the bot using the Sporkfish engine.

    - _set_position(moves: str):
        Set the chess position based on a sequence of moves.

    - play_game(game_id: str):
        Play a game on Lichess by streaming game states, setting positions, and making moves.

    - run():
        Start the Lichess bot, listening to incoming events and playing games accordingly.

    """

    def __init__(self, token: str, bot_id: str = "sporkfish"):
        """
        Initialize the LichessBot with a Lichess API token and a bot identifier.

        :param token: The Lichess API token.
        :type token: str
        :param bot_id: The identifier for the bot on Lichess. Default is "sporkfish".
        :type bot_id: str
        """
        self._session = berserk.TokenSession(token)
        self._client = berserk.Client(session=self._session)
        self._bot_id = bot_id
        self._sporkfish = uci_client.UCIClient(
            response_mode=uci_client.UCIClient.UCIProtocol.ResponseMode.RETURN
        )

    @property
    def client(self):
        return self._client

    def _make_bot_move(self, game_id: str):
        """
        Make a move for the bot using the Sporkfish engine.

        :param game_id: The ID of the game on Lichess.
        :type game_id: str
        """
        best_move = self._sporkfish.send_command("go").split()[1]
        self._client.bots.make_move(game_id, best_move)

    def _set_position(self, moves: str):
        """
        Set the chess position based on a sequence of UCI moves (space delimited).

        :param moves: A sequence of chess moves.
        :type moves: str
        """
        self._sporkfish.send_command(f"position startpos moves {moves}")

    def play_game(self, game_id: str):
        """
        Play a game on Lichess by streaming game states, setting positions, and making moves.

        :param game_id: The ID of the game on Lichess.
        :type game_id: str
        """
        states = self._client.bots.stream_game_state(game_id)
        game_full = next(states)
        logging.debug(f"Full game data: {game_full}")
        color = 0 if game_full["white"].get("id") == self._bot_id else 1
        prev_moves = game_full["state"]["moves"] or ""
        num_played_moves = len(prev_moves.split())

        if num_played_moves > 0:
            logging.info(f"Restarting game with id: {game_id}")
        else:
            logging.info(f"Starting game with id: {game_id}")

        if num_played_moves & 1 == color:
            self._set_position(prev_moves)
            self._make_bot_move(game_id)

        for state in states:
            logging.debug(f"Game state: {state}")
            if state["type"] == "gameState":
                num_moves = len(state["moves"].split())
                if num_moves & 1 == color:
                    self._set_position(state["moves"])
                    self._make_bot_move(game_id)

    def run(self):
        """
        Start the Lichess bot, listening to incoming events sequentially and playing games accordingly.
        """
        events = self._client.bots.stream_incoming_events()
        # Needs check for variant and speed
        for event in events:
            if event.get("type") == "gameStart":
                self.play_game(event["game"]["fullId"])
