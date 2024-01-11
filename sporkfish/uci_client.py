import chess
import sys
from enum import Enum, auto
import logging

from . import evaluator
from . import engine
from . import searcher
from . import opening_book


class UCIClient:

    """
    A class representing a client for the Universal Chess Interface (UCI). It wraps the communicator, engine and board in one.

    Attributes:
    - _uci_protocol (uci_communicator.UCIProtocol): The UCI communicator for handling communication with the chess engine.
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

    class UCIProtocol:
        """
        Implements the Universal Chess Interface (UCI) protocol for Sporkfish.

        Attributes:
        - _response_mode (ResponseMode): The mode for handling the response.

        Methods:
        - communicate(msg: str, board: chess.Board, engine: engine.Engine) -> str:
            Process a UCI command and respond accordingly.

        Parameters:
        - msg (str): The UCI command received.
        - board (chess.Board): The chess board.
        - engine (engine.Engine): The chess engine.

        Returns:
        - str: The UCI response if response_mode is ResponseMode.RETURN.

        Supported UCI Commands:
        - "uci": Returns information about the engine.
        - "quit": Exits the engine.
        - "isready": Signals readiness of the engine.
        - "position startpos ...": Sets up the board with the starting position.
        - "position moves ...": Updates the board with the specified moves.
        - "go ...": Initiates the engine to search for the best move.

        Examples:
        >>> uci_protocol = UCIProtocol()
        >>> uci_protocol.communicate("uci", chess.Board(), engine.Engine())
        'id name Sporkfish\nid author Sporkfish dev team\nuciok'
        """

        class ResponseMode(Enum):
            PRINT = auto()
            RETURN = auto()

        def __init__(self, response_mode=ResponseMode.PRINT):
            self._response_mode = response_mode

        def communicate(
            self, msg: str, board: chess.Board, engine: engine.Engine
        ) -> str:
            """
            Process a UCI command and respond accordingly.
            This currently only implements a subset of the full UCI commands. Commands implemented:
            "uci", "quit", "isready", "position startpos ...", "position moves ...", "go ..."

            :param msg: The UCI command received.
            :type msg: str
            :param board: The chess board.
            :type board: chess.Board
            :param engine: The engine.
            :type engine: engine.Engine
            :param response_mode: The mode for handling the response (ResponseMode.PRINT or ResponseMode.RETURN).
            :type response_mode: ResponseMode
            :return: The UCI response if response_mode is ResponseMode.RETURN.
            :rtype: str
            """
            tokens = msg.strip().split(" ")
            while "" in tokens:
                tokens.remove("")

            response = ""

            if msg == "uci":
                response = "id name Sporkfish\nid author Sporkfish dev team\nuciok"

            elif msg == "quit":
                sys.exit()

            elif msg == "isready":
                response = "readyok"

            elif msg.startswith("position"):
                if len(tokens) < 2:
                    return ""

                if tokens[1] == "startpos":
                    board.reset()
                    moves_start = 2

                if len(tokens) > moves_start and tokens[moves_start] == "moves":
                    for move in tokens[(moves_start + 1) :]:
                        board.push_uci(move)

            elif msg.startswith("go"):
                # -------------------------- Basic strategy for time management --------------------------
                # Allocate tw * time + iw * increment for searching the move
                # Pick tw (time_weight) = 0.1, iw (increment_weight) = 0.01
                # Quick analysis without increment:
                # We get to make (1.0 - 0.1)^n * S number of (half) moves, where S = start_time in seconds
                # To reach 1 second:
                # (0.9)^n * S < 1
                # n > ln (1/S) / ln 0.9
                # Assuming a blitz game of 5 mins (S = 300), we can make 54 half moves before reaching 1 second
                # Assuming a bullet game of 1 min (S = 60), we can make 38 half moves before reaching 1 second
                # In future this should be a) configurable and b) improved.
                tokens = msg.split()
                idx = 0
                timeout = None

                while idx < len(tokens):
                    # Assumes inc comes straight after time
                    if tokens[idx] == "wtime" or tokens[idx] == "btime":
                        assert (
                            len(tokens) >= idx + 3
                        ), "wtime or btime given in go string but no time or increment values passed."
                        time = tokens[idx + 1]
                        inc = tokens[idx + 3]
                        # Convert to ms -> s
                        timeout = 0.05 * (float(time) / 1000) + 0.01 * (
                            float(inc) / 1000
                        )
                        break
                    idx += 1

                move = engine.best_move(board, timeout)
                board.push(move)
                response = f"bestmove {move}" or "(none)"

            if response:
                logging.info(f"UCI Response: {response}")

            if self._response_mode == UCIClient.UCIProtocol.ResponseMode.PRINT:
                print(response)
            elif self._response_mode == UCIClient.UCIProtocol.ResponseMode.RETURN:
                return response

            # Return an empty string for unrecognized commands or cases where no response is needed
            return ""

    def __init__(self, response_mode: UCIProtocol.ResponseMode):
        """
        Initialize the UCIClient with the specified response mode.

        :param response_mode: The response mode for UCI commands.
        :type response_mode: uci_protocol.ResponseMode
        """
        self._uci_protocol = UCIClient.UCIProtocol(response_mode)
        self._engine = UCIClient.create_engine()
        self._board = chess.Board()
        if response_mode is UCIClient.UCIProtocol.ResponseMode.RETURN:
            response = self.send_command("uci")
            assert "uciok" in response, "UCIClient failed to initialize correctly."

    def send_command(self, command: str):
        """
        Send a command to the UCI engine and return the response.

        :param command: The UCI command to send.
        :type command: str
        :return: The response from the UCI engine.
        :rtype: str
        """
        logging.info(f"Sending UCI comamnd: {command}")
        return self._uci_protocol.communicate(command, self._board, self._engine)

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
    def create_engine(depth: int = 6):
        """
        Create and return an instance of the chess engine for the UCI client.
        The engine is configured with an evaluator, searcher, and opening book.

        :return: An instance of the chess engine.
        :rtype: engine.Engine
        """
        eval = evaluator.Evaluator()
        search = searcher.Searcher(eval, depth)
        ob = opening_book.OpeningBook()
        eng = engine.Engine(search, ob)
        return eng
