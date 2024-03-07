import multiprocessing
import sys
import time

import pytest
from tenacity import RetryError

from sporkfish.lichess_bot import lichess_bot_berserk
from sporkfish.lichess_bot.game_termination_reason import GameTerminationReason

error_queue = multiprocessing.Queue()
result_queue = multiprocessing.Queue()


class TestLichessBot:
    _sporkfish_api_token_file = "api_token.txt"
    _test_bot_api_token_file = "test_bot_api_token.txt"

    @staticmethod
    def _create_bot(api_token_file: str) -> lichess_bot_berserk.LichessBotBerserk:
        with open(api_token_file) as f:
            return lichess_bot_berserk.LichessBotBerserk(f.read())

    @pytest.mark.skipif(
        sys.platform != "linux",
        reason="Don't create multiple challenges to exceed rate limit of Lichess",
    )
    def test_lichess_bot_playing_ai_timed(self) -> None:
        time_limit = 30

        # If no exceptions, we pass the test.
        def run_game():
            try:
                bot = TestLichessBot._create_bot(
                    TestLichessBot._sporkfish_api_token_file
                )
                bot.client.challenges.create(
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
            raise RuntimeError(
                f"Caught exception when running LichessBot: {error_queue.get()}"
            )
        else:
            proc.terminate()

    @pytest.mark.ci
    def test_accept_challenge(self):
        sporkfish = TestLichessBot._create_bot(TestLichessBot._sporkfish_api_token_file)
        test_bot = TestLichessBot._create_bot(TestLichessBot._test_bot_api_token_file)

        assert sporkfish
        assert test_bot

        challenge_event = test_bot.client.challenges.create(
            username="Sporkfish",
            color="white",
            variant="standard",
            rated=False,
            clock_limit=30,
            clock_increment=0,
        )

        assert challenge_event
        assert sporkfish._event_action_accept_challenge(challenge_event)

        # This should crash if no game is found, thereby verifying there is a game
        sporkfish.client.bots.abort_game(challenge_event["challenge"]["id"])

    @pytest.mark.ci
    def test_decline_challenge(self):
        sporkfish = TestLichessBot._create_bot(TestLichessBot._sporkfish_api_token_file)
        test_bot = TestLichessBot._create_bot(TestLichessBot._test_bot_api_token_file)

        assert sporkfish
        assert test_bot

        # Faulty challenge as atomic variant is not supported
        challenge_event = test_bot.client.challenges.create(
            username="Sporkfish",
            color="white",
            variant="atomic",
            rated=False,
            clock_limit=30,
            clock_increment=0,
        )

        assert challenge_event
        assert not sporkfish._event_action_accept_challenge(challenge_event)
        try:
            sporkfish.client.bots.abort_game(challenge_event["challenge"]["id"])
            assert False, "Expected to fail to abort game as challenge was declined."
        except RetryError:
            # This is a success
            pass

    @pytest.mark.ci
    def test_opponent_resigned(self):
        sporkfish = TestLichessBot._create_bot(TestLichessBot._sporkfish_api_token_file)
        test_bot = TestLichessBot._create_bot(TestLichessBot._test_bot_api_token_file)

        assert sporkfish
        assert test_bot

        challenge_event = test_bot.client.challenges.create(
            username="Sporkfish",
            color="white",
            variant="standard",
            rated=False,
            clock_limit=30,
            clock_increment=0,
        )

        assert challenge_event
        assert sporkfish._event_action_accept_challenge(challenge_event)
        game_id = challenge_event["challenge"]["id"]

        def sporkfish_play() -> None:
            termination = sporkfish._play_game(game_id)
            result_queue.put(termination)

        sporkfish.client.bots.make_move(game_id, "e2e4")
        test_bot.client.bots.make_move(game_id, "e7e5")

        proc = multiprocessing.Process(target=sporkfish_play)
        proc.start()

        assert result_queue.get() == GameTerminationReason.RESIGNATION

        proc.terminate()
