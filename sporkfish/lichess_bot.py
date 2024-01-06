import berserk
import sporkfish.uci_client as uci_client
from . import uci_communicator


class LichessBot:

    """
    Does not yet support reconnecting to game.
    """

    def __init__(self, token, bot_id="sporkfish"):
        self.session = berserk.TokenSession(token)
        self.client = berserk.Client(session=self.session)
        self.bot_id = bot_id

    def play_game(self, game_id):
        print("Game is starting!")
        bot = uci_client.UCIClient(response_mode=uci_communicator.ResponseMode.RETURN)
        gen_state = self.client.bots.stream_game_state(game_id)
        initial_state = next(gen_state)
        color = (
            0
            if "id" in initial_state["white"]
            and initial_state["white"]["id"] == self.bot_id
            else 1
        )
        num_moves = 0
        prev_moves = initial_state["moves"] if "moves" in initial_state else []

        if color == 0:
            best_move = bot.send_command("go").split()[1]
            self.client.bots.make_move(game_id, best_move)

        for state in gen_state:
            num_moves += 1
            if num_moves % 2 == color:
                prev_moves = state["moves"]
                bot.send_command(f"position startpos moves {prev_moves}")
                best_move = bot.send_command("go").split()[1]
                self.client.bots.make_move(game_id, best_move)

    def run(self):
        events = self.client.bots.stream_incoming_events()
        for event in events:
            if "type" in event and event["type"] == "gameStart":
                game_id = event["game"]["fullId"]
                self.play_game(game_id)
