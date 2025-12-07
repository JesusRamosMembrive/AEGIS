# Architecture: AEGIS C++ Analyzer Module

## 1. Context & Requirements
The goal is to introduce a new module to AEGIS: a C++ library and CLI tool capable of analyzing C++ projects. This module will serve as a high-performance backend to generate code metrics and dependency graphs, which AEGIS (the main application) will consume.

**Key Requirements:**
- **Metrics:** Calculate LOC, cyclomatic complexity, and count dependencies.
- **Graph:** Generate call graphs and dependency graphs (class/file level).
- **Integration:** Expose data via JSON or gRPC/REST for AEGIS.
- **Quality/Style:** Use Modern C++ (C++17/20), `std::filesystem`, smart pointers, `std::optional/variant`.
- **Architecture:** Reusable library core + CLI wrapper.
- **Advanced Features:** Incremental analysis (diff-based), benchmarks.

**Role in AEGIS:**
Acts as a specialized language server/analyzer for C++ contexts, likely spawned as a subprocess or microservice by the main AEGIS backend.

## 2. Stage Assessment
**Stage:** 2 (Prototype/MVP) -> 3 (Production)
*Rationale:* While this is a new feature (Stage 1), the requirement for strict C++ best practices, reusable library design, and "portfolio quality" implies we skip the "hacky script" phase. We aim for a solid architectural foundation (Stage 2) capable of evolving into a robust tool (Stage 3).

## 3. Component Structure

The solution will be divided into three main layers:

### A. Core Library (`libaegis-cpp`)
The brain of the operation. Pure C++, no CLI dependencies.
- **Parser/Analysis Engine:** Interfaces with the source code (via LibClang or custom parser).
- **Model:** Internal representation of Files, Classes, Functions, and their relationships.
- **Metrics Calculator:** Algorithms to compute complexity and stats on the Model.
- **Graph Builder:** logic to construct the dependency DAG.

### B. Interface Layer
- **Serializer:** Converts internal Model/Metrics to JSON/Protobuf.
- **Diff Engine:** logic to compare current state vs cache for incremental analysis.

### C. CLI (`aegis-cpp-cli`)
The executable entry point.
- Argument parsing (CLI11/argh).
- File discovery (`std::filesystem`).
- Orchestration (Load -> Analyze -> Serialize -> Print).

## 4. Technology Stack

- **Language:** C++20 (for concepts, ranges, modules support if viable).
- **Build System:** CMake + Ninja.
- **Parsing:** `libclang` (reliable, standard) OR `tree-sitter` (faster, robust for partial code). *Recommendation: tree-sitter-cpp for speed and fault tolerance, or libclang for perfect semantic accuracy.*
- **JSON:** `nlohmann/json` or `simdjson` (for benchmarks).
- **CLI Parsing:** `CLI11`.
- **Testing:** `Google Test` + `Google Benchmark` (for the requested benchmarks).

## 5. Build Order

1.  **Skeleton & Build System:** CMake setup, dependency management (vcpkg or conan), basic "Hello World" CLI.
2.  **Core Model & Filesystem:** Scanning directories, identifying `.cpp`/`.h` files using `std::filesystem`.
3.  **Parsing Integration:** Hook up the parser (e.g., LibClang/Tree-sitter) to define a basic AST traversal.
4.  **Metrics Implementation:**
    - LOC (lines of code).
    - Cyclomatic Complexity (counting control flow nodes).
5.  **Dependency Graph:** Resolve includes and symbol references to build the internal graph.
6.  **Serialization:** Output the data to JSON format matching AEGIS expectations.
7.  **Incremental Mode:** Implement hashing (MD5/SHA) of files to skip unchanged units.
8.  **Optimization & Benchmarks:** Profile with Google Benchmark and optimize.

## 6. Testing Strategy

- **Unit Tests:**
    - Test individual metric algorithms (e.g., feed a string of code, expect Complexity=5).
    - Test graph node insertion and linking.
- **Integration Tests:**
    - Run the CLI against a known dummy C++ project and verify the JSON output structure.
    - Measure performance on a large open-source repo (e.g., fmt implementation).
- **Benchmarks:**
    - Continuous benchmarking of the parsing phase to ensure "naive" alternatives are beaten.

## 7. Evolution Triggers
- **Support for more languages:** Abstract the parser interface.
- **LSP Integration:** Convert the CLI into a full Language Server Protocol implementation.
- **Deep Semantic Analysis:** Move from syntactic parsing to full semantic understanding (requires compiler flags/compile_commands.json).
