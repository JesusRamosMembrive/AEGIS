export interface InstanceGraphNode {
  id: string;
  type: string;
  data: {
    label: string;
    type: string;
    role: 'source' | 'processing' | 'sink' | 'unknown';
    location: string;
  };
  position: { x: number; y: number };
}

export interface InstanceGraphEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
  type: string;
  animated: boolean;
}

export interface InstanceGraphResponse {
  nodes: InstanceGraphNode[];
  edges: InstanceGraphEdge[];
  metadata: {
    source_file: string;
    function_name: string;
    node_count: number;
    edge_count: number;
  };
}
