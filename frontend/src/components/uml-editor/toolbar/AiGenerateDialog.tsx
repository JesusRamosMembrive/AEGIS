/**
 * AI Generate Dialog - Generate UML from natural language using Ollama
 *
 * Allows users to describe what they want to create in natural language,
 * select an Ollama model, and generate UML entities that get added to the canvas.
 */

import { useState, useCallback } from "react";
import { useUmlEditorStore } from "../../../state/useUmlEditorStore";
import { useOllamaStatusQuery } from "../../../hooks/useOllamaStatusQuery";
import { testOllamaChat } from "../../../api/client";
import { xmlToProject } from "../../../utils/umlXmlImporter";
import {
  getUmlGenerationSystemPrompt,
  formatUserPrompt,
} from "../../../utils/umlAiPrompts";
import { DESIGN_TOKENS } from "../../../theme/designTokens";

const { colors, borders } = DESIGN_TOKENS;

interface AiGenerateDialogProps {
  isOpen: boolean;
  onClose: () => void;
}

type GenerationStatus = "idle" | "generating" | "success" | "error";

export function AiGenerateDialog({
  isOpen,
  onClose,
}: AiGenerateDialogProps): JSX.Element | null {
  const { project, mergeProject } = useUmlEditorStore();
  const { data: ollamaStatus, isLoading: isLoadingStatus } = useOllamaStatusQuery();

  const [description, setDescription] = useState("");
  const [selectedModel, setSelectedModel] = useState("");
  const [status, setStatus] = useState<GenerationStatus>("idle");
  const [errorMessage, setErrorMessage] = useState("");

  // Set default model when status loads
  const availableModels = ollamaStatus?.status?.models ?? [];
  const modelNames = availableModels.map((m) => m.name);
  if (modelNames.length > 0 && !selectedModel) {
    setSelectedModel(modelNames[0]);
  }

  const handleGenerate = useCallback(async () => {
    if (!description.trim() || !selectedModel) return;

    setStatus("generating");
    setErrorMessage("");

    try {
      const systemPrompt = getUmlGenerationSystemPrompt(project.targetLanguage);
      const userPrompt = formatUserPrompt(description);

      const response = await testOllamaChat({
        model: selectedModel,
        prompt: userPrompt,
        system_prompt: systemPrompt,
        timeout_seconds: 120,
      });

      if (!response.success) {
        throw new Error(response.message ?? "Failed to generate UML");
      }

      // Extract XML from response (handle potential markdown code blocks)
      // The response text is in the "raw" field from the Ollama response
      let xmlContent = (response.raw as { response?: string })?.response ?? response.message ?? "";

      // Remove markdown code blocks if present
      const xmlMatch = xmlContent.match(/```xml\s*([\s\S]*?)\s*```/);
      if (xmlMatch) {
        xmlContent = xmlMatch[1];
      } else {
        // Also try without xml language specifier
        const codeMatch = xmlContent.match(/```\s*([\s\S]*?)\s*```/);
        if (codeMatch) {
          xmlContent = codeMatch[1];
        }
      }

      // Trim whitespace
      xmlContent = xmlContent.trim();

      // Parse the XML
      const parseResult = xmlToProject(xmlContent);

      if (!parseResult.success || !parseResult.project) {
        throw new Error(parseResult.error ?? "Failed to parse generated XML");
      }

      // Merge the generated entities into current project
      mergeProject(parseResult.project);

      setStatus("success");
      setDescription("");

      // Close after short delay to show success
      setTimeout(() => {
        onClose();
        setStatus("idle");
      }, 1000);
    } catch (error) {
      setStatus("error");
      setErrorMessage(error instanceof Error ? error.message : "Unknown error");
    }
  }, [description, selectedModel, project.targetLanguage, mergeProject, onClose]);

  const handleClose = useCallback(() => {
    if (status !== "generating") {
      setStatus("idle");
      setErrorMessage("");
      onClose();
    }
  }, [status, onClose]);

  if (!isOpen) return null;

  const isOllamaAvailable = ollamaStatus?.status?.running ?? false;

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(0, 0, 0, 0.6)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
      }}
      onClick={handleClose}
    >
      <div
        style={{
          backgroundColor: colors.base.card,
          borderRadius: "12px",
          width: "600px",
          maxWidth: "95vw",
          border: `1px solid ${borders.default}`,
          overflow: "hidden",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            padding: "16px 24px",
            borderBottom: `1px solid ${borders.default}`,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div>
            <h2 style={{ margin: 0, fontSize: "18px", color: colors.text.secondary }}>
              Generate with AI
            </h2>
            <p style={{ margin: "4px 0 0 0", fontSize: "12px", color: colors.text.muted }}>
              Describe what you want to create in natural language
            </p>
          </div>
          <button
            onClick={handleClose}
            disabled={status === "generating"}
            style={{
              width: "32px",
              height: "32px",
              borderRadius: "6px",
              border: "none",
              backgroundColor: "transparent",
              color: colors.text.muted,
              fontSize: "20px",
              cursor: status === "generating" ? "not-allowed" : "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              opacity: status === "generating" ? 0.5 : 1,
            }}
          >
            x
          </button>
        </div>

        {/* Body */}
        <div style={{ padding: "20px 24px" }}>
          {/* Ollama Status Warning */}
          {!isLoadingStatus && !isOllamaAvailable && (
            <div
              style={{
                padding: "12px 16px",
                backgroundColor: colors.severity.warning + "20",
                border: `1px solid ${colors.severity.warning}40`,
                borderRadius: "8px",
                marginBottom: "16px",
              }}
            >
              <div style={{ fontSize: "13px", color: colors.severity.warning, fontWeight: 500 }}>
                Ollama not available
              </div>
              <div style={{ fontSize: "12px", color: colors.text.muted, marginTop: "4px" }}>
                Make sure Ollama is running and configured in Settings.
              </div>
            </div>
          )}

          {/* Description Textarea */}
          <div style={{ marginBottom: "16px" }}>
            <label
              style={{
                display: "block",
                fontSize: "12px",
                fontWeight: 500,
                color: colors.text.muted,
                marginBottom: "8px",
              }}
            >
              Describe what you want to create:
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              disabled={status === "generating"}
              placeholder="Example: A class MathOperations with static methods: add, subtract, multiply, divide. Each method takes two numbers and returns a number."
              style={{
                width: "100%",
                minHeight: "120px",
                padding: "12px",
                borderRadius: "8px",
                border: `1px solid ${borders.default}`,
                backgroundColor: colors.base.panel,
                color: colors.text.secondary,
                fontSize: "13px",
                lineHeight: 1.5,
                resize: "vertical",
                outline: "none",
                fontFamily: "inherit",
                boxSizing: "border-box",
              }}
              onFocus={(e) => {
                e.target.style.border = `1px solid ${colors.primary.main}`;
              }}
              onBlur={(e) => {
                e.target.style.border = `1px solid ${borders.default}`;
              }}
            />
          </div>

          {/* Model Selector */}
          <div style={{ marginBottom: "16px" }}>
            <label
              style={{
                display: "block",
                fontSize: "12px",
                fontWeight: 500,
                color: colors.text.muted,
                marginBottom: "8px",
              }}
            >
              Model:
            </label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              disabled={status === "generating" || modelNames.length === 0}
              style={{
                width: "100%",
                padding: "10px 12px",
                borderRadius: "6px",
                border: `1px solid ${borders.default}`,
                backgroundColor: colors.base.panel,
                color: colors.text.secondary,
                fontSize: "13px",
                cursor: "pointer",
                outline: "none",
              }}
            >
              {isLoadingStatus ? (
                <option>Loading models...</option>
              ) : modelNames.length === 0 ? (
                <option>No models available</option>
              ) : (
                modelNames.map((model: string) => (
                  <option key={model} value={model}>
                    {model}
                  </option>
                ))
              )}
            </select>
          </div>

          {/* Status Messages */}
          {status === "generating" && (
            <div
              style={{
                padding: "12px 16px",
                backgroundColor: colors.primary.main + "20",
                border: `1px solid ${colors.primary.main}40`,
                borderRadius: "8px",
                display: "flex",
                alignItems: "center",
                gap: "12px",
              }}
            >
              <div
                style={{
                  width: "16px",
                  height: "16px",
                  border: `2px solid ${colors.primary.main}`,
                  borderTopColor: "transparent",
                  borderRadius: "50%",
                  animation: "spin 1s linear infinite",
                }}
              />
              <span style={{ fontSize: "13px", color: colors.primary.main }}>
                Generating UML... This may take a moment.
              </span>
              <style>{`
                @keyframes spin {
                  to { transform: rotate(360deg); }
                }
              `}</style>
            </div>
          )}

          {status === "success" && (
            <div
              style={{
                padding: "12px 16px",
                backgroundColor: colors.complexity.low + "20",
                border: `1px solid ${colors.complexity.low}40`,
                borderRadius: "8px",
              }}
            >
              <span style={{ fontSize: "13px", color: colors.complexity.low }}>
                Successfully generated and added to canvas!
              </span>
            </div>
          )}

          {status === "error" && (
            <div
              style={{
                padding: "12px 16px",
                backgroundColor: colors.severity.danger + "20",
                border: `1px solid ${colors.severity.danger}40`,
                borderRadius: "8px",
              }}
            >
              <div style={{ fontSize: "13px", color: colors.severity.danger, fontWeight: 500 }}>
                Generation failed
              </div>
              <div style={{ fontSize: "12px", color: colors.text.muted, marginTop: "4px" }}>
                {errorMessage}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div
          style={{
            padding: "16px 24px",
            borderTop: `1px solid ${borders.default}`,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div style={{ fontSize: "12px", color: colors.text.muted }}>
            Target language: <strong>{project.targetLanguage}</strong>
          </div>
          <div style={{ display: "flex", gap: "12px" }}>
            <button
              onClick={handleClose}
              disabled={status === "generating"}
              style={{
                padding: "8px 16px",
                borderRadius: "6px",
                border: `1px solid ${borders.default}`,
                backgroundColor: "transparent",
                color: colors.text.muted,
                fontSize: "13px",
                cursor: status === "generating" ? "not-allowed" : "pointer",
                opacity: status === "generating" ? 0.5 : 1,
              }}
            >
              Cancel
            </button>
            <button
              onClick={handleGenerate}
              disabled={
                !description.trim() ||
                !selectedModel ||
                !isOllamaAvailable ||
                status === "generating"
              }
              style={{
                padding: "8px 20px",
                borderRadius: "6px",
                border: "none",
                backgroundColor:
                  description.trim() && selectedModel && isOllamaAvailable && status !== "generating"
                    ? colors.primary.main
                    : colors.gray[600],
                color: colors.contrast.light,
                fontSize: "13px",
                fontWeight: 500,
                cursor:
                  description.trim() && selectedModel && isOllamaAvailable && status !== "generating"
                    ? "pointer"
                    : "not-allowed",
                opacity:
                  description.trim() && selectedModel && isOllamaAvailable && status !== "generating"
                    ? 1
                    : 0.6,
              }}
            >
              {status === "generating" ? "Generating..." : "Generate & Add"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
