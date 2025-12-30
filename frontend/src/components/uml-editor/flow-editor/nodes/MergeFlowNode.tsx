/**
 * MergeFlowNode - Represents a merge point (multiple flows converging)
 * Displayed as a diamond shape (same as decision but typically without condition)
 */

import { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";
import { DESIGN_TOKENS } from "../../../../theme/designTokens";

const { colors } = DESIGN_TOKENS;

export interface MergeNodeData {
  label: string;
}

export const MergeFlowNode = memo(({ data, selected }: NodeProps<MergeNodeData>) => {
  const size = 32;

  return (
    <>
      {/* Multiple input handles for merging flows */}
      <Handle
        type="target"
        position={Position.Top}
        id="top"
        style={{
          background: colors.primary.main,
          width: 8,
          height: 8,
          border: `2px solid ${colors.base.panel}`,
          top: -4,
        }}
      />
      <Handle
        type="target"
        position={Position.Left}
        id="left"
        style={{
          background: colors.primary.main,
          width: 8,
          height: 8,
          border: `2px solid ${colors.base.panel}`,
          left: -4,
        }}
      />
      <Handle
        type="target"
        position={Position.Right}
        id="right"
        style={{
          background: colors.primary.main,
          width: 8,
          height: 8,
          border: `2px solid ${colors.base.panel}`,
          right: -4,
        }}
      />
      <div
        style={{
          width: size,
          height: size,
          position: "relative",
          cursor: "pointer",
        }}
        title={data.label || "Merge"}
      >
        {/* Diamond shape */}
        <div
          style={{
            width: size,
            height: size,
            backgroundColor: colors.base.elevated,
            border: selected ? `2px solid ${colors.primary.light}` : `2px solid ${colors.text.muted}`,
            boxShadow: selected ? `0 0 8px ${colors.primary.main}` : "none",
            transform: "rotate(45deg)",
            transition: "all 0.15s ease",
          }}
        />
        {/* Merge icon (arrows converging) */}
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
          }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={colors.text.primary} strokeWidth="2">
            <path d="M6 4L12 12L18 4" />
            <path d="M12 12L12 20" />
          </svg>
        </div>
      </div>
      {/* Single output handle */}
      <Handle
        type="source"
        position={Position.Bottom}
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

MergeFlowNode.displayName = "MergeFlowNode";
