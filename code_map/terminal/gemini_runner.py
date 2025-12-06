"""
Gemini Code Runner - Async subprocess for JSON streaming mode

Executes Gemini CLI with --output-format stream-json for structured output.
Supports bidirectional communication for interactive permission handling.
"""

import asyncio
import json
import logging
import os
import shutil
from pathlib import Path
from typing import Optional, Callable, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


def find_gemini_cli() -> str:
    """
    Find the Gemini CLI executable.
    """
    # Check if gemini is in PATH
    gemini_path = shutil.which("gemini")
    if gemini_path:
        return gemini_path

    # Common installation locations
    home = os.environ.get("HOME") or os.path.expanduser("~")
    common_paths = [
        Path(home) / ".local" / "bin" / "gemini",
        Path(home) / ".npm-global" / "bin" / "gemini",
        Path("/usr/local/bin/gemini"),
        Path("/usr/bin/gemini"),
    ]

    for path in common_paths:
        if path.exists() and os.access(path, os.X_OK):
            logger.info(f"Found Gemini CLI at: {path}")
            return str(path)

    # Fallback
    logger.warning(
        "Gemini CLI not found in common locations, using 'gemini' (may fail)"
    )
    return "gemini"


@dataclass
class GeminiRunnerConfig:
    """Configuration for Gemini Code runner"""

    cwd: str
    model: str = "gemini-2.5-flash"  # Default Gemini model
    continue_session: bool = True
    verbose: bool = True
    timeout: Optional[float] = None
    permission_mode: str = "default"
    auto_approve_safe_tools: bool = False
    # Gemini-specific approval mode: "auto_edit" (safer) or "yolo" (full access)
    # "auto_edit" allows file operations but NOT shell commands
    # "yolo" allows everything including shell commands (dangerous)
    gemini_approval_mode: str = "auto_edit"


