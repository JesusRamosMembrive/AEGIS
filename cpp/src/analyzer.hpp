/**
 * @file analyzer.hpp
 * @brief Semantic code analyzer using libclang.
 * @author AEGIS Team
 * @date 2024
 *
 * This module provides semantic analysis of C/C++ source files using
 * libclang. It extracts function definitions, calculates cyclomatic
 * complexity, and provides detailed metrics beyond simple LOC counting.
 *
 * @note If libclang is not available at compile time, the analyzer
 *       falls back to basic LOC calculation only.
 */

#pragma once

#include "metrics.hpp"

#include <filesystem>
#include <memory>
#include <optional>
#include <string>
#include <vector>

namespace aegis {

/**
 * @struct AnalyzerConfig
 * @brief Configuration options for the semantic analyzer.
 *
 * Provides settings to customize libclang's parsing behavior,
 * including include paths and compiler flags.
 */
struct AnalyzerConfig {
    /// Additional include paths for header resolution (e.g., "-I/usr/include")
    std::vector<std::string> include_paths;

    /// Additional compiler flags passed to libclang
    std::vector<std::string> compiler_flags;

    /// Path to compile_commands.json for accurate compilation settings
    std::optional<std::filesystem::path> compilation_database;
};

/**
 * @class Analyzer
 * @brief Semantic code analyzer using libclang.
 *
 * The Analyzer class uses libclang to parse C/C++ source files and
 * extract detailed metrics including function definitions, line counts,
 * and cyclomatic complexity.
 *
 * @par Cyclomatic Complexity
 * Cyclomatic complexity is calculated by counting decision points:
 * - if, for, while, do-while statements
 * - case labels in switch statements
 * - Ternary operators (?:)
 * - Logical operators (&& and ||)
 *
 * The minimum complexity for any function is 1.
 *
 * @par Example Usage
 * @code
 * aegis::AnalyzerConfig config;
 * config.include_paths = {"/usr/include", "/usr/local/include"};
 *
 * aegis::Analyzer analyzer(config);
 *
 * if (aegis::Analyzer::is_available()) {
 *     auto metrics = analyzer.analyze_file("/path/to/file.cpp");
 *     if (metrics) {
 *         for (const auto& func : metrics->functions) {
 *             std::cout << func.name << ": complexity = "
 *                       << func.cyclomatic_complexity << "\n";
 *         }
 *     }
 * }
 * @endcode
 *
 * @note This class is non-copyable but movable.
 * @note Uses the PIMPL idiom for ABI stability and to hide libclang dependencies.
 *
 * @see AnalyzerConfig, FileMetrics, FunctionMetrics
 */
class Analyzer {
public:
    /**
     * @brief Construct an analyzer with the given configuration.
     * @param config Analyzer configuration (defaults to empty config).
     */
    explicit Analyzer(AnalyzerConfig config = {});

    /**
     * @brief Destructor.
     *
     * Releases libclang resources if they were allocated.
     */
    ~Analyzer();

    /// @name Deleted copy operations
    /// @{
    Analyzer(const Analyzer&) = delete;
    Analyzer& operator=(const Analyzer&) = delete;
    /// @}

    /// @name Move operations
    /// @{
    Analyzer(Analyzer&&) noexcept;
    Analyzer& operator=(Analyzer&&) noexcept;
    /// @}

    /**
     * @brief Analyze a single source file.
     *
     * Parses the file using libclang (if available) to extract:
     * - Line counts (total, code, blank, comment)
     * - Function definitions with location
     * - Cyclomatic complexity for each function
     *
     * @param path Absolute path to the source file.
     * @return FileMetrics with full analysis, or std::nullopt on failure.
     *
     * @note If libclang is unavailable, falls back to calculate_file_loc().
     */
    [[nodiscard]] std::optional<FileMetrics> analyze_file(
        const std::filesystem::path& path) const;

    /**
     * @brief Analyze multiple source files.
     *
     * Iterates over all provided paths and aggregates results
     * into a ProjectMetrics structure.
     *
     * @param paths Vector of absolute file paths to analyze.
     * @return ProjectMetrics with aggregated analysis.
     *
     * @note Files that fail to parse are silently skipped.
     */
    [[nodiscard]] ProjectMetrics analyze_project(
        const std::vector<std::filesystem::path>& paths) const;

    /**
     * @brief Check if libclang-based analysis is available.
     *
     * Returns whether the analyzer was compiled with libclang support
     * and can perform semantic analysis.
     *
     * @return true if semantic analysis is available, false if only LOC counting.
     */
    [[nodiscard]] static bool is_available() noexcept;

private:
    /// @brief Private implementation (PIMPL idiom)
    struct Impl;

    /// @brief Pointer to implementation
    std::unique_ptr<Impl> impl_;
};

}  // namespace aegis
