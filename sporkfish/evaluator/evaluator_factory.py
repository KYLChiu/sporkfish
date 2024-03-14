from .evaluator import Evaluator
from .evaluator_config import EvaluatorConfig, EvaluatorMode
from .pesto import Pesto


class EvaluatorFactory:
    """
    Factory class for creating instances of different evaluator types.
    """

    @staticmethod
    def create(evaluator_cfg: EvaluatorConfig) -> Evaluator:
        """
        Build and return an instance of Evaluator based on the specified evaluation mode.

        :param evaluator_cfg: The type of evaluation to use.
        :type evaluator_cfg: EvaluatorConfig
        :return: An instance of Evaluator.
        :rtype: Evaluator
        :raises TypeError: If the specified evaluator type is not supported.
        """

        if evaluator_cfg.evaluator_mode is EvaluatorMode.PESTO:
            return Pesto()
        else:
            raise TypeError(
                f"EvaluatorFactory does not support the creation of Evaluator type: \
                {type(evaluator_cfg.evaluator_mode).__name__}."
            )
