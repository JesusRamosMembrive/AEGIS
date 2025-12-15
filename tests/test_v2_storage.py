# SPDX-License-Identifier: MIT
"""Tests for InstanceGraphStore persistence layer."""

import json
import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from code_map.v2.storage import (
    InstanceGraphStore,
    StoredInstanceGraph,
    STORAGE_VERSION,
    _parse_datetime,
)
from code_map.v2.models import (
    InstanceGraph,
    InstanceNode,
    InstanceRole,
    Location,
    WiringEdge,
)


class TestStoredInstanceGraph:
    """Tests for StoredInstanceGraph dataclass."""

    def test_to_dict_serialization(self):
        """StoredInstanceGraph can be serialized to dict."""
        now = datetime.now(timezone.utc)
        stored = StoredInstanceGraph(
            id="abc123",
            project_path="/my/project",
            source_file="main.cpp",
            function_name="main",
            analyzed_at=now,
            source_modified_at=now,
            node_count=5,
            edge_count=3,
            graph_data={"nodes": [], "edges": []},
        )

        data = stored.to_dict()

        assert data["id"] == "abc123"
        assert data["project_path"] == "/my/project"
        assert data["source_file"] == "main.cpp"
        assert data["function_name"] == "main"
        assert data["node_count"] == 5
        assert data["edge_count"] == 3
        assert "analyzed_at" in data
        assert "source_modified_at" in data

    def test_from_dict_deserialization(self):
        """StoredInstanceGraph can be deserialized from dict."""
        data = {
            "id": "xyz789",
            "project_path": "/other/project",
            "source_file": "src/main.cpp",
            "function_name": "setup",
            "analyzed_at": "2025-01-01T10:00:00+00:00",
            "source_modified_at": "2025-01-01T09:00:00+00:00",
            "node_count": 10,
            "edge_count": 7,
            "graph_data": {"nodes": [{"id": "n1"}]},
        }

        stored = StoredInstanceGraph.from_dict(data)

        assert stored.id == "xyz789"
        assert stored.project_path == "/other/project"
        assert stored.source_file == "src/main.cpp"
        assert stored.function_name == "setup"
        assert stored.node_count == 10
        assert stored.edge_count == 7
        assert stored.graph_data == {"nodes": [{"id": "n1"}]}

    def test_roundtrip_serialization(self):
        """to_dict/from_dict roundtrip preserves data."""
        now = datetime.now(timezone.utc)
        original = StoredInstanceGraph(
            id="roundtrip",
            project_path="/test",
            source_file="test.cpp",
            function_name="main",
            analyzed_at=now,
            source_modified_at=now,
            node_count=2,
            edge_count=1,
            graph_data={"test": "data"},
        )

        restored = StoredInstanceGraph.from_dict(original.to_dict())

        assert restored.id == original.id
        assert restored.project_path == original.project_path
        assert restored.source_file == original.source_file
        assert restored.node_count == original.node_count
        assert restored.graph_data == original.graph_data


class TestParseDatetime:
    """Tests for datetime parsing utility."""

    def test_parse_iso_format(self):
        """Parses standard ISO format."""
        result = _parse_datetime("2025-01-15T12:30:00+00:00")
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 12

    def test_parse_z_suffix(self):
        """Handles Z suffix for UTC."""
        result = _parse_datetime("2025-01-15T12:30:00Z")
        assert result.tzinfo is not None


