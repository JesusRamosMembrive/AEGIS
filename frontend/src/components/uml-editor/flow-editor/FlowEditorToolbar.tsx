/**
 * FlowEditorToolbar - Node palette for adding activity diagram nodes
 */

import { DESIGN_TOKENS } from "../../../theme/designTokens";
import { useUmlEditorStore } from "../../../state/useUmlEditorStore";
import type { ActivityNodeType } from "../../../api/types";

const { colors, borders } = DESIGN_TOKENS;

// Generate unique ID
const generateId = () => `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;

interface NodeTypeConfig {
  type: ActivityNodeType;
  label: string;
  icon: React.ReactNode;
  description: string;
}

// Node types available in toolbar
const nodeTypes: NodeTypeConfig[] = [
  {
    type: "action",
    label: "Action",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="3" y="6" width="18" height="12" rx="3" />
      </svg>
    ),
    description: "Activity or action step",
  },
  {
    type: "decision",
    label: "Decision",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <polygon points="12,2 22,12 12,22 2,12" />
      </svg>
    ),
    description: "Conditional branching",
  },
  {
    type: "merge",
    label: "Merge",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M6 4L12 12L18 4" />
        <path d="M12 12V20" />
      </svg>
    ),
    description: "Merge multiple flows",
  },
  {
    type: "final",
    label: "Final",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="10" />
        <circle cx="12" cy="12" r="5" fill="currentColor" />
      </svg>
    ),
    description: "End point of flow",
  },
];

interface FlowEditorToolbarProps {
  classId: string;
  methodId: string;
}

export const FlowEditorToolbar = ({ classId, methodId }: FlowEditorToolbarProps) => {
  const { getActivityDiagram, addActivityNode } = useUmlEditorStore();

  const handleAddNode = (type: ActivityNodeType) => {
    const diagram = getActivityDiagram(classId, methodId);
    if (!diagram) return;

    // Calculate position for new node (find bottom-most node and add below)
    const existingNodes = diagram.nodes;
    let newY = 150;
    let newX = 250;

    if (existingNodes.length > 0) {
      const maxY = Math.max(...existingNodes.map((n) => n.position.y));
      newY = maxY + 100;

      // Center horizontally based on existing nodes
      const avgX = existingNodes.reduce((sum, n) => sum + n.position.x, 0) / existingNodes.length;
      newX = avgX;
    }

    const newNode = {
      id: generateId(),
      type,
      position: { x: newX, y: newY },
      label: type === "action" ? "New Action" : type === "decision" ? "Condition?" : type === "merge" ? "Merge" : "End",
    };

    addActivityNode(classId, methodId, newNode);
  };

  return (
    <div
      style={{
        display: "flex",
        gap: 8,
        padding: "8px 16px",
        backgroundColor: colors.base.panel,
        borderBottom: borders.default,
        flexWrap: "wrap",
        alignItems: "center",
      }}
    >
      <span
        style={{
          fontSize: 11,
          fontWeight: 600,
          color: colors.text.muted,
          textTransform: "uppercase",
          letterSpacing: "0.5px",
          marginRight: 8,
        }}
      >
        Add Node:
      </span>
      {nodeTypes.map((nodeType) => (
        <button
          key={nodeType.type}
          onClick={() => handleAddNode(nodeType.type)}
          title={nodeType.description}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            padding: "6px 12px",
            backgroundColor: colors.base.elevated,
            color: colors.text.primary,
            border: borders.default,
            borderRadius: 6,
            cursor: "pointer",
            fontSize: 12,
            fontWeight: 500,
            transition: "all 0.15s ease",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = colors.primary.dark;
            e.currentTarget.style.borderColor = colors.primary.main;
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = colors.base.elevated;
            e.currentTarget.style.borderColor = colors.base.elevated;
          }}
        >
          {nodeType.icon}
          {nodeType.label}
        </button>
      ))}
    </div>
  );
};
