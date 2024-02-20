from sporkfish.evaluator import EvaluateMode, Evaluator

from .negamax import NegamaxSp
from .negamax_lazy_smp import NegaMaxLazySmp
from .searcher import Searcher
from .searcher_config import SearcherConfig, SearchMode


class SearcherFactory:
    """
    Factory class for creating instances of different searcher types.
    """

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
        if searcher_cfg.search_mode is SearchMode.SINGLE_PROCESS:
            evaluator = SearcherFactory._build_evaluator()
            return NegamaxSp(evaluator, searcher_cfg)
        elif searcher_cfg.search_mode is SearchMode.LAZY_SMP:
            evaluator = SearcherFactory._build_evaluator()
            return NegaMaxLazySmp(evaluator, searcher_cfg)
        else:
            raise TypeError(
                f"SearcherFactory does not support the creation of Searcher type: \
                {type(searcher_cfg.search_mode).__name__}."
            )
