import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


async def retry_async(
    operation: Callable[[], Awaitable[T]],
    *,
    attempts: int,
    base_delay: float,
    retry_for: tuple[type[BaseException], ...],
) -> T:
    """Retry transient failures with bounded exponential backoff."""
    for attempt in range(1, attempts + 1):
        try:
            return await operation()
        except retry_for:
            if attempt == attempts:
                raise
            await asyncio.sleep(base_delay * (2 ** (attempt - 1)))
    raise RuntimeError("retry loop exhausted")


def retry_sync(
    operation: Callable[[], T],
    *,
    attempts: int,
    base_delay: float,
    retry_for: tuple[type[BaseException], ...],
) -> T:
    """Synchronous counterpart to retry_async."""
    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except retry_for:
            if attempt == attempts:
                raise
            time.sleep(base_delay * (2 ** (attempt - 1)))
    raise RuntimeError("retry loop exhausted")
