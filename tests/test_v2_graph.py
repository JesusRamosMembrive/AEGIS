# SPDX-License-Identifier: MIT
"""
Tests for AEGIS v2 graph building and operations.

DoD criteria from Phase 2:
- [ ] InstanceGraph basic operations work (add node, add edge, get methods)
- [ ] Index building works correctly
- [ ] Topological sort produces correct order
- [ ] find_sources and find_sinks work correctly
- [ ] to_react_flow serialization format is correct
- [ ] Role inference produces correct results:
      - m1 = SOURCE (generates, no incoming)
      - m2 = PROCESSING (receives from m1, sends to m3)
      - m3 = SINK (receives, doesn't send)
"""

from pathlib import Path

import pytest

from code_map.v2.models import (
    InstanceGraph,
    InstanceNode,
    InstanceRole,
    Location,
    WiringEdge,
)
from code_map.v2.builder import GraphBuilder

# Test project path
ACTIA_PROJECT = Path("/home/jesusramos/Workspace/Actia Prueba Tecnica")


class TestInstanceGraphBasicOperations:
    """Test InstanceGraph basic CRUD operations."""

    @pytest.fixture
    def empty_graph(self) -> InstanceGraph:
        """Create an empty graph."""
        return InstanceGraph()

    @pytest.fixture
    def sample_node(self) -> InstanceNode:
        """Create a sample node."""
        return InstanceNode(
            id="node-1",
            name="m1",
            type_symbol="GeneratorModule",
            role=InstanceRole.SOURCE,
            location=Location(file_path=Path("/test.cpp"), line=10),
        )

    @pytest.fixture
    def sample_edge(self) -> WiringEdge:
        """Create a sample edge."""
        return WiringEdge(
            id="edge-1",
            source_id="node-1",
            target_id="node-2",
            method="setNext",
            location=Location(file_path=Path("/test.cpp"), line=20),
        )

    def test_add_node(self, empty_graph: InstanceGraph, sample_node: InstanceNode):
        """Test adding a node to the graph."""
        empty_graph.add_node(sample_node)

        assert len(empty_graph.nodes) == 1
        assert sample_node.id in empty_graph.nodes
        assert empty_graph.nodes[sample_node.id] == sample_node

    def test_add_node_creates_index(self, empty_graph: InstanceGraph, sample_node: InstanceNode):
        """Test that adding a node updates the name_to_id index."""
        empty_graph.add_node(sample_node)

        assert sample_node.name in empty_graph.name_to_id
        assert empty_graph.name_to_id[sample_node.name] == sample_node.id

    def test_add_node_initializes_adjacency_lists(
        self, empty_graph: InstanceGraph, sample_node: InstanceNode
    ):
        """Test that adding a node initializes its adjacency lists."""
        empty_graph.add_node(sample_node)

        assert sample_node.id in empty_graph.outgoing
        assert sample_node.id in empty_graph.incoming
        assert empty_graph.outgoing[sample_node.id] == []
        assert empty_graph.incoming[sample_node.id] == []

    def test_get_node(self, empty_graph: InstanceGraph, sample_node: InstanceNode):
        """Test getting a node by ID."""
        empty_graph.add_node(sample_node)

        retrieved = empty_graph.get_node(sample_node.id)
        assert retrieved == sample_node

    def test_get_node_not_found(self, empty_graph: InstanceGraph):
        """Test getting a non-existent node returns None."""
        assert empty_graph.get_node("non-existent") is None

    def test_get_node_by_name(self, empty_graph: InstanceGraph, sample_node: InstanceNode):
        """Test getting a node by name."""
        empty_graph.add_node(sample_node)

        retrieved = empty_graph.get_node_by_name(sample_node.name)
        assert retrieved == sample_node

    def test_get_node_by_name_not_found(self, empty_graph: InstanceGraph):
        """Test getting a non-existent node by name returns None."""
        assert empty_graph.get_node_by_name("non-existent") is None

    def test_add_edge(self, empty_graph: InstanceGraph):
        """Test adding an edge to the graph."""
        # Create two nodes first
        node1 = InstanceNode(
            id="node-1",
            name="m1",
            type_symbol="GeneratorModule",
            role=InstanceRole.SOURCE,
            location=Location(file_path=Path("/test.cpp"), line=10),
        )
        node2 = InstanceNode(
            id="node-2",
            name="m2",
            type_symbol="FilterModule",
            role=InstanceRole.PROCESSING,
            location=Location(file_path=Path("/test.cpp"), line=11),
        )
        empty_graph.add_node(node1)
        empty_graph.add_node(node2)

        # Add edge
        edge = WiringEdge(
            id="edge-1",
            source_id="node-1",
            target_id="node-2",
            method="setNext",
            location=Location(file_path=Path("/test.cpp"), line=20),
        )
        empty_graph.add_edge(edge)

        assert len(empty_graph.edges) == 1
        assert edge.id in empty_graph.edges

    def test_add_edge_updates_adjacency_lists(self, empty_graph: InstanceGraph):
        """Test that adding an edge updates the adjacency lists."""
        # Create two nodes first
        node1 = InstanceNode(
            id="node-1",
            name="m1",
            type_symbol="GeneratorModule",
            role=InstanceRole.SOURCE,
            location=Location(file_path=Path("/test.cpp"), line=10),
        )
        node2 = InstanceNode(
            id="node-2",
            name="m2",
            type_symbol="FilterModule",
            role=InstanceRole.PROCESSING,
            location=Location(file_path=Path("/test.cpp"), line=11),
        )
        empty_graph.add_node(node1)
        empty_graph.add_node(node2)

        # Add edge
        edge = WiringEdge(
            id="edge-1",
            source_id="node-1",
            target_id="node-2",
            method="setNext",
            location=Location(file_path=Path("/test.cpp"), line=20),
        )
        empty_graph.add_edge(edge)

        # Check outgoing from node1
        assert edge.id in empty_graph.outgoing["node-1"]
        # Check incoming to node2
        assert edge.id in empty_graph.incoming["node-2"]

    def test_get_edge(self, empty_graph: InstanceGraph, sample_edge: WiringEdge):
        """Test getting an edge by ID."""
        # Need to set up adjacency lists first
        empty_graph.outgoing["node-1"] = []
        empty_graph.incoming["node-2"] = []
        empty_graph.add_edge(sample_edge)

        retrieved = empty_graph.get_edge(sample_edge.id)
        assert retrieved == sample_edge

    def test_get_edge_not_found(self, empty_graph: InstanceGraph):
        """Test getting a non-existent edge returns None."""
        assert empty_graph.get_edge("non-existent") is None

    def test_get_outgoing_edges(self, empty_graph: InstanceGraph):
        """Test getting outgoing edges from a node."""
        # Setup graph with nodes and edges
        node1 = InstanceNode(
            id="node-1",
            name="m1",
            type_symbol="GeneratorModule",
            role=InstanceRole.SOURCE,
            location=Location(file_path=Path("/test.cpp"), line=10),
        )
        node2 = InstanceNode(
            id="node-2",
            name="m2",
            type_symbol="FilterModule",
            role=InstanceRole.PROCESSING,
            location=Location(file_path=Path("/test.cpp"), line=11),
        )
        empty_graph.add_node(node1)
        empty_graph.add_node(node2)

        edge = WiringEdge(
            id="edge-1",
            source_id="node-1",
            target_id="node-2",
            method="setNext",
            location=Location(file_path=Path("/test.cpp"), line=20),
        )
        empty_graph.add_edge(edge)

        outgoing = empty_graph.get_outgoing_edges("node-1")
        assert len(outgoing) == 1
        assert outgoing[0] == edge

    def test_get_incoming_edges(self, empty_graph: InstanceGraph):
        """Test getting incoming edges to a node."""
        # Setup graph with nodes and edges
        node1 = InstanceNode(
            id="node-1",
            name="m1",
            type_symbol="GeneratorModule",
            role=InstanceRole.SOURCE,
            location=Location(file_path=Path("/test.cpp"), line=10),
        )
        node2 = InstanceNode(
            id="node-2",
            name="m2",
            type_symbol="FilterModule",
            role=InstanceRole.PROCESSING,
            location=Location(file_path=Path("/test.cpp"), line=11),
        )
        empty_graph.add_node(node1)
        empty_graph.add_node(node2)

        edge = WiringEdge(
            id="edge-1",
            source_id="node-1",
            target_id="node-2",
            method="setNext",
            location=Location(file_path=Path("/test.cpp"), line=20),
        )
        empty_graph.add_edge(edge)

        incoming = empty_graph.get_incoming_edges("node-2")
        assert len(incoming) == 1
        assert incoming[0] == edge


