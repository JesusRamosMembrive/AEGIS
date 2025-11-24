import { useState, useRef, useEffect } from "react";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import { WebLinksAddon } from "@xterm/addon-web-links";
import { useAgentStreamingTask } from "../api/agentClient";

interface AgentControlPanelProps {
  /** Contexto adicional para el agente */
  context?: Record<string, any>;
  /** Run ID de audit trail (opcional) */
  runId?: number;
}

/**
 * Panel de control interactivo para ejecutar tareas con Claude
 *
 * Permite:
 * - Escribir prompts/comandos
 * - Ver respuestas en tiempo real en terminal
 * - Controlar ejecución (pause/resume/cancel)
 * - Historial de comandos
 */
export function AgentControlPanel({ context, runId }: AgentControlPanelProps) {
  const [prompt, setPrompt] = useState("");
  const [commandHistory, setCommandHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);

  const terminalRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<Terminal | null>(null);

  const {
    execute,
    pause,
    resume,
    cancel,
    response,
    status,
    error,
    taskId,
  } = useAgentStreamingTask();

  // Inicializar terminal
  useEffect(() => {
    if (!terminalRef.current || xtermRef.current) return;

    const terminal = new Terminal({
      cursorBlink: false,
      disableStdin: true,
      fontSize: 14,
      fontFamily: '"JetBrains Mono", "Fira Code", monospace',
      theme: {
        background: "#0a0e18",
        foreground: "#e2e8f0",
        cursor: "#3b82f6",
        black: "#1e293b",
        red: "#ef4444",
        green: "#10b981",
        yellow: "#f59e0b",
        blue: "#3b82f6",
        magenta: "#a855f7",
        cyan: "#06b6d4",
        white: "#f1f5f9",
        brightBlack: "#475569",
        brightRed: "#f87171",
        brightGreen: "#34d399",
        brightYellow: "#fbbf24",
        brightBlue: "#60a5fa",
        brightMagenta: "#c084fc",
        brightCyan: "#22d3ee",
        brightWhite: "#ffffff",
      },
      rows: 25,
      scrollback: 10000,
    });

    const fitAddon = new FitAddon();
    const webLinksAddon = new WebLinksAddon();

    terminal.loadAddon(fitAddon);
    terminal.loadAddon(webLinksAddon);

    terminal.open(terminalRef.current);
    fitAddon.fit();

    // Mensaje de bienvenida
    terminal.writeln("\x1b[1;36m╔═══════════════════════════════════════════════════════╗\x1b[0m");
    terminal.writeln("\x1b[1;36m║\x1b[0m    \x1b[1;33mATLAS Agent Control Terminal\x1b[0m                    \x1b[1;36m║\x1b[0m");
    terminal.writeln("\x1b[1;36m╚═══════════════════════════════════════════════════════╝\x1b[0m");
    terminal.writeln("");
    terminal.writeln("\x1b[2mWrite your prompt below and press Enter or click 'Execute'\x1b[0m");
    terminal.writeln("\x1b[2mUse Ctrl+↑/↓ to navigate command history\x1b[0m");
    terminal.writeln("");

    xtermRef.current = terminal;

    return () => {
      terminal.dispose();
    };
  }, []);

  // Escribir respuesta en terminal a medida que llega
  const lastResponseLengthRef = useRef(0);
  useEffect(() => {
    if (!xtermRef.current || !response) return;

    const terminal = xtermRef.current;
    const newContent = response.slice(lastResponseLengthRef.current);

    if (newContent) {
      // Escribir nuevo contenido
      terminal.write(newContent.replace(/\n/g, "\r\n"));
      lastResponseLengthRef.current = response.length;
    }
  }, [response]);

  // Escribir errores en terminal
  useEffect(() => {
    if (!xtermRef.current || !error) return;

    const terminal = xtermRef.current;
    terminal.writeln("");
    terminal.writeln(`\x1b[1;31m✗ Error:\x1b[0m ${error}`);
    terminal.writeln("");
  }, [error]);

  // Manejar envío de prompt
  const handleExecute = async () => {
    if (!prompt.trim() || status === "running") return;

    const terminal = xtermRef.current;
    if (!terminal) return;

    // Añadir al historial
    setCommandHistory((prev) => [...prev, prompt]);
    setHistoryIndex(-1);

    // Mostrar prompt en terminal
    terminal.writeln("");
    terminal.writeln(`\x1b[1;33m❯\x1b[0m ${prompt}`);
    terminal.writeln("");
    terminal.writeln("\x1b[2m─────────────────────────────────────────────────────\x1b[0m");
    terminal.writeln("");

    // Reset longitud de respuesta
    lastResponseLengthRef.current = 0;

    // Ejecutar
    await execute({
      prompt,
      context,
      run_id: runId,
      onComplete: () => {
        terminal.writeln("");
        terminal.writeln("\x1b[2m─────────────────────────────────────────────────────\x1b[0m");
        terminal.writeln("\x1b[1;32m✓ Completed\x1b[0m");
        terminal.writeln("");
      },
      onError: (err) => {
        terminal.writeln("");
        terminal.writeln(`\x1b[1;31m✗ Error: ${err}\x1b[0m`);
        terminal.writeln("");
      },
    });

    // Limpiar input
    setPrompt("");
  };

  // Manejar teclas especiales
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter para ejecutar (sin Shift)
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleExecute();
      return;
    }

    // Ctrl+ArrowUp - comando anterior
    if (e.ctrlKey && e.key === "ArrowUp") {
      e.preventDefault();
      if (commandHistory.length === 0) return;

      const newIndex = historyIndex === -1
        ? commandHistory.length - 1
        : Math.max(0, historyIndex - 1);

      setHistoryIndex(newIndex);
      setPrompt(commandHistory[newIndex]);
      return;
    }

    // Ctrl+ArrowDown - comando siguiente
    if (e.ctrlKey && e.key === "ArrowDown") {
      e.preventDefault();
      if (historyIndex === -1) return;

      const newIndex = historyIndex + 1;

      if (newIndex >= commandHistory.length) {
        setHistoryIndex(-1);
        setPrompt("");
      } else {
        setHistoryIndex(newIndex);
        setPrompt(commandHistory[newIndex]);
      }
      return;
    }
  };

  const isExecuting = status === "running";
  const isPaused = status === "paused";
  const canExecute = prompt.trim().length > 0 && !isExecuting;

  return (
    <div className="agent-control-panel">
      {/* Terminal Output */}
      <div className="agent-terminal-container">
        <div className="agent-terminal-header">
          <span className="agent-terminal-title">Agent Output</span>
          <div className="agent-terminal-status">
            {taskId && (
              <>
                <span className={`agent-status-indicator status-${status}`} />
                <span className="agent-status-text">{status}</span>
              </>
            )}
          </div>
        </div>
        <div ref={terminalRef} className="agent-terminal" />
      </div>

      {/* Control Input */}
      <div className="agent-input-container">
        <div className="agent-input-header">
          <span className="agent-input-label">Your Prompt</span>
          <span className="agent-input-hint">
            Press Enter to execute, Shift+Enter for new line
          </span>
        </div>

        <textarea
          className="agent-input-textarea"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Enter your task or question for the agent..."
          rows={4}
          disabled={isExecuting}
        />

        <div className="agent-control-buttons">
          {/* Botón principal */}
          <button
            className={`agent-btn agent-btn-primary ${!canExecute ? "disabled" : ""}`}
            onClick={handleExecute}
            disabled={!canExecute}
          >
            {isExecuting ? "⏳ Executing..." : "▶ Execute"}
          </button>

          {/* Botones de control */}
          {isExecuting && (
            <>
              <button
                className="agent-btn agent-btn-warning"
                onClick={pause}
                title="Pause execution"
              >
                ⏸ Pause
              </button>
              <button
                className="agent-btn agent-btn-danger"
                onClick={cancel}
                title="Cancel execution"
              >
                ⏹ Cancel
              </button>
            </>
          )}

          {isPaused && (
            <>
              <button
                className="agent-btn agent-btn-success"
                onClick={resume}
                title="Resume execution"
              >
                ▶ Resume
              </button>
              <button
                className="agent-btn agent-btn-danger"
                onClick={cancel}
                title="Cancel execution"
              >
                ⏹ Cancel
              </button>
            </>
          )}

          {/* Info de historial */}
          {commandHistory.length > 0 && (
            <span className="agent-history-info">
              {commandHistory.length} command{commandHistory.length !== 1 ? "s" : ""} in history
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
