from typing import Optional

from sporkfish.configurable import Configurable


class EndgameTablebaseConfig(Configurable):
    """Configuration class for an endgame tablebase."""

    def __init__(
        self,
        endgame_tablebase_path: Optional[str] = None,
        query_db: Optional[str] = None,
    ):
        """
        Initialize an EndgameTablebaseConfig instance.

        :param endgame_tablebase_path: Relative path (to root directory) to endgame tablebase folder. Defaults to None.
        :type endgame_tablebase_path: Optional[str]
        """
        self.endgame_tablebase_path = endgame_tablebase_path
        self.query_db = query_db
