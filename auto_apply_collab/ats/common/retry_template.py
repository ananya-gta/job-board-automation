import functools
import logging
from typing import Callable

from celery.utils.log import get_task_logger
from tenacity import Retrying, retry, stop_after_attempt, wait_fixed, retry_if_result, before_log, BaseRetrying

logger = get_task_logger(__name__)


class RetryStore:
    retry_simple = Retrying(
        stop=stop_after_attempt(1),
        wait=wait_fixed(1),
        # retry=retry_if_result(lambda x: x is False),
        reraise=True,
        before=before_log(logger, logging.DEBUG),
    )


    retry_if_bool = Retrying(
        stop=stop_after_attempt(1),
        wait=wait_fixed(1),
        retry=retry_if_result(lambda x: x is False),
        reraise=True,
        before=before_log(logger, logging.DEBUG),
    )


@functools.wraps(Retrying.copy)
def ats_retry(func: Retrying, *args, **kwargs) -> Callable:
    func_copy = Retrying.copy(func, *args, **kwargs)
    return func_copy.wraps
