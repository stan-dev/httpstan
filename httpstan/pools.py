import concurrent.futures
import multiprocessing as mp
import signal

import aiohttp.web


def init_call_worker() -> None:
    signal.signal(signal.SIGINT, signal.SIG_IGN)  # ignore KeyboardInterrupt


def setup_pools(app: aiohttp.web.Application) -> None:
    """Create any Process or Thread Pools needed by the application

    This won't create the pools immediately, in case a feature that uses them
    isn't used, but instead lazily. That's why the pools are represented by a
    function instead of the pool exectur object itself.

    """
    fit_executor = None

    # Use `get_context` to get a package-specific multiprocessing context.
    # See "Contexts and start methods" in the `multiprocessing` docs for details.
    def create_fit_executor(shutdown=False):
        nonlocal fit_executor

        if shutdown:
            if fit_executor is None:
                return

            fit_executor.shutdown()
            return

        if fit_executor is not None:
            return fit_executor

        fit_executor = concurrent.futures.ProcessPoolExecutor(
            mp_context=mp.get_context("fork"), initializer=init_call_worker
        )

        return fit_executor

    app["create_fit_executor"] = create_fit_executor


async def shutdown_pools(app: aiohttp.web.Application) -> None:
    app["create_fit_executor"](shutdown=True)
