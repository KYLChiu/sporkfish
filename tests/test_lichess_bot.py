import multiprocessing
import sys
import time

import pytest

from sporkfish.lichess_bot import lichess_bot_berserk

error_queue = multiprocessing.Queue()


@pytest.mark.skipif(
    sys.platform != "linux",
    reason="Multiprocess error on other OSes. To be fixed.",
)
def test_lichess_bot_playing_ai_timed() -> None:
    time_limit = 30

    def run_game():
        try:
            api_token_file = "api_token.txt"
            with open(api_token_file) as f:
                bot = lichess_bot_berserk.LichessBotBerserk(f.read())
                bot.client.send(
                    "challenges.create",
                    username="maia9",
                    color="white",
                    rated=False,
                    clock_limit=time_limit,
                    clock_increment=0,
                )
                bot.run()
        except Exception as e:
            error_queue.put(e)

    proc = multiprocessing.Process(target=run_game)
    proc.start()

    time.sleep(time_limit * 2)

    if not error_queue.empty():
        e = error_queue.get()
        raise e
    else:
        proc.terminate()

    # If no exceptions, we pass the test.
