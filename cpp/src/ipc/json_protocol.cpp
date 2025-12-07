#include "json_protocol.hpp"

#include <nlohmann/json.hpp>

namespace aegis::ipc {

using json = nlohmann::json;

std::optional<Request> parse_request(const std::string& json_str)
{
    try {
        auto j = json::parse(json_str);

        if (!j.contains("id") || !j.contains("method")) {
            return std::nullopt;
        }

        std::string id = j["id"].get<std::string>();
        std::string method = j["method"].get<std::string>();

        if (method == "analyze") {
            AnalyzeRequest req;
            req.id = std::move(id);

            if (j.contains("params")) {
                auto& params = j["params"];
                if (params.contains("root")) {
                    req.root = params["root"].get<std::string>();
                }
                if (params.contains("extensions")) {
                    req.extensions = params["extensions"].get<std::vector<std::string>>();
                }
            }

            return req;
        }
        else if (method == "file_tree") {
            FileTreeRequest req;
            req.id = std::move(id);

            if (j.contains("params")) {
                auto& params = j["params"];
                if (params.contains("root")) {
                    req.root = params["root"].get<std::string>();
                }
                if (params.contains("extensions")) {
                    req.extensions = params["extensions"].get<std::vector<std::string>>();
                }
            }

            return req;
        }
        else if (method == "shutdown") {
            ShutdownRequest req;
            req.id = std::move(id);
            return req;
        }

        return std::nullopt;
    }
    catch (const json::exception&) {
        return std::nullopt;
    }
}

void to_json(json& j, const FunctionMetrics& m)
{
    j = json{
        {"name", m.name},
        {"qualified_name", m.qualified_name},
        {"line_start", m.line_start},
        {"line_end", m.line_end},
        {"length", m.length},
        {"cyclomatic_complexity", m.cyclomatic_complexity}
    };
}

void to_json(json& j, const FileMetrics& m)
{
    j = json{
        {"path", m.path.string()},
        {"total_lines", m.total_lines},
        {"code_lines", m.code_lines},
        {"blank_lines", m.blank_lines},
        {"comment_lines", m.comment_lines},
        {"functions", m.functions}
    };
}

void to_json(json& j, const ProjectMetrics& m)
{
    j = json{
        {"total_files", m.total_files},
        {"total_lines", m.total_lines},
        {"total_code_lines", m.total_code_lines},
        {"total_functions", m.total_functions},
        {"files", m.files}
    };
}

std::string serialize_response(const std::string& id, const ProjectMetrics& metrics)
{
    json response = {
        {"id", id},
        {"result", metrics}
    };
    return response.dump();
}

std::string serialize_file_tree(
    const std::string& id,
    const std::vector<std::filesystem::path>& files)
{
    std::vector<std::string> paths;
    paths.reserve(files.size());
    for (const auto& f : files) {
        paths.push_back(f.string());
    }

    json response = {
        {"id", id},
        {"result", {
            {"files", paths},
            {"total_files", files.size()}
        }}
    };
    return response.dump();
}

std::string serialize_error(const std::string& id, const std::string& error_message)
{
    json response = {
        {"id", id},
        {"error", {
            {"message", error_message}
        }}
    };
    return response.dump();
}

} // namespace aegis::ipc
