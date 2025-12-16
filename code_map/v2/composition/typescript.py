# SPDX-License-Identifier: MIT
"""
TypeScript/JavaScript composition root extractor using tree-sitter.

Extracts instances, wiring, and lifecycle calls from TypeScript/JavaScript
composition roots (typically index.ts, main.ts, or app.ts).
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
    "setNext",
    "set_next",
    "connect",
    "addListener",
    "addEventListener",
    "addObserver",
    "subscribe",
    "link",
    "pipe",
    "chain",
    "attach",
    "register",
    "add",
    "push",
    "on",
    "use",
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
    "dispose": LifecycleMethod.SHUTDOWN,
    "destroy": LifecycleMethod.SHUTDOWN,
}

# Factory function patterns
FACTORY_PATTERNS: List[re.Pattern] = [
    re.compile(r"^create[A-Z]"),  # createFoo
    re.compile(r"^make[A-Z]"),  # makeFoo
    re.compile(r"^build[A-Z]"),  # buildFoo
    re.compile(r"Factory$"),  # FooFactory
    re.compile(r"\.create$"),  # Factory.create
]

# Composition root function names
COMPOSITION_ROOT_FUNCTIONS: Set[str] = {
    "main",
    "createApp",
    "createPipeline",
    "setup",
    "configure",
    "bootstrap",
    "init",
    "initialize",
}

# Composition root file patterns
COMPOSITION_ROOT_FILES: Set[str] = {
    "index.ts",
    "index.js",
    "main.ts",
    "main.js",
    "app.ts",
    "app.js",
}


class TypeScriptCompositionExtractor(CompositionExtractor):
    """
    TypeScript/JavaScript composition root extractor using tree-sitter.

    Detects:
    - Instance declarations (new Class(), factory calls)
    - Wiring calls (setNext, connect, pipe, etc.)
    - Lifecycle calls (start, stop, init)
    """

    def __init__(self) -> None:
        """Initialize the extractor with tree-sitter parser."""
        self._parser: Optional[Any] = None
        self._available: Optional[bool] = None

    @property
    def language_id(self) -> str:
        return "typescript"

    @property
    def file_extensions(self) -> Tuple[str, ...]:
        return (".ts", ".tsx", ".js", ".jsx", ".mjs", ".mts")

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
                language = get_language("typescript")

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

    def _get_parser_for_file(self, file_path: Path) -> Optional[Any]:
        """Get appropriate parser for file extension."""
        if not self._ensure_parser():
            return None

        # TypeScript parser handles both .ts and .js reasonably well
        # For pure JS files, we could switch to JavaScript parser if needed
        return self._parser

    def find_composition_roots(self, file_path: Path) -> List[str]:
        """Find composition root functions in a TypeScript/JavaScript file."""
        parser = self._get_parser_for_file(file_path)
        if parser is None:
            return []

        try:
            source = file_path.read_text(encoding="utf-8")
        except OSError:
            return []

        tree = parser.parse(bytes(source, "utf-8"))
        roots: List[str] = []

        # Walk AST looking for function definitions
        for node in self._walk_tree(tree.root_node):
            if node.type in ("function_declaration", "method_definition"):
                func_name = self._get_function_name(node)
                if func_name and self._is_composition_root(func_name, node, source):
                    roots.append(func_name)
            elif node.type == "variable_declarator":
                # Arrow functions or function expressions
                var_name = self._get_variable_name(node)
                if var_name and self._is_composition_root(var_name, node, source):
                    roots.append(var_name)

        # Check if this is a composition root file (index.ts, main.ts, etc.)
        if file_path.name in COMPOSITION_ROOT_FILES:
            # Look for top-level code or IIFE
            if self._has_top_level_code(tree.root_node, source):
                roots.append("__module__")

        return roots

    def _is_composition_root(
        self, func_name: str, node: Any, source: str
    ) -> bool:
        """Check if a function is a composition root."""
        # Convention: known composition root function names
        if func_name in COMPOSITION_ROOT_FUNCTIONS:
            return True

        # Check for @aegis-composition-root marker in JSDoc
        jsdoc = self._get_preceding_jsdoc(node, source)
        if jsdoc and "@aegis-composition-root" in jsdoc:
            return True

        return False

    def _has_top_level_code(self, root: Any, source: str) -> bool:
        """Check if file has meaningful top-level code (not just imports/exports)."""
        for child in root.children:
            # Skip imports, exports of declarations, comments
            if child.type in (
                "import_statement",
                "export_statement",
                "comment",
                "program",
            ):
                continue
            # Expression statements at top level might be composition code
            if child.type == "expression_statement":
                return True
            # Variable declarations with instantiation
            if child.type in ("variable_declaration", "lexical_declaration"):
                for declarator in self._walk_tree(child):
                    if declarator.type in ("new_expression", "call_expression"):
                        return True
        return False

    def extract(
        self,
        file_path: Path,
        function_name: Optional[str] = None,
    ) -> Optional[CompositionRoot]:
        """Extract composition root from a TypeScript/JavaScript file."""
        parser = self._get_parser_for_file(file_path)
        if parser is None:
            return None

        try:
            source = file_path.read_text(encoding="utf-8")
        except OSError:
            return None

        tree = parser.parse(bytes(source, "utf-8"))
        target_func = function_name or "main"

        # Special case: extract from module-level code
        if target_func == "__module__":
            return self._extract_from_module(tree.root_node, file_path, source)

        # Find the target function
        func_node = self._find_function(tree.root_node, target_func, source)
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

        # Find function body (statement_block)
        body = self._find_child_by_type(func_node, "statement_block")
        if body is None:
            # Arrow function might have direct expression
            body = func_node

        # Extract instances, wiring, and lifecycle
        self._extract_instances(body, file_path, root, source)
        self._extract_wiring(body, file_path, root, source)
        self._extract_lifecycle(body, file_path, root, source)

        return root

    def _extract_from_module(
        self, root: Any, file_path: Path, source: str
    ) -> Optional[CompositionRoot]:
        """Extract from module-level (top-level) code."""
        location = Location(
            file_path=file_path.resolve(),
            line=1,
            column=0,
        )

        comp_root = CompositionRoot(
            file_path=file_path.resolve(),
            function_name="__module__",
            location=location,
        )

        # Process top-level statements
        self._extract_instances(root, file_path, comp_root, source)
        self._extract_wiring(root, file_path, comp_root, source)
        self._extract_lifecycle(root, file_path, comp_root, source)

        return comp_root

    def _extract_instances(
        self,
        body: Any,
        file_path: Path,
        root: CompositionRoot,
        source: str,
    ) -> None:
        """Extract instance declarations from function body."""
        for node in self._walk_tree(body):
            if node.type in ("variable_declaration", "lexical_declaration"):
                # const/let/var declarations
                for child in node.children:
                    if child.type == "variable_declarator":
                        instance = self._parse_variable_declarator(
                            child, file_path, source
                        )
                        if instance:
                            root.instances.append(instance)

    def _parse_variable_declarator(
        self,
        node: Any,
        file_path: Path,
        source: str,
    ) -> Optional[InstanceInfo]:
        """Parse a variable declarator to extract instance info."""
        var_name = None
        initializer = None

        for child in node.children:
            if child.type == "identifier":
                var_name = self._get_node_text(child, source)
            elif child.type in ("new_expression", "call_expression"):
                initializer = child

        if var_name is None or initializer is None:
            return None

        # Parse the initializer
        creation_pattern = CreationPattern.UNKNOWN
        factory_name = None
        actual_type = None
        constructor_args: List[str] = []

        if initializer.type == "new_expression":
            # new Class()
            creation_pattern = CreationPattern.DIRECT
            class_node = self._find_child_by_type(initializer, "identifier")
            if class_node:
                actual_type = self._get_node_text(class_node, source)
            args_node = self._find_child_by_type(initializer, "arguments")
            if args_node:
                constructor_args = self._parse_arguments(args_node, source)

        elif initializer.type == "call_expression":
            # Factory function or method call
            call_info = self._parse_call_expression(initializer, source)
            creation_pattern = call_info.get("pattern", CreationPattern.UNKNOWN)
            factory_name = call_info.get("factory_name")
            actual_type = call_info.get("actual_type")
            constructor_args = call_info.get("args", [])

        # Skip if we couldn't identify a type or factory
        if actual_type is None and factory_name is None:
            return None

        location = Location(
            file_path=file_path.resolve(),
            line=node.start_point[0] + 1,
            column=node.start_point[1],
        )

        return InstanceInfo(
            name=var_name,
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

        if node.type != "call_expression":
            return result

        # Get the function being called
        func_name = None
        for child in node.children:
            if child.type == "identifier":
                func_name = self._get_node_text(child, source)
                break
            elif child.type == "member_expression":
                # Factory.create() pattern
                func_name = self._get_node_text(child, source)
                break

        if func_name:
            # Check if it's a factory function
            if any(p.search(func_name) for p in FACTORY_PATTERNS):
                result["pattern"] = CreationPattern.FACTORY
                result["factory_name"] = func_name
                # Try to infer type from factory name
                # e.g., createGenerator -> Generator
                for prefix in ("create", "make", "build"):
                    if func_name.startswith(prefix):
                        type_name = func_name[len(prefix):]
                        if type_name:
                            result["actual_type"] = type_name
                        break
            elif func_name[0].isupper():
                # PascalCase function call (might be constructor-like)
                result["pattern"] = CreationPattern.DIRECT
                result["actual_type"] = func_name
            else:
                # Generic function call
                result["pattern"] = CreationPattern.FACTORY
                result["factory_name"] = func_name

        # Extract arguments
        args_node = self._find_child_by_type(node, "arguments")
        if args_node:
            result["args"] = self._parse_arguments(args_node, source)

        return result

    def _parse_arguments(self, node: Any, source: str) -> List[str]:
        """Parse arguments node to extract argument strings."""
        args: List[str] = []
        for child in node.children:
            if child.type not in ("(", ")", ","):
                args.append(self._get_node_text(child, source))
        return args

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
        call_node = None
        for child in self._walk_tree(node):
            if child.type == "call_expression":
                call_node = child
                break

        if call_node is None:
            return None

        # Look for member expression: obj.method()
        member_node = self._find_child_by_type(call_node, "member_expression")
        if member_node is None:
            return None

        # Parse member expression: object.method
        source_instance = None
        method_name = None

        for child in member_node.children:
            if child.type == "identifier":
                text = self._get_node_text(child, source)
                if text in instance_names:
                    source_instance = text
                else:
                    method_name = text
            elif child.type == "property_identifier":
                method_name = self._get_node_text(child, source)

        if source_instance is None or method_name is None:
            return None

        # Check if method is a wiring method
        if method_name not in WIRING_METHODS:
            return None

        # Find the target instance in arguments
        args_node = self._find_child_by_type(call_node, "arguments")
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
        call_node = None
        for child in self._walk_tree(node):
            if child.type == "call_expression":
                call_node = child
                break

        if call_node is None:
            return None

        # Look for member expression
        member_node = self._find_child_by_type(call_node, "member_expression")
        if member_node is None:
            return None

        # Parse to get instance and method
        instance_name = None
        method_name = None

        for child in member_node.children:
            if child.type == "identifier":
                text = self._get_node_text(child, source)
                if text in instance_names:
                    instance_name = text
                elif text in LIFECYCLE_METHODS:
                    method_name = text
            elif child.type == "property_identifier":
                text = self._get_node_text(child, source)
                if text in LIFECYCLE_METHODS:
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

    def _find_function(
        self, root: Any, name: str, source: str
    ) -> Optional[Any]:
        """Find a function definition by name."""
        for node in self._walk_tree(root):
            if node.type == "function_declaration":
                func_name = self._get_function_name(node)
                if func_name == name:
                    return node
            elif node.type == "variable_declarator":
                var_name = self._get_variable_name(node)
                if var_name == name:
                    # Check if it's a function
                    for child in node.children:
                        if child.type in (
                            "arrow_function",
                            "function_expression",
                            "function",
                        ):
                            return node
        return None

    def _get_function_name(self, node: Any) -> Optional[str]:
        """Extract function name from function_declaration node."""
        for child in node.children:
            if child.type == "identifier":
                text = child.text
                if isinstance(text, bytes):
                    return text.decode("utf-8")
                return text
        return None

    def _get_variable_name(self, node: Any) -> Optional[str]:
        """Extract variable name from variable_declarator node."""
        for child in node.children:
            if child.type == "identifier":
                text = child.text
                if isinstance(text, bytes):
                    return text.decode("utf-8")
                return text
        return None

    def _get_preceding_jsdoc(self, node: Any, source: str) -> Optional[str]:
        """Get JSDoc comment preceding a node."""
        parent = node.parent
        if parent is None:
            return None

        idx = None
        for i, child in enumerate(parent.children):
            if child == node:
                idx = i
                break

        if idx is None:
            return None

        # Check previous sibling for comment
        if idx > 0:
            prev = parent.children[idx - 1]
            if prev.type == "comment":
                return self._get_node_text(prev, source)

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
