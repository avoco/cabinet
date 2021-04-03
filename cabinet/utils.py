from asyncio import iscoroutinefunction
from typing import Awaitable, Callable, TypeVar, Union, cast

# asgiref doesn't yet have type info
from asgiref import sync  # type: ignore


T = TypeVar("T")
R = TypeVar("R")

AsyncCallable = Callable[[T], Awaitable[R]]
SyncCallable = Callable[[T], R]
MaybeAsyncCallable = Union[SyncCallable, AsyncCallable]


def sync_to_async(fn: SyncCallable, thread_sensitive=True) -> AsyncCallable:
    """
    Coverts a synchronous function into an asynchronous one.

    :param fn: the function to turn asynchronous

    :param thread_sensitive: whether or not the function is thread sensitive

    :return: the asynchronous function
    """
    return cast(
        AsyncCallable,
        sync.sync_to_async(fn, thread_sensitive=thread_sensitive),
    )


def async_to_sync(fn: AsyncCallable) -> SyncCallable:
    """
    Coverts a asynchronous function into a synchronous one.

    :param fn: the function to turn synchronous

    :return: the asynchronous function
    """
    return cast(SyncCallable, sync.async_to_sync(fn))


def any_to_async(fn: MaybeAsyncCallable, thread_sensitive=True) -> AsyncCallable:
    """
    Coverts any function into an asynchronous one.

    :param fn: the function to turn asynchronous

    :param thread_sensitive: whether or not the function is thread sensitive

    :return: the asynchronous function
    """
    if iscoroutinefunction(fn):
        return fn
    return sync_to_async(fn, thread_sensitive=thread_sensitive)


def any_to_sync(fn: MaybeAsyncCallable) -> SyncCallable:
    """
    Coverts any function into a synchronous one.

    :param fn: the function to turn synchronous

    :return: the synchronous function
    """
    if iscoroutinefunction(fn):
        return async_to_sync(fn)
    return fn
