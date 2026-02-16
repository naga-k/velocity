"""Session worker — runs SDK client in a persistent background task.

The Claude Agent SDK's ClaudeSDKClient uses an internal anyio task group
that is created during connect(). All SDK operations (query, receive_response)
must happen in the SAME asyncio task as connect(). FastAPI handles each HTTP
request in a separate ASGI task, so we can't call receive_response() on a
client that was connected in a previous request's task.

Solution: each session gets a dedicated asyncio.Task ("worker") that owns
the SDK client. HTTP request handlers communicate with the worker via
asyncio.Queues. The worker stays in the same task context for the client's
entire lifetime.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from claude_agent_sdk import ClaudeSDKClient

from .orchestrator import build_options

logger = logging.getLogger(__name__)

_SENTINEL = object()  # Marks end of a response stream


class _SessionWorker:
    """Manages an SDK client in a dedicated asyncio.Task.

    The background task runs connect() and then loops: receive a query from
    the input queue, call query() + receive_response(), push each SDK message
    to the output queue, push a sentinel when done.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self._input: asyncio.Queue[
            tuple[str, str, asyncio.Queue[Any]] | None
        ] = asyncio.Queue()
        self._task: asyncio.Task[None] | None = None
        self._started = asyncio.Event()
        self._connect_error: Exception | None = None

    async def start(self) -> None:
        """Launch the background worker task."""
        self._task = asyncio.create_task(
            self._run(), name=f"session-worker-{self.session_id}"
        )
        # Wait until the worker signals it's connected (or failed)
        await self._started.wait()
        if self._connect_error is not None:
            raise self._connect_error

    async def _run(self) -> None:
        """Background loop: connect client, then serve queries."""
        # Prevent nested session detection
        os.environ.pop("CLAUDECODE", None)

        client = ClaudeSDKClient(options=build_options())
        try:
            await client.connect()
            self._started.set()

            while True:
                item = await self._input.get()
                if item is None:
                    break  # shutdown

                message, sid, out_q = item
                try:
                    await client.query(message, session_id=sid)
                    async for msg in client.receive_response():
                        await out_q.put(msg)
                except Exception as exc:
                    try:
                        await out_q.put(exc)
                    except Exception:
                        logger.error(
                            "Failed to enqueue exception for session %s",
                            self.session_id,
                        )
                finally:
                    try:
                        await out_q.put(_SENTINEL)
                    except Exception:
                        logger.error(
                            "Failed to enqueue sentinel for session %s",
                            self.session_id,
                        )

        except Exception as exc:
            logger.exception("Session worker %s crashed", self.session_id)
            self._connect_error = exc
            self._started.set()  # unblock start() if connect failed
        finally:
            try:
                await client.disconnect()
            except Exception as e:
                logger.warning(
                    "Error disconnecting client for session %s: %s",
                    self.session_id,
                    e,
                )

    async def query_and_stream(
        self, message: str, session_id: str
    ) -> asyncio.AsyncGenerator[Any, None]:
        """Send a query and yield SDK messages from the worker."""
        out_q: asyncio.Queue[Any] = asyncio.Queue()
        await self._input.put((message, session_id, out_q))
        while True:
            msg = await out_q.get()
            if msg is _SENTINEL:
                break
            if isinstance(msg, Exception):
                raise msg
            yield msg

    async def stop(self) -> None:
        """Signal the worker to shut down and wait for it."""
        await self._input.put(None)
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning(
                    "Session worker %s did not stop in time, cancelling",
                    self.session_id,
                )
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass


# ---------------------------------------------------------------------------
# Session worker pool
# ---------------------------------------------------------------------------

_workers: dict[str, _SessionWorker] = {}
_worker_locks: dict[str, asyncio.Lock] = {}


async def get_or_create_worker(session_id: str) -> _SessionWorker:
    """Return an existing worker for this session, or create and start one."""
    if session_id in _workers:
        return _workers[session_id]

    # Per-session lock prevents duplicate workers from concurrent requests
    if session_id not in _worker_locks:
        _worker_locks[session_id] = asyncio.Lock()

    async with _worker_locks[session_id]:
        # Double-check after acquiring lock
        if session_id in _workers:
            return _workers[session_id]

        worker = _SessionWorker(session_id)
        await worker.start()
        _workers[session_id] = worker
        return worker


async def remove_session_client(session_id: str) -> None:
    """Stop and remove the worker for a session."""
    _worker_locks.pop(session_id, None)
    worker = _workers.pop(session_id, None)
    if worker is not None:
        try:
            await worker.stop()
        except Exception:
            logger.warning("Error stopping worker for session %s", session_id)


async def disconnect_all_clients() -> None:
    """Stop all active workers. Called on server shutdown."""
    for sid in list(_workers.keys()):
        await remove_session_client(sid)
