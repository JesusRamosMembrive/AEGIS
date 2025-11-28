"""
Terminal API endpoints

Provides WebSocket endpoints for:
- /ws: Remote terminal access (PTY shell)
- /ws/agent: Claude Code JSON streaming mode
"""

import asyncio
import logging
import json
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from code_map.terminal import PTYShell
from code_map.terminal.agent_parser import AgentEvent
from code_map.terminal.agent_events import AgentEventManager
from code_map.terminal.claude_runner import ClaudeAgentRunner, ClaudeRunnerConfig, PERMISSION_MODES
from code_map.terminal.json_parser import JSONStreamParser
from code_map.terminal.pty_runner import PTYClaudeRunner, PTYRunnerConfig
from code_map.terminal.sdk_runner import SDKAgentRunner, SDKRunnerConfig
from code_map.terminal.gemini_runner import GeminiAgentRunner, GeminiRunnerConfig
from code_map.terminal.mcp_proxy_runner import MCPProxyRunner, MCPProxyRunnerConfig
from code_map.terminal.pty_parser import EventType as PTYEventType
from code_map.settings import load_settings

# MCP Socket Server for mcpApproval mode
from code_map.mcp.socket_server import MCPSocketServer, DEFAULT_SOCKET_PATH
from code_map.mcp.approval_bridge import ApprovalRequest

logger = logging.getLogger(__name__)

# Global MCP socket server instance (shared across connections)
_mcp_socket_server: Optional[MCPSocketServer] = None
_mcp_socket_server_lock = asyncio.Lock()


async def get_or_create_mcp_socket_server(cwd: str) -> MCPSocketServer:
    """
    Get or create the global MCP socket server instance.

    The socket server is shared across all WebSocket connections because
    the MCP Permission Server subprocess needs a single point of communication.
    """
    global _mcp_socket_server

    async with _mcp_socket_server_lock:
        if _mcp_socket_server is None:
            logger.info(f"Creating MCP socket server at {DEFAULT_SOCKET_PATH}")
            _mcp_socket_server = MCPSocketServer(
                socket_path=DEFAULT_SOCKET_PATH,
                cwd=cwd,
                timeout=300.0,  # 5 minutes
                auto_approve_safe=False,
            )
            await _mcp_socket_server.start()
            logger.info("MCP socket server started")

        return _mcp_socket_server


async def stop_mcp_socket_server():
    """Stop the global MCP socket server if running."""
    global _mcp_socket_server

    async with _mcp_socket_server_lock:
        if _mcp_socket_server is not None:
            logger.info("Stopping MCP socket server")
            await _mcp_socket_server.stop()
            _mcp_socket_server = None


router = APIRouter(prefix="/terminal", tags=["terminal"])


