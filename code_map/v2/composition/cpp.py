# SPDX-License-Identifier: MIT
"""
C++ composition root extractor using tree-sitter.

Extracts instances, wiring, and lifecycle calls from C++ composition roots
(typically main.cpp).
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
    "add_listener",
    "addObserver",
    "add_observer",
    "subscribe",
    "link",
    "pipe",
    "chain",
    "attach",
    "register",
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
}

# Factory function patterns
FACTORY_PATTERNS: List[re.Pattern] = [
    re.compile(r"^create[A-Z]"),  # createFoo
    re.compile(r"^make[A-Z]"),  # makeFoo
    re.compile(r"^build[A-Z]"),  # buildFoo
    re.compile(r"Factory$"),  # FooFactory.create
]


class CppCompositionExtractor(CompositionExtractor):
    """
    C++ composition root extractor using tree-sitter.

    Detects:
    - Instance declarations (unique_ptr, shared_ptr, auto with factories)
    - Wiring calls (setNext, connect, etc.)
    - Lifecycle calls (start, stop, init)
    """

    def __init__(self) -> None:
        """Initialize the extractor with tree-sitter parser."""
        self._parser: Optional[Any] = None
        self._available: Optional[bool] = None

    @property
    def language_id(self) -> str:
        return "cpp"

    @property
    def file_extensions(self) -> Tuple[str, ...]:
        return (".cpp", ".cc", ".cxx", ".hpp", ".h", ".hxx")

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
                language = get_language("cpp")

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
        """Find composition root functions in a C++ file."""
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

        return roots

    def _is_composition_root(
        self, func_name: str, node: Any, source: str
    ) -> bool:
        """Check if a function is a composition root."""
        # Convention: main() is always a composition root
        if func_name == "main":
            return True

        # Check for @aegis-composition-root marker in preceding comment
        lines = source.splitlines()
        start_line = node.start_point[0]

        # Look at previous lines for marker
        for offset in range(1, 10):
            idx = start_line - offset
            if idx < 0:
                break
            line = lines[idx].strip()
            if "@aegis-composition-root" in line:
                return True
            # Stop if we hit non-comment non-empty line
            if line and not line.startswith("//") and not line.startswith("/*"):
                break

        return False

    def extract(
        self,
        file_path: Path,
        function_name: Optional[str] = None,
    ) -> Optional[CompositionRoot]:
        """Extract composition root from a C++ file."""
        if not self._ensure_parser():
            return None

        try:
            source = file_path.read_text(encoding="utf-8")
        except OSError:
            return None

        tree = self._parser.parse(bytes(source, "utf-8"))
        target_func = function_name or "main"

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

        # Find function body
        body = self._find_child_by_type(func_node, "compound_statement")
        if body is None:
            return root

        # Extract instances, wiring, and lifecycle
        self._extract_instances(body, file_path, root, source)
        self._extract_wiring(body, file_path, root)
        self._extract_lifecycle(body, file_path, root)

        return root

    def _extract_instances(
        self,
        body: Any,
        file_path: Path,
        root: CompositionRoot,
        source: str,
    ) -> None:
        """Extract instance declarations from function body."""
        for node in self._walk_tree(body):
            if node.type == "declaration":
                instance = self._parse_declaration(node, file_path, source)
                if instance:
                    root.instances.append(instance)

    def _parse_declaration(
        self,
        node: Any,
        file_path: Path,
        source: str,
    ) -> Optional[InstanceInfo]:
        """Parse a variable declaration to extract instance info."""
        # Get the declarator (contains variable name and initializer)
        declarator = None
        type_name = "auto"

        for child in node.children:
            if child.type in ("init_declarator", "declarator"):
                declarator = child
            elif child.type in (
                "type_identifier",
                "primitive_type",
                "auto",
                "template_type",
            ):
                type_name = self._get_node_text(child, source)
            elif child.type == "qualified_identifier":
                type_name = self._get_node_text(child, source)

        if declarator is None:
            return None

        # Handle init_declarator: "name = initializer"
        if declarator.type == "init_declarator":
            var_name = None
            initializer = None

            for child in declarator.children:
                if child.type == "identifier":
                    var_name = self._get_node_text(child, source)
                elif child.type == "call_expression":
                    initializer = child
                elif child.type == "pointer_declarator":
                    # Handle "auto* name = ..."
                    for sub in child.children:
                        if sub.type == "identifier":
                            var_name = self._get_node_text(sub, source)

            if var_name is None:
                return None

            # Parse the initializer to get creation pattern and factory
            creation_pattern = CreationPattern.UNKNOWN
            factory_name = None
            actual_type = None
            constructor_args: List[str] = []
            is_pointer = False
            pointer_type = None

            if initializer:
                init_info = self._parse_initializer(initializer, source)
                creation_pattern = init_info.get("pattern", CreationPattern.UNKNOWN)
                factory_name = init_info.get("factory_name")
                actual_type = init_info.get("actual_type")
                constructor_args = init_info.get("args", [])
                is_pointer = init_info.get("is_pointer", False)
                pointer_type = init_info.get("pointer_type")

            location = Location(
                file_path=file_path.resolve(),
                line=node.start_point[0] + 1,
                column=node.start_point[1],
            )

            return InstanceInfo(
                name=var_name,
                type_name=type_name,
                location=location,
                creation_pattern=creation_pattern,
                actual_type=actual_type,
                factory_name=factory_name,
                constructor_args=constructor_args,
                is_pointer=is_pointer,
                pointer_type=pointer_type,
            )

        return None

    def _parse_initializer(
        self,
        node: Any,
        source: str,
    ) -> Dict[str, Any]:
        """Parse initializer expression to extract creation info."""
        result: Dict[str, Any] = {
            "pattern": CreationPattern.UNKNOWN,
            "factory_name": None,
            "actual_type": None,
            "args": [],
            "is_pointer": False,
            "pointer_type": None,
        }

        if node.type != "call_expression":
            return result

        # Get the function being called
        function_node = self._find_child_by_type(node, "identifier")
        if function_node is None:
            function_node = self._find_child_by_type(node, "qualified_identifier")
        if function_node is None:
            function_node = self._find_child_by_type(node, "template_function")

        func_name = None
        if function_node:
            func_name = self._get_node_text(function_node, source)

        # Check for std::make_unique or std::make_shared
        if func_name:
            if "make_unique" in func_name:
                result["pattern"] = CreationPattern.MAKE_UNIQUE
                result["is_pointer"] = True
                result["pointer_type"] = "unique_ptr"
                # Extract template type
                template_node = self._find_child_by_type(node, "template_argument_list")
                if template_node:
                    for child in template_node.children:
                        if child.type == "type_descriptor":
                            result["actual_type"] = self._get_node_text(child, source)
                            break

            elif "make_shared" in func_name:
                result["pattern"] = CreationPattern.MAKE_SHARED
                result["is_pointer"] = True
                result["pointer_type"] = "shared_ptr"
                template_node = self._find_child_by_type(node, "template_argument_list")
                if template_node:
                    for child in template_node.children:
                        if child.type == "type_descriptor":
                            result["actual_type"] = self._get_node_text(child, source)
                            break

            # Check if it's a factory function
            elif any(p.search(func_name) for p in FACTORY_PATTERNS):
                result["pattern"] = CreationPattern.FACTORY
                result["factory_name"] = func_name
                result["is_pointer"] = True  # Factories typically return smart pointers
                result["pointer_type"] = "unique_ptr"  # Assume unique_ptr

        # Extract constructor arguments
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
    ) -> None:
        """Extract wiring calls from function body."""
        instance_names = {inst.name for inst in root.instances}

        for node in self._walk_tree(body):
            if node.type == "expression_statement":
                wiring = self._parse_wiring_call(node, file_path, instance_names)
                if wiring:
                    root.wiring.append(wiring)

    def _parse_wiring_call(
        self,
        node: Any,
        file_path: Path,
        instance_names: Set[str],
    ) -> Optional[WiringInfo]:
        """Parse a statement to check if it's a wiring call."""
        # Find call_expression within the statement
        call_node = self._find_child_by_type(node, "call_expression")
        if call_node is None:
            return None

        # Get the source for text extraction
        try:
            source = file_path.read_text(encoding="utf-8")
        except OSError:
            return None

        # Look for member function call: obj->method() or obj.method()
        # In tree-sitter, this is a call_expression with a field_expression as function
        function_part = None
        for child in call_node.children:
            if child.type in ("field_expression", "pointer_expression"):
                function_part = child
                break

        if function_part is None:
            return None

        # Parse field_expression: argument->field or argument.field
        source_instance = None
        method_name = None

        for child in function_part.children:
            if child.type == "identifier":
                # Could be the object or the method
                text = self._get_node_text(child, source)
                if text in instance_names:
                    source_instance = text
                else:
                    method_name = text
            elif child.type == "field_identifier":
                method_name = self._get_node_text(child, source)

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
            if arg.type == "call_expression":
                # Handle m2.get() - the argument is itself a call
                inner = self._find_child_by_type(arg, "field_expression")
                if inner:
                    for child in inner.children:
                        if child.type == "identifier":
                            text = self._get_node_text(child, source)
                            if text in instance_names:
                                target_instance = text
                                break
            elif arg.type == "identifier":
                text = self._get_node_text(arg, source)
                if text in instance_names:
                    target_instance = text
            elif arg.type == "pointer_expression":
                # Handle &instance or *instance
                for child in arg.children:
                    if child.type == "identifier":
                        text = self._get_node_text(child, source)
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
    ) -> None:
        """Extract lifecycle method calls."""
        instance_names = {inst.name for inst in root.instances}
        order = 0

        try:
            source = file_path.read_text(encoding="utf-8")
        except OSError:
            return

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
        call_node = self._find_child_by_type(node, "call_expression")
        if call_node is None:
            return None

        # Look for member function call
        function_part = None
        for child in call_node.children:
            if child.type in ("field_expression", "pointer_expression"):
                function_part = child
                break

        if function_part is None:
            return None

        # Parse to get instance and method
        instance_name = None
        method_name = None

        for child in function_part.children:
            if child.type == "identifier":
                text = self._get_node_text(child, source)
                if text in instance_names:
                    instance_name = text
                elif text in LIFECYCLE_METHODS:
                    method_name = text
            elif child.type == "field_identifier":
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
        declarator = None
        for child in node.children:
            if child.type == "function_declarator":
                declarator = child
                break
            elif child.type == "pointer_declarator":
                # Handle "int* func()"
                for sub in child.children:
                    if sub.type == "function_declarator":
                        declarator = sub
                        break

        if declarator is None:
            return None

        # Find identifier in declarator
        for child in declarator.children:
            if child.type == "identifier":
                return child.text.decode("utf-8") if isinstance(child.text, bytes) else child.text
            elif child.type == "qualified_identifier":
                # Handle Class::method
                for sub in child.children:
                    if sub.type == "identifier":
                        return sub.text.decode("utf-8") if isinstance(sub.text, bytes) else sub.text

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
