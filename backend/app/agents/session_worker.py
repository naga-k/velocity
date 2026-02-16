"""Session worker — runs SDK client in Daytona sandbox per session.

Refactored to execute Claude Agent SDK inside Daytona sandboxes instead of
running the SDK locally. Each session gets an ephemeral Daytona sandbox where
the sandbox_runner.py script is uploaded and executed. The worker streams
stdout from the sandbox and parses JSON events into SDK-like message objects.

Slack API calls are proxied through the backend because Daytona Tier 1/2
sandboxes have restricted network access (slack.com is not whitelisted).
The sandbox tools write request files, the backend fulfills them via the
Daytona filesystem API, and the tools poll for response files.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import httpx

from claude_agent_sdk import AssistantMessage, ResultMessage, ToolUseBlock
from claude_agent_sdk.types import StreamEvent

from app.config import settings
from app.daytona_manager import sandbox_manager

logger = logging.getLogger(__name__)

_SENTINEL = object()  # Marks end of a response stream

# Load sandbox_runner.py content at module load time
SANDBOX_RUNNER_SCRIPT = (Path(__file__).parent / "sandbox_runner.py").read_text()


async def _handle_slack_proxy(session_id: str, request: dict) -> None:
    """Handle a Slack proxy request from the sandbox.

    The sandbox can't reach slack.com (Daytona Tier 1/2 network restrictions),
    so we make the API call from the backend and write the response back.
    """
    req_id = request.get("id", "")
    method = request.get("method", "")
    params = request.get("params", {})

    if not settings.slack_configured:
        response = {"ok": False, "error": "slack_not_configured"}
        await sandbox_manager.write_file(
            session_id, json.dumps(response), f"/tmp/slack_resp_{req_id}.json"
        )
        return

    headers = {"Authorization": f"Bearer {settings.slack_bot_token}"}
    base = "https://slack.com/api"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            if method == "conversations.list":
                resp = await client.get(
                    f"{base}/conversations.list",
                    params={"limit": params.get("limit", 50), "types": "public_channel"},
                    headers=headers,
                )
                data = resp.json()
            elif method == "conversations.history":
                resp = await client.get(
                    f"{base}/conversations.history",
                    params={"channel": params.get("channel"), "limit": params.get("limit", 20)},
                    headers=headers,
                )
                data = resp.json()
            elif method == "search.messages":
                resp = await client.get(
                    f"{base}/search.messages",
                    params={"query": params.get("query", ""), "count": params.get("limit", 20), "sort": "timestamp"},
                    headers=headers,
                )
                data = resp.json()
            elif method == "chat.postMessage":
                resp = await client.post(
                    f"{base}/chat.postMessage",
                    json={"channel": params.get("channel"), "text": params.get("text", "")},
                    headers=headers,
                )
                data = resp.json()
            else:
                data = {"ok": False, "error": f"unknown_method: {method}"}

    except Exception as e:
        logger.error(f"Slack proxy error for {method}: {e}")
        data = {"ok": False, "error": str(e)}

    # Write response back to sandbox filesystem
    ok = await sandbox_manager.write_file(
        session_id, json.dumps(data), f"/tmp/slack_resp_{req_id}.json"
    )
    if ok:
        logger.info(f"Slack proxy: {method} -> wrote response for {req_id}")
    else:
        logger.error(f"Slack proxy: failed to write response for {req_id}")


class _SessionWorker:
    """Manages a Daytona sandbox for SDK execution."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self._input: asyncio.Queue[tuple[str, str, asyncio.Queue[Any]] | None] = asyncio.Queue()
        self._task: asyncio.Task[None] | None = None
        self._started = asyncio.Event()
        self._connect_error: Exception | None = None
        self._sandbox_created = False
        self._conversation_history: list[dict[str, str]] = []

    async def start(self) -> None:
        """Launch the background worker task."""
        self._task = asyncio.create_task(
            self._run(), name=f"session-worker-sandbox-{self.session_id}"
        )
        await self._started.wait()
        if self._connect_error is not None:
            raise self._connect_error

    async def _run(self) -> None:
        """Background loop: create sandbox, upload script, then serve queries."""
        try:
            logger.info(f"Creating Daytona sandbox for session {self.session_id}")
            sandbox = await sandbox_manager.create_sandbox(self.session_id)
            if not sandbox:
                raise RuntimeError("Failed to create Daytona sandbox")

            self._sandbox_created = True

            logger.info(f"Uploading sandbox_runner.py to sandbox {self.session_id}")
            upload_ok = await sandbox_manager.upload_script(
                self.session_id,
                SANDBOX_RUNNER_SCRIPT,
                "/tmp/sandbox_runner.py",
            )
            if not upload_ok:
                raise RuntimeError("Failed to upload sandbox runner script")

            self._started.set()

            while True:
                item = await self._input.get()
                if item is None:
                    break

                message, sid, out_q = item
                try:
                    await self._execute_query(message, sid, out_q)
                except Exception as exc:
                    try:
                        await out_q.put(exc)
                    except Exception:
                        logger.error("Failed to enqueue exception for session %s", self.session_id)
                finally:
                    try:
                        await out_q.put(_SENTINEL)
                    except Exception:
                        logger.error("Failed to enqueue sentinel for session %s", self.session_id)

        except Exception as exc:
            logger.exception("Session worker %s crashed", self.session_id)
            self._connect_error = exc
            self._started.set()

        finally:
            if self._sandbox_created:
                logger.info(f"Cleaning up sandbox for session {self.session_id}")
                await sandbox_manager.cleanup_sandbox(self.session_id)

    async def _execute_query(self, message: str, session_id: str, out_q: asyncio.Queue) -> None:
        """Execute a query in the sandbox and stream parsed messages to out_q."""
        self._conversation_history.append({"role": "user", "content": message})

        # Build command
        cmd_args = [
            "python",
            "/tmp/sandbox_runner.py",
            "--message",
            message,
            "--session-id",
            session_id,
            "--anthropic-api-key",
            settings.anthropic_api_key,
            "--config",
            json.dumps({
                "model_opus": settings.anthropic_model_opus,
                "model_sonnet": settings.anthropic_model_sonnet,
                "max_turns": settings.max_turns,
                "max_budget_usd": settings.max_budget_per_session_usd,
                "slack_team_id": settings.slack_team_id if settings.slack_configured else "",
            }),
            "--history",
            json.dumps(self._conversation_history[:-1]),
        ]

        if settings.slack_configured:
            cmd_args.extend(["--slack-token", settings.slack_bot_token])

        if settings.linear_configured:
            cmd_args.extend(["--linear-api-key", settings.linear_api_key])

        if settings.github_configured:
            cmd_args.extend(["--github-token", settings.github_token])

        import shlex
        command = " ".join(shlex.quote(arg) for arg in cmd_args)

        assistant_response_chunks = []

        async def on_stdout(line: str):
            """Parse JSON line and convert to SDK message object.

            Also intercepts slack_proxy requests and fulfills them from the backend.
            """
            try:
                event = json.loads(line)
                event_type = event.get("type")

                # --- Slack proxy: intercept and fulfill from backend ---
                if event_type == "slack_proxy":
                    logger.info(f"Intercepted Slack proxy request: method={event.get('method')}, id={event.get('id')}")
                    # Fire and forget — the sandbox tool polls for the response file
                    asyncio.create_task(
                        _handle_slack_proxy(self.session_id, event)
                    )
                    return  # Don't forward proxy requests to the output queue

                if event_type == "text_delta":
                    assistant_response_chunks.append(event["text"])
                    msg = StreamEvent(
                        uuid=f"evt-{id(event)}",
                        session_id=session_id,
                        event={
                            "type": "content_block_delta",
                            "delta": {"type": "text_delta", "text": event["text"]},
                        },
                    )
                    await out_q.put(msg)

                elif event_type == "thinking_delta":
                    msg = StreamEvent(
                        uuid=f"evt-{id(event)}",
                        session_id=session_id,
                        event={
                            "type": "content_block_delta",
                            "delta": {"type": "thinking_delta", "thinking": event["text"]},
                        },
                    )
                    await out_q.put(msg)

                elif event_type == "agent_activity":
                    msg = AssistantMessage(
                        content=[
                            ToolUseBlock(
                                id=f"tool-{id(event)}",
                                name="Task",
                                input={
                                    "subagent_type": event["agent"],
                                    "description": event["task"],
                                },
                            )
                        ],
                        model=settings.anthropic_model_opus,
                    )
                    await out_q.put(msg)

                elif event_type == "tool_call":
                    msg = AssistantMessage(
                        content=[
                            ToolUseBlock(
                                id=f"tool-{id(event)}",
                                name=event["tool"],
                                input=event["params"],
                            )
                        ],
                        model=settings.anthropic_model_opus,
                    )
                    await out_q.put(msg)

                elif event_type == "done":
                    msg = ResultMessage(
                        subtype="result",
                        duration_ms=0,
                        duration_api_ms=0,
                        is_error=False,
                        num_turns=1,
                        session_id=session_id,
                        total_cost_usd=0.0,
                        usage=event.get("tokens_used", {"input_tokens": 0, "output_tokens": 0}),
                    )
                    await out_q.put(msg)

                elif event_type == "error":
                    raise RuntimeError(event["message"])

            except json.JSONDecodeError:
                logger.debug(f"Non-JSON sandbox output: {line}")
            except Exception as e:
                logger.error(f"Error processing sandbox output: {e}")
                await out_q.put(e)

        stderr_lines = []

        async def on_stderr(line: str):
            stderr_lines.append(line)
            logger.error(f"Sandbox stderr: {line}")

        result = await sandbox_manager.execute_streaming(
            session_id=self.session_id,
            command=command,
            on_stdout=on_stdout,
            on_stderr=on_stderr,
            timeout=600,
        )

        if result["error"]:
            raise RuntimeError(f"Sandbox execution failed: {result['error']}")

        if result["exit_code"] != 0:
            stderr_msg = "\n".join(stderr_lines) if stderr_lines else "No stderr output"
            raise RuntimeError(f"Sandbox script exited with code {result['exit_code']}. Stderr: {stderr_msg}")

        if assistant_response_chunks:
            assistant_response = "".join(assistant_response_chunks)
            self._conversation_history.append({"role": "assistant", "content": assistant_response})

    async def query_and_stream(
        self, message: str, session_id: str
    ) -> asyncio.AsyncGenerator[Any, None]:
        """Send a query and yield SDK messages (UNCHANGED INTERFACE)."""
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
                await asyncio.wait_for(self._task, timeout=15.0)
            except asyncio.TimeoutError:
                logger.warning("Session worker %s did not stop in time, cancelling", self.session_id)
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

    if session_id not in _worker_locks:
        _worker_locks[session_id] = asyncio.Lock()

    async with _worker_locks[session_id]:
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
