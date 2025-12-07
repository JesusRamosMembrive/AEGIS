/**
 * @file json_protocol.hpp
 * @brief JSON-based IPC protocol definitions and serialization.
 * @author AEGIS Team
 * @date 2024
 *
 * This module defines the JSON protocol used for communication
 * between the C++ analysis motor and the Python AEGIS backend.
 * It provides request parsing and response serialization functions.
 *
 * @par Protocol Format
 * All messages are JSON objects with the following structure:
 *
 * Request:
 * @code{.json}
 * {
 *     "id": "unique-request-id",
 *     "method": "analyze|file_tree|shutdown",
 *     "params": { ... }
 * }
 * @endcode
 *
 * Response (success):
 * @code{.json}
 * {
 *     "id": "matching-request-id",
 *     "result": { ... }
 * }
 * @endcode
 *
 * Response (error):
 * @code{.json}
 * {
 *     "id": "matching-request-id",
 *     "error": { "message": "error description" }
 * }
 * @endcode
 */

#pragma once

#include "../metrics.hpp"

#include <nlohmann/json.hpp>
#include <optional>
#include <string>
#include <variant>
#include <vector>

namespace aegis::ipc {

/**
 * @struct AnalyzeRequest
 * @brief Request to analyze a project for metrics.
 *
 * Triggers full analysis including file scanning, LOC counting,
 * function detection, and complexity calculation.
 */
struct AnalyzeRequest {
    std::string id;  ///< Unique request identifier for correlation
    std::string root;  ///< Root directory path to analyze
    std::vector<std::string> extensions;  ///< File extensions to include (optional)
};

/**
 * @struct FileTreeRequest
 * @brief Request to get the file tree without full analysis.
 *
 * Returns a list of source files matching the criteria
 * without performing metric calculations.
 */
struct FileTreeRequest {
    std::string id;  ///< Unique request identifier for correlation
    std::string root;  ///< Root directory path to scan
    std::vector<std::string> extensions;  ///< File extensions to include (optional)
};

/**
 * @struct ShutdownRequest
 * @brief Request to gracefully shut down the server.
 */
struct ShutdownRequest {
    std::string id;  ///< Unique request identifier for correlation
};

/**
 * @brief Union type representing all possible request types.
 *
 * Use std::visit or std::get to handle specific request types.
 */
using Request = std::variant<AnalyzeRequest, FileTreeRequest, ShutdownRequest>;

/**
 * @brief Parse a JSON request string into a Request object.
 *
 * Validates the JSON structure and extracts the appropriate
 * request type based on the "method" field.
 *
 * @param json_str The JSON string to parse.
 * @return Parsed Request variant, or std::nullopt if invalid.
 *
 * @par Supported Methods
 * - "analyze": Returns AnalyzeRequest
 * - "file_tree": Returns FileTreeRequest
 * - "shutdown": Returns ShutdownRequest
 *
 * @par Example
 * @code
 * auto request = aegis::ipc::parse_request(R"({"id":"1","method":"analyze","params":{"root":"/"}})");
 * if (request) {
 *     std::visit([](auto&& req) { ... }, *request);
 * }
 * @endcode
 */
[[nodiscard]] std::optional<Request> parse_request(const std::string& json_str);

/**
 * @brief Serialize project metrics to a JSON response.
 *
 * Creates a success response containing full project analysis results.
 *
 * @param id Request ID for correlation (should match request).
 * @param metrics The project metrics to serialize.
 * @return JSON response string.
 *
 * @see ProjectMetrics, FileMetrics, FunctionMetrics
 */
[[nodiscard]] std::string serialize_response(
    const std::string& id,
    const ProjectMetrics& metrics);

/**
 * @brief Serialize file tree to a JSON response.
 *
 * Creates a success response containing the list of discovered files.
 *
 * @param id Request ID for correlation.
 * @param files Vector of file paths to include.
 * @return JSON response string.
 */
[[nodiscard]] std::string serialize_file_tree(
    const std::string& id,
    const std::vector<std::filesystem::path>& files);

/**
 * @brief Serialize an error response.
 *
 * Creates an error response with the given message.
 *
 * @param id Request ID for correlation (empty string if unknown).
 * @param error_message Human-readable error description.
 * @return JSON error response string.
 */
[[nodiscard]] std::string serialize_error(
    const std::string& id,
    const std::string& error_message);

/**
 * @name JSON Serialization Functions
 * @brief nlohmann/json serialization support for metrics types.
 *
 * These functions enable automatic serialization of metrics
 * structures using nlohmann/json's ADL-based conversion.
 * @{
 */

/**
 * @brief Serialize FunctionMetrics to JSON.
 * @param[out] j JSON object to populate.
 * @param[in] m Function metrics to serialize.
 */
void to_json(nlohmann::json& j, const FunctionMetrics& m);

/**
 * @brief Serialize FileMetrics to JSON.
 * @param[out] j JSON object to populate.
 * @param[in] m File metrics to serialize.
 */
void to_json(nlohmann::json& j, const FileMetrics& m);

/**
 * @brief Serialize ProjectMetrics to JSON.
 * @param[out] j JSON object to populate.
 * @param[in] m Project metrics to serialize.
 */
void to_json(nlohmann::json& j, const ProjectMetrics& m);

/** @} */  // end of JSON Serialization Functions group

}  // namespace aegis::ipc
