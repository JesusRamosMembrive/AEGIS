/**
 * Cliente API para control de agente Claude
 *
 * Proporciona funciones para:
 * - Crear y ejecutar tareas
 * - Controlar flujo (pause/resume/cancel)
 * - Recibir respuestas en streaming
 */

import { useBackendStore } from "../state/useBackendStore";

// === Types ===

export interface AgentTask {
  task_id: string;
  prompt: string;
  context?: Record<string, any>;
  run_id?: number;
  status: "idle" | "running" | "paused" | "completed" | "failed" | "cancelled";
  created_at: string;
  started_at?: string;
  completed_at?: string;
  error?: string;
  response: string;
}

export interface AgentStatus {
  configured: boolean;
  anthropic_available: boolean;
  has_api_key: boolean;
  active_tasks: number;
  tasks: Record<string, AgentTask>;
}

export interface CreateTaskRequest {
  prompt: string;
  context?: Record<string, any>;
  run_id?: number;
  model?: string;
  max_tokens?: number;
  system_prompt?: string;
}

export interface CreateTaskResponse {
  task_id: string;
  status: string;
  message: string;
}

export interface StreamEvent {
  type: "status" | "content" | "error" | "complete";
  data: any;
}

// === Helper function to get API base URL ===

function getApiBaseUrl(): string {
  const backendUrl = useBackendStore.getState().backendUrl || "http://localhost:8010";
  return backendUrl.endsWith("/api") ? backendUrl : `${backendUrl}/api`;
}

// === API Functions ===

/**
 * Obtiene el estado del controlador de agente
 */
export async function getAgentStatus(): Promise<AgentStatus> {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/agent/status`);

  if (!response.ok) {
    throw new Error(`Failed to get agent status: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Crea una nueva tarea
 */
export async function createTask(request: CreateTaskRequest): Promise<CreateTaskResponse> {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/agent/tasks`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || "Failed to create task");
  }

  return response.json();
}

/**
 * Ejecuta una tarea y retorna un EventSource para recibir el streaming
 *
 * @param taskId ID de la tarea
 * @param options Opciones de ejecución
 * @returns EventSource configurado para recibir eventos SSE
 */
export function streamTask(
  taskId: string,
  options?: {
    model?: string;
    max_tokens?: number;
    system_prompt?: string;
  }
): EventSource {
  const baseUrl = getApiBaseUrl();
  const params = new URLSearchParams();

  if (options?.model) params.append("model", options.model);
  if (options?.max_tokens) params.append("max_tokens", options.max_tokens.toString());
  if (options?.system_prompt) params.append("system_prompt", options.system_prompt);

  const url = `${baseUrl}/agent/tasks/${taskId}/stream?${params.toString()}`;
  return new EventSource(url);
}

/**
 * Lista todas las tareas activas
 */
export async function listTasks(): Promise<{ tasks: AgentTask[] }> {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/agent/tasks`);

  if (!response.ok) {
    throw new Error(`Failed to list tasks: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Obtiene los detalles de una tarea específica
 */
export async function getTask(taskId: string): Promise<AgentTask> {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/agent/tasks/${taskId}`);

  if (!response.ok) {
    throw new Error(`Failed to get task: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Pausa una tarea en ejecución
 */
export async function pauseTask(taskId: string): Promise<void> {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/agent/tasks/${taskId}/pause`, {
    method: "POST",
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || "Failed to pause task");
  }
}

/**
 * Reanuda una tarea pausada
 */
export async function resumeTask(taskId: string): Promise<void> {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/agent/tasks/${taskId}/resume`, {
    method: "POST",
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || "Failed to resume task");
  }
}

/**
 * Cancela una tarea en ejecución o pausada
 */
export async function cancelTask(taskId: string): Promise<void> {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/agent/tasks/${taskId}/cancel`, {
    method: "POST",
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || "Failed to cancel task");
  }
}

/**
 * Limpia tareas completadas
 */
export async function clearCompletedTasks(): Promise<{ cleared: number; message: string }> {
  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}/agent/tasks`, {
    method: "DELETE",
  });

  if (!response.ok) {
    throw new Error(`Failed to clear tasks: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Hook personalizado para crear y ejecutar una tarea con streaming
 *
 * Uso:
 * ```tsx
 * const { execute, response, status, error } = useAgentTask();
 *
 * await execute({
 *   prompt: "Explica qué es React",
 *   onContent: (text) => console.log(text),
 *   onComplete: () => console.log("Done!"),
 * });
 * ```
 */
export function useAgentStreamingTask() {
  const [response, setResponse] = React.useState<string>("");
  const [status, setStatus] = React.useState<string>("idle");
  const [error, setError] = React.useState<string | null>(null);
  const [taskId, setTaskId] = React.useState<string | null>(null);
  const eventSourceRef = React.useRef<EventSource | null>(null);

  const execute = React.useCallback(async (
    request: CreateTaskRequest & {
      onContent?: (text: string) => void;
      onStatus?: (status: string) => void;
      onComplete?: () => void;
      onError?: (error: string) => void;
    }
  ) => {
    try {
      // Limpiar estado anterior
      setResponse("");
      setError(null);
      setStatus("creating");

      // Crear tarea
      const { task_id } = await createTask(request);
      setTaskId(task_id);

      // Iniciar streaming
      const eventSource = streamTask(task_id, {
        model: request.model,
        max_tokens: request.max_tokens,
        system_prompt: request.system_prompt,
      });

      eventSourceRef.current = eventSource;

      eventSource.onmessage = (event) => {
        try {
          const streamEvent: StreamEvent = JSON.parse(event.data);

          switch (streamEvent.type) {
            case "status":
              setStatus(streamEvent.data.status);
              request.onStatus?.(streamEvent.data.status);
              break;

            case "content":
              const text = streamEvent.data.text;
              setResponse((prev) => prev + text);
              request.onContent?.(text);
              break;

            case "complete":
              setStatus("completed");
              request.onComplete?.();
              eventSource.close();
              break;

            case "error":
              setError(streamEvent.data.error);
              setStatus("failed");
              request.onError?.(streamEvent.data.error);
              eventSource.close();
              break;
          }
        } catch (err) {
          console.error("Failed to parse SSE event:", err);
        }
      };

      eventSource.onerror = () => {
        setError("Connection error");
        setStatus("failed");
        eventSource.close();
      };

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Unknown error";
      setError(errorMessage);
      setStatus("failed");
      request.onError?.(errorMessage);
    }
  }, []);

  const pause = React.useCallback(async () => {
    if (taskId) {
      await pauseTask(taskId);
      setStatus("paused");
    }
  }, [taskId]);

  const resume = React.useCallback(async () => {
    if (taskId) {
      await resumeTask(taskId);
      setStatus("running");
    }
  }, [taskId]);

  const cancel = React.useCallback(async () => {
    if (taskId) {
      await cancelTask(taskId);
      setStatus("cancelled");
      eventSourceRef.current?.close();
    }
  }, [taskId]);

  React.useEffect(() => {
    // Cleanup on unmount
    return () => {
      eventSourceRef.current?.close();
    };
  }, []);

  return {
    execute,
    pause,
    resume,
    cancel,
    response,
    status,
    error,
    taskId,
  };
}

// Re-export React for the hook
import React from "react";
