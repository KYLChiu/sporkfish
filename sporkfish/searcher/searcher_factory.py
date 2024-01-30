from typing import Type

from sporkfish.evaluator import Evaluator

from .move_ordering import MoveOrder, MvvLvaHeuristic
from .negamax import NegaMaxLazySmp, NegamaxSp
from .searcher import Searcher
from .searcher_config import MoveOrdering, SearcherConfig, SearchMode


class SearcherFactory:
    """
    Factory class for creating instances of different searcher types.
    """

    # ideally would build evaluator as well
    @staticmethod
    def create(searcher_cfg: SearcherConfig, evaluator: Evaluator) -> Searcher:
        """
        Create an instance of the specified searcher type.
        """

        if searcher_cfg.order is MoveOrdering.MVV_LVA:
            order = MvvLvaHeuristic()
        else:
            raise Exception("Only MVV LVA move ordering is supported at the moment.")

        if searcher_cfg.mode is SearchMode.SINGLE_PROCESS:
            return NegamaxSp(evaluator, order, searcher_cfg)
        elif searcher_cfg.mode is SearchMode.LAZY_SMP:
            return NegaMaxLazySmp(evaluator, order, searcher_cfg)
        else:
            raise TypeError("Invalid enum type given for SearchMode.")
