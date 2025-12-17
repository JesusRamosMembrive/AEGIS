# SPDX-License-Identifier: MIT
"""
API endpoints for call flow graph visualization.

Provides React Flow compatible graph data showing function call chains
from a selected entry point (e.g., button handlers, event callbacks).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse

from ..v2.call_flow.extractor import PythonCallFlowExtractor
from ..v2.call_flow.cpp_extractor import CppCallFlowExtractor
from ..v2.call_flow.ts_extractor import TsCallFlowExtractor
from .schemas import (
    CallFlowEntryPointSchema,
    CallFlowEntryPointsResponse,
    CallFlowIgnoredCallSchema,
    CallFlowResolutionStatus,
    CallFlowResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/call-flow", tags=["call-flow"])

# Singleton extractor instances
_python_extractor: Optional[PythonCallFlowExtractor] = None
_cpp_extractor: Optional[CppCallFlowExtractor] = None
_ts_extractor: Optional[TsCallFlowExtractor] = None

# Supported file extensions by language
PYTHON_EXTENSIONS = {".py"}
CPP_EXTENSIONS = {".cpp", ".c", ".hpp", ".h", ".cc", ".cxx", ".hxx"}
TS_EXTENSIONS = {".ts", ".tsx", ".mts", ".cts"}
JS_EXTENSIONS = {".js", ".jsx", ".mjs", ".cjs"}
TSJS_EXTENSIONS = TS_EXTENSIONS | JS_EXTENSIONS
SUPPORTED_EXTENSIONS = PYTHON_EXTENSIONS | CPP_EXTENSIONS | TSJS_EXTENSIONS


def _get_python_extractor() -> PythonCallFlowExtractor:
    """Get or create the Python extractor singleton."""
    global _python_extractor
    if _python_extractor is None:
        _python_extractor = PythonCallFlowExtractor()
    return _python_extractor


def _get_cpp_extractor() -> CppCallFlowExtractor:
    """Get or create the C++ extractor singleton."""
    global _cpp_extractor
    if _cpp_extractor is None:
        _cpp_extractor = CppCallFlowExtractor()
    return _cpp_extractor


def _get_ts_extractor() -> TsCallFlowExtractor:
    """Get or create the TypeScript/JavaScript extractor singleton."""
    global _ts_extractor
    if _ts_extractor is None:
        _ts_extractor = TsCallFlowExtractor()
    return _ts_extractor


def _get_extractor() -> PythonCallFlowExtractor:
    """Get or create the Python extractor singleton (for backward compatibility)."""
    return _get_python_extractor()


# Maximum file size for source code preview (512 KB)
MAX_SOURCE_BYTES = 512 * 1024

# Allowed file extensions for source code viewing
ALLOWED_SOURCE_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp", ".h", ".hpp", ".go", ".rs"}


@router.get("/source/{file_path:path}", response_class=PlainTextResponse)
async def get_source_code(
    file_path: str,
    start_line: int = Query(default=1, ge=1, description="Start line number (1-indexed)"),
    end_line: Optional[int] = Query(default=None, ge=1, description="End line number (optional)"),
) -> str:
    """
    Get source code from a file for call flow node details.

    This endpoint allows reading source files that may be outside the
    configured AEGIS root, since Call Flow can analyze external projects.

    Security:
    - Only allows reading files with code extensions (.py, .js, etc.)
    - File size limited to 512 KB
    - Read-only operation

    Args:
        file_path: Absolute path to the source file
        start_line: Start line number (1-indexed, default: 1)
        end_line: End line number (optional, reads to end if not specified)

    Returns:
        Plain text source code content
    """
    path = Path(file_path)

    if not path.is_absolute():
        path = Path("/") / path

    # Security: Only allow code file extensions
    if path.suffix.lower() not in ALLOWED_SOURCE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed for source viewing: {path.suffix}. "
            f"Allowed: {', '.join(sorted(ALLOWED_SOURCE_EXTENSIONS))}",
        )

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"File not found: {path}",
        )

    if not path.is_file():
        raise HTTPException(
            status_code=400,
            detail=f"Path is not a file: {path}",
        )

    # Security: Check file size
    try:
        file_size = path.stat().st_size
        if file_size > MAX_SOURCE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File too large: {file_size} bytes (max: {MAX_SOURCE_BYTES} bytes)",
            )
    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read file stats: {exc}",
        )

    # Read file content
    try:
        with path.open("r", encoding="utf-8") as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="File is not valid UTF-8 text",
        )
    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read file: {exc}",
        )

    # Extract requested line range
    total_lines = len(lines)
    start_idx = start_line - 1  # Convert to 0-indexed

    if start_idx >= total_lines:
        raise HTTPException(
            status_code=400,
            detail=f"Start line {start_line} exceeds file length ({total_lines} lines)",
        )

    if end_line is not None:
        end_idx = min(end_line, total_lines)
        selected_lines = lines[start_idx:end_idx]
    else:
        selected_lines = lines[start_idx:]

    return "".join(selected_lines)


@router.get("/entry-points/{file_path:path}", response_model=CallFlowEntryPointsResponse)
async def list_entry_points(
    file_path: str,
) -> CallFlowEntryPointsResponse:
    """
    List available entry points (functions/methods) in a file.

    These can be used as starting points for call flow analysis.
    Supports Python (.py), C++ (.cpp, .c, .hpp, .h), and TypeScript/JavaScript files.

    Args:
        file_path: Path to source file (Python, C++, TypeScript, or JavaScript)

    Returns:
        List of entry points with name, qualified_name, line, and kind
    """
    path = Path(file_path)

    if not path.is_absolute():
        path = Path("/") / path

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"File not found: {path}",
        )

    if not path.is_file():
        raise HTTPException(
            status_code=400,
            detail=f"Path is not a file: {path}",
        )

    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {path.suffix}. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    # Select appropriate extractor based on file type
    if suffix in PYTHON_EXTENSIONS:
        extractor = _get_python_extractor()
        lang_name = "Python"
    elif suffix in CPP_EXTENSIONS:
        extractor = _get_cpp_extractor()
        lang_name = "C++"
    else:
        extractor = _get_ts_extractor()
        lang_name = "TypeScript/JavaScript"

    if not extractor.is_available():
        raise HTTPException(
            status_code=503,
            detail=f"tree-sitter for {lang_name} not available. "
            "Install tree_sitter and tree_sitter_languages packages.",
        )

    entry_points = extractor.list_entry_points(path)

    return CallFlowEntryPointsResponse(
        file_path=str(path),
        entry_points=[
            CallFlowEntryPointSchema(
                name=ep["name"],
                qualified_name=ep["qualified_name"],
                line=ep["line"],
                kind=ep["kind"],
                class_name=ep.get("class_name"),
                node_count=ep.get("node_count"),
            )
            for ep in entry_points
        ],
    )


@router.get("/{file_path:path}", response_model=CallFlowResponse)
async def get_call_flow(
    file_path: str,
    function: str = Query(..., description="Function or method name to analyze"),
    max_depth: int = Query(default=5, ge=1, le=20, description="Maximum call depth"),
    class_name: Optional[str] = Query(default=None, description="Class name if analyzing a method"),
) -> CallFlowResponse:
    """
    Extract call flow graph from a function or method.

    Returns a React Flow compatible graph showing all function calls
    reachable from the entry point up to max_depth levels.

    Supports Python (.py), C++ (.cpp, .c, .hpp, .h), and TypeScript/JavaScript files.

    Args:
        file_path: Path to source file (Python, C++, TypeScript, or JavaScript)
        function: Name of function/method to analyze
        max_depth: Maximum depth to follow calls (default: 5)
        class_name: Class name if analyzing a method (optional)

    Returns:
        React Flow compatible graph with nodes, edges, and metadata
    """
    path = Path(file_path)

    if not path.is_absolute():
        path = Path("/") / path

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"File not found: {path}",
        )

    if not path.is_file():
        raise HTTPException(
            status_code=400,
            detail=f"Path is not a file: {path}",
        )

    suffix = path.suffix.lower()

    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {path.suffix}. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    # Select appropriate extractor
    if suffix in PYTHON_EXTENSIONS:
        extractor = _get_python_extractor()
        lang_name = "Python"
    elif suffix in CPP_EXTENSIONS:
        extractor = _get_cpp_extractor()
        lang_name = "C++"
    else:
        extractor = _get_ts_extractor()
        lang_name = "TypeScript/JavaScript"

    if not extractor.is_available():
        raise HTTPException(
            status_code=503,
            detail=f"tree-sitter for {lang_name} not available. "
            "Install tree_sitter and tree_sitter_languages packages.",
        )

    # Build the function identifier
    if class_name:
        func_to_find = function
        logger.info("Extracting call flow for %s::%s in %s", class_name, function, path)
    else:
        func_to_find = function
        logger.info("Extracting call flow for %s in %s", function, path)

    # Extract call graph
    graph = extractor.extract(
        file_path=path,
        function_name=func_to_find,
        max_depth=max_depth,
        project_root=path.parent,
    )

    if graph is None:
        raise HTTPException(
            status_code=422,
            detail=f"Failed to extract call flow from {path}::{function}. "
            "Check that the function exists.",
        )

    # Convert to React Flow format
    react_flow_data = graph.to_react_flow()

    # Convert ignored calls to schema format
    ignored_calls_schema = [
        CallFlowIgnoredCallSchema(
            expression=ic.expression,
            status=CallFlowResolutionStatus(ic.status.value),
            call_site_line=ic.call_site_line,
            module_hint=ic.module_hint,
        )
        for ic in graph.ignored_calls[:50]  # Limit to first 50
    ]

    return CallFlowResponse(
        nodes=react_flow_data["nodes"],
        edges=react_flow_data["edges"],
        metadata={
            "entry_point": graph.entry_point,
            "source_file": str(graph.source_file),
            "function_name": function,
            "max_depth": graph.max_depth,
            "max_depth_reached": graph.max_depth_reached,
            "node_count": graph.node_count(),
            "edge_count": graph.edge_count(),
        },
        ignored_calls=ignored_calls_schema,
        unresolved_calls=graph.unresolved_calls[:20],  # Limit to first 20
        diagnostics=graph.diagnostics,
    )
