/**
 * DecisionFlowNode - Represents a decision/branching point
 * Displayed as a diamond shape (UML standard)
 */

import { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";
import { DESIGN_TOKENS } from "../../../../theme/designTokens";

const { colors } = DESIGN_TOKENS;

export interface DecisionNodeData {
  label: string;
  condition?: string;
  branches?: Array<{
    id: string;
    label: string;
    guard?: string;
  }>;
}

export const DecisionFlowNode = memo(({ data, selected }: NodeProps<DecisionNodeData>) => {
  const size = 40;
  const halfSize = size / 2;

  return (
    <>
      <Handle
        type="target"
        position={Position.Top}
        style={{
          background: colors.primary.main,
          width: 8,
          height: 8,
          border: `2px solid ${colors.base.panel}`,
          top: -4,
        }}
      />
      <div
        style={{
          width: size,
          height: size,
          position: "relative",
          cursor: "pointer",
        }}
        title={data.condition || data.label || "Decision"}
      >
        {/* Diamond shape using CSS transform */}
        <div
          style={{
            width: size,
            height: size,
            backgroundColor: colors.semantic.warning,
            border: selected ? `2px solid ${colors.primary.light}` : `2px solid ${colors.semantic.warningDark || "#b8860b"}`,
            boxShadow: selected ? `0 0 8px ${colors.primary.main}` : "none",
            transform: "rotate(45deg)",
            transition: "all 0.15s ease",
          }}
        />
        {/* Question mark in center */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: size,
            height: size,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 16,
            fontWeight: 700,
            color: colors.base.background,
          }}
        >
          ?
        </div>
      </div>
      {/* Condition label below */}
      {data.condition && (
        <div
          style={{
            position: "absolute",
            top: size + 4,
            left: "50%",
            transform: "translateX(-50%)",
            fontSize: 10,
            color: colors.text.muted,
            whiteSpace: "nowrap",
            maxWidth: 120,
            overflow: "hidden",
            textOverflow: "ellipsis",
            backgroundColor: colors.base.panel,
            padding: "2px 6px",
            borderRadius: 4,
          }}
        >
          {data.condition}
        </div>
      )}
      {/* Left handle for "false" branch */}
      <Handle
        type="source"
        position={Position.Left}
        id="false"
        style={{
          background: colors.semantic.error,
          width: 8,
          height: 8,
          border: `2px solid ${colors.base.panel}`,
          left: -4,
        }}
      />
      {/* Right handle for "true" branch */}
      <Handle
        type="source"
        position={Position.Right}
        id="true"
        style={{
          background: colors.semantic.success,
          width: 8,
          height: 8,
          border: `2px solid ${colors.base.panel}`,
          right: -4,
        }}
      />
      {/* Bottom handle (optional - for merge back) */}
      <Handle
        type="source"
        position={Position.Bottom}
        id="default"
        style={{
          background: colors.primary.main,
          width: 8,
          height: 8,
          border: `2px solid ${colors.base.panel}`,
          bottom: -4,
        }}
      />
    </>
  );
});

DecisionFlowNode.displayName = "DecisionFlowNode";