class TestInstanceGraphFindOperations:
    """Test graph traversal and search operations."""

    @pytest.fixture
    def chain_graph(self) -> InstanceGraph:
        """Create a chain graph: m1 -> m2 -> m3."""
        graph = InstanceGraph()

        # Create nodes
        m1 = InstanceNode(
            id="id-m1",
            name="m1",
            type_symbol="GeneratorModule",
            role=InstanceRole.SOURCE,
            location=Location(file_path=Path("/test.cpp"), line=10),
        )
        m2 = InstanceNode(
            id="id-m2",
            name="m2",
            type_symbol="FilterModule",
            role=InstanceRole.PROCESSING,
            location=Location(file_path=Path("/test.cpp"), line=11),
        )
        m3 = InstanceNode(
            id="id-m3",
            name="m3",
            type_symbol="PrinterModule",
            role=InstanceRole.SINK,
            location=Location(file_path=Path("/test.cpp"), line=12),
        )

        graph.add_node(m1)
        graph.add_node(m2)
        graph.add_node(m3)

        # Create edges: m1 -> m2 -> m3
        edge1 = WiringEdge(
            id="edge-1",
            source_id="id-m1",
            target_id="id-m2",
            method="setNext",
            location=Location(file_path=Path("/test.cpp"), line=20),
        )
        edge2 = WiringEdge(
            id="edge-2",
            source_id="id-m2",
            target_id="id-m3",
            method="setNext",
            location=Location(file_path=Path("/test.cpp"), line=21),
        )

        graph.add_edge(edge1)
        graph.add_edge(edge2)

        return graph

    def test_find_sources(self, chain_graph: InstanceGraph):
        """Test finding source nodes (no incoming edges)."""
        sources = chain_graph.find_sources()

        assert len(sources) == 1
        assert sources[0].name == "m1"

    def test_find_sinks(self, chain_graph: InstanceGraph):
        """Test finding sink nodes (no outgoing edges)."""
        sinks = chain_graph.find_sinks()

        assert len(sinks) == 1
        assert sinks[0].name == "m3"

    def test_topological_sort(self, chain_graph: InstanceGraph):
        """Test topological sorting returns nodes in correct order."""
        sorted_nodes = chain_graph.topological_sort()

        assert len(sorted_nodes) == 3
        node_names = [n.name for n in sorted_nodes]
        # m1 must come before m2, m2 must come before m3
        assert node_names.index("m1") < node_names.index("m2")
        assert node_names.index("m2") < node_names.index("m3")

    def test_topological_sort_with_cycle_returns_empty(self):
        """Test topological sort returns empty list for cyclic graph."""
        graph = InstanceGraph()

        # Create two nodes with a cycle: a -> b -> a
        node_a = InstanceNode(
            id="id-a",
            name="a",
            type_symbol="ModuleA",
            role=InstanceRole.PROCESSING,
            location=Location(file_path=Path("/test.cpp"), line=10),
        )
        node_b = InstanceNode(
            id="id-b",
            name="b",
            type_symbol="ModuleB",
            role=InstanceRole.PROCESSING,
            location=Location(file_path=Path("/test.cpp"), line=11),
        )

        graph.add_node(node_a)
        graph.add_node(node_b)

        # Create cycle
        edge1 = WiringEdge(
            id="edge-1",
            source_id="id-a",
            target_id="id-b",
            method="connect",
            location=Location(file_path=Path("/test.cpp"), line=20),
        )
        edge2 = WiringEdge(
            id="edge-2",
            source_id="id-b",
            target_id="id-a",
            method="connect",
            location=Location(file_path=Path("/test.cpp"), line=21),
        )

        graph.add_edge(edge1)
        graph.add_edge(edge2)

        sorted_nodes = graph.topological_sort()
        assert sorted_nodes == []


