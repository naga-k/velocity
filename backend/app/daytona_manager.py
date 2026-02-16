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

from app.config import settings

logger = logging.getLogger(__name__)


class DaytonaSandboxManager:
    """Manages Daytona sandboxes for agent execution."""

    def __init__(self):
        """Initialize the Daytona client."""
        self.client: AsyncDaytona | None = None
        self._sandboxes: dict[str, Sandbox] = {}

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
        """Create a new Daytona sandbox for a session.

        Args:
            session_id: Unique session identifier
            env_vars: Environment variables to set in the sandbox

        Returns:
            Sandbox instance or None if Daytona is not configured
        """
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

            # Use default snapshot (has Python & Node.js pre-installed for 27-90ms startup!)
            params = CreateSandboxFromSnapshotParams(
                snapshot="daytona-small",  # 1 vCPU, 2GB RAM - fits within memory limits
                env_vars=sandbox_env,
                auto_stop_interval=3600,  # Auto-stop after 1 hour of inactivity
                auto_delete_interval=7200,  # Auto-delete after 2 hours
            )
            sandbox = await self.client.create(params=params)

            self._sandboxes[session_id] = sandbox
            logger.info(f"Sandbox created for session {session_id}: {sandbox.id}")

            # Install only claude-agent-sdk (Python & Node already in snapshot)
            await self._setup_sandbox_environment(session_id)

            return sandbox

        except Exception as e:
            logger.error(f"Failed to create sandbox for session {session_id}: {e}")
            return None

    async def _setup_sandbox_environment(self, session_id: str) -> None:
        """Install claude-agent-sdk in the sandbox.

        Default snapshot already has Python & Node.js, so we only install the SDK.
        This takes ~5-10 seconds instead of 60 seconds!
        """
        sandbox = self._sandboxes.get(session_id)
        if not sandbox:
            return

        logger.info(f"Installing claude-agent-sdk in sandbox {session_id}")

        # Only install claude-agent-sdk (everything else is in default snapshot)
        setup_commands = [
            "pip install --quiet anthropic claude-agent-sdk httpx",
        ]

        for cmd in setup_commands:
            try:
                result = await sandbox.process.exec(cmd)
                exit_code = result.exit_code if hasattr(result, "exit_code") else 0
                logger.info(f"Setup completed with exit code {exit_code}")
            except Exception as e:
                logger.error(f"Setup command failed '{cmd}': {e}")

    async def get_sandbox(self, session_id: str) -> Sandbox | None:
        """Get existing sandbox for a session."""
        return self._sandboxes.get(session_id)

    async def upload_script(
        self, session_id: str, script_content: str, remote_path: str = "/tmp/sandbox_runner.py"
    ) -> bool:
        """Upload sandbox_runner.py to the sandbox filesystem.

        Args:
            session_id: Session identifier
            script_content: Python script content to upload
            remote_path: Destination path in sandbox (default: /tmp/sandbox_runner.py)

        Returns:
            True if upload succeeded, False otherwise
        """
        sandbox = await self.get_sandbox(session_id)
        if not sandbox:
            logger.error(f"No sandbox found for session {session_id}")
            return False

        try:
            # Upload file via Daytona SDK filesystem API
            await sandbox.fs.upload_file(script_content.encode("utf-8"), remote_path)
            logger.info(f"Uploaded script to {remote_path} in sandbox {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload script to sandbox {session_id}: {e}")
            return False

    async def execute_streaming(
        self,
        session_id: str,
        command: str,
        on_stdout: Callable[[str], Awaitable[None]],
        on_stderr: Callable[[str], Awaitable[None]] | None = None,
        timeout: int = 600,  # 10 minutes default
    ) -> dict[str, Any]:
        """Execute command in sandbox and stream output via WebSocket callbacks.

        Args:
            session_id: Session identifier
            command: Command to execute
            on_stdout: Async callback for stdout lines
            on_stderr: Optional async callback for stderr lines
            timeout: Timeout in seconds (default 600 = 10 minutes)

        Returns:
            dict with exit_code, timed_out, error keys
        """
        sandbox = await self.get_sandbox(session_id)
        if not sandbox:
            logger.error(f"No sandbox found for session {session_id}")
            return {"exit_code": -1, "timed_out": False, "error": "Sandbox not found"}

        try:
            # Create async session and execute command
            logger.info(f"Executing command in sandbox {session_id}: {command[:100]}...")

            # Execute using code_interpreter for real-time streaming
            # Daytona's code_interpreter.run_code() streams output via WebSocket
            result = await sandbox.code_interpreter.run_code(
                code=command,
                on_stdout=lambda msg: asyncio.create_task(on_stdout(msg.output)),
                on_stderr=lambda msg: asyncio.create_task(
                    on_stderr(msg.output) if on_stderr else asyncio.sleep(0)
                ),
                timeout=timeout,
            )

            exit_code = result.exit_code if hasattr(result, "exit_code") else 0
            logger.info(f"Command completed with exit code {exit_code}")

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
        """Execute a command in the session's sandbox (blocking, no streaming).

        Args:
            session_id: Session identifier
            command: Command to execute

        Returns:
            Command execution result or None if failed
        """
        sandbox = await self.get_sandbox(session_id)
        if not sandbox:
            logger.error(f"No sandbox found for session {session_id}")
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
        sandbox = self._sandboxes.pop(session_id, None)
        if sandbox:
            try:
                # Daytona sandboxes auto-delete based on auto_delete_interval
                # Manual cleanup not required, but we can stop it to save resources
                logger.info(f"Cleaning up sandbox for session {session_id}")
                # The sandbox will be auto-deleted by Daytona
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
