from unittest.mock import mock_open

import pytest

import sporkfish.runner as runner_module
from sporkfish.runner import RunConfig, RunMode, Runner


class TestRunConfig:
    def test_run_config_accepts_enum(self) -> None:
        config = RunConfig(mode=RunMode.UCI)
        assert config.mode == RunMode.UCI

    def test_run_config_accepts_string(self) -> None:
        config = RunConfig(mode="LICHESS")
        assert config.mode == RunMode.LICHESS

    def test_run_config_rejects_invalid_string(self) -> None:
        with pytest.raises(ValueError):
            RunConfig(mode="NOT_A_MODE")


class TestRunnerRun:
    def test_run_dispatches_to_selected_action(self, monkeypatch) -> None:
        called = {"uci": False, "lichess": False}

        def fake_uci() -> None:
            called["uci"] = True

        def fake_lichess() -> None:
            called["lichess"] = True

        monkeypatch.setattr(
            Runner,
            "_mode_actions",
            {RunMode.UCI: fake_uci, RunMode.LICHESS: fake_lichess},
        )

        runner = Runner(RunConfig(mode=RunMode.UCI))
        runner.run()

        assert called["uci"] is True
        assert called["lichess"] is False

    def test_run_rejects_unsupported_mode(self) -> None:
        config = RunConfig(mode=RunMode.UCI)
        config.mode = object()  # bypass enum typing to exercise unsupported-mode guard

        with pytest.raises(AssertionError, match="not supported"):
            Runner(config).run()

    def test_run_rejects_non_callable_action(self, monkeypatch) -> None:
        class NonCallableAction:
            __name__ = "non_callable_action"

        monkeypatch.setattr(
            Runner,
            "_mode_actions",
            {RunMode.UCI: NonCallableAction()},
        )

        with pytest.raises(AssertionError, match="not callable"):
            Runner(RunConfig(mode=RunMode.UCI)).run()

    def test_run_rejects_action_with_parameters(self, monkeypatch) -> None:
        def invalid_action(_x):
            return None

        monkeypatch.setattr(Runner, "_mode_actions", {RunMode.UCI: invalid_action})

        with pytest.raises(AssertionError, match="does not accept zero arguments"):
            Runner(RunConfig(mode=RunMode.UCI)).run()


class TestRunnerStaticActions:
    def test_run_uci_sends_input_to_client_once_then_stops(self, monkeypatch) -> None:
        sent_commands = []

        class FakeUCIClient:
            class UCIProtocol:
                class ResponseMode:
                    PRINT = "PRINT"

            def __init__(self, _mode) -> None:
                pass

            def send_command(self, message: str) -> None:
                sent_commands.append(message)

        inputs = iter(["uci", "isready"])

        def fake_input() -> str:
            try:
                return next(inputs)
            except StopIteration as exc:
                raise EOFError() from exc

        monkeypatch.setattr(runner_module, "UCIClient", FakeUCIClient)
        monkeypatch.setattr("builtins.input", fake_input)

        with pytest.raises(EOFError):
            Runner._run_uci()

        assert sent_commands == ["uci", "isready"]

    def test_run_lichess_reads_token_and_runs_bot(self, monkeypatch) -> None:
        observed = {"token": None, "run_called": False}

        class FakeLichessBotBerserk:
            def __init__(self, token: str) -> None:
                observed["token"] = token

            def run(self) -> None:
                observed["run_called"] = True

        monkeypatch.setattr(
            runner_module,
            "LichessBotBerserk",
            FakeLichessBotBerserk,
        )
        monkeypatch.setattr("builtins.open", mock_open(read_data="token-123"))

        Runner._run_lichess()

        assert observed["token"] == "token-123"
        assert observed["run_called"] is True
