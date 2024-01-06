import os
import chess
from . import uci_communicator
from . import evaluator
from . import engine
from . import searcher
from . import opening_book


def create_engine():
    depth = 4
    eval = evaluator.Evaluator()
    search = searcher.Searcher(eval, depth)
    ob = opening_book.OpeningBook()
    eng = engine.Engine(search, ob)
    return eng


class UCIClient:
    def __init__(self, response_mode: uci_communicator.ResponseMode):
        self._uci_communicator = uci_communicator.UCICommunicator(response_mode)
        self._engine = create_engine()
        self._board = chess.Board()
        if response_mode is uci_communicator.ResponseMode.RETURN:
            response = self.send_command("uci")
            assert "uciok" in response, "UCIClient failed to initialize correctly."

    def send_command(self, command):
        return self._uci_communicator.communicate(command, self._board, self._engine)
