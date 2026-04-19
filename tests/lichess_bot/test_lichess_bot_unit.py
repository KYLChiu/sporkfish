import datetime
from types import SimpleNamespace

import sporkfish.lichess_bot.berserk_retriable as berserk_retriable_module
from sporkfish.lichess_bot.berserk_retriable import BerserkRetriable
from sporkfish.lichess_bot.game_termination_reason import GameTerminationReason
from sporkfish.lichess_bot.lichess_bot import LichessBot
from sporkfish.lichess_bot.lichess_bot_berserk import LichessBotBerserk


class DummyLichessBot(LichessBot):
    def run(self) -> None:
        return None


class TestLichessBotBase:
    def test_get_best_move_without_time_controls(self) -> None:
        sent = []
        bot = DummyLichessBot("sporkfish")
        bot._sporkfish = SimpleNamespace(
            send_command=lambda cmd: sent.append(cmd) or "bestmove e2e4"
        )

        move = bot._get_best_move()

        assert move == "e2e4"
        assert sent == ["go"]

    def test_get_best_move_with_time_controls(self) -> None:
        sent = []
        bot = DummyLichessBot("sporkfish")
        bot._sporkfish = SimpleNamespace(
            send_command=lambda cmd: sent.append(cmd) or "bestmove g1f3"
        )

        move = bot._get_best_move(wtime=10.0, btime=20.5, winc=1.0, binc=0.5)

        assert move == "g1f3"
        assert sent == ["go wtime 10000.0 btime 20500.0 winc 1000.0 binc 500.0"]

    def test_set_position_with_and_without_moves(self) -> None:
        sent = []
        bot = DummyLichessBot("sporkfish")
        bot._sporkfish = SimpleNamespace(send_command=lambda cmd: sent.append(cmd))

        bot._set_position("e2e4 e7e5")
        bot._set_position("   ")

        assert sent == ["position startpos moves e2e4 e7e5", "position startpos"]


class TestBerserkRetriable:
    def test_retry_decorator_calls_wrapped_function(self) -> None:
        retriable = object.__new__(BerserkRetriable)

        wrapped = retriable._retry_decorator(lambda x, y=0: x + y)

        assert wrapped(3, y=4) == 7

    def test_set_retries_wraps_public_callables(self) -> None:
        class FakeApi:
            def __init__(self) -> None:
                self.data = 3

            def ping(self) -> str:
                return "pong"

            def _private(self) -> str:
                return "hidden"

        retriable = object.__new__(BerserkRetriable)
        retriable._client = SimpleNamespace(api=FakeApi())

        retriable._set_retries()

        assert retriable._client.api.ping() == "pong"
        assert hasattr(retriable._client.api.ping, "__wrapped__")

    def test_init_constructs_client_and_sets_retries(self, monkeypatch) -> None:
        calls = {"set_retries": 0}

        class FakeTokenSession:
            def __init__(self, token: str) -> None:
                self.token = token

        class FakeClient:
            def __init__(self, session) -> None:
                self.session = session

        monkeypatch.setattr(
            berserk_retriable_module.berserk, "TokenSession", FakeTokenSession
        )
        monkeypatch.setattr(berserk_retriable_module.berserk, "Client", FakeClient)
        monkeypatch.setattr(
            BerserkRetriable,
            "_set_retries",
            lambda self: calls.__setitem__("set_retries", calls["set_retries"] + 1),
        )

        retriable = BerserkRetriable("abc")

        assert isinstance(retriable._client, FakeClient)
        assert retriable._client.session.token == "abc"
        assert calls["set_retries"] == 1


