from sporkfish.evaluator.evaluator import Evaluator
from sporkfish.searcher.negamax import NegamaxSp
from sporkfish.searcher.negamax_lazy_smp import NegaMaxLazySmp
from sporkfish.searcher.searcher import Searcher
from sporkfish.searcher.searcher_config import SearcherConfig, SearchMode


class SearcherFactory:
    """
    Factory class for creating instances of different searcher types.
    """

    @staticmethod
    def create(searcher_cfg: SearcherConfig, evaluator: Evaluator) -> Searcher:
        """
        Create an instance of the specified searcher type based on the provided configuration.

        :param searcher_cfg: The configuration for creating the searcher instance.
        :type searcher_cfg: SearcherConfig
        :return: An instance of the specified searcher type.
        :rtype: Searcher
        :raises TypeError: If the specified searcher type is not supported.
        """
        if searcher_cfg.search_mode is SearchMode.SINGLE_PROCESS:
            return NegamaxSp(evaluator, searcher_cfg)
        elif searcher_cfg.search_mode is SearchMode.LAZY_SMP:
            return NegaMaxLazySmp(evaluator, searcher_cfg)
        else:
            raise TypeError(
                f"SearcherFactory does not support the creation of Searcher type: \
                {type(searcher_cfg.search_mode).__name__}."
            )
