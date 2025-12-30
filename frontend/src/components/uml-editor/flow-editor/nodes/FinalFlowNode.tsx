/**
 * FinalFlowNode - Exit point for activity diagram
 * Displayed as a filled circle inside another circle (UML standard - "bull's eye")
 */

import { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";
import { DESIGN_TOKENS } from "../../../../theme/designTokens";

const { colors } = DESIGN_TOKENS;

export interface FinalNodeData {
  label: string;
  returnValue?: string;
}

export const FinalFlowNode = memo(({ data, selected }: NodeProps<FinalNodeData>) => {
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
          width: 28,
          height: 28,
          borderRadius: "50%",
          backgroundColor: colors.base.panel,
          border: selected ? `3px solid ${colors.primary.light}` : `2px solid ${colors.primary.main}`,
          boxShadow: selected ? `0 0 8px ${colors.primary.main}` : "none",
          cursor: "pointer",
          transition: "all 0.15s ease",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
        title={data.returnValue ? `Return: ${data.returnValue}` : data.label || "End"}
      >
        {/* Inner filled circle */}
        <div
          style={{
            width: 14,
            height: 14,
            borderRadius: "50%",
            backgroundColor: colors.primary.main,
          }}
        />
      </div>
      {/* No output handle - this is the end */}
    </>
  );
});

FinalFlowNode.displayName = "FinalFlowNode";
