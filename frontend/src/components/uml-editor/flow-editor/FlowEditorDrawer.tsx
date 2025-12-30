/**
 * FlowEditorDrawer
 *
 * A bottom drawer component that opens to display the Activity Diagram editor
 * for designing the internal flow of a method.
 *
 * Features:
 * - 60% viewport height (resizable)
 * - Shows method name in header
 * - Contains ActivityCanvas for flow editing (Phase 2)
 * - Auto-initializes activity diagram if not exists
 */

import { useEffect, useCallback, useState, useRef } from "react";
import { ReactFlowProvider } from "reactflow";
import { useUmlEditorStore } from "../../../state/useUmlEditorStore";
import { DESIGN_TOKENS } from "../../../theme/designTokens";
import { ActivityCanvas } from "./ActivityCanvas";
import { FlowEditorToolbar } from "./FlowEditorToolbar";

const { colors, borders } = DESIGN_TOKENS;

// Minimum and maximum drawer heights as percentage of viewport
const MIN_HEIGHT_PERCENT = 30;
const MAX_HEIGHT_PERCENT = 85;
const DEFAULT_HEIGHT_PERCENT = 60;

// Simple icon components (since lucide-react may not be available)
const XIcon = ({ size = 16, color = "currentColor" }: { size?: number; color?: string }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="6" x2="6" y2="18" />
    <line x1="6" y1="6" x2="18" y2="18" />
  </svg>
);

const MinimizeIcon = ({ size = 16, color = "currentColor" }: { size?: number; color?: string }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="4 14 10 14 10 20" />
    <polyline points="20 10 14 10 14 4" />
    <line x1="14" y1="10" x2="21" y2="3" />
    <line x1="3" y1="21" x2="10" y2="14" />
  </svg>
);

const MaximizeIcon = ({ size = 16, color = "currentColor" }: { size?: number; color?: string }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="15 3 21 3 21 9" />
    <polyline points="9 21 3 21 3 15" />
    <line x1="21" y1="3" x2="14" y2="10" />
    <line x1="3" y1="21" x2="10" y2="14" />
  </svg>
);

const GitBranchIcon = ({ size = 20, color = "currentColor" }: { size?: number; color?: string }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="6" y1="3" x2="6" y2="15" />
    <circle cx="18" cy="6" r="3" />
    <circle cx="6" cy="18" r="3" />
    <path d="M18 9a9 9 0 0 1-9 9" />
  </svg>
);

