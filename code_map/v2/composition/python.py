# SPDX-License-Identifier: MIT
"""
Python composition root extractor using tree-sitter.

Extracts instances, wiring, and lifecycle calls from Python composition roots
(typically main.py or files with if __name__ == "__main__").
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from ..models import (
    CompositionRoot,
    CreationPattern,
    InstanceInfo,
    LifecycleCall,
    LifecycleMethod,
    Location,
    WiringInfo,
)
from .base import CompositionExtractor


# Wiring method patterns - methods that connect components
WIRING_METHODS: Set[str] = {
    "set_next",
    "setNext",
    "connect",
    "add_listener",
    "addListener",
    "add_observer",
    "addObserver",
    "subscribe",
    "link",
    "pipe",
    "chain",
    "attach",
    "register",
    "add",
    "append",
}

# Lifecycle method patterns
LIFECYCLE_METHODS: Dict[str, LifecycleMethod] = {
    "start": LifecycleMethod.START,
    "stop": LifecycleMethod.STOP,
    "init": LifecycleMethod.INIT,
    "initialize": LifecycleMethod.INIT,
    "shutdown": LifecycleMethod.SHUTDOWN,
    "connect": LifecycleMethod.CONNECT,
    "disconnect": LifecycleMethod.DISCONNECT,
    "run": LifecycleMethod.START,
    "close": LifecycleMethod.SHUTDOWN,
}

# Factory function patterns
FACTORY_PATTERNS: List[re.Pattern] = [
    re.compile(r"^create_"),  # create_foo
    re.compile(r"^make_"),  # make_foo
    re.compile(r"^build_"),  # build_foo
    re.compile(r"_factory$"),  # foo_factory
    re.compile(r"Factory$"),  # FooFactory
]

# Composition root function names
COMPOSITION_ROOT_FUNCTIONS: Set[str] = {
    "main",
    "create_app",
    "create_pipeline",
    "setup",
    "configure",
    "bootstrap",
}


class PythonCompositionExtractor(CompositionExtractor):
    """
    Python composition root extractor using tree-sitter.

    Detects:
    - Instance declarations (direct instantiation, factory calls)
    - Wiring calls (set_next, connect, etc.)
    - Lifecycle calls (start, stop, init)
    """

    def __init__(self) -> None:
        """Initialize the extractor with tree-sitter parser."""
        self._parser: Optional[Any] = None
        self._available: Optional[bool] = None

    @property
    def language_id(self) -> str:
        return "python"

    @property
    def file_extensions(self) -> Tuple[str, ...]:
        return (".py",)

    def is_available(self) -> bool:
        """Check if tree-sitter is available."""
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
                language = get_language("python")

            parser = parser_cls()
            parser.set_language(language)
            self._parser = parser
            self._available = True
            return True

        except Exception:
            self._available = False
            return False

    def _ensure_parser(self) -> bool:
        """Ensure parser is initialized."""
        if self._parser is not None:
            return True
        return self.is_available()

    def find_composition_roots(self, file_path: Path) -> List[str]:
        """Find composition root functions in a Python file."""
        if not self._ensure_parser():
            return []

        try:
            source = file_path.read_text(encoding="utf-8")
        except OSError:
            return []

        tree = self._parser.parse(bytes(source, "utf-8"))
        roots: List[str] = []

        # Walk AST looking for function definitions
        for node in self._walk_tree(tree.root_node):
            if node.type == "function_definition":
                func_name = self._get_function_name(node)
                if func_name and self._is_composition_root(func_name, node, source):
                    roots.append(func_name)

        # Check for if __name__ == "__main__" block
        if self._has_main_block(tree.root_node, source):
            roots.append("__main__")

        return roots

    def _is_composition_root(
        self, func_name: str, node: Any, source: str
    ) -> bool:
        """Check if a function is a composition root."""
        # Convention: known composition root function names
        if func_name in COMPOSITION_ROOT_FUNCTIONS:
            return True

        # Check for @aegis_composition_root decorator
        decorators = self._get_decorators(node, source)
        if "aegis_composition_root" in decorators:
            return True

        # Check for marker in docstring
        docstring = self._get_docstring(node, source)
        if docstring and "@aegis-composition-root" in docstring:
            return True

        return False

    def _has_main_block(self, root: Any, source: str) -> bool:
        """Check if file has if __name__ == '__main__' block."""
        for node in self._walk_tree(root):
            if node.type == "if_statement":
                condition = self._find_child_by_type(node, "comparison_operator")
                if condition:
                    cond_text = self._get_node_text(condition, source)
                    if "__name__" in cond_text and "__main__" in cond_text:
                        return True
        return False

    def extract(
        self,
        file_path: Path,
        function_name: Optional[str] = None,
    ) -> Optional[CompositionRoot]:
        """Extract composition root from a Python file."""
        if not self._ensure_parser():
            return None

        try:
            source = file_path.read_text(encoding="utf-8")
        except OSError:
            return None

        tree = self._parser.parse(bytes(source, "utf-8"))
        target_func = function_name or "main"

        # Special case: extract from __main__ block
        if target_func == "__main__":
            return self._extract_from_main_block(tree.root_node, file_path, source)

        # Find the target function
        func_node = self._find_function(tree.root_node, target_func)
        if func_node is None:
            return None

        # Extract location
        location = Location(
            file_path=file_path.resolve(),
            line=func_node.start_point[0] + 1,
            column=func_node.start_point[1],
        )

        # Create composition root
        root = CompositionRoot(
            file_path=file_path.resolve(),
            function_name=target_func,
            location=location,
        )

        # Find function body (block node after ":")
        body = self._find_child_by_type(func_node, "block")
        if body is None:
            return root

        # Extract instances, wiring, and lifecycle
        self._extract_instances(body, file_path, root, source)
        self._extract_wiring(body, file_path, root, source)
        self._extract_lifecycle(body, file_path, root, source)

        return root

    def _extract_from_main_block(
        self, root: Any, file_path: Path, source: str
    ) -> Optional[CompositionRoot]:
        """Extract from if __name__ == '__main__' block."""
        for node in self._walk_tree(root):
            if node.type == "if_statement":
                condition = self._find_child_by_type(node, "comparison_operator")
                if condition:
                    cond_text = self._get_node_text(condition, source)
                    if "__name__" in cond_text and "__main__" in cond_text:
                        # Found the main block
                        location = Location(
                            file_path=file_path.resolve(),
                            line=node.start_point[0] + 1,
                            column=node.start_point[1],
                        )

                        comp_root = CompositionRoot(
                            file_path=file_path.resolve(),
                            function_name="__main__",
                            location=location,
                        )

                        # Find the block inside if statement
                        body = self._find_child_by_type(node, "block")
                        if body:
                            self._extract_instances(body, file_path, comp_root, source)
                            self._extract_wiring(body, file_path, comp_root, source)
                            self._extract_lifecycle(body, file_path, comp_root, source)

                        return comp_root
        return None

    def _extract_instances(
        self,
        body: Any,
        file_path: Path,
        root: CompositionRoot,
        source: str,
    ) -> None:
        """Extract instance declarations from function body."""
        for node in self._walk_tree(body):
            if node.type == "assignment":
                instance = self._parse_assignment(node, file_path, source)
                if instance:
                    root.instances.append(instance)
            elif node.type == "expression_statement":
                # Handle augmented assignment or other patterns
                child = node.children[0] if node.children else None
                if child and child.type == "assignment":
                    instance = self._parse_assignment(child, file_path, source)
                    if instance:
                        root.instances.append(instance)

    def _parse_assignment(
        self,
        node: Any,
        file_path: Path,
        source: str,
    ) -> Optional[InstanceInfo]:
        """Parse an assignment to extract instance info."""
        # Get left side (variable name)
        left = None
        right = None

        for child in node.children:
            if child.type == "identifier":
                left = self._get_node_text(child, source)
            elif child.type == "pattern_list":
                # Multiple assignment - skip for now
                return None
            elif child.type in ("call", "call_expression"):
                right = child

        if left is None or right is None:
            # Check if right side is after "=" sign
            found_eq = False
            for child in node.children:
                if child.type == "=":
                    found_eq = True
                elif found_eq and child.type == "call":
                    right = child
                    break

        if left is None or right is None:
            return None

        # Parse the call expression
        creation_pattern = CreationPattern.UNKNOWN
        factory_name = None
        actual_type = None
        constructor_args: List[str] = []

        if right.type == "call":
            call_info = self._parse_call_expression(right, source)
            creation_pattern = call_info.get("pattern", CreationPattern.UNKNOWN)
            factory_name = call_info.get("factory_name")
            actual_type = call_info.get("actual_type")
            constructor_args = call_info.get("args", [])

        # Skip simple literals or non-instance assignments
        if actual_type is None and factory_name is None:
            return None

        location = Location(
            file_path=file_path.resolve(),
            line=node.start_point[0] + 1,
            column=node.start_point[1],
        )

        return InstanceInfo(
            name=left,
            type_name=actual_type or "object",
            location=location,
            creation_pattern=creation_pattern,
            actual_type=actual_type,
            factory_name=factory_name,
            constructor_args=constructor_args,
            is_pointer=False,
            pointer_type=None,
        )

    def _parse_call_expression(
        self,
        node: Any,
        source: str,
    ) -> Dict[str, Any]:
        """Parse call expression to extract creation info."""
        result: Dict[str, Any] = {
            "pattern": CreationPattern.UNKNOWN,
            "factory_name": None,
            "actual_type": None,
            "args": [],
        }

        if node.type != "call":
            return result

        # Get the function being called
        function_node = self._find_child_by_type(node, "identifier")
        if function_node is None:
            function_node = self._find_child_by_type(node, "attribute")

        func_name = None
        if function_node:
            func_name = self._get_node_text(function_node, source)

        if func_name:
            # Check if it's a class instantiation (starts with uppercase)
            if func_name[0].isupper():
                result["pattern"] = CreationPattern.DIRECT
                result["actual_type"] = func_name
            # Check if it's a factory function
            elif any(p.search(func_name) for p in FACTORY_PATTERNS):
                result["pattern"] = CreationPattern.FACTORY
                result["factory_name"] = func_name
                # Try to infer type from factory name
                # e.g., create_generator -> Generator
                for prefix in ("create_", "make_", "build_"):
                    if func_name.startswith(prefix):
                        type_name = func_name[len(prefix):].title()
                        result["actual_type"] = type_name
                        break
            else:
                # Generic function call that returns an object
                result["pattern"] = CreationPattern.FACTORY
                result["factory_name"] = func_name

        # Extract arguments
        args_node = self._find_child_by_type(node, "argument_list")
        if args_node:
            for child in args_node.children:
                if child.type not in ("(", ")", ","):
                    arg_text = self._get_node_text(child, source)
                    result["args"].append(arg_text)

        return result

    def _extract_wiring(
        self,
        body: Any,
        file_path: Path,
        root: CompositionRoot,
        source: str,
    ) -> None:
        """Extract wiring calls from function body."""
        instance_names = {inst.name for inst in root.instances}

        for node in self._walk_tree(body):
            if node.type == "expression_statement":
                wiring = self._parse_wiring_call(node, file_path, instance_names, source)
                if wiring:
                    root.wiring.append(wiring)

    def _parse_wiring_call(
        self,
        node: Any,
        file_path: Path,
        instance_names: Set[str],
        source: str,
    ) -> Optional[WiringInfo]:
        """Parse a statement to check if it's a wiring call."""
        # Find call expression within the statement
        call_node = self._find_child_by_type(node, "call")
        if call_node is None:
            # Check children of expression_statement
            for child in node.children:
                if child.type == "call":
                    call_node = child
                    break

        if call_node is None:
            return None

        # Look for attribute access: obj.method()
        attr_node = self._find_child_by_type(call_node, "attribute")
        if attr_node is None:
            return None

        # Parse attribute: object.method
        source_instance = None
        method_name = None

        for child in attr_node.children:
            if child.type == "identifier":
                text = self._get_node_text(child, source)
                if text in instance_names:
                    source_instance = text
                else:
                    method_name = text

        if source_instance is None or method_name is None:
            return None

        # Check if method is a wiring method
        if method_name not in WIRING_METHODS:
            return None

        # Find the target instance in arguments
        args_node = self._find_child_by_type(call_node, "argument_list")
        if args_node is None:
            return None

        target_instance = None
        for arg in args_node.children:
            if arg.type == "identifier":
                text = self._get_node_text(arg, source)
                if text in instance_names:
                    target_instance = text
                    break

        if target_instance is None:
            return None

        location = Location(
            file_path=file_path.resolve(),
            line=node.start_point[0] + 1,
            column=node.start_point[1],
        )

        return WiringInfo(
            source=source_instance,
            target=target_instance,
            method=method_name,
            location=location,
        )

    def _extract_lifecycle(
        self,
        body: Any,
        file_path: Path,
        root: CompositionRoot,
        source: str,
    ) -> None:
        """Extract lifecycle method calls."""
        instance_names = {inst.name for inst in root.instances}
        order = 0

        for node in self._walk_tree(body):
            if node.type == "expression_statement":
                lc = self._parse_lifecycle_call(
                    node, file_path, instance_names, source, order
                )
                if lc:
                    root.lifecycle.append(lc)
                    order += 1

    def _parse_lifecycle_call(
        self,
        node: Any,
        file_path: Path,
        instance_names: Set[str],
        source: str,
        order: int,
    ) -> Optional[LifecycleCall]:
        """Parse a statement to check if it's a lifecycle call."""
        call_node = self._find_child_by_type(node, "call")
        if call_node is None:
            for child in node.children:
                if child.type == "call":
                    call_node = child
                    break

        if call_node is None:
            return None

        # Look for attribute access
        attr_node = self._find_child_by_type(call_node, "attribute")
        if attr_node is None:
            return None

        # Parse to get instance and method
        instance_name = None
        method_name = None

        for child in attr_node.children:
            if child.type == "identifier":
                text = self._get_node_text(child, source)
                if text in instance_names:
                    instance_name = text
                elif text in LIFECYCLE_METHODS:
                    method_name = text

        if instance_name is None or method_name is None:
            return None

        lifecycle_method = LIFECYCLE_METHODS.get(method_name)
        if lifecycle_method is None:
            return None

        location = Location(
            file_path=file_path.resolve(),
            line=node.start_point[0] + 1,
            column=node.start_point[1],
        )

        return LifecycleCall(
            instance=instance_name,
            method=lifecycle_method,
            location=location,
            order=order,
        )

    # ─────────────────────────────────────────────────────────────
    # Helper methods
    # ─────────────────────────────────────────────────────────────

    def _walk_tree(self, node: Any):
        """Walk AST tree yielding all nodes."""
        yield node
        for child in node.children:
            yield from self._walk_tree(child)

    def _find_function(self, root: Any, name: str) -> Optional[Any]:
        """Find a function definition by name."""
        for node in self._walk_tree(root):
            if node.type == "function_definition":
                func_name = self._get_function_name(node)
                if func_name == name:
                    return node
        return None

    def _get_function_name(self, node: Any) -> Optional[str]:
        """Extract function name from function_definition node."""
        for child in node.children:
            if child.type == "identifier":
                text = child.text
                if isinstance(text, bytes):
                    return text.decode("utf-8")
                return text
        return None

    def _get_decorators(self, node: Any, source: str) -> List[str]:
        """Get decorator names from a function definition."""
        decorators = []
        # Look at siblings before the function definition
        parent = node.parent
        if parent is None:
            return decorators

        idx = None
        for i, child in enumerate(parent.children):
            if child == node:
                idx = i
                break

        if idx is None:
            return decorators

        # Check previous siblings for decorators
        for i in range(idx - 1, -1, -1):
            sibling = parent.children[i]
            if sibling.type == "decorator":
                dec_text = self._get_node_text(sibling, source)
                # Extract decorator name from @name or @name(...)
                if dec_text.startswith("@"):
                    dec_name = dec_text[1:].split("(")[0].strip()
                    decorators.append(dec_name)
            else:
                break

        return decorators

    def _get_docstring(self, node: Any, source: str) -> Optional[str]:
        """Get docstring from a function definition."""
        body = self._find_child_by_type(node, "block")
        if body is None:
            return None

        # First statement might be docstring
        for child in body.children:
            if child.type == "expression_statement":
                for subchild in child.children:
                    if subchild.type == "string":
                        return self._get_node_text(subchild, source)
            break  # Only check first statement
        return None

    def _find_child_by_type(self, node: Any, type_name: str) -> Optional[Any]:
        """Find first direct child of given type."""
        for child in node.children:
            if child.type == type_name:
                return child
        return None

    def _get_node_text(self, node: Any, source: str) -> str:
        """Get the source text for a node."""
        if hasattr(node, "text"):
            text = node.text
            if isinstance(text, bytes):
                return text.decode("utf-8")
            return text

        # Fallback to extracting from source
        start = node.start_byte
        end = node.end_byte
        return source[start:end]
