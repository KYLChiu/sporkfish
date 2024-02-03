import logging
import sys
from enum import Enum, auto

from config import load_config

from .board.board import Board
from .board.board_factory import BoardFactory, BoardPyChess
from .endgame_tablebase import EndgameTablebase, EndgameTablebaseConfig
from .engine import Engine
from .evaluator import Evaluator
from .opening_book import OpeningBook, OpeningBookConfig
from .searcher.searcher_config import SearcherConfig
from .searcher.searcher_factory import SearcherFactory
from .time_manager import TimeManager, TimeManagerConfig


class UCIClient:
    """
    A class representing a client for the Universal Chess Interface (UCI). It wraps the communicator, engine and board in one.

    Attributes:
    - _uci_protocol (uci_protocol.UCIProtocol): The UCI protocol for handling communication with the chess engine.
    - _engine (engine.Engine): The chess engine used by the UCI client.
    - _board (Board): The current chess board state.

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
        - communicate(msg: str, board: Board, engine: engine.Engine) -> str:
            Process a UCI command and respond accordingly.

        Parameters:
        - msg (str): The UCI command received.
        - board (Board): The chess board.
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
        >>> uci_protocol.communicate("uci", Board(), engine.Engine())
        'id name Sporkfish\nid author Sporkfish dev team\nuciok'
        """

        class ResponseMode(Enum):
            PRINT = auto()
            RETURN = auto()

        def __init__(self, response_mode: ResponseMode = ResponseMode.PRINT) -> None:
            self._response_mode = response_mode

        def communicate(
            self,
            msg: str,
            board: Board,
            engine: Engine,
            time_manager: TimeManager,
        ) -> str:
            """
            Process a UCI command and respond accordingly.
            This currently only implements a subset of the full UCI commands. Commands implemented:
            "uci", "quit", "isready", "position startpos ...", "position moves ...", "go ..."

            :param msg: The UCI command received.
            :type msg: str
            :param board: The chess board.
            :type board: Board
            :param engine: The engine.
            :type engine: Engine
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
                tokens = msg.split()
                idx = 1
                timeout = None

                # Get the time and increment
                while idx < len(tokens):
                    # Assumes increment comes straight after time
                    if tokens[idx] == "wtime" or tokens[idx] == "btime":
                        assert (
                            len(tokens) >= idx + 3
                        ), "wtime or btime given in go string but no time or increment values passed."
                        # Convert to ms -> s
                        time = float(tokens[idx + 1]) / 1000.0
                        increment = float(tokens[idx + 3]) / 1000.0
                        timeout = time_manager.get_timeout(time, increment)
                        break
                    idx += 1

                move = engine.best_move(board, timeout)  # type: ignore
                board.push(move)  # type: ignore
                response = f"bestmove {move}" or "(none)"

            if response:
                logging.info(f"UCI Response: {response}")

            if self._response_mode == UCIClient.UCIProtocol.ResponseMode.PRINT:
                print(response)
            elif self._response_mode == UCIClient.UCIProtocol.ResponseMode.RETURN:
                return response

            # Return an empty string for unrecognized commands or cases where no response is needed
            return ""

    def __init__(self, response_mode: UCIProtocol.ResponseMode) -> None:
        """
        Initialize the UCIClient with the specified response mode.

        :param response_mode: The response mode for UCI commands.
        :type response_mode: uci_protocol.ResponseMode
        """
        self._uci_protocol = UCIClient.UCIProtocol(response_mode)
        self._engine = UCIClient.create_engine()
        self._time_manager = TimeManager(
            TimeManagerConfig.from_dict(
                load_config().get("TimeManagerConfig")  # type: ignore
            )
        )
        self._board = BoardFactory.create(BoardPyChess)
        if response_mode is UCIClient.UCIProtocol.ResponseMode.RETURN:
            response = self.send_command("uci")
            assert "uciok" in response, "UCIClient failed to initialize correctly."

    def send_command(self, command: str) -> str:
        """
        Send a command to the UCI engine and return the response.

        :param command: The UCI command to send.
        :type command: str
        :return: The response from the UCI engine.
        :rtype: str
        """
        logging.info(f"Sending UCI comamnd: {command}")
        return self._uci_protocol.communicate(
            command, self._board, self._engine, self._time_manager
        )

    @property
    def engine(self) -> Engine:
        """
        Get the chess engine instance.

        :return: The chess engine instance.
        :rtype: engine.Engine
        """
        return self._engine

    @property
    def board(self) -> Board:
        """
        Get the current chess board state.

        :return: The current chess board state.
        :rtype: Board
        """
        return self._board

    @staticmethod
    def create_engine() -> Engine:
        """
        Create and return an instance of the chess engine for the UCI client.
        The engine is configured from config yaml file.

        :return: An instance of the chess engine.
        :rtype: engine.Engine
        """

        config = load_config()
        search = SearcherFactory.create(
            SearcherConfig.from_dict(config.get("SearcherConfig"))  # type: ignore
        )
        ob = OpeningBook(
            OpeningBookConfig.from_dict(config.get("OpeningBookConfig"))  # type: ignore
        )
        et = EndgameTablebase(
            EndgameTablebaseConfig.from_dict(config.get("EndgameTablebaseConfig"))  # type: ignore
        )
        eng = Engine(search, ob, et)
        return eng