@router.websocket("/ws")
async def terminal_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for remote terminal access

    Spawns a shell process and provides bidirectional communication using text protocol.

    Client can send:
    - Raw text for shell input
    - "__RESIZE__:cols:rows" for terminal resize
    - "__AGENT__:enable" to enable agent parsing
    - "__AGENT__:disable" to disable agent parsing

    Server sends:
    - Raw text from shell output
    - "__AGENT__:event:{json}" for agent events (when enabled)
    """
    try:
        await websocket.accept()
        print("[TERMINAL] WebSocket connection accepted")  # DEBUG
        logger.info("Terminal WebSocket connection accepted")

        # Track agent parsing state
        agent_parsing_enabled = False
        agent_event_manager = None

        # Spawn shell process (agent parsing disabled by default)
        shell = PTYShell(cols=80, rows=24, enable_agent_parsing=False)

        try:
            shell.spawn()
            print(f"[TERMINAL] Shell spawned: PID={shell.pid}, FD={shell.master_fd}")  # DEBUG
            logger.info(f"Shell spawned successfully: PID={shell.pid}, FD={shell.master_fd}")
        except Exception as e:
            print(f"[TERMINAL] ERROR spawning shell: {e}")  # DEBUG
            logger.error(f"Failed to spawn shell: {e}", exc_info=True)
            await websocket.send_text(f"Failed to spawn shell: {str(e)}\r\n")
            await websocket.close()
            return
    except Exception as e:
        print(f"[TERMINAL] ERROR during initialization: {e}")  # DEBUG
        logger.error(f"Error during WebSocket initialization: {e}", exc_info=True)
        try:
            await websocket.close()
        except:
            pass
        return

    # Create queue for shell output
    output_queue: asyncio.Queue[str | None] = asyncio.Queue()

    # Get the event loop for thread-safe queue operations
    loop = asyncio.get_running_loop()

    # Create task for reading shell output
    async def read_output():
        """Read shell output and send to WebSocket"""
        def send_output(data: str):
            """Callback for shell output - runs in sync context"""
            try:
                # Validate loop is still running before queueing
                # This prevents errors when reconnecting after page reload
                if loop.is_running():
                    # Put data in queue (thread-safe)
                    loop.call_soon_threadsafe(output_queue.put_nowait, data)
                else:
                    logger.warning("Attempted to queue output to closed event loop")
            except Exception as e:
                logger.error(f"Error queueing output: {e}")

        await shell.read(send_output)

        # Shell exited - signal end with None
        logger.info("Shell process exited")
        try:
            if loop.is_running():
                loop.call_soon_threadsafe(output_queue.put_nowait, None)
        except Exception:
            pass

    # Start reading shell output
    print("[TERMINAL] Creating read task")  # DEBUG
    read_task = asyncio.create_task(read_output())
    print("[TERMINAL] Read task created")  # DEBUG

    try:
        # Send initial welcome message
        print("[TERMINAL] Sending welcome message")  # DEBUG
        await websocket.send_text("Connected to shell. Type commands.\r\n")
        print("[TERMINAL] Welcome message sent")  # DEBUG

        # Main event loop - handle both input and output
        while True:
            # Wait for either WebSocket message or shell output
            recv_task = asyncio.create_task(websocket.receive_text())
            pty_task = asyncio.create_task(output_queue.get())

            done, pending = await asyncio.wait(
                {recv_task, pty_task}, return_when=asyncio.FIRST_COMPLETED
            )

            # Handle shell output
            if pty_task in done:
                msg = pty_task.result()
                if msg is None:
                    # PTY closed - close WebSocket
                    if websocket.application_state == WebSocketState.CONNECTED:
                        await websocket.close()
                    break

                # Send shell output to client
                if websocket.application_state == WebSocketState.CONNECTED:
                    await websocket.send_text(msg)

            # Handle client input
            if recv_task in done:
                try:
                    raw = recv_task.result()

                    # Check for special protocols
                    if raw.startswith("__RESIZE__"):
                        try:
                            _, cols, rows = raw.split(":")
                            shell.resize(int(cols), int(rows))
                            logger.debug(f"Terminal resized to {cols}x{rows}")
                        except Exception as e:
                            logger.error(f"Error parsing resize command: {e}")

                    elif raw.startswith("__AGENT__"):
                        try:
                            parts = raw.split(":", 1)
                            if len(parts) > 1:
                                cmd = parts[1]
                                if cmd == "enable":
                                    # Enable agent parsing
                                    if not agent_parsing_enabled:
                                        agent_parsing_enabled = True
                                        shell.enable_agent_parsing = True

                                        # Create new parser and event manager
                                        from code_map.terminal.agent_parser import AgentOutputParser
                                        import uuid
                                        shell.agent_parser = AgentOutputParser()
                                        agent_event_manager = AgentEventManager(str(uuid.uuid4()))

                                        # Set callback to send events to WebSocket
                                        async def send_agent_event(event: AgentEvent):
                                            """Send agent event to WebSocket"""
                                            try:
                                                # Process event in manager
                                                await agent_event_manager.process_event(event)

                                                # Send event to client
                                                event_msg = f"__AGENT__:event:{event.to_json()}"
                                                if websocket.application_state == WebSocketState.CONNECTED:
                                                    await websocket.send_text(event_msg)
                                            except Exception as e:
                                                logger.error(f"Error sending agent event: {e}")

                                        # Wrap async callback for sync context
                                        def agent_event_callback(event: AgentEvent):
                                            """Sync wrapper for agent event callback"""
                                            if loop.is_running():
                                                loop.call_soon_threadsafe(
                                                    lambda: asyncio.create_task(send_agent_event(event))
                                                )

                                        shell.set_agent_event_callback(agent_event_callback)
                                        logger.info("Agent parsing enabled")

                                        # Send confirmation
                                        if websocket.application_state == WebSocketState.CONNECTED:
                                            await websocket.send_text("__AGENT__:status:enabled\r\n")

                                elif cmd == "disable":
                                    # Disable agent parsing
                                    agent_parsing_enabled = False
                                    shell.enable_agent_parsing = False
                                    shell.agent_parser = None
                                    shell.agent_event_callback = None
                                    agent_event_manager = None
                                    logger.info("Agent parsing disabled")

                                    # Send confirmation
                                    if websocket.application_state == WebSocketState.CONNECTED:
                                        await websocket.send_text("__AGENT__:status:disabled\r\n")

                                elif cmd == "summary" and agent_event_manager:
                                    # Send current session summary
                                    summary = agent_event_manager.get_state_summary()
                                    summary_msg = f"__AGENT__:summary:{json.dumps(summary)}"
                                    if websocket.application_state == WebSocketState.CONNECTED:
                                        await websocket.send_text(summary_msg)

                        except Exception as e:
                            logger.error(f"Error handling agent command: {e}")

                    else:
                        # Regular input - send to shell
                        shell.write(raw)

                except WebSocketDisconnect:
                    logger.info("WebSocket disconnected")
                    break

            # Cancel pending tasks
            for task in pending:
                task.cancel()

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"Error in terminal session: {e}", exc_info=True)
    finally:
        # Cleanup - proper order to prevent race conditions
        logger.info("Cleaning up terminal session")

        # 1. Stop the shell (sets running = False, but don't wait for thread yet)
        shell.running = False

        # 2. Cancel the read task immediately
        read_task.cancel()

        try:
            await read_task
        except asyncio.CancelledError:
            pass

        # 3. Now clean up shell resources (including thread join in executor to avoid blocking)
        import concurrent.futures
        loop = asyncio.get_running_loop()
        try:
            # Run blocking shell.close() in thread pool to avoid blocking event loop
            await loop.run_in_executor(None, shell.close)
        except Exception as e:
            logger.error(f"Error during shell cleanup: {e}")

        # 4. Close WebSocket last
        try:
            if websocket.application_state == WebSocketState.CONNECTED:
                await websocket.close()
        except Exception:
            pass


@router.websocket("/ws/agent")
async def agent_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for Claude Code JSON streaming mode

    Uses `claude -p --output-format stream-json --verbose` to get structured
    output instead of TUI rendering. Supports bidirectional communication for
    interactive permission handling.

    Client sends JSON commands:
    - {"command": "run", "prompt": "...", "continue": true}
    - {"command": "cancel"}
    - {"command": "new_session"}
    - {"command": "permission_response", "approved": true, "always": false}

    Server sends JSON events:
    - {"type": "system", "subtype": "init", ...}
    - {"type": "assistant", "subtype": "text", "content": "..."}
    - {"type": "assistant", "subtype": "tool_use", "content": {...}}
    - {"type": "user", "subtype": "tool_result", "content": {...}}
    - {"type": "permission_request", "tool": "...", "input": {...}, "request_id": "..."}
    - {"type": "done"}
    - {"type": "error", "content": "..."}
    """
    await websocket.accept()
    logger.info("Agent WebSocket connection accepted")

    # Load settings to get root path
    settings = load_settings()
    cwd = str(settings.root_path)

    # Initialize parser and runner
    parser = JSONStreamParser()
    runner: ClaudeAgentRunner | None = None
    continue_session = True  # Default: continue last session

    # Permission request handling state
    pending_permission_future: asyncio.Future | None = None
    pending_permission_id: str | None = None

    # MCP approval mode state (using dict to avoid nonlocal issues)
    mcp_state = {"socket_server": None, "using_mcp": False}

    async def send_event(event_data: dict):
        """Send parsed event to WebSocket"""
        try:
            parsed = parser.parse_line(json.dumps(event_data))
            if parsed:
                # print(f"DEBUG: Sending parsed event to WS: {parsed.to_dict().get('type')}")
                await websocket.send_json(parsed.to_dict())
            else:
                # Send raw event if parsing fails
                print(f"DEBUG: Sending raw event to WS: {event_data.get('type')}")
                await websocket.send_json(event_data)
        except Exception as e:
            logger.error(f"Error sending event: {e}")

    async def send_error(message: str):
        """Send error event to WebSocket"""
        try:
            await websocket.send_json({
                "type": "error",
                "content": message
            })
        except Exception as e:
            logger.error(f"Error sending error message: {e}")

    async def send_done():
        """Send done event to WebSocket"""
        try:
            await websocket.send_json({"type": "done"})
        except Exception as e:
            logger.error(f"Error sending done message: {e}")

    async def handle_permission_request(event: dict) -> dict:
        """
        Handle permission request from Claude by forwarding to frontend
        and waiting for user response.

        Returns dict with 'approved' and optionally 'always' keys.
        """
        nonlocal pending_permission_future, pending_permission_id

        # Generate unique request ID
        import uuid
        request_id = str(uuid.uuid4())
        pending_permission_id = request_id

        # Extract tool info from the event
        tool_name = "unknown"
        tool_input = {}

        if event.get("type") == "assistant" and event.get("subtype") == "tool_use":
            content = event.get("content", {})
            if isinstance(content, dict):
                tool_name = content.get("name", "unknown")
                tool_input = content.get("input", {})

        # Send permission request to frontend
        permission_event = {
            "type": "permission_request",
            "request_id": request_id,
            "tool": tool_name,
            "input": tool_input,
            "raw_event": event
        }

        logger.info(f"Sending permission request to frontend: {tool_name} (id={request_id})")

        try:
            await websocket.send_json(permission_event)
        except Exception as e:
            logger.error(f"Error sending permission request: {e}")
            return {"approved": False}

        # Create future to wait for response
        pending_permission_future = asyncio.get_event_loop().create_future()

        try:
            # Wait for response (with timeout)
            response = await asyncio.wait_for(pending_permission_future, timeout=300.0)
            logger.info(f"Permission response received: {response}")
            return response
        except asyncio.TimeoutError:
            logger.warning(f"Permission request timed out: {request_id}")
            return {"approved": False}
        finally:
            pending_permission_future = None
            pending_permission_id = None

    try:
        # Send connected confirmation
        await websocket.send_json({
            "type": "connected",
            "cwd": cwd
        })

        # Create task for running prompts (so we can handle permission responses concurrently)
        run_task: asyncio.Task | None = None

        while True:
            try:
                # Wait for command from client
                raw_message = await websocket.receive_text()
                message = json.loads(raw_message)
                command = message.get("command")
                print(f"DEBUG: Received WS command: {command}")

                if command == "run":
                    prompt = message.get("prompt", "")
                    if not prompt:
                        await send_error("Empty prompt")
                        continue

                    # Get permission mode (default, acceptEdits, bypassPermissions, dontAsk, plan, mcpApproval, sdk)
                    permission_mode = message.get("permission_mode", "default")

                    # Extended modes include SDK mode and mcpProxy
                    EXTENDED_MODES = PERMISSION_MODES + ("sdk", "mcpProxy")
                    if permission_mode not in EXTENDED_MODES:
                        logger.warning(f"Invalid permission mode: {permission_mode}, using default")
                        permission_mode = "default"

                    # Check if should continue session
                    should_continue = message.get("continue", continue_session)

                    # ========================================================
                    # SDK MODE: Use Anthropic SDK directly for full tool control
                    # ========================================================
                    if permission_mode == "sdk":
                        logger.info("SDK mode: using Anthropic SDK with tool interception")

                        # SDK mode always uses fresh sessions (conversation history managed internally)
                        sdk_config = SDKRunnerConfig(
                            cwd=cwd,
                            auto_approve_read=message.get("auto_approve_safe", True),
                        )
                        sdk_runner = SDKAgentRunner(sdk_config)

                        # Store SDK runner for approval responses
                        # We use a mutable container to allow nested function access
                        sdk_state = {"runner": sdk_runner}

                        # Handler for SDK tool approval requests
                        async def handle_sdk_tool_approval(request):
                            """Send SDK tool approval request to frontend"""
                            print(f"DEBUG: [SDK] Tool approval request for {request.tool_name}", flush=True)
                            try:
                                approval_event = {
                                    "type": "tool_approval_request",
                                    "request_id": request.request_id,
                                    "tool_name": request.tool_name,
                                    "tool_input": request.tool_input,
                                    "tool_use_id": request.tool_use_id,
                                    "preview_type": request.preview_type,
                                    "preview_data": request.preview_data,
                                    "file_path": request.file_path,
                                    "original_content": request.original_content,
                                    "new_content": request.new_content,
                                    "diff_lines": request.diff_lines,
                                }
                                await websocket.send_json(approval_event)
                                logger.info(f"SDK tool approval request sent: {request.tool_name}")
                            except Exception as e:
                                logger.error(f"Error sending SDK tool approval request: {e}")

                        # Run SDK prompt
                        async def run_sdk_prompt_task():
                            nonlocal runner
                            # Store runner reference for approval responses
                            runner = sdk_state["runner"]

                            exit_code = await sdk_runner.run_prompt(
                                prompt=prompt,
                                on_event=send_event,
                                on_error=send_error,
                                on_done=send_done,
                                on_tool_approval_request=handle_sdk_tool_approval,
                            )
                            logger.info(f"SDK prompt completed with exit code {exit_code}")

                        run_task = asyncio.create_task(run_sdk_prompt_task())
                        continue  # Skip the CLI runner code below

                    # ========================================================
                    # MCP PROXY MODE: Claude CLI with MCP tool proxy for approval
                    # Uses user's Claude CLI subscription - no separate API key needed
                    # ========================================================
                    if permission_mode == "mcpProxy":
                        logger.info("mcpProxy mode: using MCP tool proxy for approval")

                        # Set up the MCP socket server to receive approval requests
                        mcp_state["using_mcp"] = True
                        mcp_state["socket_server"] = await get_or_create_mcp_socket_server(cwd)

                        # Set the frontend callback for approval requests
                        async def send_mcp_proxy_approval_request(request: ApprovalRequest):
                            """Forward MCP proxy approval request to frontend via WebSocket"""
                            print(f"DEBUG: [mcpProxy] Approval request for {request.tool_name}", flush=True)
                            print(f"DEBUG: [mcpProxy] request_id={request.request_id}, file_path={request.file_path}", flush=True)
                            try:
                                approval_event = {
                                    "type": "tool_approval_request",
                                    "request_id": request.request_id,
                                    "tool_name": request.tool_name,
                                    "tool_input": request.tool_input,
                                    # Use request_id as tool_use_id since MCP proxy doesn't have real tool_use_id
                                    "tool_use_id": request.request_id,
                                    "context": request.context,
                                    "preview_type": request.preview_type,
                                    "preview_data": request.preview_data,
                                    "file_path": request.file_path,
                                    "original_content": request.original_content,
                                    "new_content": request.new_content,
                                    "diff_lines": request.diff_lines,
                                }
                                print(f"DEBUG: [mcpProxy] Sending approval_event to WebSocket...", flush=True)
                                await websocket.send_json(approval_event)
                                print(f"DEBUG: [mcpProxy] approval_event SENT successfully", flush=True)
                                logger.info(f"MCP proxy approval request sent: {request.tool_name}")
                            except Exception as e:
                                print(f"DEBUG: [mcpProxy] EXCEPTION sending approval_event: {e}", flush=True)
                                logger.error(f"Error sending MCP proxy approval request: {e}")
                                raise

                        mcp_state["socket_server"].set_frontend_callback(send_mcp_proxy_approval_request)

                        # Create the MCP proxy runner
                        mcp_proxy_config = MCPProxyRunnerConfig(
                            cwd=cwd,
                            continue_session=message.get("continue", True),
                            verbose=True,
                            socket_path=DEFAULT_SOCKET_PATH,
                        )
                        mcp_proxy_runner = MCPProxyRunner(mcp_proxy_config)

                        # Run the prompt with MCP proxy
                        async def run_mcp_proxy_prompt_task():
                            nonlocal runner
                            runner = mcp_proxy_runner  # Store for cancel support

                            exit_code = await mcp_proxy_runner.run_prompt(
                                prompt=prompt,
                                on_event=send_event,
                                on_error=send_error,
                                on_done=send_done,
                            )
                            logger.info(f"MCP proxy prompt completed with exit code {exit_code}")

                        run_task = asyncio.create_task(run_mcp_proxy_prompt_task())
                        continue  # Skip the CLI runner code below

                    # ========================================================
                    # CLI MODES: Use Claude CLI subprocess
                    # ========================================================

                    # IMPORTANT: In toolApproval mode, we execute tools locally after
                    # Claude exits. This means Claude's session state doesn't match reality.
                    # To avoid "unexpected tool_use_id in tool_result" errors, we MUST
                    # start a fresh session each time in toolApproval mode.
                    if permission_mode == "toolApproval":
                        logger.info("toolApproval mode: forcing new session to avoid state mismatch")
                        should_continue = False

                    # Setup MCP approval mode if selected
                    if permission_mode == "mcpApproval":
                        logger.info("mcpApproval mode: setting up MCP socket server")
                        mcp_state["using_mcp"] = True

                        # Get or create the global MCP socket server
                        mcp_state["socket_server"] = await get_or_create_mcp_socket_server(cwd)

                        # Set the frontend callback to forward approval requests via WebSocket
                        async def send_mcp_approval_request(request: ApprovalRequest):
                            """Forward MCP approval request to frontend via WebSocket"""
                            print(f"DEBUG: [send_mcp_approval_request] ENTERED for {request.tool_name}", flush=True)
                            try:
                                approval_event = {
                                    "type": "mcp_approval_request",
                                    "request_id": request.request_id,
                                    "tool_name": request.tool_name,
                                    "tool_input": request.tool_input,
                                    "context": request.context,
                                    "preview_type": request.preview_type,
                                    "preview_data": request.preview_data,
                                    "file_path": request.file_path,
                                    "original_content": request.original_content,
                                    "new_content": request.new_content,
                                    "diff_lines": request.diff_lines,
                                }
                                print(f"DEBUG: [send_mcp_approval_request] Sending to WebSocket...", flush=True)
                                await websocket.send_json(approval_event)
                                print(f"DEBUG: [send_mcp_approval_request] WebSocket message SENT", flush=True)
                                logger.info(f"MCP approval request sent to frontend: {request.tool_name}")
                            except Exception as e:
                                print(f"DEBUG: [send_mcp_approval_request] EXCEPTION: {e}", flush=True)
                                logger.error(f"Error sending MCP approval request: {e}")
                                raise

                        mcp_state["socket_server"].set_frontend_callback(send_mcp_approval_request)

                    # Create runner with current settings
                    config = ClaudeRunnerConfig(
                        cwd=cwd,
                        continue_session=should_continue,
                        verbose=True,
                        permission_mode=permission_mode,
                        auto_approve_safe_tools=message.get("auto_approve_safe", False),
                        mcp_socket_path=DEFAULT_SOCKET_PATH if permission_mode == "mcpApproval" else "",
                    )
                    runner = ClaudeAgentRunner(config)

                    # Reset parser for potentially new session
                    if not should_continue:
                        parser.reset()

                    logger.info(f"Running prompt (continue={should_continue}, permission_mode={permission_mode}): {prompt[:50]}...")

                    # Handler for tool approval requests (toolApproval mode)
                    async def handle_tool_approval_request(request):
                        """Send tool approval request to frontend"""
                        print(f"DEBUG: [handle_tool_approval_request] ENTERED for {request.tool_name}", flush=True)
                        try:
                            approval_event = {
                                "type": "tool_approval_request",
                                "request_id": request.request_id,
                                "tool_name": request.tool_name,
                                "tool_input": request.tool_input,
                                "tool_use_id": request.tool_use_id,
                                "preview_type": request.preview_type,
                                "preview_data": request.preview_data,
                                "file_path": request.file_path,
                                "original_content": request.original_content,
                                "new_content": request.new_content,
                                "diff_lines": request.diff_lines,
                            }
                            print(f"DEBUG: [handle_tool_approval_request] About to send WebSocket message...", flush=True)
                            await websocket.send_json(approval_event)
                            print(f"DEBUG: [handle_tool_approval_request] WebSocket message SENT for {request.tool_name}", flush=True)
                            logger.info(f"Tool approval request sent: {request.tool_name}")
                        except Exception as e:
                            print(f"DEBUG: [handle_tool_approval_request] EXCEPTION: {e}", flush=True)
                            logger.error(f"Error sending tool approval request: {e}")

                    # Run the prompt in a task so we can handle permission responses
                    async def run_prompt_task():
                        nonlocal continue_session
                        exit_code = await runner.run_prompt(
                            prompt=prompt,
                            on_event=send_event,
                            on_error=send_error,
                            on_done=send_done,
                            on_permission_request=handle_permission_request,
                            on_tool_approval_request=handle_tool_approval_request,
                        )
                        logger.info(f"Prompt completed with exit code {exit_code}")

                        # Check if session is broken (tools executed locally in plan mode)
                        # If so, tell frontend to NOT continue the session next time
                        if runner.session_broken:
                            logger.info("Session broken due to local tool execution, notifying frontend")
                            try:
                                await websocket.send_json({
                                    "type": "session_broken",
                                    "reason": "Tools were executed locally after Claude exited. Start a new session for the next prompt.",
                                })
                            except Exception as e:
                                logger.error(f"Error sending session_broken event: {e}")
                            # Also reset local continue_session flag
                            continue_session = False

                    run_task = asyncio.create_task(run_prompt_task())

                elif command == "permission_response":
                    # Handle permission response from frontend
                    if pending_permission_future and not pending_permission_future.done():
                        response = {
                            "approved": message.get("approved", False),
                            "always": message.get("always", False)
                        }
                        pending_permission_future.set_result(response)
                        logger.info(f"Permission response set: {response}")
                    else:
                        logger.warning("Received permission_response but no pending request")

                elif command == "tool_approval_response":
                    # Handle tool approval response from frontend
                    # Works for both toolApproval mode (via runner) and mcpProxy mode (via socket server)
                    request_id = message.get("request_id", "")
                    approved = message.get("approved", False)
                    feedback = message.get("feedback", "")

                    print(f"DEBUG: tool_approval_response: request_id={request_id}, approved={approved}, mcp_using={mcp_state['using_mcp']}", flush=True)

                    # Try mcpProxy mode first (via socket server)
                    if mcp_state["using_mcp"] and mcp_state["socket_server"]:
                        print(f"DEBUG: Using MCP socket server for approval response", flush=True)
                        success = mcp_state["socket_server"].respond_to_approval(
                            request_id=request_id,
                            approved=approved,
                            message=feedback,
                            updated_input=None,
                        )
                        if success:
                            logger.info(f"Tool approval response (mcpProxy) processed: approved={approved}")
                            print(f"DEBUG: Tool approval response (mcpProxy) processed successfully", flush=True)
                        else:
                            logger.warning(f"Tool approval response (mcpProxy) failed: request_id={request_id}")
                            print(f"DEBUG: Tool approval response (mcpProxy) FAILED for request_id={request_id}", flush=True)

                    # Fallback to toolApproval mode (via runner)
                    elif runner and hasattr(runner, 'respond_to_tool_approval'):
                        print(f"DEBUG: Using runner for approval response", flush=True)
                        success = runner.respond_to_tool_approval(request_id, approved, feedback)
                        if success:
                            logger.info(f"Tool approval response processed: approved={approved}")
                            print(f"DEBUG: Tool approval response processed successfully")
                        else:
                            logger.warning(f"Tool approval response failed: request_id={request_id}")
                            print(f"DEBUG: Tool approval response FAILED for request_id={request_id}")
                    else:
                        logger.warning("Received tool_approval_response but no handler available")
                        print(f"DEBUG: No handler for tool_approval_response! mcp_using={mcp_state['using_mcp']}, runner={runner}", flush=True)

                elif command == "mcp_approval_response":
                    # Handle MCP approval response from frontend (mcpApproval mode)
                    if mcp_state["socket_server"]:
                        request_id = message.get("request_id", "")
                        approved = message.get("approved", False)
                        user_message = message.get("message", "")
                        updated_input = message.get("updated_input")

                        print(f"DEBUG: MCP approval response: request_id={request_id}, approved={approved}", flush=True)

                        success = mcp_state["socket_server"].respond_to_approval(
                            request_id=request_id,
                            approved=approved,
                            message=user_message,
                            updated_input=updated_input,
                        )

                        if success:
                            logger.info(f"MCP approval response processed: approved={approved}")
                            print(f"DEBUG: MCP approval response processed successfully")
                        else:
                            logger.warning(f"MCP approval response failed: request_id={request_id}")
                            print(f"DEBUG: MCP approval response FAILED for request_id={request_id}")
                    else:
                        logger.warning("Received mcp_approval_response but no MCP socket server")
                        print(f"DEBUG: MCP approval response but no socket server!")

                elif command == "cancel":
                    if runner and runner.is_running:
                        await runner.cancel()
                        await websocket.send_json({
                            "type": "cancelled"
                        })
                    else:
                        await websocket.send_json({
                            "type": "cancelled",
                            "note": "No running process"
                        })

                elif command == "new_session":
                    # Mark next run as new session
                    continue_session = False
                    parser.reset()
                    await websocket.send_json({
                        "type": "session_reset"
                    })

                elif command == "status":
                    # Return current session info
                    await websocket.send_json({
                        "type": "status",
                        "session_info": parser.get_session_info(),
                        "running": runner.is_running if runner else False,
                        "continue_session": continue_session
                    })

                else:
                    await send_error(f"Unknown command: {command}")

            except json.JSONDecodeError as e:
                await send_error(f"Invalid JSON: {e}")

    except WebSocketDisconnect:
        logger.info("Agent WebSocket disconnected")
    except Exception as e:
        logger.error(f"Error in agent session: {e}", exc_info=True)
    finally:
        # Cleanup
        if runner and runner.is_running:
            await runner.cancel()

        try:
            if websocket.application_state == WebSocketState.CONNECTED:
                await websocket.close()
        except Exception:
            pass

        logger.info("Agent session cleaned up")


