import logging
from typing import Optional

import chess
import requests

from sporkfish.board.board import Board
from sporkfish.endgame_tablebases.endgame_tablebase import EndgameTablebase


class LilaTablebase(EndgameTablebase):
    """
    Class for handling the lila endgame tablebase in chess engines.

    :ivar BASE_URL: The base URL for the lila endgame tablebase service.

    :method __init__() -> None: Initializes the LilaTablebase instance.
    :method query(board_fen: str) -> Optional[chess.Move]: Queries the tablebase service for the best move given a board position in FEN format.
    """

    BASE_URL = "http://tablebase.lichess.ovh/standard?fen="

    def __init__(self) -> None:
        EndgameTablebase.__init__(self)

    def query(self, board: Board) -> Optional[chess.Move]:
        """
        Queries the tablebase service for the best move given a board position.

        :param board: The current state of the chess board.
        :type board: Board
        :return: The best move as a `chess.Move` object, or `None` if no move is found.
        :rtype: Optional[chess.Move]
        :raises ConnectionError: If there is an issue connecting to the tablebase service.
        """

        full_url = LilaTablebase.BASE_URL + board.fen()
        try:
            response = requests.get(full_url).json()
            best_move = (
                chess.Move.from_uci(response["moves"][0]["uci"])
                if len(response["moves"]) > 0 and response["dtz"]
                else None
            )

            if best_move:
                logging.debug("Lila query succeeded. Best move retrieved: {best_move}")
            else:
                logging.debug("Lila query succeeded. No best move found.")

            return best_move

        except requests.exceptions.RequestException:
            logging.error("Failed to connect to Lila tablebase service, error: {e}")
            return None
