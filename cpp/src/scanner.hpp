/**
 * @file scanner.hpp
 * @brief Project file scanner for source code discovery.
 * @author AEGIS Team
 * @date 2024
 *
 * This module provides functionality to recursively scan project directories
 * and discover source files based on configurable extensions and exclusion rules.
 */

#pragma once

#include <filesystem>
#include <memory>
#include <string>
#include <unordered_set>
#include <vector>

namespace aegis {

/**
 * @struct FileInfo
 * @brief Information about a discovered source file.
 *
 * Contains metadata about a file found during project scanning,
 * including its path and size.
 */
struct FileInfo {
    std::filesystem::path path;  ///< Absolute path to the file
    std::uintmax_t size_bytes{0};  ///< File size in bytes
};

/**
 * @struct ScannerConfig
 * @brief Configuration options for the project scanner.
 *
 * Defines the scanning behavior including root directory,
 * file extensions to include, and directories to exclude.
 *
 * @see Scanner
 */
struct ScannerConfig {
    /// Root directory to scan (will be resolved to absolute path)
    std::filesystem::path root;

    /// File extensions to include in scan results (e.g., ".cpp", ".hpp")
    std::unordered_set<std::string> extensions{
        ".c", ".h", ".cpp", ".hpp", ".cc", ".cxx", ".hxx"
    };

    /// Directory names to exclude from scanning
    std::unordered_set<std::string> excluded_dirs{
        ".git", ".svn", ".hg",
        "node_modules", "__pycache__", ".venv", "venv",
        "build", "cmake-build-debug", "cmake-build-release",
        ".idea", ".vscode"
    };

    /// Whether to follow symbolic links during traversal
    bool follow_symlinks{false};
};

/**
 * @class Scanner
 * @brief Scans a project directory for source files.
 *
 * The Scanner class provides recursive directory traversal to discover
 * source files matching configured extensions while respecting exclusion rules.
 *
 * @par Example Usage
 * @code
 * aegis::ScannerConfig config;
 * config.root = "/path/to/project";
 * config.extensions = {".cpp", ".hpp"};
 *
 * aegis::Scanner scanner(std::move(config));
 * auto files = scanner.scan();
 *
 * for (const auto& file : files) {
 *     std::cout << file.path << " (" << file.size_bytes << " bytes)\n";
 * }
 * @endcode
 *
 * @note This class is non-copyable but movable.
 * @see ScannerConfig, FileInfo
 */
class Scanner {
public:
    /**
     * @brief Construct a scanner with the given configuration.
     * @param config Scanner configuration specifying root, extensions, and exclusions.
     */
    explicit Scanner(ScannerConfig config);

    /**
     * @brief Default destructor.
     */
    ~Scanner() = default;

    /// @name Deleted copy operations
    /// @{
    Scanner(const Scanner&) = delete;
    Scanner& operator=(const Scanner&) = delete;
    /// @}

    /// @name Default move operations
    /// @{
    Scanner(Scanner&&) noexcept = default;
    Scanner& operator=(Scanner&&) noexcept = default;
    /// @}

    /**
     * @brief Scan the project and return all matching files.
     *
     * Recursively traverses the configured root directory, collecting
     * files that match the configured extensions while skipping
     * excluded directories.
     *
     * @return Vector of FileInfo objects sorted by path.
     * @throws std::filesystem::filesystem_error If root directory is inaccessible.
     */
    [[nodiscard]] std::vector<FileInfo> scan() const;

    /**
     * @brief Get the scanner configuration.
     * @return Const reference to the current configuration.
     */
    [[nodiscard]] const ScannerConfig& config() const noexcept;

private:
    ScannerConfig config_;  ///< Scanner configuration

    /**
     * @brief Check if a path should be excluded from scanning.
     * @param path Path to check.
     * @return true if the path should be excluded, false otherwise.
     */
    [[nodiscard]] bool should_exclude(const std::filesystem::path& path) const;

    /**
     * @brief Check if a file has a valid (included) extension.
     * @param path Path to the file.
     * @return true if the file's extension is in the configured set.
     */
    [[nodiscard]] bool has_valid_extension(const std::filesystem::path& path) const;
};

}  // namespace aegis
