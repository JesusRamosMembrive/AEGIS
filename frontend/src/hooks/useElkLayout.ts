import { useCallback, useState } from "react";
import type { Node, Edge } from "reactflow";
import ELK from "elkjs/lib/elk.bundled.js";

const elk = new ELK();

export type LayoutDirection = "DOWN" | "RIGHT";

// ELK layout options for optimal node placement and edge routing
// Reference: https://www.eclipse.org/elk/reference/options.html
const getElkOptions = (direction: LayoutDirection) => ({
  "elk.algorithm": "layered",
  "elk.direction": direction,
  // Spacing between nodes in the same layer
  "elk.spacing.nodeNode": "50",
  // Spacing between layers (rows/columns)
  "elk.layered.spacing.nodeNodeBetweenLayers": "80",
  // Spacing for edges
  "elk.spacing.edgeNode": "30",
  "elk.spacing.edgeEdge": "20",
  // Edge routing strategy - ORTHOGONAL creates right-angle edges
  "elk.layered.edgeRouting": "ORTHOGONAL",
  // Minimize edge crossings
  "elk.layered.crossingMinimization.strategy": "LAYER_SWEEP",
  // Node placement strategy for compact layout
  "elk.layered.nodePlacement.strategy": "NETWORK_SIMPLEX",
  // Consider node size for better spacing
  "elk.layered.considerModelOrder.strategy": "NODES_AND_EDGES",
});

// Default node dimensions - will be overridden by actual node sizes
const DEFAULT_NODE_WIDTH = 180;
const DEFAULT_NODE_HEIGHT = 60;
const DECISION_NODE_WIDTH = 200;
const DECISION_NODE_HEIGHT = 120;
const RETURN_NODE_WIDTH = 140;
const RETURN_NODE_HEIGHT = 80;

interface LayoutResult {
  nodes: Node[];
  edges: Edge[];
}

/**
 * Hook for automatic graph layout using ELK (Eclipse Layout Kernel).
 *
 * ELK provides sophisticated graph layout algorithms that:
 * - Prevent node overlaps
 * - Minimize edge crossings
 * - Create hierarchical/layered layouts
 *
 * @returns Layout function and loading state
 */
export function useElkLayout() {
  const [isLayouting, setIsLayouting] = useState(false);

  const getLayoutedElements = useCallback(
    async (
      nodes: Node[],
      edges: Edge[],
      direction: LayoutDirection = "DOWN"
    ): Promise<LayoutResult> => {
      if (nodes.length === 0) {
        return { nodes, edges };
      }

      setIsLayouting(true);

      try {
        const isHorizontal = direction === "RIGHT";

        // Build ELK graph structure
        const graph = {
          id: "root",
          layoutOptions: getElkOptions(direction),
          children: nodes.map((node) => {
            // Determine node dimensions based on type
            const isDecision = node.type === "decisionNode";
            const isReturn = node.type === "returnNode";
            let width = DEFAULT_NODE_WIDTH;
            let height = DEFAULT_NODE_HEIGHT;
            if (isDecision) {
              width = DECISION_NODE_WIDTH;
              height = DECISION_NODE_HEIGHT;
            } else if (isReturn) {
              width = RETURN_NODE_WIDTH;
              height = RETURN_NODE_HEIGHT;
            }
            // Allow explicit node dimensions to override defaults
            width = node.width || width;
            height = node.height || height;

            return {
              id: node.id,
              width,
              height,
              // ELK will compute x, y positions
            };
          }),
          edges: edges.map((edge) => ({
            id: edge.id,
            sources: [edge.source],
            targets: [edge.target],
          })),
        };

        const layoutedGraph = await elk.layout(graph);

        // Map ELK results back to React Flow format
        const layoutedNodes = nodes.map((node) => {
          const elkNode = layoutedGraph.children?.find((n) => n.id === node.id);

          if (elkNode) {
            return {
              ...node,
              position: {
                x: elkNode.x ?? node.position.x,
                y: elkNode.y ?? node.position.y,
              },
              // Update handle positions based on layout direction
              targetPosition: isHorizontal ? "left" : "top",
              sourcePosition: isHorizontal ? "right" : "bottom",
            };
          }
          return node;
        });

        return {
          nodes: layoutedNodes as Node[],
          edges, // Edges don't need position updates in React Flow
        };
      } catch (error) {
        console.error("ELK layout failed:", error);
        // Return original nodes/edges on failure
        return { nodes, edges };
      } finally {
        setIsLayouting(false);
      }
    },
    []
  );

  return {
    getLayoutedElements,
    isLayouting,
  };
}
