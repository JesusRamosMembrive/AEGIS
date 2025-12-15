# SPDX-License-Identifier: MIT
"""Tests for InstanceGraphService."""

import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from code_map.v2.service import (
    InstanceGraphService,
    CPP_EXTENSIONS,
    _generate_graph_id,
    _get_file_mtime,
)
from code_map.v2.models import (
    CompositionRoot,
    InstanceGraph,
    InstanceInfo,
    InstanceNode,
    InstanceRole,
    Location,
    CreationPattern,
)


class TestHelperFunctions:
    """Tests for module-level helper functions."""

    def test_generate_graph_id_deterministic(self):
        """Same inputs produce same ID."""
        id1 = _generate_graph_id("/project", "main.cpp", "main")
        id2 = _generate_graph_id("/project", "main.cpp", "main")
        assert id1 == id2

    def test_generate_graph_id_different_for_different_inputs(self):
        """Different inputs produce different IDs."""
        id1 = _generate_graph_id("/project", "main.cpp", "main")
        id2 = _generate_graph_id("/project", "other.cpp", "main")
        id3 = _generate_graph_id("/project", "main.cpp", "setup")
        assert id1 != id2
        assert id1 != id3
        assert id2 != id3

    def test_get_file_mtime_returns_datetime(self, tmp_path: Path):
        """Returns datetime for existing file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        result = _get_file_mtime(test_file)

        assert result is not None
        assert isinstance(result, datetime)
        assert result.tzinfo is not None  # Should be UTC

    def test_get_file_mtime_returns_none_for_missing(self, tmp_path: Path):
        """Returns None for non-existent file."""
        result = _get_file_mtime(tmp_path / "nonexistent.txt")
        assert result is None


class TestCppExtensions:
    """Tests for CPP_EXTENSIONS constant."""

    def test_includes_common_extensions(self):
        """Includes standard C++ file extensions."""
        assert ".cpp" in CPP_EXTENSIONS
        assert ".hpp" in CPP_EXTENSIONS
        assert ".h" in CPP_EXTENSIONS
        assert ".cc" in CPP_EXTENSIONS

    def test_case_sensitivity(self):
        """Extensions should be lowercase."""
        for ext in CPP_EXTENSIONS:
            assert ext == ext.lower()


class TestInstanceGraphService:
    """Tests for InstanceGraphService."""

    @pytest.fixture
    def service(self, tmp_path: Path):
        """Create a service for testing."""
        return InstanceGraphService(tmp_path)

    @pytest.fixture
    def mock_extractor(self):
        """Create a mock extractor that returns a composition root."""
        extractor = MagicMock()
        extractor.is_available.return_value = True
        extractor.extract.return_value = CompositionRoot(
            file_path=Path("/test/main.cpp"),
            function_name="main",
            location=Location(
                file_path=Path("/test/main.cpp"),
                line=1,
            ),
            instances=[
                InstanceInfo(
                    name="module1",
                    type_name="TestModule",
                    location=Location(
                        file_path=Path("/test/main.cpp"),
                        line=10,
                    ),
                    creation_pattern=CreationPattern.FACTORY,
                )
            ],
            wiring=[],
            lifecycle=[],
        )
        return extractor

    def test_init_sets_root(self, tmp_path: Path):
        """Service stores resolved root path."""
        service = InstanceGraphService(tmp_path)
        assert service.root == tmp_path.resolve()

    def test_init_creates_store(self, tmp_path: Path):
        """Service creates storage instance."""
        service = InstanceGraphService(tmp_path)
        assert service.store is not None

    def test_init_creates_extractor_and_builder(self, tmp_path: Path):
        """Service creates extractor and builder."""
        service = InstanceGraphService(tmp_path)
        assert service.extractor is not None
        assert service.builder is not None

    def test_init_empty_cache(self, tmp_path: Path):
        """Service starts with empty cache."""
        service = InstanceGraphService(tmp_path)
        assert len(service._cache) == 0

    @pytest.mark.asyncio
    async def test_startup_sets_started_flag(self, service: InstanceGraphService):
        """Startup sets _started flag."""
        await service.startup()
        assert service._started is True
        await service.shutdown()

    @pytest.mark.asyncio
    async def test_startup_idempotent(self, service: InstanceGraphService):
        """Multiple startup calls are safe."""
        await service.startup()
        await service.startup()  # Should not error
        assert service._started is True
        await service.shutdown()

    @pytest.mark.asyncio
    async def test_shutdown_clears_cache(self, service: InstanceGraphService, tmp_path: Path):
        """Shutdown clears the cache."""
        await service.startup()
        # Manually add a real graph to cache (MagicMock would fail JSON serialization on persist)
        source = tmp_path / "test.cpp"
        mock_graph = InstanceGraph(source_file=source, function_name="main")
        service._cache["test"] = (mock_graph, datetime.now(timezone.utc))

        await service.shutdown()

        assert len(service._cache) == 0
        assert service._started is False

    @pytest.mark.asyncio
    async def test_shutdown_idempotent(self, service: InstanceGraphService):
        """Multiple shutdown calls are safe."""
        await service.startup()
        await service.shutdown()
        await service.shutdown()  # Should not error
        assert service._started is False

    @pytest.mark.asyncio
    async def test_get_graph_returns_none_for_missing_file(
        self, service: InstanceGraphService, tmp_path: Path
    ):
        """get_graph returns None for non-existent file."""
        await service.startup()
        result = await service.get_graph(tmp_path / "nonexistent.cpp")
        assert result is None
        await service.shutdown()

    @pytest.mark.asyncio
    async def test_get_graph_returns_none_when_extractor_unavailable(
        self, service: InstanceGraphService, tmp_path: Path
    ):
        """get_graph returns None when tree-sitter unavailable."""
        # Create a dummy source file
        source = tmp_path / "main.cpp"
        source.write_text("int main() {}")

        await service.startup()
        # Mock extractor as unavailable
        service.extractor.is_available = MagicMock(return_value=False)

        result = await service.get_graph(source)
        assert result is None
        await service.shutdown()

    @pytest.mark.asyncio
    async def test_get_graph_uses_cache(
        self, service: InstanceGraphService, tmp_path: Path
    ):
        """get_graph returns cached graph on second call."""
        source = tmp_path / "main.cpp"
        source.write_text("int main() {}")

        # Create a mock graph
        mock_graph = InstanceGraph(source_file=source, function_name="main")
        mock_graph.add_node(InstanceNode(
            id="n1",
            name="test",
            type_symbol="TestModule",
            role=InstanceRole.SOURCE,
            location=Location(file_path=source, line=1),
        ))

        await service.startup()

        # Manually populate cache
        graph_id = _generate_graph_id(
            str(service.root),
            str(source.relative_to(service.root)),
            "main",
        )
        mtime = _get_file_mtime(source) or datetime.now(timezone.utc)
        service._cache[graph_id] = (mock_graph, mtime)

        # Should get cached graph
        result = await service.get_graph(source, "main")
        assert result is mock_graph

        await service.shutdown()

    @pytest.mark.asyncio
    async def test_get_graph_force_refresh_bypasses_cache(
        self, service: InstanceGraphService, tmp_path: Path, mock_extractor
    ):
        """force_refresh=True bypasses the cache."""
        source = tmp_path / "main.cpp"
        source.write_text("int main() {}")

        mock_graph = InstanceGraph(source_file=source, function_name="main")

        await service.startup()

        # Populate cache
        graph_id = _generate_graph_id(
            str(service.root),
            str(source.relative_to(service.root)),
            "main",
        )
        mtime = _get_file_mtime(source) or datetime.now(timezone.utc)
        service._cache[graph_id] = (mock_graph, mtime)

        # Replace extractor with mock
        service.extractor = mock_extractor

        # Force refresh should call extractor
        result = await service.get_graph(source, "main", force_refresh=True)

        mock_extractor.extract.assert_called_once()
        # Result should be from extractor, not cache
        assert result != mock_graph  # Different instance

        await service.shutdown()

    @pytest.mark.asyncio
    async def test_invalidate_for_file_removes_from_cache(
        self, service: InstanceGraphService, tmp_path: Path
    ):
        """invalidate_for_file removes affected graphs."""
        source = tmp_path / "main.cpp"
        source.write_text("int main() {}")

        await service.startup()

        # Populate cache
        graph_id = _generate_graph_id(
            str(service.root),
            str(source.relative_to(service.root)),
            "main",
        )
        mock_graph = InstanceGraph(source_file=source, function_name="main")
        mtime = datetime.now(timezone.utc)
        service._cache[graph_id] = (mock_graph, mtime)
        service._file_deps[graph_id] = {source.resolve()}

        # Invalidate
        invalidated = await service.invalidate_for_file(source)

        assert graph_id in invalidated
        assert graph_id not in service._cache

        await service.shutdown()

    @pytest.mark.asyncio
    async def test_invalidate_ignores_non_cpp_files(
        self, service: InstanceGraphService, tmp_path: Path
    ):
        """invalidate_for_file ignores non-C++ files."""
        python_file = tmp_path / "script.py"

        await service.startup()
        invalidated = await service.invalidate_for_file(python_file)
        assert invalidated == []
        await service.shutdown()

    @pytest.mark.asyncio
    async def test_handle_file_changes_returns_summary(
        self, service: InstanceGraphService, tmp_path: Path
    ):
        """handle_file_changes returns change summary."""
        cpp_file = tmp_path / "module.cpp"
        cpp_file.write_text("// C++ code")
        py_file = tmp_path / "script.py"
        py_file.write_text("# Python code")

        await service.startup()
        result = await service.handle_file_changes([cpp_file, py_file])

        assert "invalidated" in result
        assert "refreshed" in result
        assert result["cpp_files_changed"] == 1

        await service.shutdown()

    @pytest.mark.asyncio
    async def test_list_graphs_empty_initially(
        self, service: InstanceGraphService
    ):
        """list_graphs returns empty list initially."""
        await service.startup()
        result = service.list_graphs()
        assert result == []
        await service.shutdown()

    @pytest.mark.asyncio
    async def test_list_graphs_returns_cached_info(
        self, service: InstanceGraphService, tmp_path: Path
    ):
        """list_graphs returns info about cached graphs."""
        source = tmp_path / "main.cpp"

        mock_graph = InstanceGraph(source_file=source, function_name="main")
        mock_graph.add_node(InstanceNode(
            id="n1",
            name="module",
            type_symbol="Module",
            role=InstanceRole.SOURCE,
            location=Location(file_path=source, line=1),
        ))

        await service.startup()

        # Populate cache
        mtime = datetime.now(timezone.utc)
        service._cache["test-id"] = (mock_graph, mtime)

        result = service.list_graphs()

        assert len(result) == 1
        assert result[0]["id"] == "test-id"
        assert result[0]["node_count"] == 1
        assert result[0]["edge_count"] == 0

        await service.shutdown()

    @pytest.mark.asyncio
    async def test_get_cached_graph_returns_cached(
        self, service: InstanceGraphService, tmp_path: Path
    ):
        """get_cached_graph returns graph from cache."""
        mock_graph = InstanceGraph(source_file=Path("/test"), function_name="main")

        await service.startup()
        service._cache["my-id"] = (mock_graph, datetime.now(timezone.utc))

        result = service.get_cached_graph("my-id")
        assert result is mock_graph

        await service.shutdown()

    @pytest.mark.asyncio
    async def test_get_cached_graph_returns_none_for_unknown(
        self, service: InstanceGraphService
    ):
        """get_cached_graph returns None for unknown ID."""
        await service.startup()
        result = service.get_cached_graph("nonexistent-id")
        assert result is None
        await service.shutdown()


class TestServicePersistence:
    """Tests for service persistence behavior."""

    @pytest.mark.asyncio
    async def test_shutdown_persists_graphs(self, tmp_path: Path):
        """Graphs are persisted on shutdown."""
        service = InstanceGraphService(tmp_path)
        source = tmp_path / "main.cpp"
        source.write_text("int main() {}")

        mock_graph = InstanceGraph(source_file=source, function_name="main")
        mock_graph.add_node(InstanceNode(
            id="n1",
            name="test",
            type_symbol="Test",
            role=InstanceRole.SOURCE,
            location=Location(file_path=source, line=1),
        ))

        await service.startup()

        # Populate cache
        mtime = datetime.now(timezone.utc)
        service._cache["persist-test"] = (mock_graph, mtime)

        await service.shutdown()

        # Check file was created
        assert service.store.exists()

    @pytest.mark.asyncio
    async def test_startup_loads_valid_cached_graphs(self, tmp_path: Path):
        """Startup loads graphs with valid source files."""
        # Create source file
        source = tmp_path / "main.cpp"
        source.write_text("int main() {}")
        source_mtime = _get_file_mtime(source)

        # Create persisted data
        service = InstanceGraphService(tmp_path)
        from code_map.v2.storage import StoredInstanceGraph
        from datetime import timedelta

        stored = StoredInstanceGraph(
            id="cached-graph",
            project_path=str(tmp_path),
            source_file="main.cpp",
            function_name="main",
            analyzed_at=datetime.now(timezone.utc),
            # Make source_modified_at newer than actual file to simulate valid cache
            source_modified_at=source_mtime + timedelta(seconds=1) if source_mtime else datetime.now(timezone.utc),
            node_count=1,
            edge_count=0,
            graph_data={
                "nodes": [
                    {
                        "id": "n1",
                        "name": "cached_module",
                        "type_symbol": "CachedModule",
                        "role": "source",
                        "location": {
                            "file_path": str(source),
                            "line": 1,
                        },
                    }
                ],
                "edges": [],
                "source_file": str(source),
                "function_name": "main",
            },
        )
        service.store.save([stored])

        # Create new service and startup
        service2 = InstanceGraphService(tmp_path)
        await service2.startup()

        # Should have loaded the cached graph
        assert "cached-graph" in service2._cache

        await service2.shutdown()
