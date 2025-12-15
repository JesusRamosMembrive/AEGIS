# SPDX-License-Identifier: MIT
"""
API endpoints for instance graph visualization.

Provides React Flow compatible graph data from C++ composition roots.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from code_map.v2 import GraphBuilder
from code_map.v2.composition import CppCompositionExtractor

from .schemas import InstanceGraphResponse

router = APIRouter(prefix="/instance-graph", tags=["instance-graph"])

# Singleton extractor and builder instances
_extractor = CppCompositionExtractor()
_builder = GraphBuilder()


@router.get("/{project_path:path}", response_model=InstanceGraphResponse)
async def get_instance_graph(project_path: str) -> InstanceGraphResponse:
    """
    Extract instance graph from a C++ project's main.cpp.

    Args:
        project_path: Path to directory containing main.cpp

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

    # Look for main.cpp in the project directory
    main_cpp = project_dir / "main.cpp"
    if not main_cpp.exists():
        # Try src/main.cpp as fallback
        main_cpp = project_dir / "src" / "main.cpp"
        if not main_cpp.exists():
            raise HTTPException(
                status_code=404,
                detail=f"main.cpp not found in {project_dir} or {project_dir}/src/",
            )

    # Check if tree-sitter is available
    if not _extractor.is_available():
        raise HTTPException(
            status_code=503,
            detail="tree-sitter is not available. Install tree_sitter and tree_sitter_languages packages.",
        )

    # Extract composition root
    composition_root = _extractor.extract(main_cpp)
    if composition_root is None:
        raise HTTPException(
            status_code=422,
            detail=f"Failed to extract composition root from {main_cpp}. Check that main() function exists.",
        )

    # Build the instance graph
    graph = _builder.build(composition_root)

    # Convert to React Flow format
    react_flow_data = graph.to_react_flow()

    return InstanceGraphResponse(
        nodes=react_flow_data["nodes"],
        edges=react_flow_data["edges"],
        metadata={
            "source_file": str(main_cpp),
            "function_name": composition_root.function_name,
            "node_count": len(graph.nodes),
            "edge_count": len(graph.edges),
        },
    )


@router.post("/{project_path:path}/refresh", response_model=InstanceGraphResponse)
async def refresh_instance_graph(project_path: str) -> InstanceGraphResponse:
    """
    Force re-analysis of the instance graph.

    This endpoint re-parses the source file without caching.

    Args:
        project_path: Path to directory containing main.cpp

    Returns:
        React Flow compatible graph with nodes, edges, and metadata
    """
    # For now, this is identical to GET since we don't have caching
    # In the future, this could clear any cached analysis
    return await get_instance_graph(project_path)
