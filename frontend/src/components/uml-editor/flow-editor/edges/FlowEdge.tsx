/**
 * FlowEdge - Standard control flow edge
 * Solid line with arrow
 */

import { memo } from "react";
import { BaseEdge, EdgeLabelRenderer, getBezierPath, type EdgeProps } from "reactflow";
import { DESIGN_TOKENS } from "../../../../theme/designTokens";

const { colors } = DESIGN_TOKENS;

export interface FlowEdgeData {
  label?: string;
}

export const FlowEdge = memo(({
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
}: EdgeProps<FlowEdgeData>) => {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        style={{
          stroke: selected ? colors.primary.main : colors.text.muted,
          strokeWidth: selected ? 2 : 1.5,
          transition: "stroke 0.15s ease, stroke-width 0.15s ease",
        }}
      />
      {data?.label && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: "absolute",
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
              fontSize: 10,
              fontWeight: 500,
              color: colors.text.secondary,
              backgroundColor: colors.base.panel,
              padding: "2px 6px",
              borderRadius: 4,
              pointerEvents: "all",
            }}
            className="nodrag nopan"
          >
            {data.label}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
});

FlowEdge.displayName = "FlowEdge";
