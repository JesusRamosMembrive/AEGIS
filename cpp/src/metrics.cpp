#include "metrics.hpp"

#include <fstream>
#include <string>

namespace aegis {

namespace {

/// @brief Check if a line is blank (empty or only whitespace)
bool is_blank_line(const std::string& line)
{
    return line.find_first_not_of(" \t\r\n") == std::string::npos;
}

/// @brief Check if a line is a comment (simple heuristic)
/// @note This is a basic check; full parsing requires AST analysis
bool is_comment_line(const std::string& line)
{
    const auto first_char = line.find_first_not_of(" \t");
    if (first_char == std::string::npos) {
        return false;
    }

    // Single-line comments: // or #
    if (line[first_char] == '/' && first_char + 1 < line.size() &&
        line[first_char + 1] == '/')
    {
        return true;
    }

    // Python/Shell style comments
    if (line[first_char] == '#') {
        return true;
    }

    // Block comment start: /*
    if (line[first_char] == '/' && first_char + 1 < line.size() &&
        line[first_char + 1] == '*')
    {
        return true;
    }

    // Block comment continuation: starts with *
    if (line[first_char] == '*') {
        return true;
    }

    return false;
}

} // anonymous namespace

std::optional<FileMetrics> calculate_file_loc(const std::filesystem::path& path)
{
    std::ifstream file(path);
    if (!file.is_open()) {
        return std::nullopt;
    }

    FileMetrics metrics;
    metrics.path = path;

    std::string line;
    bool in_block_comment = false;

    while (std::getline(file, line)) {
        ++metrics.total_lines;

        if (is_blank_line(line)) {
            ++metrics.blank_lines;
            continue;
        }

        // Simple block comment tracking
        if (!in_block_comment) {
            const auto comment_start = line.find("/*");
            if (comment_start != std::string::npos) {
                const auto comment_end = line.find("*/", comment_start + 2);
                if (comment_end == std::string::npos) {
                    in_block_comment = true;
                }
                // Check if entire line is comment
                const auto first_char = line.find_first_not_of(" \t");
                if (first_char == comment_start) {
                    ++metrics.comment_lines;
                    continue;
                }
            }
        } else {
            // In block comment
            ++metrics.comment_lines;
            if (line.find("*/") != std::string::npos) {
                in_block_comment = false;
            }
            continue;
        }

        if (is_comment_line(line)) {
            ++metrics.comment_lines;
        } else {
            ++metrics.code_lines;
        }
    }

    return metrics;
}

ProjectMetrics calculate_project_loc(const std::vector<std::filesystem::path>& paths)
{
    ProjectMetrics project;
    project.total_files = static_cast<std::uint32_t>(paths.size());

    for (const auto& path : paths) {
        auto file_metrics = calculate_file_loc(path);
        if (file_metrics) {
            project.total_lines += file_metrics->total_lines;
            project.total_code_lines += file_metrics->code_lines;
            project.files.push_back(std::move(*file_metrics));
        }
    }

    return project;
}

} // namespace aegis
