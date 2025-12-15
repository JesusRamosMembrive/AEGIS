# SPDX-License-Identifier: MIT
"""
Base class for composition root extractors.

Defines the interface that all language-specific extractors must implement.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Tuple

from ..models import CompositionRoot


class CompositionExtractor(ABC):
    """
    Abstract base class for composition root extraction.

    Each language implementation provides methods to:
    1. Detect composition root functions (main, create_app, etc.)
    2. Extract instance declarations
    3. Extract wiring calls
    4. Extract lifecycle calls
    """

    @property
    @abstractmethod
    def language_id(self) -> str:
        """Unique identifier for the language (e.g., 'cpp', 'python')."""
        pass

    @property
    @abstractmethod
    def file_extensions(self) -> Tuple[str, ...]:
        """File extensions this extractor handles."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if required dependencies (tree-sitter, etc.) are available."""
        pass

    @abstractmethod
    def find_composition_roots(self, file_path: Path) -> List[str]:
        """
        Find composition root functions in a file.

        By convention, these include:
        - main() function
        - Functions marked with @aegis-composition-root
        - create_app(), create_pipeline(), etc.

        Args:
            file_path: Path to the source file

        Returns:
            List of function names that are composition roots
        """
        pass

    @abstractmethod
    def extract(
        self,
        file_path: Path,
        function_name: Optional[str] = None,
    ) -> Optional[CompositionRoot]:
        """
        Extract composition root information from a file.

        Args:
            file_path: Path to the source file
            function_name: Specific function to extract (defaults to main)

        Returns:
            CompositionRoot with instances, wiring, and lifecycle,
            or None if no composition root found
        """
        pass

    def supports_file(self, file_path: Path) -> bool:
        """Check if this extractor can handle the given file."""
        return file_path.suffix.lower() in self.file_extensions
