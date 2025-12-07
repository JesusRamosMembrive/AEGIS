#include "scanner.hpp"

#include <algorithm>

namespace aegis {

Scanner::Scanner(ScannerConfig config)
    : config_(std::move(config))
{
}

std::vector<FileInfo> Scanner::scan() const
{
    std::vector<FileInfo> files;

    if (!std::filesystem::exists(config_.root)) {
        return files;
    }

    auto options = std::filesystem::directory_options::skip_permission_denied;
    if (config_.follow_symlinks) {
        options |= std::filesystem::directory_options::follow_directory_symlink;
    }

    for (const auto& entry : std::filesystem::recursive_directory_iterator(
             config_.root, options))
    {
        // Skip directories themselves
        if (entry.is_directory()) {
            continue;
        }

        const auto& path = entry.path();

        // Check if any parent directory should be excluded
        if (should_exclude(path)) {
            continue;
        }

        // Check extension
        if (!has_valid_extension(path)) {
            continue;
        }

        FileInfo info;
        info.path = path;
        try {
            info.size_bytes = entry.file_size();
        } catch (const std::filesystem::filesystem_error&) {
            info.size_bytes = 0;
        }

        files.push_back(std::move(info));
    }

    // Sort by path for consistent ordering
    std::sort(files.begin(), files.end(),
        [](const FileInfo& a, const FileInfo& b) {
            return a.path < b.path;
        });

    return files;
}

const ScannerConfig& Scanner::config() const noexcept
{
    return config_;
}

bool Scanner::should_exclude(const std::filesystem::path& path) const
{
    for (const auto& part : path) {
        const auto name = part.string();
        // Skip hidden directories (except root)
        if (!name.empty() && name[0] == '.' && name != ".") {
            if (config_.excluded_dirs.count(name) > 0 ||
                (name.size() > 1 && name[0] == '.'))
            {
                return true;
            }
        }
        if (config_.excluded_dirs.count(name) > 0) {
            return true;
        }
    }
    return false;
}

bool Scanner::has_valid_extension(const std::filesystem::path& path) const
{
    const auto ext = path.extension().string();
    return config_.extensions.count(ext) > 0;
}

} // namespace aegis
