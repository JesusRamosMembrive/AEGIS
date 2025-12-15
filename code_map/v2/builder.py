# SPDX-License-Identifier: MIT
"""
Graph builder for converting CompositionRoot to InstanceGraph.

This module implements Phase 2 of the AEGIS v2 architecture:
- Converts Phase 1 output (CompositionRoot) to graph model (InstanceGraph)
- Generates UUIDs for nodes and edges
- Builds index maps for efficient lookups
- Infers roles based on graph topology
"""

from __future__ import annotations

from typing import Dict, Set
from uuid import uuid4

from .models import (
    CompositionRoot,
    InstanceGraph,
    InstanceInfo,
    InstanceNode,
    InstanceRole,
    WiringEdge,
    WiringInfo,
)


class GraphBuilder:
    """
    Builds an InstanceGraph from a CompositionRoot.

    The builder:
    1. Creates InstanceNode for each InstanceInfo (with UUID)
    2. Creates WiringEdge for each WiringInfo (with UUID)
    3. Builds adjacency lists for graph traversal
    4. Infers roles based on edge connectivity:
       - SOURCE: No incoming edges (generates data)
       - SINK: No outgoing edges (consumes data)
       - PROCESSING: Both incoming and outgoing edges
       - UNKNOWN: No edges (isolated node)
    """

    def build(self, composition_root: CompositionRoot) -> InstanceGraph:
        """
        Convert a CompositionRoot to an InstanceGraph.

        Args:
            composition_root: Phase 1 output with instances and wiring

        Returns:
            InstanceGraph with nodes, edges, indexes, and inferred roles
        """
        graph = InstanceGraph(
            source_file=composition_root.file_path,
            function_name=composition_root.function_name,
        )

        # Step 1: Create nodes with temporary UNKNOWN role
        name_to_id: Dict[str, str] = {}
        for instance in composition_root.instances:
            node = self._create_node(instance)
            graph.add_node(node)
            name_to_id[instance.name] = node.id

        # Step 2: Create edges
        for wiring in composition_root.wiring:
            edge = self._create_edge(wiring, name_to_id)
            if edge is not None:
                graph.add_edge(edge)

        # Step 3: Infer roles based on connectivity
        self._infer_roles(graph)

        return graph

    def _create_node(self, instance: InstanceInfo) -> InstanceNode:
        """Create a graph node from instance info."""
        # Determine the type symbol - prefer actual_type if available
        type_symbol = instance.actual_type or instance.type_name

        # If we have a factory name, we can infer the type from it
        # e.g., createGeneratorModule -> GeneratorModule
        if instance.factory_name and type_symbol == "auto":
            # Try to extract type from factory name
            factory = instance.factory_name
            if factory.startswith("create"):
                type_symbol = factory[6:]  # Remove "create" prefix
            elif factory.startswith("make"):
                type_symbol = factory[4:]  # Remove "make" prefix

        return InstanceNode(
            id=str(uuid4()),
            name=instance.name,
            type_symbol=type_symbol,
            role=InstanceRole.UNKNOWN,  # Will be inferred later
            location=instance.location,
            args=instance.constructor_args,
            config={
                "creation_pattern": instance.creation_pattern.value,
                "factory_name": instance.factory_name,
                "is_pointer": instance.is_pointer,
                "pointer_type": instance.pointer_type,
            },
        )

    def _create_edge(
        self,
        wiring: WiringInfo,
        name_to_id: Dict[str, str],
    ) -> WiringEdge | None:
        """Create a graph edge from wiring info."""
        source_id = name_to_id.get(wiring.source)
        target_id = name_to_id.get(wiring.target)

        if source_id is None or target_id is None:
            # One of the endpoints doesn't exist in the graph
            return None

        return WiringEdge(
            id=str(uuid4()),
            source_id=source_id,
            target_id=target_id,
            method=wiring.method,
            location=wiring.location,
            metadata={
                "wiring_type": wiring.wiring_type,
            } if wiring.wiring_type else {},
        )

    def _infer_roles(self, graph: InstanceGraph) -> None:
        """
        Infer node roles based on edge connectivity.

        Role inference rules:
        - No incoming edges, has outgoing -> SOURCE (data producer)
        - Has incoming edges, no outgoing -> SINK (data consumer)
        - Has both incoming and outgoing -> PROCESSING (transformer)
        - No edges at all -> UNKNOWN (isolated)
        """
        for node in graph.iter_nodes():
            has_incoming = len(graph.incoming.get(node.id, [])) > 0
            has_outgoing = len(graph.outgoing.get(node.id, [])) > 0

            if has_incoming and has_outgoing:
                node.role = InstanceRole.PROCESSING
            elif has_outgoing and not has_incoming:
                node.role = InstanceRole.SOURCE
            elif has_incoming and not has_outgoing:
                node.role = InstanceRole.SINK
            else:
                node.role = InstanceRole.UNKNOWN
