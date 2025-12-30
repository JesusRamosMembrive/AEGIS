/**
 * InitialFlowNode - Entry point for activity diagram
 * Displayed as a filled circle (UML standard)
 */

import { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";
import { DESIGN_TOKENS } from "../../../../theme/designTokens";

const { colors } = DESIGN_TOKENS;

export interface InitialNodeData {
  label: string;
}

export const InitialFlowNode = memo(({ data, selected }: NodeProps<InitialNodeData>) => {
  return (
    <>
      {/* No input handle - this is the start */}
      <div
        style={{
          width: 24,
          height: 24,
          borderRadius: "50%",
          backgroundColor: colors.primary.main,
          border: selected ? `3px solid ${colors.primary.light}` : `2px solid ${colors.primary.dark}`,
          boxShadow: selected ? `0 0 8px ${colors.primary.main}` : "none",
          cursor: "pointer",
          transition: "all 0.15s ease",
        }}
        title={data.label || "Start"}
      />
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

InitialFlowNode.displayName = "InitialFlowNode";
