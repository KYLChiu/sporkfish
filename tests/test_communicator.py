import sporkfish.communicator_uci as communicator_uci
import pytest
import io
import chess
from unittest.mock import patch, MagicMock
import threading
from contextlib import redirect_stdout


@pytest.fixture
def run_command():
    def _run_command(command):
        def wrapper(output_buffer):
            with redirect_stdout(output_buffer):
                board = chess.Board()
                engine = MagicMock()
                uci = communicator_uci.CommunicatorUCI()
                uci._communicate(command, board, engine)

        output_buffer = io.StringIO()
        thread = threading.Thread(target=wrapper, args=(output_buffer,))
        thread.daemon = True
        thread.start()
        thread.join()

        return output_buffer.getvalue()

    return _run_command


def test_uci(run_command):
    captured_output = run_command("uci")
    assert "id name Sporkfish\nid author Kelvin Chiu\nuciok\n" == captured_output


def test_go(run_command):
    captured_output = run_command("go")
    assert "bestmove" in captured_output
