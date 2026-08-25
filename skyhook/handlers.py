import inspect
import types
from typing import Callable, Iterator, Optional


def skyhook_handler(fn: Optional[Callable] = None, *, html: bool = False) -> Callable:
    """
    Decorator to mark a function as a Skyhook handler.

    Works in three forms:
        @skyhook_handler                # no parentheses
        @skyhook_handler()              # parentheses, no args
        @skyhook_handler(html=True)     # with html kwarg

    Sets __skyhook_handler__ = True on the function, marking it as dispatchable.
    When html=True, also sets __skyhook_html_handler__ = True, signaling that
    the handler returns HTML and should have origin-allowlist checks applied.

    Args:
        fn: The function being decorated (None if called with parentheses)
        html: If True, mark this as an HTML handler

    Returns:
        The decorated function or a decorator function
    """
    if fn is not None and not callable(fn):
        raise TypeError(
            "@skyhook_handler: unexpected positional argument. "
            "Use @skyhook_handler() or @skyhook_handler(html=True)."
        )

    def decorator(func: Callable) -> Callable:
        func.__skyhook_handler__ = True
        func.__skyhook_html_handler__ = html
        return func

    # Case 1: @skyhook_handler (no parentheses, fn is the decorated function)
    if fn is not None:
        return decorator(fn)

    # Case 2 & 3: @skyhook_handler() or @skyhook_handler(html=True)
    return decorator


def iter_handlers(module: types.ModuleType) -> Iterator[Callable]:
    """
    Yield all callables in a module that have __skyhook_handler__ = True.

    Skips handlers that were imported into the module rather than defined there.

    Args:
        module: A Python module to scan for handlers

    Yields:
        Callable objects marked as Skyhook handlers defined in this module
    """
    for name in dir(module):
        obj = getattr(module, name)
        if callable(obj) and getattr(obj, "__skyhook_handler__", False):
            if inspect.getmodule(obj) is module:
                yield obj
