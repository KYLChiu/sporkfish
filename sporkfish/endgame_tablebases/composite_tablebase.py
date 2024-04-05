import chess

from sporkfish.board.board import Board

from .endgame_tablebase import EndgameTablebase
from .endgame_tablebase_config import EndgameTablebaseConfig, EndgameTablebaseMode
from .lila_tablebase import LilaTablebase
from .local_tablebase import LocalTablebase


class CompositeTablebase(LocalTablebase, LilaTablebase, EndgameTablebase):
    """
    A class that combines multiple tablebases into a composite tablebase.

    Inherits from LocalTablebase, LilaTablebase, and EndgameTablebase.

    :ivar _config: The configuration for the endgame tablebase.

    :param config: The configuration for the endgame tablebase, defaults to EndgameTablebaseConfig()
    :type config: EndgameTablebaseConfig, optional
    """

    def __init__(
        self, config: EndgameTablebaseConfig = EndgameTablebaseConfig()
    ) -> None:
        """
        Initializes the CompositeTablebase with the given configuration.

        :param config: The configuration for the endgame tablebase, defaults to EndgameTablebaseConfig()
        :type config: EndgameTablebaseConfig, optional
        """
        EndgameTablebase.__init__(self)
        LocalTablebase.__init__(self, config)
        LilaTablebase.__init__(self)

        self._config = config

    def query(self, board: Board) -> chess.Move | None:
        """
        Queries the tablebase based on the given board state.

        The method of querying depends on the endgame tablebase mode specified in the configuration.
        If the mode is LOCAL, it first tries to query the LocalTablebase. If no result is found, it queries the LilaTablebase.
        If the mode is LILA, it first tries to query the LilaTablebase. If no result is found, it queries the LocalTablebase.

        :param board: The current state of the chess board.
        :type board: Board
        :return: The best move according to the tablebase, or None if no move is found.
        :rtype: chess.Move | None
        """

        match self._config.endgame_tablebase_mode:
            case EndgameTablebaseMode.LOCAL:
                if local := LocalTablebase.query(self, board):
                    return local
                else:
                    return LilaTablebase.query(self, board)
            case EndgameTablebaseMode.LILA:
                if lila := LilaTablebase.query(self, board):
                    return lila
                else:
                    return LocalTablebase.query(board)