class TestInstanceGraphSerialization:
    """Test graph serialization methods."""

    @pytest.fixture
    def simple_graph(self) -> InstanceGraph:
        """Create a simple graph for serialization tests."""
        graph = InstanceGraph(
            source_file=Path("/test/main.cpp"),
            function_name="main",
        )

        node1 = InstanceNode(
            id="id-m1",
            name="m1",
            type_symbol="GeneratorModule",
            role=InstanceRole.SOURCE,
            location=Location(file_path=Path("/test/main.cpp"), line=10),
        )
        node2 = InstanceNode(
            id="id-m2",
            name="m2",
            type_symbol="FilterModule",
            role=InstanceRole.SINK,
            location=Location(file_path=Path("/test/main.cpp"), line=11),
        )

        graph.add_node(node1)
        graph.add_node(node2)

        edge = WiringEdge(
            id="edge-1",
            source_id="id-m1",
            target_id="id-m2",
            method="setNext",
            location=Location(file_path=Path("/test/main.cpp"), line=20),
        )
        graph.add_edge(edge)

        return graph

    def test_to_dict(self, simple_graph: InstanceGraph):
        """Test to_dict serialization."""
        data = simple_graph.to_dict()

        assert "nodes" in data
        assert "edges" in data
        assert "source_file" in data
        assert "function_name" in data

        assert len(data["nodes"]) == 2
        assert len(data["edges"]) == 1
        assert data["source_file"] == "/test/main.cpp"
        assert data["function_name"] == "main"

    def test_to_react_flow(self, simple_graph: InstanceGraph):
        """Test React Flow format serialization."""
        rf_data = simple_graph.to_react_flow()

        assert "nodes" in rf_data
        assert "edges" in rf_data

        # Check node format
        assert len(rf_data["nodes"]) == 2
        for node in rf_data["nodes"]:
            assert "id" in node
            assert "type" in node
            assert "data" in node
            assert "position" in node
            assert "x" in node["position"]
            assert "y" in node["position"]
            assert "label" in node["data"]
            assert "role" in node["data"]

        # Check edge format
        assert len(rf_data["edges"]) == 1
        edge = rf_data["edges"][0]
        assert "id" in edge
        assert "source" in edge
        assert "target" in edge
        assert "label" in edge
        assert edge["label"] == "setNext"


