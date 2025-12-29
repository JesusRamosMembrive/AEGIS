/**
 * ReturnFlowNode - React Flow node for return statements in call flow.
 *
 * Renders as a rounded rectangle with "return" label and the return value.
 * Makes it clear when a branch just returns a value instead of calling functions.
 */

import { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";
import { DESIGN_TOKENS } from "../../theme/designTokens";

interface ReturnFlowNodeData {
  label: string;
  returnValue: string;
  filePath?: string | null;
  line: number;
  column: number;
  parentCallId: string;
  branchId?: string;
  decisionId?: string;
  depth: number;
}

const { colors, borders } = DESIGN_TOKENS;

// Color for return nodes - use a distinct color (cyan/teal)
const RETURN_COLOR = "#06b6d4"; // cyan-500
const RETURN_COLOR_LIGHT = "#22d3ee"; // cyan-400

export const ReturnFlowNode = memo(
  ({ data }: NodeProps<ReturnFlowNodeData>) => {
    // Truncate return value if too long
    const displayValue =
      data.returnValue.length > 30
        ? `${data.returnValue.substring(0, 27)}...`
        : data.returnValue;

    return (
      <>
        {/* Handles for connections - both positions for layout flexibility */}
        <Handle
          type="target"
          position={Position.Left}
          id="target-left"
          style={{
            background: RETURN_COLOR,
            border: `2px solid ${RETURN_COLOR_LIGHT}`,
            width: 10,
            height: 10,
          }}
        />
        <Handle
          type="target"
          position={Position.Top}
          id="target-top"
          style={{
            background: RETURN_COLOR,
            border: `2px solid ${RETURN_COLOR_LIGHT}`,
            width: 10,
            height: 10,
          }}
        />

        {/* Return node container */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            padding: "10px 14px",
            background: `linear-gradient(135deg, ${colors.base.card}, ${colors.base.panel})`,
            border: `2px solid ${RETURN_COLOR}`,
            borderRadius: "12px",
            minWidth: "100px",
            maxWidth: "180px",
            boxShadow: `0 2px 8px ${RETURN_COLOR}30`,
          }}
        >
          {/* Return keyword badge */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "4px",
              padding: "2px 10px",
              background: `${RETURN_COLOR}25`,
              borderRadius: "10px",
              marginBottom: "6px",
            }}
          >
            <span
              style={{
                fontSize: "10px",
                fontWeight: 700,
                color: RETURN_COLOR_LIGHT,
                textTransform: "uppercase",
                letterSpacing: "0.5px",
              }}
            >
              ← return
            </span>
          </div>

          {/* Return value */}
          <div
            style={{
              fontSize: "12px",
              fontFamily: "monospace",
              fontWeight: 500,
              color: colors.text.main,
              textAlign: "center",
              wordBreak: "break-word",
              padding: "4px 0",
            }}
            title={data.returnValue}
          >
            {displayValue}
          </div>

          {/* Line number */}
          <div
            style={{
              fontSize: "9px",
              color: colors.gray[500],
              fontFamily: "monospace",
              marginTop: "4px",
            }}
          >
            Line {data.line}
          </div>
        </div>
      </>
    );
  }
);

ReturnFlowNode.displayName = "ReturnFlowNode";
