import { useCallback, useMemo, useRef, useEffect, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  MarkerType,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type NodeTypes,
  type EdgeTypes,
} from "reactflow";
import "reactflow/dist/style.css";

import { CallFlowNode } from "./CallFlowNode";
import { CallFlowEdge } from "./CallFlowEdge";
import { DecisionFlowNode } from "./DecisionFlowNode";
import { BranchFlowEdge } from "./BranchFlowEdge";
import { DESIGN_TOKENS } from "../../theme/designTokens";

const { colors, borders } = DESIGN_TOKENS;

// Decision node from API (already in React Flow format)
interface DecisionNodeFromAPI {
  id: string;
  type: "decisionNode";
  position: { x: number; y: number };
  data: {
    label: string;
    decisionType: string;
    conditionText: string;
    filePath: string;
    line: number;
    column: number;
    parentCallId: string;
    depth: number;
    branches: Array<{
      branch_id: string;
      label: string;
      condition_text: string;
      is_expanded: boolean;
      call_count: number;
      start_line: number;
      end_line: number;
    }>;
  };
}

interface CallFlowGraphProps {
  nodes: Node[];
  edges: Edge[];
  decisionNodes?: DecisionNodeFromAPI[];
  onNodeSelect?: (nodeId: string | null) => void;
  onEdgeSelect?: (edgeId: string | null) => void;
  onBranchExpand?: (branchId: string) => void;
}

const nodeTypes: NodeTypes = {
  callFlowNode: CallFlowNode,
  decisionNode: DecisionFlowNode,
};

const edgeTypes: EdgeTypes = {
  callFlow: CallFlowEdge,
  branchFlow: BranchFlowEdge,
};

export function CallFlowGraph({
  nodes,
  edges,
  decisionNodes = [],
  onNodeSelect,
  onEdgeSelect,
  onBranchExpand,
}: CallFlowGraphProps) {
  // Use ref to keep a stable reference to onBranchExpand
  // This prevents stale closure issues with React Flow's internal caching
  const onBranchExpandRef = useRef(onBranchExpand);
  useEffect(() => {
    onBranchExpandRef.current = onBranchExpand;
  }, [onBranchExpand]);

  // Stable callback that always uses the latest onBranchExpand
  const stableOnBranchExpand = useCallback((branchId: string) => {
    onBranchExpandRef.current?.(branchId);
  }, []);

  // Map regular call nodes - add draggable property
  const mappedCallNodes = useMemo(
    () =>
      nodes.map((node) => ({
        ...node,
        type: "callFlowNode",
        draggable: true,
      })),
    [nodes]
  );

  // Map decision nodes - they come from API already in React Flow format
  // Just need to add the onBranchExpand callback to their data
  const mappedDecisionNodes = useMemo(
    () =>
      decisionNodes.map((dn) => ({
        ...dn,
        draggable: true,
        data: {
          ...dn.data,
          onBranchExpand: stableOnBranchExpand,
        },
      })),
    [decisionNodes, stableOnBranchExpand]
  );

  // Combine all nodes from props
  const propsNodes = useMemo(
    () => [...mappedCallNodes, ...mappedDecisionNodes],
    [mappedCallNodes, mappedDecisionNodes]
  );

  // Map edges - detect branch edges by checking if target is a decision node
  const propsEdges = useMemo(
    () =>
      edges.map((edge) => {
        const isBranchEdge = edge.data?.branchId != null;
        return {
          ...edge,
          type: isBranchEdge ? "branchFlow" : "callFlow",
          animated: !isBranchEdge, // Only animate regular call edges
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: isBranchEdge
              ? colors.callFlow.decision
              : colors.primary.main,
          },
        };
      }),
    [edges]
  );

  // Use React Flow's state management for draggable nodes
  const [flowNodes, setFlowNodes, onNodesChange] = useNodesState(propsNodes);
  const [flowEdges, setFlowEdges, onEdgesChange] = useEdgesState(propsEdges);

  // Sync with props when they change (new nodes/edges from parent)
  useEffect(() => {
    setFlowNodes(propsNodes);
  }, [propsNodes, setFlowNodes]);

  useEffect(() => {
    setFlowEdges(propsEdges);
  }, [propsEdges, setFlowEdges]);

  const handleNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      onNodeSelect?.(node.id);
    },
    [onNodeSelect]
  );

  const handleEdgeClick = useCallback(
    (_event: React.MouseEvent, edge: Edge) => {
      onEdgeSelect?.(edge.id);
    },
    [onEdgeSelect]
  );

  const handlePaneClick = useCallback(() => {
    onNodeSelect?.(null);
    onEdgeSelect?.(null);
  }, [onNodeSelect, onEdgeSelect]);

  const minimapNodeColor = useCallback((node: Node) => {
    // Decision nodes have a distinct color
    if (node.type === "decisionNode") {
      return colors.callFlow.decision;
    }
    if (node.data?.isEntryPoint) {
      return colors.callFlow.entryPoint;
    }
    const kind = node.data?.kind || "function";
    const kindColors: Record<string, string> = {
      function: colors.callFlow.function,
      method: colors.callFlow.method,
      external: colors.callFlow.external,
      builtin: colors.callFlow.builtin,
      class: colors.callFlow.class,
    };
    return kindColors[kind] || colors.callFlow.function;
  }, []);

  return (
    <div style={{ width: "100%", height: "100%", backgroundColor: colors.base.panel }}>
      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        onEdgeClick={handleEdgeClick}
        onPaneClick={handlePaneClick}
        fitView
        fitViewOptions={{
          padding: 0.2,
          maxZoom: 1,
        }}
        defaultEdgeOptions={{
          animated: true,
          style: {
            strokeWidth: 2,
            stroke: colors.primary.main,
          },
        }}
        proOptions={{ hideAttribution: true }}
      >
        <Background
          color={borders.default}
          gap={16}
          size={1}
          style={{ backgroundColor: colors.base.panel }}
        />
        <Controls
          style={{
            backgroundColor: colors.base.card,
            border: `1px solid ${borders.default}`,
            borderRadius: "8px",
          }}
        />
        <MiniMap
          nodeColor={minimapNodeColor}
          style={{
            backgroundColor: colors.base.card,
            border: `1px solid ${borders.default}`,
            borderRadius: "8px",
          }}
          maskColor={`${colors.base.panel}B3`} // B3 = 70% opacity
        />
      </ReactFlow>
    </div>
  );
}
