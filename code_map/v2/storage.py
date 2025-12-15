# SPDX-License-Identifier: MIT
"""
Persistence layer for Instance Graph.

Provides storage and retrieval of instance graphs to/from disk,
enabling fast startup and cache-based responses.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..constants import META_DIR_NAME

logger = logging.getLogger(__name__)

# Storage format version for migration support
STORAGE_VERSION = "1.0"


@dataclass
class StoredInstanceGraph:
    """
    Represents a persisted instance graph with metadata.

    This is the storage representation that includes analysis timestamps
    and file modification times for cache invalidation.

    Attributes:
        id: Unique identifier for this graph
        project_path: Normalized path to the project root
        source_file: Path to the composition root file (e.g., main.cpp)
        function_name: Name of the composition root function (e.g., "main")
        analyzed_at: When the analysis was performed
        source_modified_at: When the source file was last modified
        node_count: Number of nodes in the graph
        edge_count: Number of edges in the graph
        graph_data: Serialized graph data (nodes and edges)
    """

    id: str
    project_path: str
    source_file: str
    function_name: str
    analyzed_at: datetime
    source_modified_at: datetime
    node_count: int
    edge_count: int
    graph_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON storage."""
        return {
            "id": self.id,
            "project_path": self.project_path,
            "source_file": self.source_file,
            "function_name": self.function_name,
            "analyzed_at": self.analyzed_at.isoformat(),
            "source_modified_at": self.source_modified_at.isoformat(),
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "graph_data": self.graph_data,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StoredInstanceGraph":
        """Deserialize from dictionary."""
        return cls(
            id=data["id"],
            project_path=data["project_path"],
            source_file=data["source_file"],
            function_name=data["function_name"],
            analyzed_at=_parse_datetime(data["analyzed_at"]),
            source_modified_at=_parse_datetime(data["source_modified_at"]),
            node_count=data.get("node_count", 0),
            edge_count=data.get("edge_count", 0),
            graph_data=data.get("graph_data", {}),
        )


def _parse_datetime(value: str) -> datetime:
    """Parse ISO format datetime string."""
    if value.endswith("Z"):
        value = value.replace("Z", "+00:00")
    return datetime.fromisoformat(value)


class InstanceGraphStore:
    """
    Manages persistence of instance graphs to disk.

    Stores graphs in `.code-map/instance-graphs.json` within the project root.
    Supports multiple graphs per project (for multiple composition roots).

    Example:
        >>> store = InstanceGraphStore(Path("/my/project"))
        >>> graphs = store.load()
        >>> store.save(graphs)
    """

    def __init__(
        self,
        root: Path,
        filename: str = "instance-graphs.json",
        cache_dir: Optional[Path] = None,
    ) -> None:
        """
        Initialize the store.

        Args:
            root: Project root directory
            filename: Name of the storage file
            cache_dir: Alternative cache directory (for Docker/read-only mounts)
        """
        self.root = Path(root).expanduser().resolve()
        if cache_dir is not None:
            self.meta_dir = Path(cache_dir).expanduser().resolve()
        else:
            self.meta_dir = self.root / META_DIR_NAME
        self.store_path = self.meta_dir / filename

    def load(self) -> List[StoredInstanceGraph]:
        """
        Load graphs from disk.

        Returns:
            List of stored graphs, empty if file doesn't exist or is invalid.
        """
        if not self.store_path.exists():
            logger.debug("No stored graphs found at %s", self.store_path)
            return []

        try:
            data = self.store_path.read_text(encoding="utf-8")
            payload = json.loads(data)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load stored graphs: %s", e)
            return []

        # Version check for future migrations
        version = payload.get("version", "1.0")
        if version != STORAGE_VERSION:
            logger.warning(
                "Storage version mismatch: expected %s, got %s",
                STORAGE_VERSION,
                version,
            )
            # For now, try to load anyway - future versions may need migration

        graphs: List[StoredInstanceGraph] = []
        for entry in payload.get("graphs", []):
            try:
                graph = StoredInstanceGraph.from_dict(entry)
                graphs.append(graph)
            except (KeyError, TypeError, ValueError) as e:
                logger.warning("Failed to deserialize graph entry: %s", e)
                continue

        logger.info("Loaded %d stored graphs from %s", len(graphs), self.store_path)
        return graphs

    def save(self, graphs: List[StoredInstanceGraph]) -> None:
        """
        Save graphs to disk.

        Args:
            graphs: List of graphs to persist
        """
        payload = {
            "version": STORAGE_VERSION,
            "project_path": str(self.root),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "graphs": [g.to_dict() for g in graphs],
        }

        # Ensure directory exists
        self.meta_dir.mkdir(parents=True, exist_ok=True)

        # Write atomically by writing to temp file first
        temp_path = self.store_path.with_suffix(".tmp")
        try:
            temp_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            temp_path.replace(self.store_path)
            logger.info("Saved %d graphs to %s", len(graphs), self.store_path)
        except OSError as e:
            logger.error("Failed to save graphs: %s", e)
            # Clean up temp file if it exists
            if temp_path.exists():
                temp_path.unlink()
            raise

    def delete(self) -> bool:
        """
        Delete the storage file.

        Returns:
            True if file was deleted, False if it didn't exist.
        """
        if self.store_path.exists():
            self.store_path.unlink()
            logger.info("Deleted stored graphs at %s", self.store_path)
            return True
        return False

    def exists(self) -> bool:
        """Check if storage file exists."""
        return self.store_path.exists()
