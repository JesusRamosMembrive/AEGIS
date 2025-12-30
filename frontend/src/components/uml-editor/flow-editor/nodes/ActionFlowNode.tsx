/**
 * ActionFlowNode - Represents an action/activity step
 * Displayed as a rounded rectangle (UML standard)
 */

import { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";
import { DESIGN_TOKENS } from "../../../../theme/designTokens";

const { colors, borders } = DESIGN_TOKENS;

export interface ActionNodeData {
  label: string;
  description?: string;
  pseudocode?: string;
  swimlaneId?: string;
}

export const ActionFlowNode = memo(({ data, selected }: NodeProps<ActionNodeData>) => {
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
        }}
      />
      <div
        style={{
          minWidth: 120,
          maxWidth: 200,
          padding: "10px 16px",
          borderRadius: 8,
          backgroundColor: colors.base.panel,
          border: selected ? `2px solid ${colors.primary.main}` : borders.default,
          boxShadow: selected ? `0 0 8px ${colors.primary.main}40` : "0 2px 4px rgba(0,0,0,0.2)",
          cursor: "pointer",
          transition: "all 0.15s ease",
        }}
        title={data.description || data.pseudocode || data.label}
      >
        <div
          style={{
            fontSize: 13,
            fontWeight: 500,
            color: colors.text.primary,
            textAlign: "center",
            wordBreak: "break-word",
          }}
        >
          {data.label || "Action"}
        </div>
        {data.pseudocode && (
          <div
            style={{
              fontSize: 10,
              color: colors.text.muted,
              marginTop: 4,
              fontFamily: "monospace",
              whiteSpace: "pre-wrap",
              maxHeight: 40,
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
          >
            {data.pseudocode}
          </div>
        )}
      </div>
      <Handle
        type="source"
        position={Position.Bottom}
        style={{
          background: colors.primary.main,
          width: 8,
          height: 8,
          border: `2px solid ${colors.base.panel}`,
        }}
      />
    </>
  );
});

ActionFlowNode.displayName = "ActionFlowNode";
