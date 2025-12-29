/**
 * DecisionFlowNode - React Flow node for decision points in call flow.
 *
 * Renders as a diamond shape to distinguish from regular call nodes.
 * Shows branches that can be clicked to expand.
 */

import { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";
import { DESIGN_TOKENS } from "../../theme/designTokens";

interface BranchInfo {
  branch_id: string;
  label: string;
  condition_text: string;
  is_expanded: boolean; // Currently visible
  is_loaded?: boolean;  // Data has been fetched (can be toggled)
  call_count: number;
  start_line: number;
  end_line: number;
}

interface DecisionFlowNodeData {
  id: string;
  decisionType: string; // if_else | match_case | try_except | ternary
  conditionText: string;
  filePath?: string | null;
  line: number;
  column: number;
  parentCallId: string;
  branches: BranchInfo[];
  depth: number;
  onBranchExpand?: (branchId: string) => void;
}

const { colors } = DESIGN_TOKENS;

const DECISION_TYPE_LABELS: Record<string, string> = {
  if_else: "IF/ELSE",
  match_case: "MATCH",
  try_except: "TRY/EXCEPT",
  ternary: "TERNARY",
};

const DECISION_TYPE_ICONS: Record<string, string> = {
  if_else: "?",
  match_case: "=",
  try_except: "!",
  ternary: ":",
};

const getBranchColor = (label: string, isExpanded: boolean): string => {
  if (isExpanded) return colors.callFlow.branchExpanded;

  const lowerLabel = label.toLowerCase();
  if (lowerLabel === "true") return colors.callFlow.branchTrue;
  if (lowerLabel === "false") return colors.callFlow.branchFalse;
  if (lowerLabel.startsWith("except")) return colors.callFlow.branchExcept;
  if (lowerLabel.startsWith("case")) return colors.callFlow.branchCase;
  return colors.callFlow.branchUnexpanded;
};

export const DecisionFlowNode = memo(
  ({ data }: NodeProps<DecisionFlowNodeData>) => {
  const typeLabel = DECISION_TYPE_LABELS[data.decisionType] || data.decisionType.toUpperCase();
  const typeIcon = DECISION_TYPE_ICONS[data.decisionType] || "?";

  const handleBranchClick = (e: React.MouseEvent, branchId: string) => {
    e.stopPropagation(); // Prevent ReactFlow from capturing the click as node selection
    // Always call the handler - it now supports toggle (expand/collapse)
    data.onBranchExpand?.(branchId);
  };

  return (
    <>
      {/* Handles for connections */}
      <Handle
        type="target"
        position={Position.Left}
        style={{
          background: colors.callFlow.decision,
          border: `2px solid ${colors.callFlow.decisionBorder}`,
          width: 10,
          height: 10,
        }}
      />
      <Handle
        type="source"
        position={Position.Right}
        style={{
          background: colors.callFlow.decision,
          border: `2px solid ${colors.callFlow.decisionBorder}`,
          width: 10,
          height: 10,
        }}
      />

      {/* Diamond-shaped container */}
      <div
        style={{
          position: "relative",
          width: "160px",
          minHeight: "80px",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          padding: "8px",
        }}
      >
        {/* Diamond background */}
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            width: "60px",
            height: "60px",
            transform: "translate(-50%, -50%) rotate(45deg)",
            background: `linear-gradient(135deg, ${colors.callFlow.decision}20, ${colors.callFlow.decisionBorder}30)`,
            border: `2px solid ${colors.callFlow.decisionBorder}`,
            borderRadius: "4px",
            zIndex: 0,
          }}
        />

        {/* Content on top of diamond */}
        <div
          style={{
            position: "relative",
            zIndex: 1,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "6px",
            padding: "8px",
            background: colors.base.card,
            borderRadius: "8px",
            border: `1px solid ${colors.callFlow.decisionBorder}`,
            minWidth: "140px",
          }}
        >
          {/* Type badge */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "4px",
              padding: "2px 8px",
              background: `${colors.callFlow.decision}30`,
              borderRadius: "4px",
              fontSize: "10px",
              fontWeight: 600,
              color: colors.callFlow.decisionBorder,
              textTransform: "uppercase",
            }}
          >
            <span style={{ fontSize: "12px" }}>{typeIcon}</span>
            {typeLabel}
          </div>

          {/* Condition text */}
          <div
            style={{
              fontSize: "11px",
              fontFamily: "monospace",
              color: colors.text.main,
              maxWidth: "130px",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
              textAlign: "center",
            }}
            title={data.conditionText}
          >
            {data.conditionText.length > 25
              ? `${data.conditionText.substring(0, 22)}...`
              : data.conditionText}
          </div>

          {/* Branches */}
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "4px",
              width: "100%",
            }}
          >
            {data.branches.map((branch) => {
              const isVisible = branch.is_expanded;
              const isLoaded = branch.is_loaded ?? false;
              const branchColor = getBranchColor(branch.label, isVisible);

              // Determine icon and tooltip based on state
              let icon: string;
              let tooltip: string;
              if (isVisible) {
                icon = "−"; // Minus sign to indicate "click to collapse"
                tooltip = `Click to hide: ${branch.condition_text}`;
              } else if (isLoaded) {
                icon = "+"; // Plus sign, but already loaded
                tooltip = `Click to show: ${branch.condition_text}`;
              } else {
                icon = "+"; // Plus sign, needs to load
                tooltip = `Click to expand: ${branch.condition_text}`;
              }

              return (
                <div
                  key={branch.branch_id}
                  onClick={(e) => handleBranchClick(e, branch.branch_id)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "4px 8px",
                    background: `${branchColor}20`,
                    border: `1px solid ${branchColor}`,
                    borderRadius: "4px",
                    cursor: "pointer",
                    transition: "all 0.2s ease",
                    opacity: isVisible ? 1 : 0.8,
                  }}
                  title={tooltip}
                >
                  <span
                    style={{
                      fontSize: "10px",
                      fontWeight: 600,
                      color: branchColor,
                    }}
                  >
                    {branch.label}
                  </span>
                  <span
                    style={{
                      fontSize: "9px",
                      color: colors.text.muted,
                      display: "flex",
                      alignItems: "center",
                      gap: "4px",
                    }}
                  >
                    {branch.call_count > 0 && (
                      <span>{branch.call_count} calls</span>
                    )}
                    <span
                      style={{
                        color: isVisible
                          ? colors.callFlow.branchExpanded
                          : isLoaded
                          ? colors.primary.main
                          : colors.text.muted,
                        fontWeight: 700,
                        fontSize: "12px",
                      }}
                    >
                      {icon}
                    </span>
                  </span>
                </div>
              );
            })}
          </div>

          {/* Line number */}
          <div
            style={{
              fontSize: "9px",
              color: colors.gray[500],
              fontFamily: "monospace",
            }}
          >
            Line {data.line}
          </div>
        </div>
      </div>
    </>
  );
});

DecisionFlowNode.displayName = "DecisionFlowNode";
