# SPDX-License-Identifier: MIT
"""
Data models for Call Flow Graph.

Represents function/method call chains for visualization in React Flow.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional


@dataclass
class CallNode:
    """
    A node in the call flow graph representing a function or method.

    Attributes:
        id: Unique identifier (typically file:line:name)
        name: Simple function/method name
        qualified_name: Full qualified name including class (e.g., "MainWindow.on_click")
        file_path: Path to the source file
        line: Line number where the function is defined
        kind: Type of callable ("function", "method", "external", "builtin")
        is_entry_point: True if this is the starting point of the graph
        depth: Distance from entry point (0 = entry point)
        docstring: First line of docstring if available
    """

    id: str
    name: str
    qualified_name: str
    file_path: Optional[Path] = None
    line: int = 0
    kind: str = "function"  # function | method | external | builtin
    is_entry_point: bool = False
    depth: int = 0
    docstring: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "qualified_name": self.qualified_name,
            "file_path": str(self.file_path) if self.file_path else None,
            "line": self.line,
            "kind": self.kind,
            "is_entry_point": self.is_entry_point,
            "depth": self.depth,
            "docstring": self.docstring,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CallNode":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            qualified_name=data["qualified_name"],
            file_path=Path(data["file_path"]) if data.get("file_path") else None,
            line=data.get("line", 0),
            kind=data.get("kind", "function"),
            is_entry_point=data.get("is_entry_point", False),
            depth=data.get("depth", 0),
            docstring=data.get("docstring"),
        )


@dataclass
class CallEdge:
    """
    An edge representing a function call from source to target.

    Attributes:
        source_id: ID of the calling function
        target_id: ID of the called function
        call_site_line: Line number where the call occurs
        call_type: Type of call ("direct", "method", "super", "static")
        arguments: Optional list of argument names/values
    """

    source_id: str
    target_id: str
    call_site_line: int
    call_type: str = "direct"  # direct | method | super | static
    arguments: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "call_site_line": self.call_site_line,
            "call_type": self.call_type,
            "arguments": self.arguments,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CallEdge":
        """Create from dictionary."""
        return cls(
            source_id=data["source_id"],
            target_id=data["target_id"],
            call_site_line=data["call_site_line"],
            call_type=data.get("call_type", "direct"),
            arguments=data.get("arguments"),
        )


@dataclass
class CallGraph:
    """
    Complete call flow graph from an entry point.

    Represents all reachable function calls from a starting function,
    up to a configurable maximum depth.

    Attributes:
        entry_point: ID of the entry point function
        nodes: Dictionary of node_id -> CallNode
        edges: List of call edges
        max_depth: Maximum depth that was requested
        max_depth_reached: True if exploration stopped due to depth limit
        external_calls: List of external calls that were not followed
        source_file: The entry point source file
    """

    entry_point: str
    nodes: Dict[str, CallNode] = field(default_factory=dict)
    edges: List[CallEdge] = field(default_factory=list)
    max_depth: int = 5
    max_depth_reached: bool = False
    external_calls: List[str] = field(default_factory=list)
    source_file: Optional[Path] = None

    def add_node(self, node: CallNode) -> None:
        """Add a node to the graph."""
        self.nodes[node.id] = node

    def add_edge(self, edge: CallEdge) -> None:
        """Add an edge to the graph."""
        self.edges.append(edge)

    def get_node(self, node_id: str) -> Optional[CallNode]:
        """Get a node by ID."""
        return self.nodes.get(node_id)

    def iter_nodes(self) -> Iterator[CallNode]:
        """Iterate over all nodes."""
        yield from self.nodes.values()

    def iter_edges(self) -> Iterator[CallEdge]:
        """Iterate over all edges."""
        yield from self.edges

    def node_count(self) -> int:
        """Get number of nodes."""
        return len(self.nodes)

    def edge_count(self) -> int:
        """Get number of edges."""
        return len(self.edges)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "entry_point": self.entry_point,
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
            "edges": [e.to_dict() for e in self.edges],
            "max_depth": self.max_depth,
            "max_depth_reached": self.max_depth_reached,
            "external_calls": self.external_calls,
            "source_file": str(self.source_file) if self.source_file else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CallGraph":
        """Create from dictionary."""
        graph = cls(
            entry_point=data["entry_point"],
            max_depth=data.get("max_depth", 5),
            max_depth_reached=data.get("max_depth_reached", False),
            external_calls=data.get("external_calls", []),
            source_file=Path(data["source_file"]) if data.get("source_file") else None,
        )
        for nid, ndata in data.get("nodes", {}).items():
            graph.nodes[nid] = CallNode.from_dict(ndata)
        for edata in data.get("edges", []):
            graph.edges.append(CallEdge.from_dict(edata))
        return graph

    def to_react_flow(self) -> Dict[str, Any]:
        """
        Convert to React Flow format for frontend visualization.

        Returns:
            Dictionary with 'nodes' and 'edges' arrays for React Flow.
        """
        react_nodes = []
        react_edges = []

        # Calculate positions (simple left-to-right by depth)
        depth_counts: Dict[int, int] = {}

        for node in self.iter_nodes():
            depth = node.depth
            y_index = depth_counts.get(depth, 0)
            depth_counts[depth] = y_index + 1

            react_nodes.append({
                "id": node.id,
                "type": "callNode",
                "position": {
                    "x": depth * 280,
                    "y": y_index * 120,
                },
                "data": {
                    "label": node.name,
                    "qualifiedName": node.qualified_name,
                    "filePath": str(node.file_path) if node.file_path else None,
                    "line": node.line,
                    "kind": node.kind,
                    "isEntryPoint": node.is_entry_point,
                    "depth": node.depth,
                    "docstring": node.docstring,
                },
            })

        for i, edge in enumerate(self.iter_edges()):
            react_edges.append({
                "id": f"e{i}",
                "source": edge.source_id,
                "target": edge.target_id,
                "type": "smoothstep",
                "animated": edge.source_id == self.entry_point,
                "data": {
                    "callSiteLine": edge.call_site_line,
                    "callType": edge.call_type,
                },
            })

        return {
            "nodes": react_nodes,
            "edges": react_edges,
        }
