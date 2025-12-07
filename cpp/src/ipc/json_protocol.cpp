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

json function_to_json(const FunctionMetrics& m)
{
    json j = json::object();
    j["name"] = m.name;
    j["qualified_name"] = m.qualified_name;
    j["line_start"] = m.line_start;
    j["line_end"] = m.line_end;
    j["length"] = m.length;
    j["cyclomatic_complexity"] = m.cyclomatic_complexity;
    return j;
}

json file_to_json(const FileMetrics& m)
{
    json j = json::object();
    j["path"] = m.path.string();
    j["total_lines"] = m.total_lines;
    j["code_lines"] = m.code_lines;
    j["blank_lines"] = m.blank_lines;
    j["comment_lines"] = m.comment_lines;

    json functions = json::array();
    for (const auto& func : m.functions) {
        functions.push_back(function_to_json(func));
    }
    j["functions"] = functions;
    return j;
}

json project_to_json(const ProjectMetrics& m)
{
    json j = json::object();
    j["total_files"] = m.total_files;
    j["total_lines"] = m.total_lines;
    j["total_code_lines"] = m.total_code_lines;
    j["total_functions"] = m.total_functions;

    json files = json::array();
    for (const auto& file : m.files) {
        files.push_back(file_to_json(file));
    }
    j["files"] = files;
    return j;
}

void to_json(json& j, const FunctionMetrics& m)
{
    j = function_to_json(m);
}

void to_json(json& j, const FileMetrics& m)
{
    j = file_to_json(m);
}

void to_json(json& j, const ProjectMetrics& m)
{
    j = project_to_json(m);
}

std::string serialize_response(const std::string& id, const ProjectMetrics& metrics)
{
    json response = json::object();
    response["id"] = id;
    response["result"] = project_to_json(metrics);
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

    json result = json::object();
    result["files"] = paths;
    result["total_files"] = files.size();

    json response = json::object();
    response["id"] = id;
    response["result"] = result;
    return response.dump();
}

std::string serialize_error(const std::string& id, const std::string& error_message)
{
    json error = json::object();
    error["message"] = error_message;

    json response = json::object();
    response["id"] = id;
    response["error"] = error;
    return response.dump();
}

} // namespace aegis::ipc