class TestInstanceGraphStore:
    """Tests for InstanceGraphStore persistence."""

    def test_store_path_default(self, tmp_path: Path):
        """Default store path is .code-map/instance-graphs.json."""
        store = InstanceGraphStore(tmp_path)
        assert store.store_path == tmp_path / ".code-map" / "instance-graphs.json"

    def test_store_path_custom_filename(self, tmp_path: Path):
        """Custom filename is supported."""
        store = InstanceGraphStore(tmp_path, filename="custom.json")
        assert store.store_path == tmp_path / ".code-map" / "custom.json"

    def test_store_path_custom_cache_dir(self, tmp_path: Path):
        """Custom cache directory is supported."""
        cache_dir = tmp_path / "custom-cache"
        store = InstanceGraphStore(tmp_path, cache_dir=cache_dir)
        assert store.store_path == cache_dir / "instance-graphs.json"

    def test_load_empty_returns_empty_list(self, tmp_path: Path):
        """Load returns empty list when file doesn't exist."""
        store = InstanceGraphStore(tmp_path)
        result = store.load()
        assert result == []

    def test_load_invalid_json_returns_empty(self, tmp_path: Path):
        """Load returns empty list for invalid JSON."""
        store = InstanceGraphStore(tmp_path)
        store.meta_dir.mkdir(parents=True, exist_ok=True)
        store.store_path.write_text("not valid json")

        result = store.load()
        assert result == []

    def test_save_creates_directory(self, tmp_path: Path):
        """Save creates meta directory if missing."""
        store = InstanceGraphStore(tmp_path)
        now = datetime.now(timezone.utc)
        graphs = [
            StoredInstanceGraph(
                id="test",
                project_path=str(tmp_path),
                source_file="main.cpp",
                function_name="main",
                analyzed_at=now,
                source_modified_at=now,
                node_count=1,
                edge_count=0,
                graph_data={},
            )
        ]

        store.save(graphs)

        assert store.meta_dir.exists()
        assert store.store_path.exists()

    def test_save_and_load_roundtrip(self, tmp_path: Path):
        """Saved graphs can be loaded back."""
        store = InstanceGraphStore(tmp_path)
        now = datetime.now(timezone.utc)
        graphs = [
            StoredInstanceGraph(
                id="graph1",
                project_path=str(tmp_path),
                source_file="main.cpp",
                function_name="main",
                analyzed_at=now,
                source_modified_at=now,
                node_count=5,
                edge_count=3,
                graph_data={"nodes": ["a", "b"], "edges": ["x"]},
            )
        ]

        store.save(graphs)
        loaded = store.load()

        assert len(loaded) == 1
        assert loaded[0].id == "graph1"
        assert loaded[0].node_count == 5
        assert loaded[0].edge_count == 3
        assert loaded[0].graph_data == {"nodes": ["a", "b"], "edges": ["x"]}

    def test_save_includes_version(self, tmp_path: Path):
        """Saved file includes storage version."""
        store = InstanceGraphStore(tmp_path)
        now = datetime.now(timezone.utc)
        graphs = [
            StoredInstanceGraph(
                id="test",
                project_path=str(tmp_path),
                source_file="main.cpp",
                function_name="main",
                analyzed_at=now,
                source_modified_at=now,
                node_count=0,
                edge_count=0,
                graph_data={},
            )
        ]

        store.save(graphs)

        content = json.loads(store.store_path.read_text())
        assert content["version"] == STORAGE_VERSION

    def test_delete_removes_file(self, tmp_path: Path):
        """Delete removes the storage file."""
        store = InstanceGraphStore(tmp_path)
        now = datetime.now(timezone.utc)
        store.save([
            StoredInstanceGraph(
                id="to-delete",
                project_path=str(tmp_path),
                source_file="main.cpp",
                function_name="main",
                analyzed_at=now,
                source_modified_at=now,
                node_count=0,
                edge_count=0,
                graph_data={},
            )
        ])
        assert store.exists()

        result = store.delete()

        assert result is True
        assert not store.exists()

    def test_delete_nonexistent_returns_false(self, tmp_path: Path):
        """Delete returns False when file doesn't exist."""
        store = InstanceGraphStore(tmp_path)
        result = store.delete()
        assert result is False

    def test_exists_false_initially(self, tmp_path: Path):
        """Exists returns False initially."""
        store = InstanceGraphStore(tmp_path)
        assert not store.exists()

    def test_exists_true_after_save(self, tmp_path: Path):
        """Exists returns True after save."""
        store = InstanceGraphStore(tmp_path)
        now = datetime.now(timezone.utc)
        store.save([
            StoredInstanceGraph(
                id="exists-test",
                project_path=str(tmp_path),
                source_file="main.cpp",
                function_name="main",
                analyzed_at=now,
                source_modified_at=now,
                node_count=0,
                edge_count=0,
                graph_data={},
            )
        ])
        assert store.exists()


