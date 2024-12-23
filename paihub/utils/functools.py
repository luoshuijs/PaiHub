import asyncio
from collections.abc import Callable, Coroutine
from concurrent.futures import Executor
from functools import partial, wraps
from typing import Any, ParamSpec, TypeVar

T = TypeVar("T")
P = ParamSpec("P")


def async_wrap(
    func: Callable[P, T],
    loop: asyncio.AbstractEventLoop | None = None,
    executor: Executor | None = None,
) -> Callable[P, Coroutine[Any, Any, T]]:
    """Transform a synchronous function to an asynchronous one with type hints."""

    if loop is None:
        loop = asyncio.get_event_loop()

    @wraps(func)
    async def run(*args: "P.args", **kwargs: "P.kwargs") -> "T":
        p_func = partial(func, *args, **kwargs)
        return await loop.run_in_executor(executor, p_func)

    return run
