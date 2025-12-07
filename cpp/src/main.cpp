#include "analyzer.hpp"
#include "ipc/json_protocol.hpp"
#include "ipc/socket_server.hpp"
#include "scanner.hpp"

#include <filesystem>
#include <iostream>
#include <string>
#include <variant>

namespace {

constexpr const char* DEFAULT_SOCKET_PATH = "/tmp/aegis-cpp.sock";
constexpr const char* VERSION = "0.1.0";

void print_usage(const char* program_name)
{
    std::cout << "AEGIS Static Analysis Motor v" << VERSION << "\n\n"
              << "Usage:\n"
              << "  " << program_name << " [options]\n\n"
              << "Options:\n"
              << "  --socket <path>   Unix socket path (default: " << DEFAULT_SOCKET_PATH << ")\n"
              << "  --help            Show this help message\n"
              << "  --version         Show version\n";
}

std::string handle_request(const std::string& request_json, aegis::Analyzer& analyzer)
{
    auto request = aegis::ipc::parse_request(request_json);
    if (!request) {
        return aegis::ipc::serialize_error("", "Invalid request format");
    }

    return std::visit([&analyzer](auto&& req) -> std::string {
        using T = std::decay_t<decltype(req)>;

        if constexpr (std::is_same_v<T, aegis::ipc::AnalyzeRequest>) {
            // Configure scanner
            aegis::ScannerConfig scan_config;
            scan_config.root = req.root;

            if (!req.extensions.empty()) {
                scan_config.extensions.clear();
                for (const auto& ext : req.extensions) {
                    scan_config.extensions.insert(ext);
                }
            }

            // Scan for files
            aegis::Scanner scanner(std::move(scan_config));
            auto files = scanner.scan();

            // Extract paths
            std::vector<std::filesystem::path> paths;
            paths.reserve(files.size());
            for (const auto& f : files) {
                paths.push_back(f.path);
            }

            // Analyze
            auto metrics = analyzer.analyze_project(paths);

            return aegis::ipc::serialize_response(req.id, metrics);
        }
        else if constexpr (std::is_same_v<T, aegis::ipc::FileTreeRequest>) {
            aegis::ScannerConfig scan_config;
            scan_config.root = req.root;

            if (!req.extensions.empty()) {
                scan_config.extensions.clear();
                for (const auto& ext : req.extensions) {
                    scan_config.extensions.insert(ext);
                }
            }

            aegis::Scanner scanner(std::move(scan_config));
            auto files = scanner.scan();

            std::vector<std::filesystem::path> paths;
            paths.reserve(files.size());
            for (const auto& f : files) {
                paths.push_back(f.path);
            }

            return aegis::ipc::serialize_file_tree(req.id, paths);
        }
        else if constexpr (std::is_same_v<T, aegis::ipc::ShutdownRequest>) {
            // Return acknowledgment; server will stop after this
            return R"({"id":")" + req.id + R"(","result":{"status":"shutdown"}})";
        }
        else {
            return aegis::ipc::serialize_error("", "Unknown request type");
        }
    }, *request);
}

int run_server(const std::string& socket_path)
{
    std::cout << "Starting AEGIS Static Analysis Motor v" << VERSION << std::endl;
    std::cout << "Socket: " << socket_path << std::endl;
    std::cout << "libclang available: " << (aegis::Analyzer::is_available() ? "yes" : "no") << std::endl;

    aegis::AnalyzerConfig config;
    aegis::Analyzer analyzer(std::move(config));

    aegis::ipc::SocketServer server(socket_path);
    server.set_handler([&analyzer](const std::string& request) {
        return handle_request(request, analyzer);
    });

    std::cout << "Listening for connections..." << std::endl;
    server.run();

    return 0;
}

} // anonymous namespace

int main(int argc, char* argv[])
{
    std::string socket_path = DEFAULT_SOCKET_PATH;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];

        if (arg == "--help" || arg == "-h") {
            print_usage(argv[0]);
            return 0;
        }
        else if (arg == "--version" || arg == "-v") {
            std::cout << "AEGIS Static Analysis Motor v" << VERSION << std::endl;
            return 0;
        }
        else if (arg == "--socket" && i + 1 < argc) {
            socket_path = argv[++i];
        }
        else {
            std::cerr << "Unknown option: " << arg << std::endl;
            print_usage(argv[0]);
            return 1;
        }
    }

    try {
        return run_server(socket_path);
    }
    catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }
}
