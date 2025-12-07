/**
 * @file socket_server.hpp
 * @brief Unix Domain Socket server for IPC communication.
 * @author AEGIS Team
 * @date 2024
 *
 * This module provides a cross-platform Unix Domain Socket server
 * for inter-process communication between the C++ analysis motor
 * and the Python AEGIS backend.
 *
 * @note On Windows, requires Windows 10 version 1803 or later
 *       for Unix Domain Socket support.
 */

#pragma once

#include <functional>
#include <memory>
#include <string>

namespace aegis::ipc {

/**
 * @brief Callback type for handling incoming messages.
 *
 * The handler receives a JSON request string and must return
 * a JSON response string.
 *
 * @param request The incoming JSON request string.
 * @return The JSON response string to send back to the client.
 */
using MessageHandler = std::function<std::string(const std::string&)>;

/**
 * @class SocketServer
 * @brief Unix Domain Socket server for IPC.
 *
 * The SocketServer class implements a simple request-response protocol
 * over Unix Domain Sockets. Messages are newline-delimited JSON strings.
 *
 * @par Protocol
 * - Client connects to the socket
 * - Client sends JSON request terminated by newline
 * - Server processes request via MessageHandler
 * - Server sends JSON response terminated by newline
 * - Connection remains open for multiple requests
 *
 * @par Example Usage
 * @code
 * aegis::ipc::SocketServer server("/tmp/aegis.sock");
 *
 * server.set_handler([](const std::string& request) {
 *     // Parse request, process, return response
 *     return R"({"status": "ok"})";
 * });
 *
 * // This blocks until stop() is called
 * server.run();
 * @endcode
 *
 * @note This class is non-copyable but movable.
 * @note Uses the PIMPL idiom for platform abstraction.
 *
 * @see MessageHandler
 */
class SocketServer {
public:
    /**
     * @brief Construct a server bound to the given socket path.
     *
     * The socket file is created when run() is called and removed
     * when the server is destroyed or stopped.
     *
     * @param socket_path Filesystem path for the Unix domain socket.
     */
    explicit SocketServer(std::string socket_path);

    /**
     * @brief Destructor.
     *
     * Stops the server if running and removes the socket file.
     */
    ~SocketServer();

    /// @name Deleted copy operations
    /// @{
    SocketServer(const SocketServer&) = delete;
    SocketServer& operator=(const SocketServer&) = delete;
    /// @}

    /// @name Move operations
    /// @{
    SocketServer(SocketServer&&) noexcept;
    SocketServer& operator=(SocketServer&&) noexcept;
    /// @}

    /**
     * @brief Set the message handler callback.
     *
     * The handler is called for each complete message received.
     * Must be set before calling run().
     *
     * @param handler Function to handle incoming messages.
     */
    void set_handler(MessageHandler handler);

    /**
     * @brief Start the server and begin accepting connections.
     *
     * Creates the socket, binds to the configured path, and enters
     * the accept loop. This method blocks until stop() is called
     * from another thread or the handler returns a shutdown signal.
     *
     * @throws std::runtime_error If socket creation or binding fails.
     */
    void run();

    /**
     * @brief Stop the server.
     *
     * Signals the server to stop accepting connections and exit
     * the run() loop. Safe to call from any thread.
     */
    void stop();

    /**
     * @brief Check if the server is currently running.
     * @return true if the server is in the run() loop.
     */
    [[nodiscard]] bool is_running() const noexcept;

    /**
     * @brief Get the configured socket path.
     * @return Const reference to the socket path string.
     */
    [[nodiscard]] const std::string& socket_path() const noexcept;

private:
    /// @brief Private implementation (PIMPL idiom)
    struct Impl;

    /// @brief Pointer to implementation
    std::unique_ptr<Impl> impl_;
};

}  // namespace aegis::ipc
