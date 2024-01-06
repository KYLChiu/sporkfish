from enum import Enum, auto
import chess
import chess.polyglot
import sys
from . import engine


class ResponseMode(Enum):
    PRINT = auto()
    RETURN = auto()


class UCICommunicator:
    """
    Implements the UCICommunicator protocol for Sporkfish.
    """

    def __init__(self, response_mode=ResponseMode.PRINT):
        self._response_mode = response_mode

    def communicate(self, msg: str, board: chess.Board, engine: engine.Engine) -> str:
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
            move = engine.make_move(board)
            response = f"bestmove {move}" or "(none)"

        if self._response_mode == ResponseMode.PRINT:
            print(response)
        elif self._response_mode == ResponseMode.RETURN:
            return response

        # Return an empty string for unrecognized commands or cases where no response is needed
        return ""
