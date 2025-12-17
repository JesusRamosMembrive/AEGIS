# SPDX-License-Identifier: MIT
"""
API endpoints for instance graph visualization.

Provides React Flow compatible graph data from composition roots.
Supports C++, Python, and TypeScript projects.
Uses InstanceGraphService for caching and persistence.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException

from ..state import AppState
from .deps import get_app_state
from .schemas import InstanceGraphResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/instance-graph", tags=["instance-graph"])

# Entry point patterns by language, in order of priority
# Each pattern is (relative_path, function_name)
ENTRY_POINT_PATTERNS: Dict[str, List[Tuple[str, str]]] = {
    "cpp": [
        ("main.cpp", "main"),
        ("src/main.cpp", "main"),
    ],
    "python": [
        ("main.py", "main"),
        ("src/main.py", "main"),
        ("app.py", "main"),
        ("__main__.py", "main"),
    ],
    "typescript": [
        ("src/index.ts", "main"),
        ("index.ts", "main"),
        ("src/main.ts", "main"),
        ("main.ts", "main"),
        ("src/app.ts", "main"),
        ("app.ts", "main"),
    ],
}


def _detect_python_entry_point(file_path: Path) -> Optional[str]:
    """
    Detect the composition root pattern in a Python file.

    Checks for:
    1. def main() function (preferred)
    2. if __name__ == "__main__": block (fallback)

    Args:
        file_path: Path to the Python file

    Returns:
        "main" if def main() exists
        "__main__" if if __name__ == "__main__": exists
        None if neither found
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except OSError:
        return None

    # Check for def main(): (preferred)
    if re.search(r"^def main\s*\(", content, re.MULTILINE):
        return "main"

    # Check for if __name__ == "__main__": (fallback)
    if re.search(r'if\s+__name__\s*==\s*["\']__main__["\']', content):
        return "__main__"

    return None


def _find_entry_point(project_dir: Path) -> Optional[Tuple[Path, str, str]]:
    """
    Find the composition root entry point in a project directory.

    Searches for common entry point patterns across supported languages.
    For Python files, auto-detects whether to use def main() or __main__ block.

    Args:
        project_dir: Path to the project directory

    Returns:
        Tuple of (entry_file_path, function_name, language) or None if not found
    """
    # Check each language's patterns
    for language, patterns in ENTRY_POINT_PATTERNS.items():
        for rel_path, default_func in patterns:
            entry_file = project_dir / rel_path
            if entry_file.exists():
                # For Python, auto-detect the actual entry point pattern
                if language == "python":
                    func_name = _detect_python_entry_point(entry_file)
                    if func_name:
                        logger.debug(
                            "Found Python entry point: %s::%s", entry_file, func_name
                        )
                        return (entry_file, func_name, language)
                    # Python file exists but has no valid entry point
                    logger.debug(
                        "Python file %s has no main() or __main__ block", entry_file
                    )
                    continue
                else:
                    # Non-Python: use default function name
                    logger.debug("Found entry point: %s (%s)", entry_file, language)
                    return (entry_file, default_func, language)

    return None


