/**
 * ActivityCanvas - React Flow canvas for editing activity diagrams
 */

import { useCallback, useMemo, useEffect } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  type Node,
  type Edge,
  type OnNodesChange,
  type OnEdgesChange,
  type OnConnect,
  applyNodeChanges,
  applyEdgeChanges,
  addEdge,
  MarkerType,
  ConnectionLineType,
} from "reactflow";
import "reactflow/dist/style.css";

import { useUmlEditorStore } from "../../../state/useUmlEditorStore";
import { DESIGN_TOKENS } from "../../../theme/designTokens";

import { InitialFlowNode } from "./nodes/InitialFlowNode";
import { FinalFlowNode } from "./nodes/FinalFlowNode";
import { ActionFlowNode } from "./nodes/ActionFlowNode";
import { DecisionFlowNode } from "./nodes/DecisionFlowNode";
import { MergeFlowNode } from "./nodes/MergeFlowNode";

import { FlowEdge } from "./edges/FlowEdge";
import { BranchEdge } from "./edges/BranchEdge";

import type { ActivityNode, ActivityEdge, ActivityDiagram } from "../../../api/types";

const { colors } = DESIGN_TOKENS;

// Register custom node types
const nodeTypes = {
  initial: InitialFlowNode,
  final: FinalFlowNode,
  action: ActionFlowNode,
  decision: DecisionFlowNode,
  merge: MergeFlowNode,
};

// Register custom edge types
const edgeTypes = {
  flow: FlowEdge,
  branch: BranchEdge,
};

// Default edge options
const defaultEdgeOptions = {
  type: "flow",
  markerEnd: {
    type: MarkerType.ArrowClosed,
    color: colors.text.muted,
    width: 20,
    height: 20,
  },
  style: {
    stroke: colors.text.muted,
    strokeWidth: 1.5,
  },
};

interface ActivityCanvasProps {
  classId: string;
  methodId: string;
}

// Convert activity nodes to React Flow nodes
const activityNodesToFlowNodes = (activityNodes: ActivityNode[]): Node[] => {
  return activityNodes.map((node) => ({
    id: node.id,
    type: node.type,
    position: node.position,
    data: {
      label: node.label,
      description: (node as any).description,
      pseudocode: (node as any).pseudocode,
      condition: (node as any).condition,
      branches: (node as any).branches,
      returnValue: (node as any).returnValue,
      swimlaneId: (node as any).swimlaneId,
    },
  }));
};

// Convert activity edges to React Flow edges
const activityEdgesToFlowEdges = (activityEdges: ActivityEdge[]): Edge[] => {
  return activityEdges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    sourceHandle: edge.sourceHandle,
    targetHandle: edge.targetHandle,
    type: edge.type === "branch" ? "branch" : "flow",
    data: {
      label: edge.label,
      guard: edge.guard,
      branch: edge.branch,
    },
    markerEnd: {
      type: MarkerType.ArrowClosed,
      color: edge.type === "branch"
        ? (edge.branch === "true" ? colors.semantic.success : edge.branch === "false" ? colors.semantic.error : colors.text.muted)
        : colors.text.muted,
      width: 20,
      height: 20,
    },
  }));
};

// Convert React Flow nodes back to activity nodes
const flowNodesToActivityNodes = (flowNodes: Node[]): ActivityNode[] => {
  return flowNodes.map((node) => ({
    id: node.id,
    type: node.type as ActivityNode["type"],
    position: node.position,
    label: node.data?.label || "",
    description: node.data?.description,
    pseudocode: node.data?.pseudocode,
    condition: node.data?.condition,
    branches: node.data?.branches,
    returnValue: node.data?.returnValue,
    swimlaneId: node.data?.swimlaneId,
  }));
};

// Convert React Flow edges back to activity edges
const flowEdgesToActivityEdges = (flowEdges: Edge[]): ActivityEdge[] => {
  return flowEdges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    sourceHandle: edge.sourceHandle,
    targetHandle: edge.targetHandle,
    type: (edge.type === "branch" ? "branch" : "flow") as ActivityEdge["type"],
    label: edge.data?.label,
    guard: edge.data?.guard,
    branch: edge.data?.branch,
  }));
};

