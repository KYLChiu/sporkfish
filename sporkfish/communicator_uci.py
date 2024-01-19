import chess
import chess.polyglot
import sys
from . import engine


class CommunicatorUCI:
    """
    Class for communicating with a UCI (Universal Chess Interface) chess engine.
    """

    def __init__(self):
        """
        Initialize the CommunicatorUCI instance.

        :return: None
        """
        pass

    def communicate_loop(self, board: chess.Board, engine: engine.Engine) -> None:
        """
        Enter a communication loop to handle UCI commands.

        :param board: The chess board.
        :type board: chess.Board
        :param engine: The chess engine.
        :type engine: engine.Engine
        :return: None
        """
        while True:
            msg = input()
            self._communicate(msg, board, engine)

    def _communicate(self, msg: str, board: chess.Board, engine: engine.Engine) -> None:
        """
        Process a UCI command and respond accordingly.
        This currently only implements a subset of the full UCI commands. Comamnds implemented:
        "uci", "quit", "isready", "position startpos ...", "position moves ...", "go ..."

        :param msg: The UCI command received.
        :type msg: str
        :param board: The chess board.
        :type board: chess.Board
        :param engine: The chess engine.
        :type engine: engine.Engine
        :return: None
        """
        tokens = msg.strip().split(" ")
        while "" in tokens:
            tokens.remove("")

        if msg == "uci":
            print("id name Sporkfish")
            print("id author Kelvin Chiu")
            print("uciok")

        elif msg == "quit":
            sys.exit()

        elif msg == "isready":
            print("readyok")

        elif msg.startswith("position"):
            if len(tokens) < 2:
                return

            if tokens[1] == "startpos":
                board.reset()
                moves_start = 2

            if len(tokens) > moves_start and tokens[moves_start] == "moves":
                for move in tokens[(moves_start + 1) :]:
                    board.push_uci(move)

        elif msg.startswith("go"):
            move = engine.make_move(board)
            print(f"bestmove {move}" or "(none)")