class TestInstanceGraphFromDict:
    """Tests for InstanceGraph deserialization."""

    def test_from_dict_empty_graph(self):
        """Empty graph can be deserialized."""
        data = {
            "nodes": [],
            "edges": [],
            "source_file": None,
            "function_name": None,
        }

        graph = InstanceGraph.from_dict(data)

        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0

    def test_from_dict_with_nodes(self):
        """Graph with nodes can be deserialized."""
        data = {
            "nodes": [
                {
                    "id": "n1",
                    "name": "generator",
                    "type_symbol": "GeneratorModule",
                    "role": "source",
                    "location": {
                        "file_path": "/test/main.cpp",
                        "line": 10,
                        "column": 0,
                    },
                }
            ],
            "edges": [],
            "source_file": "/test/main.cpp",
            "function_name": "main",
        }

        graph = InstanceGraph.from_dict(data)

        assert len(graph.nodes) == 1
        node = graph.get_node("n1")
        assert node is not None
        assert node.name == "generator"
        assert node.type_symbol == "GeneratorModule"
        assert node.role == InstanceRole.SOURCE

    def test_from_dict_with_edges(self):
        """Graph with edges can be deserialized."""
        data = {
            "nodes": [
                {
                    "id": "n1",
                    "name": "m1",
                    "type_symbol": "ModuleA",
                    "role": "source",
                    "location": {"file_path": "/test.cpp", "line": 1},
                },
                {
                    "id": "n2",
                    "name": "m2",
                    "type_symbol": "ModuleB",
                    "role": "sink",
                    "location": {"file_path": "/test.cpp", "line": 2},
                },
            ],
            "edges": [
                {
                    "id": "e1",
                    "source_id": "n1",
                    "target_id": "n2",
                    "method": "setNext",
                    "location": {"file_path": "/test.cpp", "line": 3},
                }
            ],
            "source_file": "/test.cpp",
            "function_name": "main",
        }

        graph = InstanceGraph.from_dict(data)

        assert len(graph.edges) == 1
        edge = graph.get_edge("e1")
        assert edge is not None
        assert edge.source_id == "n1"
        assert edge.target_id == "n2"
        assert edge.method == "setNext"

    def test_from_dict_rebuilds_indexes(self):
        """Deserialization rebuilds name_to_id index."""
        data = {
            "nodes": [
                {
                    "id": "uuid-123",
                    "name": "myModule",
                    "type_symbol": "TestModule",
                    "role": "processing",
                    "location": {"file_path": "/test.cpp", "line": 1},
                }
            ],
            "edges": [],
        }

        graph = InstanceGraph.from_dict(data)

        # Should be able to lookup by name
        node = graph.get_node_by_name("myModule")
        assert node is not None
        assert node.id == "uuid-123"

    def test_from_dict_rebuilds_adjacency(self):
        """Deserialization rebuilds adjacency lists."""
        data = {
            "nodes": [
                {
                    "id": "n1",
                    "name": "a",
                    "type_symbol": "A",
                    "role": "source",
                    "location": {"file_path": "/test.cpp", "line": 1},
                },
                {
                    "id": "n2",
                    "name": "b",
                    "type_symbol": "B",
                    "role": "sink",
                    "location": {"file_path": "/test.cpp", "line": 2},
                },
            ],
            "edges": [
                {
                    "id": "e1",
                    "source_id": "n1",
                    "target_id": "n2",
                    "method": "connect",
                    "location": {"file_path": "/test.cpp", "line": 3},
                }
            ],
        }

        graph = InstanceGraph.from_dict(data)

        # Should be able to traverse edges
        outgoing = graph.get_outgoing_edges("n1")
        assert len(outgoing) == 1
        assert outgoing[0].target_id == "n2"

        incoming = graph.get_incoming_edges("n2")
        assert len(incoming) == 1
        assert incoming[0].source_id == "n1"

    def test_roundtrip_to_dict_from_dict(self):
        """to_dict/from_dict roundtrip preserves graph structure."""
        # Create a graph
        graph = InstanceGraph(
            source_file=Path("/project/main.cpp"),
            function_name="main",
        )
        node1 = InstanceNode(
            id="node-1",
            name="producer",
            type_symbol="ProducerModule",
            role=InstanceRole.SOURCE,
            location=Location(file_path=Path("/project/main.cpp"), line=10),
        )
        node2 = InstanceNode(
            id="node-2",
            name="consumer",
            type_symbol="ConsumerModule",
            role=InstanceRole.SINK,
            location=Location(file_path=Path("/project/main.cpp"), line=20),
        )
        edge = WiringEdge(
            id="edge-1",
            source_id="node-1",
            target_id="node-2",
            method="setNext",
            location=Location(file_path=Path("/project/main.cpp"), line=30),
        )
        graph.add_node(node1)
        graph.add_node(node2)
        graph.add_edge(edge)

        # Roundtrip
        data = graph.to_dict()
        restored = InstanceGraph.from_dict(data)

        # Verify
        assert len(restored.nodes) == 2
        assert len(restored.edges) == 1
        assert restored.function_name == "main"
        assert restored.get_node_by_name("producer") is not None
        assert restored.get_node_by_name("consumer") is not None
        assert len(restored.get_outgoing_edges("node-1")) == 1
