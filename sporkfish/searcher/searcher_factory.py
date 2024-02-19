from sporkfish.evaluator import EvaluateMode, Evaluator

from .move_ordering import KillerMoveHeuristic, MoveOrder, MvvLvaHeuristic
from .negamax import NegamaxSp
from .negamax_lazy_smp import NegaMaxLazySmp
from .searcher import Searcher
from .searcher_config import MoveOrderMode, SearcherConfig, SearchMode


class SearcherFactory:
    """
    Factory class for creating instances of different searcher types.
    """

    @staticmethod
    def _build_moveorder(searcher_cfg: SearcherConfig) -> MoveOrder:
        """
        Build and return an instance of MoveOrder based on the specified order type.

        :param searcher_cfg: The searcher config.
        :type searcher_cfg: SearcherConfig
        :return: An instance of MoveOrder.
        :rtype: MoveOrder
        :raises TypeError: If the specified order type is not supported.
        """
        order_type = searcher_cfg.move_order_mode

        if order_type is MoveOrderMode.MVV_LVA:
            return MvvLvaHeuristic()
        elif order_type is MoveOrderMode.KILLER_MOVE:
            max_depth = searcher_cfg.max_depth
            return KillerMoveHeuristic(max_depth)
        else:
            raise TypeError(
                f"SearcherFactory does not support the creation of MoveOrdering type: \
                {type(order_type).__name__}."
            )

    @staticmethod
    def _build_evaluator(
        evaluator_type: EvaluateMode = EvaluateMode.PESTO,
    ) -> Evaluator:
        """
        Build and return an instance of Evaluator based on the specified evaluation mode.

        :param evaluator_type: The type of evaluation to use.
        :type evaluator_type: EvaluateMode
        :return: An instance of Evaluator.
        :rtype: Evaluator
        :raises TypeError: If the specified evaluator type is not supported.
        """
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
        Create an instance of the specified searcher type based on the provided configuration.

        :param searcher_cfg: The configuration for creating the searcher instance.
        :type searcher_cfg: SearcherConfig
        :return: An instance of the specified searcher type.
        :rtype: Searcher
        :raises TypeError: If the specified searcher type is not supported.
        """
        order = SearcherFactory._build_moveorder(searcher_cfg)

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
