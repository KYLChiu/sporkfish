import os
import chess
from . import uci_communicator
from . import evaluator
from . import engine
from . import searcher
from . import opening_book


class UCIClient:
    """
    A class representing a client for the Universal Chess Interface (UCI).

    Attributes:
    - _uci_communicator (uci_communicator.UCICommunicator): The UCI communicator for handling communication with the chess engine.
    - _engine (engine.Engine): The chess engine used by the UCI client.
    - _board (chess.Board): The current chess board state.

    Methods:
    - send_command(command: str) -> str:
        Send a command to the UCI engine and return the response.

    Properties:
    - engine: Get the chess engine instance.
    - board: Get the current chess board state.

    Static Methods:
    - create_engine() -> engine.Engine:
        Create and return an instance of the chess engine for the UCI client.
        The engine is configured with an evaluator, searcher, and opening book.

    """

    def __init__(self, response_mode: uci_communicator.ResponseMode):
        """
        Initialize the UCIClient with the specified response mode.

        :param response_mode: The response mode for UCI commands.
        :type response_mode: uci_communicator.ResponseMode
        """
        self._uci_communicator = uci_communicator.UCICommunicator(response_mode)
        self._engine = UCIClient.create_engine()
        self._board = chess.Board()
        if response_mode is uci_communicator.ResponseMode.RETURN:
            response = self.send_command("uci")
            assert "uciok" in response, "UCIClient failed to initialize correctly."

    def send_command(self, command):
        """
        Send a command to the UCI engine and return the response.

        :param command: The UCI command to send.
        :type command: str
        :return: The response from the UCI engine.
        :rtype: str
        """
        return self._uci_communicator.communicate(command, self._board, self._engine)

    @property
    def engine(self):
        """
        Get the chess engine instance.

        :return: The chess engine instance.
        :rtype: engine.Engine
        """
        return self._engine

    @property
    def board(self):
        """
        Get the current chess board state.

        :return: The current chess board state.
        :rtype: chess.Board
        """
        return self._board

    @staticmethod
    def create_engine():
        """
        Create and return an instance of the chess engine for the UCI client.
        The engine is configured with an evaluator, searcher, and opening book.

        :return: An instance of the chess engine.
        :rtype: engine.Engine
        """
        depth = 3
        eval = evaluator.Evaluator()
        search = searcher.Searcher(eval, depth)
        ob = opening_book.OpeningBook()
        eng = engine.Engine(search, ob)
        return eng
