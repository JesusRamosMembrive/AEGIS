# SPDX-License-Identifier: MIT
"""
Composition root extraction module.

Provides language-specific strategies for extracting instances and wiring
from composition roots (main functions, factories, etc.).
"""

from .base import CompositionExtractor
from .cpp import CppCompositionExtractor
from .python import PythonCompositionExtractor
from .typescript import TypeScriptCompositionExtractor

__all__ = [
    "CompositionExtractor",
    "CppCompositionExtractor",
    "PythonCompositionExtractor",
    "TypeScriptCompositionExtractor",
]
