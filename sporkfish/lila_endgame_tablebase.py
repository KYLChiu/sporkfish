import logging
from typing import Optional

import chess
import chess.syzygy
import requests


class LilaTablebase:
    """Class for handling the lila endgame tablebase in chess engines."""

    base_url = "http://tablebase.lichess.ovh/standard?fen="

    def query_bestmove(board_fen: str) -> Optional[chess.Move]:
        """
        Queries the tablebase service for the best move given a board position in FEN format.

        :param board_fen: The FEN representation of the chess board.
        :type board_fen: str

        :return: The best move as a `chess.Move` object, or `None` if no move is found.
        :rtype: Optional[chess.Move]

        :raises ConnectionError: If there is an issue connecting to the tablebase service.
        """
        full_url = LilaTablebase.base_url + board_fen
        try:
            response = requests.get(full_url).json()
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
