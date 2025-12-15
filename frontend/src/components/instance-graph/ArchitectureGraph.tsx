import { useCallback, useMemo } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  type Node,
  type Edge,
  type NodeTypes,
  type EdgeTypes,
} from "reactflow";
import "reactflow/dist/style.css";

import { ModuleInstanceNode } from "./ModuleInstanceNode";
import { WiringEdge } from "./WiringEdge";

interface ArchitectureGraphProps {
  nodes: Node[];
  edges: Edge[];
  onNodeSelect?: (nodeId: string | null) => void;
  onEdgeSelect?: (edgeId: string | null) => void;
}

const nodeTypes: NodeTypes = {
  moduleInstance: ModuleInstanceNode,
};

const edgeTypes: EdgeTypes = {
  wiring: WiringEdge,
};

export function ArchitectureGraph({
  nodes,
  edges,
  onNodeSelect,
  onEdgeSelect,
}: ArchitectureGraphProps) {
  // Map nodes to use our custom type for proper rendering
  const mappedNodes = useMemo(
    () =>
      nodes.map((node) => ({
        ...node,
        type: "moduleInstance",
      })),
    [nodes]
  );

  // Map edges to use our custom type
  const mappedEdges = useMemo(
    () =>
      edges.map((edge) => ({
        ...edge,
        type: "wiring",
      })),
    [edges]
  );

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
    const role = node.data?.role || 'unknown';
    const colors = {
      source: '#10b981',
      processing: '#3b82f6',
      sink: '#a855f7',
      unknown: '#6b7280',
    };
    return colors[role as keyof typeof colors] || colors.unknown;
  }, []);

  return (
    <div style={{ width: '100%', height: '100%', backgroundColor: '#0f172a' }}>
      <ReactFlow
        nodes={mappedNodes}
        edges={mappedEdges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
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
            strokeWidth: 1.5,
            stroke: '#475569',
          },
        }}
        proOptions={{ hideAttribution: true }}
      >
        <Background
          color="#334155"
          gap={16}
          size={1}
          style={{ backgroundColor: '#0f172a' }}
        />
        <Controls
          style={{
            backgroundColor: '#1e293b',
            border: '1px solid #334155',
            borderRadius: '8px',
          }}
        />
        <MiniMap
          nodeColor={minimapNodeColor}
          style={{
            backgroundColor: '#1e293b',
            border: '1px solid #334155',
            borderRadius: '8px',
          }}
          maskColor="rgba(15, 23, 42, 0.7)"
        />
      </ReactFlow>
    </div>
  );
}