@router.get("/{project_path:path}", response_model=InstanceGraphResponse)
async def get_instance_graph(
    project_path: str,
    state: AppState = Depends(get_app_state),
) -> InstanceGraphResponse:
    """
    Extract instance graph from a project's composition root.

    Automatically detects the project language and finds the entry point.
    Supports C++ (main.cpp), Python (main.py), and TypeScript (index.ts).

    Uses cached graph if available and source hasn't changed.

    Args:
        project_path: Path to project directory

    Returns:
        React Flow compatible graph with nodes, edges, and metadata
    """
    project_dir = Path(project_path)

    if not project_dir.is_absolute():
        project_dir = Path("/") / project_dir

    if not project_dir.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Project directory not found: {project_dir}",
        )

    if not project_dir.is_dir():
        raise HTTPException(
            status_code=400,
            detail=f"Path is not a directory: {project_dir}",
        )

    # Find entry point (multi-language support)
    entry_point = _find_entry_point(project_dir)
    if entry_point is None:
        # List what we searched for
        searched = []
        for lang, patterns in ENTRY_POINT_PATTERNS.items():
            for rel_path, _ in patterns:
                searched.append(f"{rel_path} ({lang})")
        raise HTTPException(
            status_code=404,
            detail=f"No composition root found in {project_dir}. Searched for: {', '.join(searched[:6])}...",
        )

    entry_file, func_name, language = entry_point
    logger.info("Using entry point: %s::%s (%s)", entry_file, func_name, language)

    # Check if tree-sitter is available for this language
    extractor = state.instance_graph._get_extractor(entry_file)
    if extractor is None or not extractor.is_available():
        raise HTTPException(
            status_code=503,
            detail=f"tree-sitter not available for {language}. Install tree_sitter and tree_sitter_languages packages.",
        )

    # Get graph from service (uses cache if valid)
    logger.info("[DEBUG] API: Calling get_graph for %s", entry_file)
    graph = await state.instance_graph.get_graph(entry_file, func_name)
    logger.info("[DEBUG] API: get_graph returned graph=%s", graph is not None)
    if graph is None:
        raise HTTPException(
            status_code=422,
            detail=f"Failed to extract composition root from {entry_file}. Check that {func_name}() function exists.",
        )

    # Log node type_locations for debugging
    for node in graph.iter_nodes():
        logger.info("[DEBUG] API GET: Node '%s' type_location=%s", node.name, node.type_location)

    # Convert to React Flow format
    react_flow_data = graph.to_react_flow()

    return InstanceGraphResponse(
        nodes=react_flow_data["nodes"],
        edges=react_flow_data["edges"],
        metadata={
            "source_file": str(entry_file),
            "function_name": graph.function_name or func_name,
            "language": language,
            "node_count": len(graph.nodes),
            "edge_count": len(graph.edges),
        },
    )


@router.post("/{project_path:path}/refresh", response_model=InstanceGraphResponse)
async def refresh_instance_graph(
    project_path: str,
    state: AppState = Depends(get_app_state),
) -> InstanceGraphResponse:
    """
    Force re-analysis of the instance graph.

    This endpoint re-parses the source file, bypassing the cache.

    Args:
        project_path: Path to project directory

    Returns:
        React Flow compatible graph with nodes, edges, and metadata
    """
    project_dir = Path(project_path)

    if not project_dir.is_absolute():
        project_dir = Path("/") / project_dir

    if not project_dir.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Project directory not found: {project_dir}",
        )

    if not project_dir.is_dir():
        raise HTTPException(
            status_code=400,
            detail=f"Path is not a directory: {project_dir}",
        )

    # Find entry point (multi-language support)
    entry_point = _find_entry_point(project_dir)
    if entry_point is None:
        searched = []
        for lang, patterns in ENTRY_POINT_PATTERNS.items():
            for rel_path, _ in patterns:
                searched.append(f"{rel_path} ({lang})")
        raise HTTPException(
            status_code=404,
            detail=f"No composition root found in {project_dir}. Searched for: {', '.join(searched[:6])}...",
        )

    entry_file, func_name, language = entry_point
    logger.info("Force refresh for: %s::%s (%s)", entry_file, func_name, language)

    # Check if tree-sitter is available
    extractor = state.instance_graph._get_extractor(entry_file)
    if extractor is None or not extractor.is_available():
        raise HTTPException(
            status_code=503,
            detail=f"tree-sitter not available for {language}. Install tree_sitter and tree_sitter_languages packages.",
        )

    # Force refresh by bypassing cache
    graph = await state.instance_graph.get_graph(entry_file, func_name, force_refresh=True)
    if graph is None:
        raise HTTPException(
            status_code=422,
            detail=f"Failed to extract composition root from {entry_file}. Check that {func_name}() function exists.",
        )

    # Convert to React Flow format
    react_flow_data = graph.to_react_flow()

    return InstanceGraphResponse(
        nodes=react_flow_data["nodes"],
        edges=react_flow_data["edges"],
        metadata={
            "source_file": str(entry_file),
            "function_name": graph.function_name or func_name,
            "language": language,
            "node_count": len(graph.nodes),
            "edge_count": len(graph.edges),
        },
    )


@router.get("/", response_model=List[Dict[str, Any]])
async def list_instance_graphs(
    state: AppState = Depends(get_app_state),
) -> List[Dict[str, Any]]:
    """
    List all cached instance graphs.

    Returns:
        List of graph summaries with id, source_file, stats, and cache timestamp
    """
    return state.instance_graph.list_graphs()
