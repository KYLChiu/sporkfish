from enum import Enum
from typing import Optional

from sporkfish.configurable import Configurable


class EndgameTablebaseMode(Enum):
    LOCAL = "LOCAL"
    LILA = "LILA"


class EndgameTablebaseConfig(Configurable):
    """
    Configuration class for an endgame tablebase.

    :ivar endgame_tablebase_path: Relative path (to root directory) to endgame tablebase folder.
    :ivar endgame_tablebase_mode: The mode of the endgame tablebase, defaults to EndgameTablebaseMode.LOCAL.

    :param endgame_tablebase_path: Relative path (to root directory) to endgame tablebase folder, defaults to None.
    :type endgame_tablebase_path: Optional[str], optional
    :param endgame_tablebase_mode: The mode of the endgame tablebase, defaults to EndgameTablebaseMode.LOCAL.
    :type endgame_tablebase_mode: EndgameTablebaseMode, optional
    """

    def __init__(
        self,
        endgame_tablebase_path: Optional[str] = None,
        endgame_tablebase_mode: EndgameTablebaseMode = EndgameTablebaseMode.LOCAL,
    ):
        """
        Initialize an EndgameTablebaseConfig instance.

        :param endgame_tablebase_path: Relative path (to root directory) to endgame tablebase folder, defaults to None.
        :type endgame_tablebase_path: Optional[str], optional
        :param endgame_tablebase_mode: The mode of the endgame tablebase, defaults to EndgameTablebaseMode.LOCAL.
        :type endgame_tablebase_mode: EndgameTablebaseMode, optional
        """
        self.endgame_tablebase_path = endgame_tablebase_path
        self.endgame_tablebase_mode = (
            endgame_tablebase_mode
            if isinstance(endgame_tablebase_mode, EndgameTablebaseMode)
            else EndgameTablebaseMode(endgame_tablebase_mode)
        )