// Generate unique ID
const generateId = () => `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;

export const ActivityCanvas = ({ classId, methodId }: ActivityCanvasProps) => {
  const {
    getActivityDiagram,
    setActivityDiagram,
    initializeActivityDiagram,
    selectedFlowNodeId,
    selectedFlowEdgeId,
    setSelectedFlowNode,
    setSelectedFlowEdge,
  } = useUmlEditorStore();

  // Initialize diagram if needed
  useEffect(() => {
    initializeActivityDiagram(classId, methodId);
  }, [classId, methodId, initializeActivityDiagram]);

  const diagram = getActivityDiagram(classId, methodId);

  // Convert to React Flow format
  const nodes = useMemo(() => {
    if (!diagram?.nodes) return [];
    return activityNodesToFlowNodes(diagram.nodes);
  }, [diagram?.nodes]);

  const edges = useMemo(() => {
    if (!diagram?.edges) return [];
    return activityEdgesToFlowEdges(diagram.edges);
  }, [diagram?.edges]);

  // Handle node changes (position, selection)
  const onNodesChange: OnNodesChange = useCallback(
    (changes) => {
      if (!diagram) return;

      const updatedNodes = applyNodeChanges(changes, nodes);
      const activityNodes = flowNodesToActivityNodes(updatedNodes);

      setActivityDiagram(classId, methodId, {
        ...diagram,
        nodes: activityNodes,
      });

      // Handle selection
      changes.forEach((change) => {
        if (change.type === "select") {
          if (change.selected) {
            setSelectedFlowNode(change.id);
            setSelectedFlowEdge(null);
          } else if (selectedFlowNodeId === change.id) {
            setSelectedFlowNode(null);
          }
        }
      });
    },
    [diagram, nodes, classId, methodId, setActivityDiagram, selectedFlowNodeId, setSelectedFlowNode, setSelectedFlowEdge]
  );

  // Handle edge changes
  const onEdgesChange: OnEdgesChange = useCallback(
    (changes) => {
      if (!diagram) return;

      const updatedEdges = applyEdgeChanges(changes, edges);
      const activityEdges = flowEdgesToActivityEdges(updatedEdges);

      setActivityDiagram(classId, methodId, {
        ...diagram,
        edges: activityEdges,
      });

      // Handle selection
      changes.forEach((change) => {
        if (change.type === "select") {
          if (change.selected) {
            setSelectedFlowEdge(change.id);
            setSelectedFlowNode(null);
          } else if (selectedFlowEdgeId === change.id) {
            setSelectedFlowEdge(null);
          }
        }
      });
    },
    [diagram, edges, classId, methodId, setActivityDiagram, selectedFlowEdgeId, setSelectedFlowEdge, setSelectedFlowNode]
  );

  // Handle new connections
  const onConnect: OnConnect = useCallback(
    (connection) => {
      if (!diagram || !connection.source || !connection.target) return;

      // Determine edge type based on source handle
      const isFromDecision = connection.sourceHandle === "true" || connection.sourceHandle === "false";

      const newEdge: ActivityEdge = {
        id: generateId(),
        source: connection.source,
        target: connection.target,
        sourceHandle: connection.sourceHandle || undefined,
        targetHandle: connection.targetHandle || undefined,
        type: isFromDecision ? "branch" : "flow",
        branch: isFromDecision ? (connection.sourceHandle as "true" | "false") : undefined,
      };

      setActivityDiagram(classId, methodId, {
        ...diagram,
        edges: [...diagram.edges, newEdge],
      });
    },
    [diagram, classId, methodId, setActivityDiagram]
  );

  // Handle keyboard shortcuts
  const onKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      if (event.key === "Delete" || event.key === "Backspace") {
        if (!diagram) return;

        if (selectedFlowNodeId) {
          // Don't delete initial node
          const nodeToDelete = diagram.nodes.find(n => n.id === selectedFlowNodeId);
          if (nodeToDelete?.type === "initial") return;

          // Remove node and its connected edges
          const updatedNodes = diagram.nodes.filter((n) => n.id !== selectedFlowNodeId);
          const updatedEdges = diagram.edges.filter(
            (e) => e.source !== selectedFlowNodeId && e.target !== selectedFlowNodeId
          );

          setActivityDiagram(classId, methodId, {
            ...diagram,
            nodes: updatedNodes,
            edges: updatedEdges,
          });
          setSelectedFlowNode(null);
        } else if (selectedFlowEdgeId) {
          const updatedEdges = diagram.edges.filter((e) => e.id !== selectedFlowEdgeId);
          setActivityDiagram(classId, methodId, {
            ...diagram,
            edges: updatedEdges,
          });
          setSelectedFlowEdge(null);
        }
      }
    },
    [diagram, selectedFlowNodeId, selectedFlowEdgeId, classId, methodId, setActivityDiagram, setSelectedFlowNode, setSelectedFlowEdge]
  );

  return (
    <div
      style={{ width: "100%", height: "100%" }}
      onKeyDown={onKeyDown}
      tabIndex={0}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        defaultEdgeOptions={defaultEdgeOptions}
        connectionLineType={ConnectionLineType.Bezier}
        connectionLineStyle={{ stroke: colors.primary.main, strokeWidth: 2 }}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.2}
        maxZoom={2}
        deleteKeyCode={["Delete", "Backspace"]}
        style={{ backgroundColor: colors.base.background }}
      >
        <Background color={colors.base.elevated} gap={20} size={1} />
        <Controls
          style={{
            backgroundColor: colors.base.panel,
            borderRadius: 8,
            border: `1px solid ${colors.base.elevated}`,
          }}
        />
        <MiniMap
          style={{
            backgroundColor: colors.base.panel,
            borderRadius: 8,
          }}
          nodeColor={(node) => {
            switch (node.type) {
              case "initial":
              case "final":
                return colors.primary.main;
              case "action":
                return colors.base.elevated;
              case "decision":
                return colors.semantic.warning;
              case "merge":
                return colors.text.muted;
              default:
                return colors.base.panel;
            }
          }}
          maskColor={`${colors.base.background}80`}
        />
      </ReactFlow>
    </div>
  );
};