class TestGraphBuilder:
    """Test GraphBuilder conversion from CompositionRoot to InstanceGraph."""

    @pytest.fixture
    def extractor(self):
        """Create extractor instance."""
        from code_map.v2.composition import CppCompositionExtractor

        ext = CppCompositionExtractor()
        if not ext.is_available():
            pytest.skip("tree-sitter not available")
        return ext

    @pytest.fixture
    def builder(self) -> GraphBuilder:
        """Create builder instance."""
        return GraphBuilder()

    def test_build_creates_nodes(self, extractor, builder):
        """Test that builder creates nodes for all instances."""
        main_cpp = ACTIA_PROJECT / "main.cpp"
        if not main_cpp.exists():
            pytest.skip("Actia project not found")

        root = extractor.extract(main_cpp)
        assert root is not None

        graph = builder.build(root)

        # Should have at least 3 nodes (m1, m2, m3)
        # Note: May have additional nodes like timeToRunSeconds
        assert len(graph.nodes) >= 3

        # Check all module instances are present
        assert graph.get_node_by_name("m1") is not None
        assert graph.get_node_by_name("m2") is not None
        assert graph.get_node_by_name("m3") is not None

    def test_build_creates_edges(self, extractor, builder):
        """Test that builder creates edges for all wiring."""
        main_cpp = ACTIA_PROJECT / "main.cpp"
        if not main_cpp.exists():
            pytest.skip("Actia project not found")

        root = extractor.extract(main_cpp)
        assert root is not None

        graph = builder.build(root)

        # Should have 2 edges (m1->m2, m2->m3)
        assert len(graph.edges) == 2

    def test_build_nodes_have_uuids(self, extractor, builder):
        """Test that nodes have valid UUID strings."""
        main_cpp = ACTIA_PROJECT / "main.cpp"
        if not main_cpp.exists():
            pytest.skip("Actia project not found")

        root = extractor.extract(main_cpp)
        assert root is not None

        graph = builder.build(root)

        for node in graph.iter_nodes():
            # UUID4 format: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
            assert len(node.id) == 36
            assert node.id.count("-") == 4

    def test_build_edges_have_uuids(self, extractor, builder):
        """Test that edges have valid UUID strings."""
        main_cpp = ACTIA_PROJECT / "main.cpp"
        if not main_cpp.exists():
            pytest.skip("Actia project not found")

        root = extractor.extract(main_cpp)
        assert root is not None

        graph = builder.build(root)

        for edge in graph.iter_edges():
            assert len(edge.id) == 36
            assert edge.id.count("-") == 4

    def test_build_indexes_name_to_id(self, extractor, builder):
        """Test that name_to_id index is built correctly."""
        main_cpp = ACTIA_PROJECT / "main.cpp"
        if not main_cpp.exists():
            pytest.skip("Actia project not found")

        root = extractor.extract(main_cpp)
        assert root is not None

        graph = builder.build(root)

        # Check index has all module names
        assert "m1" in graph.name_to_id
        assert "m2" in graph.name_to_id
        assert "m3" in graph.name_to_id

        # Check index points to correct nodes
        m1_node = graph.get_node(graph.name_to_id["m1"])
        assert m1_node is not None
        assert m1_node.name == "m1"

    def test_build_adjacency_lists(self, extractor, builder):
        """Test that adjacency lists are built correctly."""
        main_cpp = ACTIA_PROJECT / "main.cpp"
        if not main_cpp.exists():
            pytest.skip("Actia project not found")

        root = extractor.extract(main_cpp)
        assert root is not None

        graph = builder.build(root)

        # m1 should have outgoing edge
        m1 = graph.get_node_by_name("m1")
        assert m1 is not None
        assert len(graph.outgoing.get(m1.id, [])) == 1
        assert len(graph.incoming.get(m1.id, [])) == 0

        # m2 should have both incoming and outgoing
        m2 = graph.get_node_by_name("m2")
        assert m2 is not None
        assert len(graph.outgoing.get(m2.id, [])) == 1
        assert len(graph.incoming.get(m2.id, [])) == 1

        # m3 should have only incoming
        m3 = graph.get_node_by_name("m3")
        assert m3 is not None
        assert len(graph.outgoing.get(m3.id, [])) == 0
        assert len(graph.incoming.get(m3.id, [])) == 1