class TestLichessBotBerserk:
    def _new_bot(self) -> LichessBotBerserk:
        bot = object.__new__(LichessBotBerserk)
        bot._bot_id = "sporkfish"
        return bot

    def test_extract_second(self) -> None:
        bot = self._new_bot()
        dt = datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc)

        assert bot._extract_second(dt) == dt.timestamp()
        assert bot._extract_second(2500) == 2.5
        assert bot._extract_second("x") is None

    def test_get_times_correspondence(self) -> None:
        bot = self._new_bot()

        assert bot._get_times({"perf": {"name": "Correspondence"}}) == (
            None,
            None,
            None,
            None,
        )

    def test_get_times_from_nested_state(self) -> None:
        bot = self._new_bot()

        times = bot._get_times(
            {
                "state": {
                    "wtime": 30000,
                    "btime": 25000,
                    "winc": 500,
                    "binc": 0,
                }
            }
        )

        assert times == (30.0, 25.0, 0.5, 0.0)

    def test_play_move_when_turn(self) -> None:
        bot = self._new_bot()
        made_moves = []
        bot._set_position = lambda moves: made_moves.append(("set", moves))
        bot._get_times = lambda _state: (10.0, 10.0, 0.0, 0.0)
        bot._get_best_move = lambda *_args: "e2e4"
        bot._berserk = SimpleNamespace(
            _client=SimpleNamespace(
                bots=SimpleNamespace(
                    make_move=lambda gid, move: made_moves.append((gid, move))
                )
            )
        )

        bot._play_move(color=0, prev_moves="", game_id="g1", state={})

        assert made_moves == [("set", ""), ("g1", "e2e4")]

    def test_play_move_skips_when_not_turn(self) -> None:
        bot = self._new_bot()
        calls = []
        bot._set_position = lambda _moves: calls.append("set")
        bot._get_times = lambda _state: (10.0, 10.0, 0.0, 0.0)
        bot._get_best_move = lambda *_args: "e7e5"
        bot._berserk = SimpleNamespace(
            _client=SimpleNamespace(
                bots=SimpleNamespace(make_move=lambda _gid, _move: calls.append("move"))
            )
        )

        bot._play_move(color=0, prev_moves="e2e4", game_id="g1", state={})

        assert calls == []

    def test_handle_states_resignation(self) -> None:
        bot = self._new_bot()
        bot._play_move = lambda *_args, **_kwargs: None

        states = iter(
            [
                {"white": {"id": "sporkfish"}, "state": {"moves": ""}},
                {"type": "gameStateResign"},
            ]
        )

        term = bot._handle_states("g1", states)

        assert term == GameTerminationReason.RESIGNATION

    def test_handle_states_unknown(self) -> None:
        bot = self._new_bot()
        bot._play_move = lambda *_args, **_kwargs: None

        states = iter([{"white": {"id": "sporkfish"}, "state": {"moves": ""}}])

        term = bot._handle_states("g1", states)

        assert term == GameTerminationReason.UNKNOWN

    def test_should_accept_challenge(self) -> None:
        assert LichessBotBerserk._should_accept_challenge(
            {"challenge": {"variant": {"key": "standard"}, "speed": "blitz"}}
        )
        assert not LichessBotBerserk._should_accept_challenge(
            {"challenge": {"variant": {"key": "atomic"}, "speed": "blitz"}}
        )

    def test_event_action_accept_and_decline(self) -> None:
        accepted = []
        declined = []
        bot = self._new_bot()
        bot._berserk = SimpleNamespace(
            _client=SimpleNamespace(
                bots=SimpleNamespace(
                    accept_challenge=lambda cid: accepted.append(cid),
                    decline_challenge=lambda cid: declined.append(cid),
                )
            )
        )

        accepted_event = {
            "challenge": {
                "id": "c1",
                "variant": {"key": "standard"},
                "speed": "rapid",
            }
        }
        declined_event = {
            "challenge": {
                "id": "c2",
                "variant": {"key": "atomic"},
                "speed": "rapid",
            }
        }

        assert bot._event_action_accept_challenge(accepted_event)
        assert not bot._event_action_accept_challenge(declined_event)
        assert accepted == ["c1"]
        assert declined == ["c2"]

    def test_event_action_game_finish_handles_post_failure(self) -> None:
        bot = self._new_bot()

        def boom(*_args, **_kwargs):
            raise RuntimeError("fail")

        bot._berserk = SimpleNamespace(
            _client=SimpleNamespace(bots=SimpleNamespace(post_message=boom))
        )

        # Method should swallow and log exceptions.
        bot._event_action_game_finish({"game": {"fullId": "g1"}})

    def test_run_dispatches_known_events(self) -> None:
        bot = self._new_bot()
        calls = []
        bot._berserk = SimpleNamespace(
            _client=SimpleNamespace(
                bots=SimpleNamespace(
                    stream_incoming_events=lambda: iter(
                        [
                            {
                                "type": "challenge",
                                "challenge": {
                                    "id": "c1",
                                    "variant": {"key": "standard"},
                                    "speed": "blitz",
                                },
                            },
                            {"type": "gameStart", "game": {"fullId": "g1"}},
                            {"type": "gameFinish", "game": {"fullId": "g1"}},
                            {"type": "unknown"},
                        ]
                    )
                )
            )
        )
        bot._event_actions = {
            "challenge": lambda _self, _event: calls.append("challenge"),
            "gameStart": lambda _self, _event: calls.append("gameStart"),
            "gameFinish": lambda _self, _event: calls.append("gameFinish"),
        }

        bot.run()

        assert calls == ["challenge", "gameStart", "gameFinish"]
