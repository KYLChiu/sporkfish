from enum import Enum

from ..configurable import Configurable


class EvaluatorMode(Enum):
    SIMPLE = "SIMPLE"
    PESTO = "PESTO"


class EvaluatorConfig(Configurable):
    """
    Configuratoin class for the evaluator.

    :param evaluator_mode: Evaluator mode (default: EvaluatorMode.PESTO).
                            Determines the evaluator mode used by the evaluator.
    """

    def __init__(self, evaluator_mode: EvaluatorMode = EvaluatorMode.PESTO) -> None:
        self.evaluator_mode = (
            evaluator_mode
            if isinstance(evaluator_mode, EvaluatorMode)
            else EvaluatorMode(evaluator_mode)
        )
