from sporkfish.evaluator import EvaluateMode, Evaluator

from .move_ordering import MoveOrder, MvvLvaHeuristic
from .negamax import NegamaxSp
from .negamax_lazy_smp import NegaMaxLazySmp
from .searcher import Searcher
from .searcher_config import MoveOrderMode, SearcherConfig, SearchMode


class SearcherFactory:
    """
    Factory class for creating instances of different searcher types.
    """

    @staticmethod
    def _build_moveorder(order_type: MoveOrderMode) -> MoveOrder:
        if order_type is MoveOrderMode.MVV_LVA:
            return MvvLvaHeuristic()
        else:
            raise TypeError(
                f"SearcherFactory does not support the creation of MoveOrdering type: \
                            {type(order_type).__name__}."
            )

    @staticmethod
    def _build_evaluator(
        evaluator_type: EvaluateMode = EvaluateMode.PESTO,
    ) -> Evaluator:
        # this method needs changing when refactoring Evaluator design, see:
        # https://github.com/KYLChiu/sporkfish/issues/88
        if evaluator_type is EvaluateMode.PESTO:
            return Evaluator()
        else:
            raise TypeError(
                f"SearcherFactory does not support the creation of Evaluator type: \
                            {type(evaluator_type).__name__}."
            )

    @staticmethod
    def create(searcher_cfg: SearcherConfig) -> Searcher:
        """
        Create an instance of the specified searcher type.
        """
        order = SearcherFactory._build_moveorder(searcher_cfg.move_order_mode)

        if searcher_cfg.search_mode is SearchMode.SINGLE_PROCESS:
            evaluator = SearcherFactory._build_evaluator()
            return NegamaxSp(evaluator, order, searcher_cfg)
        elif searcher_cfg.search_mode is SearchMode.LAZY_SMP:
            evaluator = SearcherFactory._build_evaluator()
            return NegaMaxLazySmp(evaluator, order, searcher_cfg)
        else:
            raise TypeError(
                f"SearcherFactory does not support the creation of Searcher type: \
                            {type(searcher_cfg.search_mode).__name__}."
            )
