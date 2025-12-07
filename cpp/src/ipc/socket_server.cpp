#include "socket_server.hpp"

#include <array>
#include <atomic>
#include <cstring>
#include <stdexcept>
#include <vector>

// Platform-specific includes
#ifdef _WIN32
    #ifndef WIN32_LEAN_AND_MEAN
        #define WIN32_LEAN_AND_MEAN
    #endif
    #include <winsock2.h>
    #include <afunix.h>
    #include <ws2tcpip.h>
    using socket_t = SOCKET;
    constexpr socket_t INVALID_SOCKET_VALUE = INVALID_SOCKET;
    #define CLOSE_SOCKET closesocket
#else
    #include <sys/socket.h>
    #include <sys/un.h>
    #include <unistd.h>
    #include <fcntl.h>
    using socket_t = int;
    constexpr socket_t INVALID_SOCKET_VALUE = -1;
    #define CLOSE_SOCKET close
#endif

namespace aegis::ipc {

struct SocketServer::Impl {
    std::string socket_path;
    socket_t server_socket{INVALID_SOCKET_VALUE};
    std::atomic<bool> running{false};
    MessageHandler handler;

#ifdef _WIN32
    bool wsa_initialized{false};
#endif

    explicit Impl(std::string path) : socket_path(std::move(path)) {}

    ~Impl()
    {
        cleanup();
    }

    void cleanup()
    {
        if (server_socket != INVALID_SOCKET_VALUE) {
            CLOSE_SOCKET(server_socket);
            server_socket = INVALID_SOCKET_VALUE;
        }

#ifdef _WIN32
        if (wsa_initialized) {
            WSACleanup();
            wsa_initialized = false;
        }
#else
        // Remove socket file
        if (!socket_path.empty()) {
            ::unlink(socket_path.c_str());
        }
#endif
    }

    bool initialize()
    {
#ifdef _WIN32
        WSADATA wsa_data;
        if (WSAStartup(MAKEWORD(2, 2), &wsa_data) != 0) {
            return false;
        }
        wsa_initialized = true;
#endif

        // Remove existing socket file
#ifndef _WIN32
        ::unlink(socket_path.c_str());
#endif

        // Create socket
        server_socket = ::socket(AF_UNIX, SOCK_STREAM, 0);
        if (server_socket == INVALID_SOCKET_VALUE) {
            return false;
        }

        // Bind to path
#ifdef _WIN32
        sockaddr_un addr{};
#else
        struct sockaddr_un addr{};
#endif
        addr.sun_family = AF_UNIX;

        if (socket_path.size() >= sizeof(addr.sun_path)) {
            return false;
        }
        std::strncpy(addr.sun_path, socket_path.c_str(), sizeof(addr.sun_path) - 1);

        if (::bind(server_socket, reinterpret_cast<struct sockaddr*>(&addr),
                   sizeof(addr)) < 0)
        {
            return false;
        }

        // Listen
        if (::listen(server_socket, 5) < 0) {
            return false;
        }

        return true;
    }

    void handle_client(socket_t client_socket)
    {
        constexpr size_t BUFFER_SIZE = 65536;
        std::vector<char> buffer(BUFFER_SIZE);
        std::string accumulated;

        while (running.load()) {
#ifdef _WIN32
            int bytes_read = ::recv(client_socket, buffer.data(),
                                    static_cast<int>(buffer.size()), 0);
#else
            ssize_t bytes_read = ::recv(client_socket, buffer.data(),
                                        buffer.size(), 0);
#endif
            if (bytes_read <= 0) {
                break;  // Connection closed or error
            }

            accumulated.append(buffer.data(), static_cast<size_t>(bytes_read));

            // Look for complete message (newline-delimited)
            size_t pos;
            while ((pos = accumulated.find('\n')) != std::string::npos) {
                std::string message = accumulated.substr(0, pos);
                accumulated.erase(0, pos + 1);

                if (!message.empty() && handler) {
                    std::string response = handler(message);
                    response += '\n';

#ifdef _WIN32
                    ::send(client_socket, response.data(),
                           static_cast<int>(response.size()), 0);
#else
                    ::send(client_socket, response.data(), response.size(), 0);
#endif
                }
            }
        }

        CLOSE_SOCKET(client_socket);
    }
};

SocketServer::SocketServer(std::string socket_path)
    : impl_(std::make_unique<Impl>(std::move(socket_path)))
{
}

SocketServer::~SocketServer()
{
    stop();
}

SocketServer::SocketServer(SocketServer&&) noexcept = default;
SocketServer& SocketServer::operator=(SocketServer&&) noexcept = default;

void SocketServer::set_handler(MessageHandler handler)
{
    impl_->handler = std::move(handler);
}

void SocketServer::run()
{
    if (!impl_->initialize()) {
        throw std::runtime_error("Failed to initialize socket server");
    }

    impl_->running.store(true);

    while (impl_->running.load()) {
        // Accept connection
        socket_t client = ::accept(impl_->server_socket, nullptr, nullptr);
        if (client == INVALID_SOCKET_VALUE) {
            if (!impl_->running.load()) {
                break;  // Server was stopped
            }
            continue;  // Try again
        }

        // Handle client (single-threaded for simplicity)
        impl_->handle_client(client);
    }
}

void SocketServer::stop()
{
    impl_->running.store(false);
    impl_->cleanup();
}

bool SocketServer::is_running() const noexcept
{
    return impl_->running.load();
}

const std::string& SocketServer::socket_path() const noexcept
{
    return impl_->socket_path;
}

} // namespace aegis::ipc
