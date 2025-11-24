import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { AgentControlPanel } from "./AgentControlPanel";
import { getAgentStatus, type AgentStatus } from "../api/agentClient";

/**
 * Vista principal para control de agente
 *
 * Proporciona interfaz completa para:
 * - Enviar tareas al agente Claude
 * - Ver respuestas en tiempo real
 * - Controlar ejecución
 */
export function AgentControlView() {
  const [context, setContext] = useState<Record<string, any>>({});

  // Obtener estado del agente
  const { data: agentStatus, isLoading, error, refetch } = useQuery<AgentStatus>({
    queryKey: ["agent", "status"],
    queryFn: getAgentStatus,
    refetchInterval: 5000, // Refetch cada 5 segundos
  });

  // Auto-refetch cuando cambia la configuración
  useEffect(() => {
    const interval = setInterval(() => {
      refetch();
    }, 5000);

    return () => clearInterval(interval);
  }, [refetch]);

  const isConfigured = agentStatus?.configured ?? false;
  const hasApiKey = agentStatus?.has_api_key ?? false;

  return (
    <div className="audit-page">
      {/* Hero Section */}
      <section className="audit-hero">
        <div>
          <span className="audit-eyebrow">Interactive Agent Control</span>
          <h1>Claude Agent Terminal</h1>
          <p className="audit-subtitle">
            Send tasks to Claude, see responses in real-time, and control execution interactively.
            Perfect for pair programming and iterative development.
          </p>
        </div>

        <div className="audit-hero-meta">
          {isLoading && (
            <div className="audit-badge status-neutral">
              Loading...
            </div>
          )}

          {!isLoading && isConfigured && (
            <div className="audit-badge status-success">
              ✓ Agent Configured
            </div>
          )}

          {!isLoading && !isConfigured && (
            <div className="audit-badge status-danger">
              ⚠ Not Configured
            </div>
          )}

          {error && (
            <div className="audit-badge status-danger">
              Connection Error
            </div>
          )}
        </div>
      </section>

      {/* Configuration Alert */}
      {!isLoading && !isConfigured && (
        <div className="config-alert config-alert-warning">
          <div className="config-alert-icon">⚠️</div>
          <div className="config-alert-content">
            <h3>Agent Not Configured</h3>
            {!hasApiKey ? (
              <p>
                Please set your <code>ANTHROPIC_API_KEY</code> environment variable to use the agent controller.
                Restart the backend after setting the key.
              </p>
            ) : (
              <p>
                The Anthropic Python package is not installed. Run{" "}
                <code>pip install anthropic</code> and restart the backend.
              </p>
            )}
          </div>
        </div>
      )}

      {/* Main Control Panel */}
      {isConfigured && (
        <div className="agent-control-view-container">
          <AgentControlPanel context={context} />
        </div>
      )}

      {/* Help Section */}
      <section className="agent-help-section">
        <h2>How to Use</h2>
        <div className="agent-help-grid">
          <div className="agent-help-card">
            <div className="agent-help-icon">💬</div>
            <h3>Write Your Prompt</h3>
            <p>
              Enter any task, question, or instruction for Claude. Be specific about what you want
              the agent to do.
            </p>
          </div>

          <div className="agent-help-card">
            <div className="agent-help-icon">▶️</div>
            <h3>Execute & Watch</h3>
            <p>
              Press Enter or click Execute. The agent will start working and stream the response
              in real-time to the terminal.
            </p>
          </div>

          <div className="agent-help-card">
            <div className="agent-help-icon">⏸️</div>
            <h3>Control Flow</h3>
            <p>
              Pause, resume, or cancel execution at any time. Perfect for reviewing intermediate
              results or adjusting direction.
            </p>
          </div>

          <div className="agent-help-card">
            <div className="agent-help-icon">📜</div>
            <h3>Command History</h3>
            <p>
              Use Ctrl+↑/↓ to navigate through previous commands. Reuse and modify past prompts
              easily.
            </p>
          </div>
        </div>
      </section>

      {/* Status Info */}
      {agentStatus && (
        <section className="agent-status-section">
          <h2>Agent Status</h2>
          <div className="agent-status-grid">
            <div className="agent-status-card">
              <span className="agent-status-label">Active Tasks</span>
              <span className="agent-status-value">{agentStatus.active_tasks}</span>
            </div>

            <div className="agent-status-card">
              <span className="agent-status-label">API Available</span>
              <span className="agent-status-value">
                {agentStatus.anthropic_available ? "✓ Yes" : "✗ No"}
              </span>
            </div>

            <div className="agent-status-card">
              <span className="agent-status-label">API Key</span>
              <span className="agent-status-value">
                {agentStatus.has_api_key ? "✓ Configured" : "✗ Missing"}
              </span>
            </div>

            <div className="agent-status-card">
              <span className="agent-status-label">Status</span>
              <span className="agent-status-value">
                {agentStatus.configured ? "✓ Ready" : "⚠ Not Ready"}
              </span>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
