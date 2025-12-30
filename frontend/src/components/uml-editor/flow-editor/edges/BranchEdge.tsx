/**
 * BranchEdge - Conditional branch edge from decision nodes
 * Styled based on true/false condition with guard labels
 */

import { memo } from "react";
import { BaseEdge, EdgeLabelRenderer, getBezierPath, type EdgeProps } from "reactflow";
import { DESIGN_TOKENS } from "../../../../theme/designTokens";

const { colors } = DESIGN_TOKENS;

export interface BranchEdgeData {
  label?: string;
  guard?: string;
  branch?: "true" | "false" | "default";
}

export const BranchEdge = memo(({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  selected,
  markerEnd,
}: EdgeProps<BranchEdgeData>) => {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  // Color based on branch type
  const getBranchColor = () => {
    if (selected) return colors.primary.main;
    switch (data?.branch) {
      case "true":
        return colors.semantic.success;
      case "false":
        return colors.semantic.error;
      default:
        return colors.text.muted;
    }
  };

  const branchColor = getBranchColor();
  const displayLabel = data?.guard || data?.label || (data?.branch === "true" ? "[true]" : data?.branch === "false" ? "[false]" : "");

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        style={{
          stroke: branchColor,
          strokeWidth: selected ? 2.5 : 2,
          strokeDasharray: data?.branch === "default" ? "5,5" : "none",
          transition: "stroke 0.15s ease, stroke-width 0.15s ease",
        }}
      />
      {displayLabel && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: "absolute",
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
              fontSize: 10,
              fontWeight: 600,
              color: branchColor,
              backgroundColor: colors.base.panel,
              padding: "2px 8px",
              borderRadius: 4,
              border: `1px solid ${branchColor}40`,
              pointerEvents: "all",
            }}
            className="nodrag nopan"
          >
            {displayLabel}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
});

BranchEdge.displayName = "BranchEdge";
