"""Daytona Sandbox Manager for Agent SDK execution.

Manages the lifecycle of Daytona sandboxes for running Claude Agent SDK sessions.
Each chat session gets its own ephemeral sandbox for isolated code execution.
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Awaitable, Callable
from typing import Any

from daytona import AsyncDaytona, CreateSandboxFromSnapshotParams, Sandbox
from daytona.common.process import SessionExecuteRequest

from app.config import settings

logger = logging.getLogger(__name__)


class DaytonaSandboxManager:
    """Manages Daytona sandboxes for agent execution."""

    def __init__(self):
        """Initialize the Daytona client."""
        self.client: AsyncDaytona | None = None
        self._sandboxes: dict[str, Sandbox] = {}
        self._sessions_created: set[str] = set()  # Track which sandboxes have process sessions

    async def initialize(self):
        """Initialize the async Daytona client."""
        if not settings.daytona_configured:
            logger.warning("Daytona not configured - sandbox features will be disabled")
            return

        # Set environment variables for Daytona SDK
        os.environ["DAYTONA_API_KEY"] = settings.daytona_api_key
        os.environ["DAYTONA_API_URL"] = settings.daytona_api_url
        os.environ["DAYTONA_TARGET"] = settings.daytona_target

        self.client = AsyncDaytona()
        logger.info("Daytona sandbox manager initialized")

    async def create_sandbox(
        self, session_id: str, env_vars: dict[str, str] | None = None
    ) -> Sandbox | None:
        """Create a new Daytona sandbox for a session."""
        if not self.client:
            logger.warning("Daytona client not initialized - cannot create sandbox")
            return None

        try:
            # Prepare environment variables for the sandbox
            sandbox_env = {
                "ANTHROPIC_API_KEY": settings.anthropic_api_key,
                **(env_vars or {}),
            }

            # Add optional integration tokens if available
            if settings.slack_configured:
                sandbox_env["SLACK_BOT_TOKEN"] = settings.slack_bot_token
            if settings.linear_configured:
                sandbox_env["LINEAR_API_KEY"] = settings.linear_api_key

            logger.info(f"Creating Daytona sandbox for session {session_id}")

            params = CreateSandboxFromSnapshotParams(
                snapshot="daytona-small",
                env_vars=sandbox_env,
                auto_stop_interval=3600,
                auto_delete_interval=7200,
            )
            sandbox = await self.client.create(params=params)

            self._sandboxes[session_id] = sandbox
            logger.info(f"Sandbox created for session {session_id}: {sandbox.id}")

            # Install dependencies and create process session
            await self._setup_sandbox_environment(session_id)

            return sandbox

        except Exception as e:
            logger.error(f"Failed to create sandbox for session {session_id}: {e}")
            return None

    async def _setup_sandbox_environment(self, session_id: str) -> None:
        """Install claude-agent-sdk and create process session."""
        sandbox = self._sandboxes.get(session_id)
        if not sandbox:
            return

        logger.info(f"Installing claude-agent-sdk in sandbox {session_id}")

        setup_commands = [
            "pip install --quiet anthropic httpx git+https://github.com/naga-k/claude-agent-sdk-python.git@fix/558-message-buffer-deadlock",
        ]

        for cmd in setup_commands:
            try:
                result = await sandbox.process.exec(cmd)
                exit_code = result.exit_code if hasattr(result, "exit_code") else 0
                logger.info(f"Setup completed with exit code {exit_code}")
            except Exception as e:
                logger.error(f"Setup command failed '{cmd}': {e}")

        # Create a process session for streaming execution
        try:
            await sandbox.process.create_session(session_id)
            self._sessions_created.add(session_id)
            logger.info(f"Process session created for {session_id}")
        except Exception as e:
            logger.warning(f"Failed to create process session: {e} — will fall back to exec()")

    async def get_sandbox(self, session_id: str) -> Sandbox | None:
        """Get existing sandbox for a session."""
        return self._sandboxes.get(session_id)

    async def upload_script(
        self, session_id: str, script_content: str, remote_path: str = "/tmp/sandbox_runner.py"
    ) -> bool:
        """Upload a file to the sandbox filesystem."""
        sandbox = await self.get_sandbox(session_id)
        if not sandbox:
            logger.error(f"No sandbox found for session {session_id}")
            return False

        try:
            await sandbox.fs.upload_file(script_content.encode("utf-8"), remote_path)
            logger.info(f"Uploaded script to {remote_path} in sandbox {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload script to sandbox {session_id}: {e}")
            return False

    async def write_file(self, session_id: str, content: str, remote_path: str) -> bool:
        """Write content to a file in the sandbox (for proxy responses)."""
        sandbox = await self.get_sandbox(session_id)
        if not sandbox:
            return False

        try:
            await sandbox.fs.upload_file(content.encode("utf-8"), remote_path)
            return True
        except Exception as e:
            logger.error(f"Failed to write file {remote_path} in sandbox {session_id}: {e}")
            return False

    async def execute_streaming(
        self,
        session_id: str,
        command: str,
        on_stdout: Callable[[str], Awaitable[None]],
        on_stderr: Callable[[str], Awaitable[None]] | None = None,
        timeout: int = 600,
    ) -> dict[str, Any]:
        """Execute command in sandbox with real-time streaming.

        Uses session-based execution (create_session + execute_session_command)
        to get cmd_id for streaming. Falls back to exec() if sessions unavailable.
        """
        sandbox = await self.get_sandbox(session_id)
        if not sandbox:
            logger.error(f"No sandbox found for session {session_id}")
            return {"exit_code": -1, "timed_out": False, "error": "Sandbox not found"}

        try:
            logger.info(f"Executing command in sandbox {session_id}: {command[:100]}...")

            # Try session-based execution first (gives us cmd_id for streaming)
            if session_id in self._sessions_created:
                try:
                    # run_async=True: command starts immediately, returns cmd_id for streaming
                    req = SessionExecuteRequest(command=command, run_async=True)
                    cmd_response = await sandbox.process.execute_session_command(
                        session_id, req, timeout=timeout
                    )
                    cmd_id = cmd_response.cmd_id if hasattr(cmd_response, "cmd_id") else None

                    if cmd_id:
                        logger.info(f"Streaming via session (async), cmd_id={cmd_id}")

                        async def stdout_handler(line: str):
                            if line and on_stdout:
                                await on_stdout(line)

                        async def stderr_handler(line: str):
                            if line and on_stderr:
                                await on_stderr(line)

                        # This blocks until the command completes, streaming output as it arrives
                        await sandbox.process.get_session_command_logs_async(
                            session_id,
                            cmd_id,
                            stdout_handler,
                            stderr_handler if on_stderr else None,
                        )

                        # Get final exit code after command completes
                        try:
                            cmd_info = await sandbox.process.get_session_command(session_id, cmd_id)
                            exit_code = cmd_info.exit_code if hasattr(cmd_info, "exit_code") else 0
                        except Exception:
                            exit_code = 0

                        logger.info(f"Session command completed with exit code {exit_code}")
                        return {"exit_code": exit_code, "timed_out": False, "error": None}

                except Exception as e:
                    logger.warning(f"Session execution failed: {e} — falling back to exec()")

            # Fallback: synchronous exec()
            cmd_result = await sandbox.process.exec(command)
            exit_code = cmd_result.exit_code if hasattr(cmd_result, "exit_code") else 0
            stdout = cmd_result.result if hasattr(cmd_result, "result") else ""
            stderr = cmd_result.error if hasattr(cmd_result, "error") else ""
            if stderr and on_stderr:
                for line in stderr.strip().split('\n'):
                    if line:
                        await on_stderr(line)
            if stdout and on_stdout:
                for line in stdout.strip().split('\n'):
                    if line:
                        await on_stdout(line)
            return {"exit_code": exit_code, "timed_out": False, "error": None}

        except asyncio.TimeoutError:
            logger.error(f"Command timed out after {timeout}s in sandbox {session_id}")
            return {"exit_code": -1, "timed_out": True, "error": f"Timeout after {timeout}s"}

        except Exception as e:
            logger.error(f"Error executing command in sandbox {session_id}: {e}")
            return {"exit_code": -1, "timed_out": False, "error": str(e)}

    async def execute_in_sandbox(
        self, session_id: str, command: str
    ) -> dict[str, Any] | None:
        """Execute a command in the session's sandbox (blocking, no streaming)."""
        sandbox = await self.get_sandbox(session_id)
        if not sandbox:
            return None

        try:
            response = await sandbox.process.exec(command)
            return {
                "exit_code": response.exit_code if hasattr(response, "exit_code") else 0,
                "stdout": response.result if hasattr(response, "result") else "",
                "stderr": response.error if hasattr(response, "error") else "",
            }
        except Exception as e:
            logger.error(f"Failed to execute command in sandbox {session_id}: {e}")
            return None

    async def cleanup_sandbox(self, session_id: str) -> None:
        """Clean up a sandbox when session ends."""
        self._sessions_created.discard(session_id)
        sandbox = self._sandboxes.pop(session_id, None)
        if sandbox:
            try:
                logger.info(f"Cleaning up sandbox for session {session_id}")
            except Exception as e:
                logger.error(f"Error cleaning up sandbox {session_id}: {e}")

    async def shutdown(self):
        """Shutdown the manager and clean up all sandboxes."""
        logger.info("Shutting down Daytona sandbox manager")
        cleanup_tasks = [self.cleanup_sandbox(sid) for sid in list(self._sandboxes.keys())]
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        self.client = None


# Global singleton instance
sandbox_manager = DaytonaSandboxManager()