class TestRoleInferenceDoD:
    """
    DoD Test: Role inference produces correct results for Actia project.

    This is the critical Definition of Done test:
    - m1 = SOURCE (generates, no incoming edges)
    - m2 = PROCESSING (receives from m1, sends to m3)
    - m3 = SINK (receives, doesn't send)
    """

    @pytest.fixture
    def extractor(self):
        """Create extractor instance."""
        from code_map.v2.composition import CppCompositionExtractor

        ext = CppCompositionExtractor()
        if not ext.is_available():
            pytest.skip("tree-sitter not available")
        return ext

    @pytest.fixture
    def builder(self) -> GraphBuilder:
        """Create builder instance."""
        return GraphBuilder()

    def test_role_inference_actia_dod(self, extractor, builder):
        """
        DoD: Verify role inference for Actia project produces correct results.

        Expected roles:
        - m1 = SOURCE (generates data, no incoming edges)
        - m2 = PROCESSING (receives from m1, sends to m3)
        - m3 = SINK (receives data, doesn't send)
        """
        main_cpp = ACTIA_PROJECT / "main.cpp"
        if not main_cpp.exists():
            pytest.skip("Actia project not found")

        root = extractor.extract(main_cpp)
        assert root is not None

        graph = builder.build(root)

        # Verify m1 is SOURCE
        m1 = graph.get_node_by_name("m1")
        assert m1 is not None, "m1 node not found"
        assert m1.role == InstanceRole.SOURCE, f"m1 should be SOURCE, got {m1.role}"

        # Verify m2 is PROCESSING
        m2 = graph.get_node_by_name("m2")
        assert m2 is not None, "m2 node not found"
        assert m2.role == InstanceRole.PROCESSING, f"m2 should be PROCESSING, got {m2.role}"

        # Verify m3 is SINK
        m3 = graph.get_node_by_name("m3")
        assert m3 is not None, "m3 node not found"
        assert m3.role == InstanceRole.SINK, f"m3 should be SINK, got {m3.role}"

    def test_role_inference_isolated_node(self, builder):
        """Test that isolated nodes (no edges) get UNKNOWN role."""
        from code_map.v2.models import (
            CompositionRoot,
            InstanceInfo,
            Location,
            CreationPattern,
        )

        # Create a composition root with one instance and no wiring
        root = CompositionRoot(
            file_path=Path("/test.cpp"),
            function_name="main",
            location=Location(file_path=Path("/test.cpp"), line=1),
            instances=[
                InstanceInfo(
                    name="isolated",
                    type_name="auto",
                    location=Location(file_path=Path("/test.cpp"), line=10),
                    creation_pattern=CreationPattern.FACTORY,
                )
            ],
            wiring=[],
        )

        graph = builder.build(root)

        isolated = graph.get_node_by_name("isolated")
        assert isolated is not None
        assert isolated.role == InstanceRole.UNKNOWN

    def test_role_inference_source_only(self, builder):
        """Test role inference for a node with only outgoing edges."""
        from code_map.v2.models import (
            CompositionRoot,
            InstanceInfo,
            WiringInfo,
            Location,
            CreationPattern,
        )

        # Create: source -> sink
        root = CompositionRoot(
            file_path=Path("/test.cpp"),
            function_name="main",
            location=Location(file_path=Path("/test.cpp"), line=1),
            instances=[
                InstanceInfo(
                    name="source",
                    type_name="auto",
                    location=Location(file_path=Path("/test.cpp"), line=10),
                    creation_pattern=CreationPattern.FACTORY,
                ),
                InstanceInfo(
                    name="sink",
                    type_name="auto",
                    location=Location(file_path=Path("/test.cpp"), line=11),
                    creation_pattern=CreationPattern.FACTORY,
                ),
            ],
            wiring=[
                WiringInfo(
                    source="source",
                    target="sink",
                    method="setNext",
                    location=Location(file_path=Path("/test.cpp"), line=20),
                ),
            ],
        )

        graph = builder.build(root)

        source = graph.get_node_by_name("source")
        assert source is not None
        assert source.role == InstanceRole.SOURCE

        sink = graph.get_node_by_name("sink")
        assert sink is not None
        assert sink.role == InstanceRole.SINK

    def test_role_inference_processing(self, builder):
        """Test role inference for a node with both incoming and outgoing edges."""
        from code_map.v2.models import (
            CompositionRoot,
            InstanceInfo,
            WiringInfo,
            Location,
            CreationPattern,
        )

        # Create: a -> processor -> b
        root = CompositionRoot(
            file_path=Path("/test.cpp"),
            function_name="main",
            location=Location(file_path=Path("/test.cpp"), line=1),
            instances=[
                InstanceInfo(
                    name="a",
                    type_name="auto",
                    location=Location(file_path=Path("/test.cpp"), line=10),
                    creation_pattern=CreationPattern.FACTORY,
                ),
                InstanceInfo(
                    name="processor",
                    type_name="auto",
                    location=Location(file_path=Path("/test.cpp"), line=11),
                    creation_pattern=CreationPattern.FACTORY,
                ),
                InstanceInfo(
                    name="b",
                    type_name="auto",
                    location=Location(file_path=Path("/test.cpp"), line=12),
                    creation_pattern=CreationPattern.FACTORY,
                ),
            ],
            wiring=[
                WiringInfo(
                    source="a",
                    target="processor",
                    method="setNext",
                    location=Location(file_path=Path("/test.cpp"), line=20),
                ),
                WiringInfo(
                    source="processor",
                    target="b",
                    method="setNext",
                    location=Location(file_path=Path("/test.cpp"), line=21),
                ),
            ],
        )

        graph = builder.build(root)

        processor = graph.get_node_by_name("processor")
        assert processor is not None
        assert processor.role == InstanceRole.PROCESSING


