"""
Terminal API endpoints

Provides WebSocket endpoints for:
- /ws: Remote terminal access (PTY shell)
- /ws/agent: Claude Code JSON streaming mode
"""

import asyncio
import logging
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from code_map.terminal import PTYShell
from code_map.terminal.agent_parser import AgentEvent
from code_map.terminal.agent_events import AgentEventManager
from code_map.terminal.claude_runner import ClaudeAgentRunner, ClaudeRunnerConfig
from code_map.terminal.json_parser import JSONStreamParser
from code_map.settings import load_settings

logger = logging.getLogger(__name__)

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
    output instead of TUI rendering.

    Client sends JSON commands:
    - {"command": "run", "prompt": "...", "continue": true}
    - {"command": "cancel"}
    - {"command": "new_session"}

    Server sends JSON events:
    - {"type": "system", "subtype": "init", ...}
    - {"type": "assistant", "subtype": "text", "content": "..."}
    - {"type": "assistant", "subtype": "tool_use", "content": {...}}
    - {"type": "user", "subtype": "tool_result", "content": {...}}
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

    async def send_event(event_data: dict):
        """Send parsed event to WebSocket"""
        try:
            parsed = parser.parse_line(json.dumps(event_data))
            if parsed:
                await websocket.send_json(parsed.to_dict())
            else:
                # Send raw event if parsing fails
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

    try:
        # Send connected confirmation
        await websocket.send_json({
            "type": "connected",
            "cwd": cwd
        })

        while True:
            try:
                # Wait for command from client
                raw_message = await websocket.receive_text()
                message = json.loads(raw_message)
                command = message.get("command")

                if command == "run":
                    prompt = message.get("prompt", "")
                    if not prompt:
                        await send_error("Empty prompt")
                        continue

                    # Check if should continue session
                    should_continue = message.get("continue", continue_session)

                    # Create runner with current settings
                    config = ClaudeRunnerConfig(
                        cwd=cwd,
                        continue_session=should_continue,
                        verbose=True
                    )
                    runner = ClaudeAgentRunner(config)

                    # Reset parser for potentially new session
                    if not should_continue:
                        parser.reset()

                    logger.info(f"Running prompt (continue={should_continue}): {prompt[:50]}...")

                    # Run the prompt and stream events
                    exit_code = await runner.run_prompt(
                        prompt=prompt,
                        on_event=send_event,
                        on_error=send_error,
                        on_done=send_done
                    )

                    logger.info(f"Prompt completed with exit code {exit_code}")

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
