#include "analyzer.hpp"

// Conditional libclang include
#if __has_include(<clang-c/Index.h>)
    #include <clang-c/Index.h>
    #define HAS_LIBCLANG 1
#else
    #define HAS_LIBCLANG 0
#endif

#include <fstream>
#include <sstream>

namespace aegis {

#if HAS_LIBCLANG

struct Analyzer::Impl {
    CXIndex index{nullptr};
    AnalyzerConfig config;

    Impl(AnalyzerConfig cfg)
        : config(std::move(cfg))
    {
        index = clang_createIndex(0, 0);
    }

    ~Impl()
    {
        if (index) {
            clang_disposeIndex(index);
        }
    }

    // Non-copyable
    Impl(const Impl&) = delete;
    Impl& operator=(const Impl&) = delete;
};

Analyzer::Analyzer(AnalyzerConfig config)
    : impl_(std::make_unique<Impl>(std::move(config)))
{
}

Analyzer::~Analyzer() = default;

Analyzer::Analyzer(Analyzer&&) noexcept = default;
Analyzer& Analyzer::operator=(Analyzer&&) noexcept = default;

namespace {

/// @brief Count cyclomatic complexity by counting control flow statements
struct ComplexityVisitor {
    std::uint32_t complexity{1};  // Base complexity
    std::uint32_t line_start{0};
    std::uint32_t line_end{0};
    std::string function_name;
    std::vector<FunctionMetrics> functions;
    bool in_function{false};
};

CXChildVisitResult visit_cursor(CXCursor cursor, CXCursor parent, CXClientData data)
{
    auto* visitor = static_cast<ComplexityVisitor*>(data);
    CXCursorKind kind = clang_getCursorKind(cursor);

    // Track function definitions
    if (kind == CXCursor_FunctionDecl || kind == CXCursor_CXXMethod) {
        if (clang_isCursorDefinition(cursor)) {
            // Save previous function if any
            if (visitor->in_function && !visitor->function_name.empty()) {
                FunctionMetrics fm;
                fm.name = visitor->function_name;
                fm.qualified_name = visitor->function_name;
                fm.line_start = visitor->line_start;
                fm.line_end = visitor->line_end;
                fm.length = visitor->line_end - visitor->line_start + 1;
                fm.cyclomatic_complexity = visitor->complexity;
                visitor->functions.push_back(std::move(fm));
            }

            // Start new function
            visitor->in_function = true;
            visitor->complexity = 1;

            CXString name = clang_getCursorSpelling(cursor);
            visitor->function_name = clang_getCString(name);
            clang_disposeString(name);

            CXSourceRange range = clang_getCursorExtent(cursor);
            CXSourceLocation start = clang_getRangeStart(range);
            CXSourceLocation end = clang_getRangeEnd(range);

            unsigned start_line, end_line;
            clang_getSpellingLocation(start, nullptr, &start_line, nullptr, nullptr);
            clang_getSpellingLocation(end, nullptr, &end_line, nullptr, nullptr);

            visitor->line_start = start_line;
            visitor->line_end = end_line;
        }
    }

    // Count control flow for cyclomatic complexity
    if (visitor->in_function) {
        switch (kind) {
            case CXCursor_IfStmt:
            case CXCursor_ForStmt:
            case CXCursor_WhileStmt:
            case CXCursor_DoStmt:
            case CXCursor_CaseStmt:
            case CXCursor_ConditionalOperator:  // ternary
            case CXCursor_BinaryOperator:       // && and ||
                ++visitor->complexity;
                break;
            default:
                break;
        }

        // Check for && and || operators
        if (kind == CXCursor_BinaryOperator) {
            CXString spelling = clang_getCursorSpelling(cursor);
            std::string op = clang_getCString(spelling);
            clang_disposeString(spelling);
            if (op == "&&" || op == "||") {
                ++visitor->complexity;
            }
        }
    }

    return CXChildVisit_Recurse;
}

} // anonymous namespace

std::optional<FileMetrics> Analyzer::analyze_file(
    const std::filesystem::path& path) const
{
    if (!impl_ || !impl_->index) {
        return std::nullopt;
    }

    // Build command line arguments
    std::vector<const char*> args;
    args.push_back("-std=c++20");

    for (const auto& include : impl_->config.include_paths) {
        static std::vector<std::string> include_args;
        include_args.push_back("-I" + include);
        args.push_back(include_args.back().c_str());
    }

    for (const auto& flag : impl_->config.compiler_flags) {
        args.push_back(flag.c_str());
    }

    const std::string path_str = path.string();

    CXTranslationUnit tu = clang_parseTranslationUnit(
        impl_->index,
        path_str.c_str(),
        args.data(),
        static_cast<int>(args.size()),
        nullptr,
        0,
        CXTranslationUnit_SkipFunctionBodies
    );

    if (!tu) {
        // Fall back to basic LOC calculation
        return calculate_file_loc(path);
    }

    // First get basic LOC metrics
    auto metrics = calculate_file_loc(path);
    if (!metrics) {
        clang_disposeTranslationUnit(tu);
        return std::nullopt;
    }

    // Then analyze for functions and complexity
    ComplexityVisitor visitor;
    CXCursor root = clang_getTranslationUnitCursor(tu);
    clang_visitChildren(root, visit_cursor, &visitor);

    // Save last function if any
    if (visitor.in_function && !visitor.function_name.empty()) {
        FunctionMetrics fm;
        fm.name = visitor.function_name;
        fm.qualified_name = visitor.function_name;
        fm.line_start = visitor.line_start;
        fm.line_end = visitor.line_end;
        fm.length = visitor.line_end - visitor.line_start + 1;
        fm.cyclomatic_complexity = visitor.complexity;
        visitor.functions.push_back(std::move(fm));
    }

    metrics->functions = std::move(visitor.functions);
    metrics->path = path;

    // Update total functions count
    clang_disposeTranslationUnit(tu);

    return metrics;
}

ProjectMetrics Analyzer::analyze_project(
    const std::vector<std::filesystem::path>& paths) const
{
    ProjectMetrics project;
    project.total_files = static_cast<std::uint32_t>(paths.size());

    for (const auto& path : paths) {
        auto file_metrics = analyze_file(path);
        if (file_metrics) {
            project.total_lines += file_metrics->total_lines;
            project.total_code_lines += file_metrics->code_lines;
            project.total_functions += static_cast<std::uint32_t>(
                file_metrics->functions.size());
            project.files.push_back(std::move(*file_metrics));
        }
    }

    return project;
}

bool Analyzer::is_available() noexcept
{
    return true;
}

#else // !HAS_LIBCLANG

// Fallback implementation when libclang is not available
struct Analyzer::Impl {
    AnalyzerConfig config;

    explicit Impl(AnalyzerConfig cfg) : config(std::move(cfg)) {}
};

Analyzer::Analyzer(AnalyzerConfig config)
    : impl_(std::make_unique<Impl>(std::move(config)))
{
}

Analyzer::~Analyzer() = default;

Analyzer::Analyzer(Analyzer&&) noexcept = default;
Analyzer& Analyzer::operator=(Analyzer&&) noexcept = default;

std::optional<FileMetrics> Analyzer::analyze_file(
    const std::filesystem::path& path) const
{
    // Without libclang, just return LOC metrics
    return calculate_file_loc(path);
}

ProjectMetrics Analyzer::analyze_project(
    const std::vector<std::filesystem::path>& paths) const
{
    return calculate_project_loc(paths);
}

bool Analyzer::is_available() noexcept
{
    return false;
}

#endif // HAS_LIBCLANG

} // namespace aegis
