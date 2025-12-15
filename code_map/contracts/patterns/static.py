# SPDX-License-Identifier: MIT
"""
Level 4: Static analysis for contract inference.

Extracts implied contracts from code patterns like:
- assert() statements
- throw/raise statements
- null checks
- mutex/lock usage
"""

import re
from pathlib import Path
from typing import List

from ..schema import ContractData, ThreadSafety


class StaticAnalyzer:
    """Infers contracts from static code patterns."""

    # Precondition patterns
    PRECONDITION_PATTERNS = [
        # C++ assert
        (re.compile(r"assert\s*\(\s*(.+?)\s*\)"), "cpp"),
        # C++ null check before throw
        (re.compile(r"if\s*\(\s*!?\s*(\w+)\s*\)\s*throw"), "cpp"),
        (re.compile(r"if\s*\(\s*(\w+)\s*==\s*nullptr\s*\)"), "cpp"),
        # Python assert
        (re.compile(r"assert\s+(.+?)(?:,|\n|$)"), "python"),
        # Python if-raise
        (re.compile(r"if\s+(.+?):\s*\n\s*raise"), "python"),
    ]

    # Thread safety patterns
    THREAD_SAFETY_PATTERNS = [
        # C++
        (re.compile(r"std::mutex"), "cpp", ThreadSafety.SAFE),
        (re.compile(r"std::lock_guard"), "cpp", ThreadSafety.SAFE),
        (re.compile(r"std::unique_lock"), "cpp", ThreadSafety.SAFE),
        (re.compile(r"std::atomic"), "cpp", ThreadSafety.SAFE),
        (re.compile(r"std::shared_mutex"), "cpp", ThreadSafety.SAFE),
        # Python
        (re.compile(r"threading\.Lock"), "python", ThreadSafety.SAFE),
        (re.compile(r"threading\.RLock"), "python", ThreadSafety.SAFE),
        (re.compile(r"asyncio\.Lock"), "python", ThreadSafety.SAFE),
    ]

    # Error patterns
    ERROR_PATTERNS = [
        # C++ throw
        (re.compile(r"throw\s+(\w+)(?:\s*\()?"), "cpp"),
        # Python raise
        (re.compile(r"raise\s+(\w+)(?:\s*\()?"), "python"),
    ]

    def analyze(self, source: str, file_path: Path) -> ContractData:
        """
        Analyze source code for implied contracts.

        Args:
            source: Source code content
            file_path: Path to determine language

        Returns:
            ContractData with inferred contracts
        """
        contract = ContractData(
            confidence=0.4,
            source_level=4,
            inferred=True,
            file_path=file_path,
        )

        # Determine language
        ext = file_path.suffix.lower()
        lang = "cpp" if ext in (".cpp", ".hpp", ".h", ".cc", ".c") else "python"

        # Extract preconditions
        preconditions = self._extract_preconditions(source, lang)
        contract.preconditions = preconditions[:5]  # Limit to avoid noise

        # Detect thread safety
        thread_safety = self._detect_thread_safety(source, lang)
        if thread_safety:
            contract.thread_safety = thread_safety

        # Extract errors
        errors = self._extract_errors(source, lang)
        contract.errors = list(set(errors))[:5]  # Dedupe and limit

        if contract.is_empty():
            contract.confidence = 0.0
            contract.confidence_notes = "No patterns detected in static analysis"

        return contract

    def _extract_preconditions(self, source: str, lang: str) -> List[str]:
        """Extract preconditions from assert patterns."""
        preconditions = []

        for pattern, pattern_lang in self.PRECONDITION_PATTERNS:
            if pattern_lang != lang:
                continue
            for match in pattern.finditer(source):
                condition = match.group(1).strip()
                if condition and len(condition) < 100:  # Skip overly complex
                    # Clean up the condition
                    condition = " ".join(condition.split())
                    preconditions.append(condition)

        return preconditions

    def _detect_thread_safety(self, source: str, lang: str) -> ThreadSafety | None:
        """Detect thread safety from synchronization primitives."""
        for pattern, pattern_lang, safety in self.THREAD_SAFETY_PATTERNS:
            if pattern_lang != lang:
                continue
            if pattern.search(source):
                return safety
        return None

    def _extract_errors(self, source: str, lang: str) -> List[str]:
        """Extract error types from throw/raise statements."""
        errors = []

        for pattern, pattern_lang in self.ERROR_PATTERNS:
            if pattern_lang != lang:
                continue
            for match in pattern.finditer(source):
                error_type = match.group(1).strip()
                if error_type and error_type not in ("if", "else", "return"):
                    errors.append(error_type)

        return errors