const PlayIcon = ({ size = 48 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="5 3 19 12 5 21 5 3" />
  </svg>
);

export function FlowEditorDrawer() {
  const {
    isFlowDrawerOpen,
    flowEditorClassId,
    flowEditorMethodId,
    closeFlowEditor,
    getClassById,
    getActivityDiagram,
    initializeActivityDiagram,
  } = useUmlEditorStore();

  const [heightPercent, setHeightPercent] = useState(DEFAULT_HEIGHT_PERCENT);
  const [isResizing, setIsResizing] = useState(false);
  const drawerRef = useRef<HTMLDivElement>(null);

  // Get class and method info for display
  const cls = flowEditorClassId ? getClassById(flowEditorClassId) : null;
  const method = cls?.methods.find((m) => m.id === flowEditorMethodId);

  // Initialize activity diagram when drawer opens
  useEffect(() => {
    if (isFlowDrawerOpen && flowEditorClassId && flowEditorMethodId) {
      initializeActivityDiagram(flowEditorClassId, flowEditorMethodId);
    }
  }, [isFlowDrawerOpen, flowEditorClassId, flowEditorMethodId, initializeActivityDiagram]);

  // Get the activity diagram
  const activityDiagram =
    flowEditorClassId && flowEditorMethodId
      ? getActivityDiagram(flowEditorClassId, flowEditorMethodId)
      : null;

  // Handle keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isFlowDrawerOpen) {
        closeFlowEditor();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isFlowDrawerOpen, closeFlowEditor]);

  // Handle resize drag
  const handleResizeMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
  }, []);

  useEffect(() => {
    if (!isResizing) return;

    const handleMouseMove = (e: MouseEvent) => {
      const viewportHeight = window.innerHeight;
      const newHeight = ((viewportHeight - e.clientY) / viewportHeight) * 100;
      setHeightPercent(Math.min(MAX_HEIGHT_PERCENT, Math.max(MIN_HEIGHT_PERCENT, newHeight)));
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isResizing]);

  // Toggle minimize/maximize
  const toggleSize = useCallback(() => {
    setHeightPercent((prev) =>
      prev < DEFAULT_HEIGHT_PERCENT ? DEFAULT_HEIGHT_PERCENT : MIN_HEIGHT_PERCENT
    );
  }, []);

  if (!isFlowDrawerOpen) return null;

  const nodeCount = activityDiagram?.nodes.length ?? 0;
  const edgeCount = activityDiagram?.edges.length ?? 0;

  return (
    <div
      ref={drawerRef}
      style={{
        position: "fixed",
        bottom: 0,
        left: 0,
        right: 0,
        height: `${heightPercent}vh`,
        backgroundColor: colors.base.panel,
        borderTop: `2px solid ${colors.primary.main}`,
        boxShadow: "0 -4px 20px rgba(0, 0, 0, 0.4)",
        zIndex: 1000,
        display: "flex",
        flexDirection: "column",
        transition: isResizing ? "none" : "height 0.2s ease-out",
      }}
    >
      {/* Resize handle */}
      <div
        onMouseDown={handleResizeMouseDown}
        style={{
          position: "absolute",
          top: -4,
          left: 0,
          right: 0,
          height: 8,
          cursor: "ns-resize",
          backgroundColor: isResizing ? colors.primary.main : "transparent",
        }}
      />

      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "12px 16px",
          borderBottom: `1px solid ${borders.default}`,
          backgroundColor: colors.base.card,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <GitBranchIcon size={20} color={colors.primary.main} />
          <div>
            <h3
              style={{
                margin: 0,
                fontSize: 14,
                fontWeight: 600,
                color: colors.text.secondary,
              }}
            >
              Flow Editor: {cls?.name ?? "Class"}.{method?.name ?? "method"}()
            </h3>
            <span
              style={{
                fontSize: 12,
                color: colors.text.muted,
              }}
            >
              {nodeCount} nodes, {edgeCount} edges
              {activityDiagram?.detailLevel && ` • ${activityDiagram.detailLevel} mode`}
            </span>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {/* Minimize/Maximize button */}
          <button
            onClick={toggleSize}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              width: 32,
              height: 32,
              border: `1px solid ${borders.default}`,
              borderRadius: 6,
              backgroundColor: "transparent",
              cursor: "pointer",
              color: colors.text.muted,
            }}
            title={heightPercent < DEFAULT_HEIGHT_PERCENT ? "Expand" : "Minimize"}
          >
            {heightPercent < DEFAULT_HEIGHT_PERCENT ? (
              <MaximizeIcon size={16} />
            ) : (
              <MinimizeIcon size={16} />
            )}
          </button>

          {/* Close button */}
          <button
            onClick={closeFlowEditor}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              width: 32,
              height: 32,
              border: `1px solid ${borders.default}`,
              borderRadius: 6,
              backgroundColor: "transparent",
              cursor: "pointer",
              color: colors.text.muted,
            }}
            title="Close (ESC)"
          >
            <XIcon size={16} />
          </button>
        </div>
      </div>

      {/* Canvas Area */}
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
      >
        {/* Toolbar */}
        {flowEditorClassId && flowEditorMethodId && (
          <FlowEditorToolbar classId={flowEditorClassId} methodId={flowEditorMethodId} />
        )}

        {/* Activity Canvas */}
        <div
          style={{
            flex: 1,
            backgroundColor: colors.base.background,
          }}
        >
          {flowEditorClassId && flowEditorMethodId ? (
            <ReactFlowProvider>
              <ActivityCanvas classId={flowEditorClassId} methodId={flowEditorMethodId} />
            </ReactFlowProvider>
          ) : (
            <div
              style={{
                height: "100%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: colors.text.muted,
              }}
            >
              <div style={{ textAlign: "center" }}>
                <PlayIcon size={48} />
                <p style={{ margin: "12px 0 0", fontSize: 14 }}>No method selected</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