class GeminiAgentRunner:
    """
    Executes Gemini CLI in JSON streaming mode with bidirectional communication.
    """

    def __init__(self, config: GeminiRunnerConfig):
        self.config = config
        self.process: Optional[asyncio.subprocess.Process] = None
        self.running = False
        self._cancelled = False
        self._pending_approval_tasks: list[asyncio.Task] = []
        self._session_broken = False

        # Tool approval manager
        self._tool_approval_manager = None
        if config.permission_mode == "toolApproval":
            from .tool_approval import ToolApprovalManager

            self._tool_approval_manager = ToolApprovalManager(
                cwd=config.cwd,
                auto_approve_safe=config.auto_approve_safe_tools,
            )

    async def run_prompt(
        self,
        prompt: str,
        on_event: Callable[[dict], Any],
        on_error: Optional[Callable[[str], Any]] = None,
        on_done: Optional[Callable[[], Any]] = None,
        on_permission_request: Optional[Callable[[dict], Any]] = None,
        on_tool_approval_request: Optional[Callable[[Any], Any]] = None,
    ) -> int:
        """
        Execute a prompt and stream JSON events
        """
        gemini_bin = find_gemini_cli()
        cmd = [
            gemini_bin,
            prompt,  # Gemini takes prompt as argument
            "--output-format",
            "stream-json",
        ]

        # Add model flag if not using default
        if self.config.model and self.config.model != "gemini-2.5-flash":
            cmd.extend(["--model", self.config.model])

        # Set approval mode - Gemini CLI requires explicit approval mode to expose tools
        # Without it, write tools (write_file, replace, run_shell_command) aren't available
        # Options:
        # - "default": Gemini prompts for approval (can't handle in stream mode - hangs)
        # - "auto_edit": Auto-approve write_file/replace, but NOT run_shell_command
        # - "yolo": Auto-approve all tools including run_shell_command
        #
        # We use config.gemini_approval_mode which defaults to "auto_edit" for safety.
        # This prevents Gemini from running destructive shell commands (rm, git init, etc.)
        # while still allowing file read/write operations.
        #
        # If permission_mode is "toolApproval", we still need auto_edit/yolo because
        # we can't handle Gemini's interactive approval prompts in stream-json mode.
        # The toolApproval logic in AEGIS is a separate layer on top.
        gemini_mode = self.config.gemini_approval_mode
        if gemini_mode == "yolo":
            cmd.extend(["--yolo"])
        else:
            # Default to auto_edit for safer operation
            cmd.extend(["--approval-mode", "auto_edit"])

        logger.info(f"Starting Gemini CLI: {' '.join(cmd)}...")

        self.running = True
        self._cancelled = False

        try:
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.config.cwd,
            )

            logger.info(f"Gemini CLI process started: PID={self.process.pid}")

            # Read stdout line by line
            async def read_stdout():
                if self.process.stdout is None:
                    return

                while self.running and not self._cancelled:
                    try:
                        line = await self.process.stdout.readline()
                        if not line:
                            break

                        line_str = line.decode("utf-8").strip()
                        if not line_str:
                            continue

                        try:
                            event = json.loads(line_str)

                            # Map Gemini events to Claude format for frontend compatibility
                            mapped_event = self._map_event(event)

                            if mapped_event:
                                # Check for tool_use in toolApproval mode
                                if (
                                    self._is_tool_use_event(mapped_event)
                                    and self._tool_approval_manager
                                    and on_tool_approval_request
                                ):
                                    logger.info(
                                        "[toolApproval] Intercepting tool_use for approval"
                                    )
                                    approval_task = asyncio.create_task(
                                        self._handle_tool_approval(
                                            mapped_event,
                                            on_event,
                                            on_tool_approval_request,
                                        )
                                    )
                                    self._pending_approval_tasks.append(approval_task)
                                else:
                                    result = on_event(mapped_event)
                                    if asyncio.iscoroutine(result):
                                        await result

                        except json.JSONDecodeError:
                            if on_error:
                                result = on_error(f"[PARSE ERROR] {line_str}")
                                if asyncio.iscoroutine(result):
                                    await result

                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        logger.error(f"Error reading stdout: {e}")
                        break

            # Read stderr
            async def read_stderr():
                if self.process.stderr is None:
                    return

                # Patterns to skip entirely (informational, not errors)
                skip_patterns = [
                    "loaded cached credentials",
                    "authenticating",
                    "loading",
                    "initializing",
                    "connecting",
                    "yolo mode",  # YOLO mode notification
                    "auto_edit mode",  # auto_edit mode notification
                    "all tool calls will be automatically approved",
                    "edit tools will be automatically approved",
                    "approval mode",
                ]

                # Patterns to log but not show to user (API/backend issues)
                log_only_patterns = [
                    "attempt",  # "Attempt 1 failed with status 429"
                    "retrying",
                    "gaxioserror",  # Google API errors
                    "resource exhausted",
                    "rate limit",
                    "429",
                    "too many requests",
                    "backoff",
                ]

                while self.running and not self._cancelled:
                    try:
                        line = await self.process.stderr.readline()
                        if not line:
                            break

                        line_str = line.decode("utf-8").strip()
                        if not line_str:
                            continue

                        line_lower = line_str.lower()

                        # Skip informational messages entirely
                        if any(pattern in line_lower for pattern in skip_patterns):
                            logger.debug(f"[Gemini info] {line_str}")
                            continue

                        # Log API errors but don't send to frontend
                        if any(pattern in line_lower for pattern in log_only_patterns):
                            logger.warning(f"[Gemini API] {line_str[:200]}")
                            continue

                        # Send other errors to frontend
                        if on_error:
                            result = on_error(line_str)
                            if asyncio.iscoroutine(result):
                                await result
                    except asyncio.CancelledError:
                        break

            stdout_task = asyncio.create_task(read_stdout())
            stderr_task = asyncio.create_task(read_stderr())

            await self.process.wait()

            await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)

            if self._pending_approval_tasks:
                await asyncio.gather(
                    *self._pending_approval_tasks, return_exceptions=True
                )
                self._pending_approval_tasks.clear()

            if on_done:
                result = on_done()
                if asyncio.iscoroutine(result):
                    await result

            return self.process.returncode or 0

        except Exception as e:
            logger.error(f"Error running Gemini CLI: {e}", exc_info=True)
            if on_error:
                result = on_error(f"Error: {str(e)}")
                if asyncio.iscoroutine(result):
                    await result
            return -1
        finally:
            self.running = False
            self.process = None

    def _map_event(self, event: dict) -> Optional[dict]:
        """Map Gemini event to Claude event format"""
        event_type = event.get("type")

        # Handle init event - contains session info and model
        if event_type == "init":
            model = event.get("model", "unknown")
            session_id = event.get("session_id", "")
            return {
                "type": "system",
                "subtype": "init",
                "content": {
                    "session_id": session_id,
                    "model": f"gemini ({model})" if model else "gemini",
                    "tools": [],
                    "mcp_servers": [],
                },
            }

        if event_type == "message":
            role = event.get("role")
            content = event.get("content")
            if role == "assistant":
                return {"type": "assistant", "subtype": "text", "content": content}

        elif event_type == "tool_use":
            return {
                "type": "assistant",
                "subtype": "tool_use",
                "content": {
                    "name": event.get("tool_name"),
                    "input": event.get("parameters"),
                    "id": event.get("tool_id"),
                },
            }

        elif event_type == "tool_result":
            # We might not need to map this if we are intercepting tool use
            # But if Gemini executes it, we should show it
            return {
                "type": "user",
                "subtype": "tool_result",
                "content": {
                    "tool_use_id": event.get("tool_id"),
                    "content": event.get("output")
                    or event.get("error", {}).get("message", ""),
                    "is_error": event.get("status") == "error",
                },
            }

        # Handle result event - contains token usage stats
        elif event_type == "result":
            stats = event.get("stats", {})
            return {
                "type": "system",
                "subtype": "usage",
                "content": {
                    "input_tokens": stats.get("input_tokens", 0),
                    "output_tokens": stats.get("output_tokens", 0),
                    "cached_input_tokens": 0,
                    "total_tokens": stats.get("total_tokens", 0),
                    "duration_ms": stats.get("duration_ms", 0),
                },
            }

        return None

    def _is_tool_use_event(self, event: dict) -> bool:
        return event.get("type") == "assistant" and event.get("subtype") == "tool_use"

    def _extract_tool_use_from_event(self, event: dict) -> tuple[str, dict, str] | None:
        if event.get("subtype") == "tool_use":
            content = event.get("content", {})
            return (
                content.get("name", "unknown"),
                content.get("input", {}),
                content.get("id", ""),
            )
        return None

    async def _handle_tool_approval(self, event, on_event, on_tool_approval_request):
        # Similar logic to ClaudeAgentRunner._handle_tool_approval
        # But adapted for Gemini

        tool_info = self._extract_tool_use_from_event(event)
        if not tool_info:
            return

        tool_name, tool_input, tool_id = tool_info

        # Forward event to frontend
        result = on_event(event)
        if asyncio.iscoroutine(result):
            await result

        async def send_approval_request(request):
            try:
                result = on_tool_approval_request(request)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Error sending approval request: {e}")

        approved, feedback = await self._tool_approval_manager.process_tool_use(
            tool_name=tool_name,
            tool_input=tool_input,
            tool_use_id=tool_id,
            on_approval_request=send_approval_request,
        )

        if approved:
            # Execute tool manually
            # We need to implement _execute_tool similar to ClaudeRunner
            # For now, I'll copy the _execute_tool logic from ClaudeRunner or import it if possible
            # Since I can't easily import private methods, I'll duplicate the logic for now
            # or refactor later.
            tool_result = await self._execute_tool(tool_name, tool_input)

            result_event = {
                "type": "user",
                "subtype": "tool_result",
                "local_execution": True,
                "content": {
                    "tool_use_id": tool_id,
                    "content": tool_result.get("content", ""),
                    "is_error": tool_result.get("is_error", False),
                },
            }
            result = on_event(result_event)
            if asyncio.iscoroutine(result):
                await result

            # Note: We are not sending the result back to Gemini process because
            # we are running it in a one-off command mode (prompt as arg).
            # So the process likely exits after tool_use or waits?
            # If it waits, we can't easily write to stdin if we didn't set it up for chat loop.
            # The current implementation passes prompt as arg, so it might be a single turn.
            # We'll see.

        else:
            # Rejected
            result_event = {
                "type": "user",
                "subtype": "tool_result",
                "local_execution": True,
                "content": {
                    "tool_use_id": tool_id,
                    "content": f"[REJECTED] {feedback}",
                    "is_error": True,
                },
            }
            result = on_event(result_event)
            if asyncio.iscoroutine(result):
                await result

    async def _execute_tool(self, tool_name: str, tool_input: dict) -> dict:
        """
        Execute a tool locally after approval.
        This is only called in toolApproval mode when we intercept tool calls.
        """
        if tool_name == "run_shell_command":
            # Gemini uses run_shell_command, Claude uses Bash
            return await self._execute_bash(tool_input)

        if tool_name == "write_file":
            return await self._execute_write_file(tool_input)

        if tool_name == "replace":
            return await self._execute_replace(tool_input)

        # For other tools, let them pass through - they're read-only
        return {
            "content": f"Tool {tool_name} not implemented in runner (read-only tools execute in CLI)",
            "is_error": True,
        }

    async def _execute_bash(self, tool_input: dict) -> dict:
        """Execute a shell command."""
        command = tool_input.get("command", "")
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.config.cwd,
            )
            stdout, stderr = await proc.communicate()
            return {
                "content": stdout.decode("utf-8") + stderr.decode("utf-8"),
                "is_error": proc.returncode != 0,
            }
        except Exception as e:
            return {"content": str(e), "is_error": True}

    async def _execute_write_file(self, tool_input: dict) -> dict:
        """Write content to a file."""
        file_path = tool_input.get("file_path", "")
        content = tool_input.get("content", "")
        try:
            # Resolve path relative to cwd
            from pathlib import Path

            full_path = Path(self.config.cwd) / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)
            return {"content": f"File written: {file_path}", "is_error": False}
        except Exception as e:
            return {"content": str(e), "is_error": True}

    async def _execute_replace(self, tool_input: dict) -> dict:
        """Replace text in a file."""
        file_path = tool_input.get("file_path", "")
        old_string = tool_input.get("old_string", "")
        new_string = tool_input.get("new_string", "")
        try:
            from pathlib import Path

            full_path = Path(self.config.cwd) / file_path
            if not full_path.exists():
                return {"content": f"File not found: {file_path}", "is_error": True}

            content = full_path.read_text()
            if old_string not in content:
                return {
                    "content": f"String not found in {file_path}",
                    "is_error": True,
                }

            new_content = content.replace(old_string, new_string, 1)
            full_path.write_text(new_content)
            return {"content": f"Replaced in {file_path}", "is_error": False}
        except Exception as e:
            return {"content": str(e), "is_error": True}

    async def cancel(self):
        if self.process:
            self.process.terminate()
        self._cancelled = True

    def respond_to_tool_approval(
        self, request_id: str, approved: bool, feedback: Optional[str] = None
    ) -> bool:
        """
        Respond to a pending tool approval request.
        """
        if self._tool_approval_manager:
            return self._tool_approval_manager.respond_to_approval(
                request_id, approved, feedback
            )
        return False