@router.websocket("/ws/agent-pty")
async def agent_pty_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for Claude Code PTY mode with real terminal interaction.

    This mode spawns Claude in a pseudo-terminal (PTY) for proper Ink UI support,
    parses the terminal output into structured events, and enables real tool approval
    by detecting permission prompts in the output.

    Client sends JSON commands:
    - {"command": "start"} - Start a new PTY session
    - {"command": "run", "prompt": "..."} - Send a prompt to Claude
    - {"command": "approve"} - Approve a pending permission (send 'y')
    - {"command": "deny"} - Deny a pending permission (send 'n')
    - {"command": "always_allow"} - Always allow this permission (send 'a')
    - {"command": "cancel"} - Cancel current operation (send Ctrl+C)
    - {"command": "stop"} - Stop the PTY session

    Server sends JSON events:
    - {"type": "session_started"}
    - {"type": "thinking", "data": {...}}
    - {"type": "completion", "data": {...}}
    - {"type": "permission_request", "data": {...}}
    - {"type": "message", "data": {...}}
    - {"type": "error", "data": {...}}
    - {"type": "session_ended"}
    """
    await websocket.accept()
    logger.info("Agent PTY WebSocket connection accepted")

    # Load settings to get root path
    settings = load_settings()
    cwd = str(settings.root_path)

    # PTY runner instance
    runner: PTYClaudeRunner | None = None

    # Pending permission state
    pending_permission: dict | None = None

    async def send_event(event: dict):
        """Send event to WebSocket"""
        try:
            if websocket.application_state == WebSocketState.CONNECTED:
                await websocket.send_json(event)
        except Exception as e:
            logger.error(f"Error sending event: {e}")

    async def handle_permission_request(event: dict) -> asyncio.Future:
        """
        Handle permission request by forwarding to frontend.
        Returns a Future that will be resolved when user responds.
        """
        nonlocal pending_permission

        # Store pending permission info
        pending_permission = {
            "event": event,
            "future": asyncio.get_event_loop().create_future(),
        }

        # Send to frontend
        await send_event({
            "type": "permission_request",
            "data": event.get("data", {}),
            "raw_text": event.get("raw_text", ""),
        })

        return pending_permission["future"]

    try:
        # Send connected confirmation
        await websocket.send_json({
            "type": "connected",
            "cwd": cwd,
            "mode": "pty"
        })

        while True:
            try:
                # Wait for command from client
                raw_message = await websocket.receive_text()
                message = json.loads(raw_message)
                command = message.get("command")
                logger.debug(f"PTY WebSocket received command: {command}")

                if command == "start":
                    # Start PTY session
                    logger.info("PTY WebSocket: start command received")
                    print(f"DEBUG: PTY start command received, cwd={cwd}", flush=True)

                    if runner is not None:
                        await runner.stop_session()

                    config = PTYRunnerConfig(
                        working_directory=cwd,
                        timeout=message.get("timeout", 300.0),
                        init_wait=message.get("init_wait", 5.0),
                    )
                    runner = PTYClaudeRunner(config)

                    # Set event callback
                    runner.set_event_callback(lambda e: asyncio.create_task(send_event(e)))

                    # Set permission callback
                    runner.set_permission_callback(handle_permission_request)

                    # Start session
                    logger.info("PTY: Calling start_session()...")
                    success = await runner.start_session()
                    logger.info(f"PTY: start_session() returned success={success}")

                    if success:
                        logger.info("PTY: Sending session_started event")
                        await send_event({"type": "session_started"})
                        logger.info("PTY: session_started event sent")
                    else:
                        logger.warning("PTY: Sending session failed error")
                        await send_event({
                            "type": "error",
                            "content": "Failed to start PTY session"
                        })

                elif command == "run":
                    # Send prompt to Claude
                    if runner is None or not runner.is_running:
                        await send_event({
                            "type": "error",
                            "content": "No active PTY session. Send 'start' first."
                        })
                        continue

                    prompt = message.get("prompt", "")
                    if not prompt:
                        await send_event({
                            "type": "error",
                            "content": "Empty prompt"
                        })
                        continue

                    logger.info(f"PTY running prompt: {prompt[:50]}...")

                    # Run prompt and stream events
                    try:
                        async for event in runner.send_prompt(prompt):
                            await send_event(event)
                    except Exception as e:
                        logger.error(f"Error running prompt: {e}")
                        await send_event({
                            "type": "error",
                            "content": str(e)
                        })

                    # Send done event
                    await send_event({"type": "done"})

                elif command == "approve":
                    # Approve pending permission
                    if pending_permission and not pending_permission["future"].done():
                        pending_permission["future"].set_result({
                            "approved": True,
                            "always": False,
                        })
                        pending_permission = None
                        logger.info("Permission approved")
                    elif runner and runner._process:
                        # Direct key send if no pending future
                        runner._process.send('y')
                        logger.info("Sent 'y' key directly")

                elif command == "deny":
                    # Deny pending permission
                    if pending_permission and not pending_permission["future"].done():
                        pending_permission["future"].set_result({
                            "approved": False,
                        })
                        pending_permission = None
                        logger.info("Permission denied")
                    elif runner and runner._process:
                        # Direct key send
                        runner._process.send('n')
                        logger.info("Sent 'n' key directly")

                elif command == "always_allow":
                    # Always allow permission
                    if pending_permission and not pending_permission["future"].done():
                        pending_permission["future"].set_result({
                            "approved": True,
                            "always": True,
                        })
                        pending_permission = None
                        logger.info("Permission always allowed")
                    elif runner and runner._process:
                        # Direct key send
                        runner._process.send('a')
                        logger.info("Sent 'a' key directly")

                elif command == "cancel":
                    # Send Ctrl+C to cancel
                    if runner and runner._process:
                        runner._process.sendcontrol('c')
                        logger.info("Sent Ctrl+C to cancel")
                        await send_event({"type": "cancelled"})

                elif command == "stop":
                    # Stop PTY session
                    if runner:
                        await runner.stop_session()
                        runner = None
                    await send_event({"type": "session_ended"})

                elif command == "status":
                    # Return current status
                    await send_event({
                        "type": "status",
                        "data": {
                            "running": runner is not None and runner.is_running,
                            "state": runner.state.value if runner else "idle",
                            "has_pending_permission": pending_permission is not None,
                        }
                    })

                else:
                    await send_event({
                        "type": "error",
                        "content": f"Unknown command: {command}"
                    })

            except json.JSONDecodeError as e:
                await send_event({
                    "type": "error",
                    "content": f"Invalid JSON: {e}"
                })

    except WebSocketDisconnect:
        logger.info("Agent PTY WebSocket disconnected")
    except Exception as e:
        logger.error(f"Error in agent PTY session: {e}", exc_info=True)
    finally:
        # Cleanup
        if runner:
            await runner.stop_session()

        try:
            if websocket.application_state == WebSocketState.CONNECTED:
                await websocket.close()
        except Exception:
            pass

        logger.info("Agent PTY session cleaned up")


@router.websocket("/ws/gemini-agent")
async def gemini_agent_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for Gemini Code JSON streaming mode
    """
    await websocket.accept()
    logger.info("Gemini Agent WebSocket connection accepted")

    settings = load_settings()
    cwd = str(settings.root_path)

    parser = JSONStreamParser()
    runner: GeminiAgentRunner | None = None
    
    async def send_event(event_data: dict):
        """Send parsed event to WebSocket"""
        try:
            await websocket.send_json(event_data)
        except Exception as e:
            logger.error(f"Error sending event: {e}")

    async def send_error(message: str):
        await websocket.send_json({
            "type": "error",
            "content": message
        })

    async def send_done():
        await websocket.send_json({"type": "done"})

    async def handle_tool_approval_request(request):
        """Send tool approval request to frontend"""
        try:
            approval_event = {
                "type": "tool_approval_request",
                "request_id": request.request_id,
                "tool_name": request.tool_name,
                "tool_input": request.tool_input,
                "tool_use_id": request.tool_use_id,
                "preview_type": request.preview_type,
                "preview_data": request.preview_data,
                "file_path": request.file_path,
                "original_content": request.original_content,
                "new_content": request.new_content,
                "diff_lines": request.diff_lines,
            }
            await websocket.send_json(approval_event)
        except Exception as e:
            logger.error(f"Error sending tool approval request: {e}")

    try:
        await websocket.send_json({
            "type": "connected",
            "cwd": cwd
        })

        while True:
            try:
                raw_message = await websocket.receive_text()
                message = json.loads(raw_message)
                command = message.get("command")

                if command == "run":
                    prompt = message.get("prompt", "")
                    if not prompt:
                        await send_error("Empty prompt")
                        continue

                    permission_mode = message.get("permission_mode", "default")
                    
                    config = GeminiRunnerConfig(
                        cwd=cwd,
                        permission_mode=permission_mode,
                        auto_approve_safe_tools=message.get("auto_approve_safe", False),
                    )
                    runner = GeminiAgentRunner(config)

                    # Run prompt in task
                    asyncio.create_task(runner.run_prompt(
                        prompt=prompt,
                        on_event=send_event,
                        on_error=send_error,
                        on_done=send_done,
                        on_tool_approval_request=handle_tool_approval_request,
                    ))

                elif command == "tool_approval_response":
                    if runner:
                        request_id = message.get("request_id", "")
                        approved = message.get("approved", False)
                        feedback = message.get("feedback")
                        
                        runner.respond_to_tool_approval(request_id, approved, feedback)

                elif command == "cancel":
                    if runner:
                        await runner.cancel()
                        await websocket.send_json({"type": "cancelled"})

            except json.JSONDecodeError as e:
                await send_error(f"Invalid JSON: {e}")

    except WebSocketDisconnect:
        logger.info("Gemini Agent WebSocket disconnected")
    except Exception as e:
        logger.error(f"Error in Gemini agent session: {e}", exc_info=True)
    finally:
        if runner:
            await runner.cancel()
