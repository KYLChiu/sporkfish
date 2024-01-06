import berserk
import sporkfish.uci_client as uci_client
import logging
from . import uci_communicator


class LichessBot:
    def __init__(self, token, bot_id="sporkfish"):
        self._session = berserk.TokenSession(token)
        self._client = berserk.Client(session=self._session)
        self._bot_id = bot_id
        self._sporkfish = uci_client.UCIClient(
            response_mode=uci_communicator.ResponseMode.RETURN
        )

    def _make_bot_move(self, game_id):
        best_move = self._sporkfish.send_command("go").split()[1]
        self._client.bots.make_move(game_id, best_move)

    def _set_position(self, moves):
        self._sporkfish.send_command(f"position startpos moves {moves}")

    def _play_game(self, game_id):
        gen_state = self._client.bots.stream_game_state(game_id)
        game_full = next(gen_state)
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

        for state in gen_state:
            logging.debug(f"Game state: {game_full}")
            num_moves = len(state["moves"].split())
            if num_moves & 1 == color:
                self._set_position(state["moves"])
                self._make_bot_move(game_id)

    def run(self):
        events = self._client.bots.stream_incoming_events()
        for event in events:
            if event.get("type") == "gameStart":
                self._play_game(event["game"]["fullId"])
