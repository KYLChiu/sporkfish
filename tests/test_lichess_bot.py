from sporkfish import lichess_bot
import berserk.exceptions


def test_lichess_bot_playing_ai():
    try:
        bot = lichess_bot.LichessBot(token=open("api_token.txt").read())
        challenge = bot.client.challenges.create_ai(level=1, color="white")
        game_id = challenge["id"]
        # Ideally we don't test private functionality but no need to play the whole game
        bot._make_bot_move(game_id)
        bot.client.bots.resign_game(game_id)
    except berserk.exceptions.ResponseError as e:
        assert False, f"LichessBot failed with exception: {e}"
