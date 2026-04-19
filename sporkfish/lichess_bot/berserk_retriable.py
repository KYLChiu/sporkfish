import functools
import inspect
import logging
from typing import Any, Callable, Mapping, Sequence

import berserk
import berserk.exceptions
import requests.exceptions
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


# TODO: I can't get this to work with metaclasses. Maybe in a future PR.
# The goal is to automatically wrap all functions in berserk.Client so they are retriable.
class BerserkRetriable:
    """
    Interface to interact with Lichess API with retry logic.
    Wraps the berserk.Client API.
    """

    # Retry configuration parameters
    _NUM_RETRIES = 5
    _WAIT_MIN_SECONDS = 1
    _WAIT_MAX_SECONDS = 30

    # Exception types that warrant a retry
    _RETRIABLE_EXCEPTIONS = (
        berserk.exceptions.ResponseError,
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.ReadTimeout,
    )

    def __init__(self, token: str):
        """
        Initialize the Berserk instance with the Lichess API token.

        :param token: The Lichess API token.
        :type token: str
        """
        self._client = berserk.Client(berserk.TokenSession(token))
        self._set_retries()

    # This is a bit dodgy, but it's the only way to patch the berserk.Client API for now.
    # The issue is that berserk only contains all its API once initialized, so we can't patch it before.
    def _set_retries(self) -> None:
        """
        Patches all public callable functions from modules in the berserk.Client with retry logic.
        """
        for module in (
            getattr(self._client, name)
            for name in dir(self._client)
            if not name.startswith("_")
        ):
            for attr_name, attr in inspect.getmembers(module):
                if not attr_name.startswith("_") and callable(attr):
                    setattr(module, attr_name, self._retry_decorator(attr))

    def _retry_decorator(
        self,
        func: Callable,
    ) -> Callable:
        """
        Wraps a method on the Lichess API with retry logic.

        :param func: The berserk API.
        :type func: Callable
        :return: The API wrapped in retry logic.
        :rtype: Callable
        """

        @functools.wraps(func)
        @retry(
            stop=stop_after_attempt(BerserkRetriable._NUM_RETRIES),
            wait=wait_exponential(
                min=BerserkRetriable._WAIT_MIN_SECONDS,
                max=BerserkRetriable._WAIT_MAX_SECONDS,
            ),
            retry=retry_if_exception_type(BerserkRetriable._RETRIABLE_EXCEPTIONS),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )
        def wrapper(
            *args: Sequence[Any],
            **kwargs: Mapping[str, Any],
        ) -> Any:
            return func(*args, **kwargs)

        return wrapper