class TestGraphBuilderTypeInference:
    """Test type symbol inference in GraphBuilder."""

    @pytest.fixture
    def builder(self) -> GraphBuilder:
        """Create builder instance."""
        return GraphBuilder()

    def test_type_symbol_from_factory_name(self, builder):
        """Test that type_symbol is inferred from factory name when type is auto."""
        from code_map.v2.models import (
            CompositionRoot,
            InstanceInfo,
            Location,
            CreationPattern,
        )

        root = CompositionRoot(
            file_path=Path("/test.cpp"),
            function_name="main",
            location=Location(file_path=Path("/test.cpp"), line=1),
            instances=[
                InstanceInfo(
                    name="m1",
                    type_name="auto",
                    location=Location(file_path=Path("/test.cpp"), line=10),
                    creation_pattern=CreationPattern.FACTORY,
                    factory_name="createGeneratorModule",
                ),
            ],
            wiring=[],
        )

        graph = builder.build(root)

        m1 = graph.get_node_by_name("m1")
        assert m1 is not None
        # Should extract "GeneratorModule" from "createGeneratorModule"
        assert m1.type_symbol == "GeneratorModule"

    def test_type_symbol_from_actual_type(self, builder):
        """Test that type_symbol uses actual_type when available."""
        from code_map.v2.models import (
            CompositionRoot,
            InstanceInfo,
            Location,
            CreationPattern,
        )

        root = CompositionRoot(
            file_path=Path("/test.cpp"),
            function_name="main",
            location=Location(file_path=Path("/test.cpp"), line=1),
            instances=[
                InstanceInfo(
                    name="m1",
                    type_name="auto",
                    actual_type="ConcreteModule",
                    location=Location(file_path=Path("/test.cpp"), line=10),
                    creation_pattern=CreationPattern.MAKE_UNIQUE,
                ),
            ],
            wiring=[],
        )

        graph = builder.build(root)

        m1 = graph.get_node_by_name("m1")
        assert m1 is not None
        assert m1.type_symbol == "ConcreteModule"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
