# SPDX-License-Identifier: MIT
"""
C++ Call Flow extractor using tree-sitter.

Extracts function definitions from C++ code to build call graphs.
This is a simplified version that focuses on entry point listing.
Full call flow analysis for C++ is more complex due to:
- Header files and forward declarations
- Namespaces and classes
- Templates and overloading
- Multiple translation units
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CppCallFlowExtractor:
    """
    Extracts function definitions from C++ source code.

    Currently supports:
    - Free function definitions
    - Class method definitions (both inline and out-of-class)
    - Entry point listing for visualization

    Example:
        >>> extractor = CppCallFlowExtractor()
        >>> entries = extractor.list_entry_points(Path("main.cpp"))
    """

    # C++ file extensions
    CPP_EXTENSIONS = {".cpp", ".c", ".hpp", ".h", ".cc", ".cxx", ".hxx"}

    def __init__(self) -> None:
        """Initialize the extractor with tree-sitter parser."""
        self._parser: Optional[Any] = None
        self._available: Optional[bool] = None

    def is_available(self) -> bool:
        """Check if tree-sitter with C++ support is available."""
        if self._available is not None:
            return self._available

        try:
            from code_map.dependencies import optional_dependencies

            modules = optional_dependencies.load("tree_sitter_languages")
            if not modules:
                self._available = False
                return False

            import warnings

            parser_cls = getattr(modules.get("tree_sitter"), "Parser", None)
            get_language = getattr(
                modules.get("tree_sitter_languages"), "get_language", None
            )

            if parser_cls is None or get_language is None:
                self._available = False
                return False

            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=FutureWarning)
                language = get_language("cpp")

            parser = parser_cls()
            parser.set_language(language)
            self._parser = parser
            self._available = True
            return True

        except Exception as e:
            logger.debug(f"C++ tree-sitter not available: {e}")
            self._available = False
            return False

    def _ensure_parser(self) -> bool:
        """Ensure parser is initialized."""
        if self._parser is not None:
            return True
        return self.is_available()

    def _walk_tree(self, node: Any):
        """Walk tree yielding all nodes."""
        yield node
        for child in node.children:
            yield from self._walk_tree(child)

    def _get_node_text(self, node: Any, source: bytes) -> str:
        """Get text content of a node."""
        return source[node.start_byte:node.end_byte].decode("utf-8")

    def _get_function_name(self, node: Any, source: bytes) -> Optional[str]:
        """
        Extract function name from a function_definition node.

        Handles:
        - Simple functions: void foo() {}
        - Methods: void Class::foo() {}
        - Destructors: ~Class()
        - Constructors: Class()
        """
        for child in node.children:
            if child.type == "function_declarator":
                return self._get_declarator_name(child, source)
        return None

    def _get_declarator_name(self, node: Any, source: bytes) -> Optional[str]:
        """Extract the actual name from a declarator."""
        for child in node.children:
            if child.type == "identifier":
                return self._get_node_text(child, source)
            elif child.type == "qualified_identifier":
                # For Class::method, get the method name
                parts = []
                for sub in child.children:
                    if sub.type == "identifier":
                        parts.append(self._get_node_text(sub, source))
                    elif sub.type == "destructor_name":
                        parts.append(self._get_node_text(sub, source))
                return parts[-1] if parts else None
            elif child.type == "destructor_name":
                return self._get_node_text(child, source)
            elif child.type == "field_identifier":
                return self._get_node_text(child, source)
        return None

    def _get_class_context(self, node: Any, source: bytes) -> Optional[str]:
        """
        Get the class name if this function is defined inside a class.

        Also checks for qualified names like Class::method.
        """
        # Check for qualified identifier in function_declarator
        for child in node.children:
            if child.type == "function_declarator":
                for sub in child.children:
                    if sub.type == "qualified_identifier":
                        # Class::method format
                        for part in sub.children:
                            if part.type == "namespace_identifier":
                                return self._get_node_text(part, source)
                            elif part.type == "identifier":
                                # First identifier is the class name
                                text = self._get_node_text(part, source)
                                # Skip if this is the function name (last part)
                                if part.next_sibling is not None:
                                    return text
                        break

        # Check parent nodes for class definition
        parent = node.parent
        while parent:
            if parent.type in ("class_specifier", "struct_specifier"):
                for child in parent.children:
                    if child.type == "type_identifier":
                        return self._get_node_text(child, source)
            parent = parent.parent

        return None

    def _is_template_function(self, node: Any) -> bool:
        """Check if this is a template function."""
        parent = node.parent
        while parent:
            if parent.type == "template_declaration":
                return True
            parent = parent.parent
        return False

    def _should_skip_function(self, name: str) -> bool:
        """Check if function should be skipped."""
        # Skip private/internal functions (starting with underscore)
        if name.startswith("_") and not name.startswith("__"):
            return True
        # Skip common internal patterns
        if name in ("main",):
            return False  # Always include main
        return False

    def list_entry_points(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        List all functions and methods in a C++ file that could be entry points.

        Args:
            file_path: Path to C++ file

        Returns:
            List of entry point info with name, qualified_name, line, kind
        """
        if not self._ensure_parser():
            return []

        try:
            source = file_path.read_bytes()
        except OSError as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return []

        tree = self._parser.parse(source)
        entry_points: List[Dict[str, Any]] = []

        for node in self._walk_tree(tree.root_node):
            if node.type == "function_definition":
                func_name = self._get_function_name(node, source)

                if not func_name:
                    continue

                if self._should_skip_function(func_name):
                    continue

                class_name = self._get_class_context(node, source)
                is_template = self._is_template_function(node)

                if class_name:
                    qualified_name = f"{class_name}::{func_name}"
                    kind = "method"
                else:
                    qualified_name = func_name
                    kind = "function"

                if is_template:
                    kind = f"template_{kind}"

                entry_points.append({
                    "name": func_name,
                    "qualified_name": qualified_name,
                    "line": node.start_point[0] + 1,
                    "kind": kind,
                    "class_name": class_name,
                })

        return entry_points

    @classmethod
    def supports_extension(cls, extension: str) -> bool:
        """Check if this extractor supports the given file extension."""
        return extension.lower() in cls.CPP_EXTENSIONS
