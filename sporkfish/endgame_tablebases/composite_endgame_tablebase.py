import chess

from sporkfish.board.board import Board

from .endgame_tablebase import EndgameTablebase
from .endgame_tablebase_config import EndgameTablebaseConfig
from .lila_endgame_tablebase import LilaTablebase
from .local_endgame_tablebase import LocalTablebase


class CompositeTablebase(LocalTablebase, LilaTablebase, EndgameTablebase):
    def __init__(
        self, config: EndgameTablebaseConfig = EndgameTablebaseConfig()
    ) -> None:
        EndgameTablebase.__init__(self)
        LocalTablebase.__init__(self, config)
        LilaTablebase.__init__(self)

        self._config = config

    def query(self, board: Board) -> chess.Move | None:
        return (
            LilaTablebase.query(board.fen())
            if self._config.query_db is None
            else LocalTablebase.query(board)
        )
