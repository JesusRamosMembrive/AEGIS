/**
 * @file metrics.hpp
 * @brief Code metrics data structures and LOC calculation.
 * @author AEGIS Team
 * @date 2024
 *
 * This module defines data structures for representing code metrics
 * at function, file, and project levels. It also provides basic
 * line-of-code (LOC) calculation functionality.
 */

#pragma once

#include <cstdint>
#include <filesystem>
#include <optional>
#include <string>
#include <vector>

namespace aegis {

/**
 * @struct FunctionMetrics
 * @brief Metrics for a single function or method.
 *
 * Contains detailed metrics about a function including its location,
 * size, and cyclomatic complexity.
 */
struct FunctionMetrics {
    std::string name;  ///< Simple function name
    std::string qualified_name;  ///< Fully qualified name (includes class/namespace)
    std::uint32_t line_start{0};  ///< Starting line number (1-indexed)
    std::uint32_t line_end{0};  ///< Ending line number (1-indexed)
    std::uint32_t length{0};  ///< Number of lines (line_end - line_start + 1)
    std::uint32_t cyclomatic_complexity{1};  ///< Cyclomatic complexity (minimum is 1)
};

/**
 * @struct FileMetrics
 * @brief Metrics for a single source file.
 *
 * Contains line counts broken down by type (code, blank, comment)
 * and a list of functions defined in the file.
 */
struct FileMetrics {
    std::filesystem::path path;  ///< Absolute path to the file
    std::uint32_t total_lines{0};  ///< Total lines including blanks and comments
    std::uint32_t code_lines{0};  ///< Lines containing actual code
    std::uint32_t blank_lines{0};  ///< Empty or whitespace-only lines
    std::uint32_t comment_lines{0};  ///< Lines containing comments
    std::vector<FunctionMetrics> functions;  ///< Functions defined in this file
};

/**
 * @struct ProjectMetrics
 * @brief Aggregated metrics for an entire project.
 *
 * Contains summary statistics across all analyzed files
 * as well as per-file breakdown.
 */
struct ProjectMetrics {
    std::uint32_t total_files{0};  ///< Number of files analyzed
    std::uint32_t total_lines{0};  ///< Sum of all lines across files
    std::uint32_t total_code_lines{0};  ///< Sum of code lines across files
    std::uint32_t total_functions{0};  ///< Total number of functions found
    std::vector<FileMetrics> files;  ///< Per-file metrics
};

/**
 * @brief Calculate basic line metrics for a single file.
 *
 * Reads the file and counts total lines, code lines, blank lines,
 * and comment lines. Uses simple heuristics for comment detection.
 *
 * @param path Absolute path to the source file.
 * @return FileMetrics with line counts, or std::nullopt if file cannot be read.
 *
 * @note This function does not populate the functions vector.
 *       Use Analyzer::analyze_file() for full analysis.
 *
 * @par Example
 * @code
 * auto metrics = aegis::calculate_file_loc("/path/to/file.cpp");
 * if (metrics) {
 *     std::cout << "Code lines: " << metrics->code_lines << "\n";
 * }
 * @endcode
 *
 * @see calculate_project_loc, Analyzer::analyze_file
 */
[[nodiscard]] std::optional<FileMetrics> calculate_file_loc(
    const std::filesystem::path& path);

/**
 * @brief Calculate basic LOC metrics for multiple files.
 *
 * Iterates over the provided paths and aggregates line counts
 * into a ProjectMetrics structure.
 *
 * @param paths Vector of absolute file paths to analyze.
 * @return ProjectMetrics with aggregated line counts.
 *
 * @note Files that cannot be read are silently skipped.
 * @note This function does not populate function metrics.
 *
 * @par Example
 * @code
 * std::vector<std::filesystem::path> files = {"/a.cpp", "/b.cpp"};
 * auto project = aegis::calculate_project_loc(files);
 * std::cout << "Total LOC: " << project.total_lines << "\n";
 * @endcode
 *
 * @see calculate_file_loc, Analyzer::analyze_project
 */
[[nodiscard]] ProjectMetrics calculate_project_loc(
    const std::vector<std::filesystem::path>& paths);

}  // namespace aegis
