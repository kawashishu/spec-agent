import functools
import inspect
import time

from spec.config import logger


def timeit(func):
    """
    Decorator to measure execution time for:
    - Asynchronous functions (coroutines)
    - Asynchronous generator functions
    - Synchronous functions

    Args:
        func (callable): The function to decorate.

    Returns:
        The decorated function with execution time logging.

    Usage:
        @timeit
        async def async_function():
            ...
    """
    if inspect.iscoroutinefunction(func):

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            try:
                return await func(*args, **kwargs)
            finally:
                end_time = time.perf_counter()
                elapsed = end_time - start_time
                logger.info(
                    f"Async [`{func.__name__.upper()}`] TOOK: {elapsed:.4f} seconds."
                )

        return async_wrapper

    elif inspect.isasyncgenfunction(func):

        @functools.wraps(func)
        async def async_gen_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            try:
                async for item in func(*args, **kwargs):
                    yield item
            finally:
                end_time = time.perf_counter()
                elapsed = end_time - start_time
                logger.info(
                    f"Async Generator [`{func.__name__.upper()}`] TOOK: {elapsed:.4f} seconds."
                )

        return async_gen_wrapper

    elif inspect.isfunction(func):

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                end_time = time.perf_counter()
                elapsed = end_time - start_time
                logger.info(
                    f"Sync [`{func.__name__.upper()}`] TOOK: {elapsed:.4f} seconds."
                )

        return sync_wrapper

    else:
        raise TypeError(
            "Decorator `timeit` only supports coroutine functions, async generator functions, and regular functions."
        )

