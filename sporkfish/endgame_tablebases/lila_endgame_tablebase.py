import logging
from typing import Optional

import chess
import chess.syzygy
import requests

from sporkfish.endgame_tablebases.endgame_tablebase import EndgameTablebase


class LilaTablebase(EndgameTablebase):
    """Class for handling the lila endgame tablebase in chess engines."""

    BASE_URL = "http://tablebase.lichess.ovh/standard?fen="

    def __init__(self) -> None:
        EndgameTablebase.__init__(self)

    def query(self, board_fen: str) -> Optional[chess.Move]:
        """
        Queries the tablebase service for the best move given a board position in FEN format.

        :param board_fen: The FEN representation of the chess board.
        :type board_fen: str

        :return: The best move as a `chess.Move` object, or `None` if no move is found.
        :rtype: Optional[chess.Move]

        :raises ConnectionError: If there is an issue connecting to the tablebase service.
        """
        FULL_URL = LilaTablebase.base_url + board_fen
        try:
            response = requests.get(FULL_URL).json()
            best_move = (
                chess.Move.from_uci(response["moves"][0]["uci"])
                if len(response["moves"]) > 0
                else None
            )
            logging.info("Lila query succeeded. Best move retrieved: {best_move}")
            return best_move
        except ConnectionError as _:
            logging.warning("Lila query failed, skipping")
            return None
