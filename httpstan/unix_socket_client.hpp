#ifndef HTTPSTAN_UNIX_SOCKET_CLIENT_HPP
#define HTTPSTAN_UNIX_SOCKET_CLIENT_HPP

#include <cerrno>
#include <cstddef>
#include <cstring>
#include <stdexcept>
#include <string>
#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#include <algorithm>
#include <climits>
#else
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
#endif

namespace httpstan {

/**
 * <code>unix_socket_client</code> owns a blocking, connected Unix-domain
 * (<code>AF_UNIX</code> / <code>SOCK_STREAM</code>) stream socket.
 *
 * It is a small RAII replacement for the sliver of <code>boost::asio</code>
 * that httpstan used: connect to a filesystem path, write newline-terminated
 * messages, and close on destruction. On Windows the endpoint is an
 * authenticated TCP loopback connection because CPython lacks AF_UNIX.
 */
class unix_socket_client {
private:
#ifdef _WIN32
  SOCKET fd_ = INVALID_SOCKET;

  struct winsock_session {
    winsock_session() {
      WSADATA data{};
      int error = WSAStartup(MAKEWORD(2, 2), &data);
      if (error != 0) {
        throw std::runtime_error("WSAStartup: " + std::to_string(error));
      }
    }
    ~winsock_session() { WSACleanup(); }
  };
  winsock_session session_;

  void close_socket() noexcept {
    if (fd_ != INVALID_SOCKET) {
      ::closesocket(fd_);
      fd_ = INVALID_SOCKET;
    }
  }

  void write_all(const char *data, std::size_t remaining) {
    while (remaining > 0) {
      int chunk = static_cast<int>((std::min)(remaining, static_cast<std::size_t>(INT_MAX)));
      int n = ::send(fd_, data, chunk, 0);
      if (n == SOCKET_ERROR) {
        int error = WSAGetLastError();
        if (error == WSAEINTR) continue;
        throw std::runtime_error("send: " + std::to_string(error));
      }
      if (n == 0) throw std::runtime_error("send: zero bytes written");
      data += n;
      remaining -= static_cast<std::size_t>(n);
    }
  }

public:
  explicit unix_socket_client(const std::string &endpoint) {
    // endpoint = tcp:<port>:<random secret>; never include the secret in errors.
    if (endpoint.rfind("tcp:", 0) != 0) throw std::runtime_error("invalid callback endpoint");
    std::size_t split = endpoint.find(':', 4);
    if (split == std::string::npos) throw std::runtime_error("invalid callback endpoint");
    int port = std::stoi(endpoint.substr(4, split - 4));
    std::string secret = endpoint.substr(split + 1);
    if (port <= 0 || port > 65535 || secret.size() != 64) {
      throw std::runtime_error("invalid callback endpoint");
    }
    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(static_cast<unsigned short>(port));
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    fd_ = ::socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (fd_ == INVALID_SOCKET) throw std::runtime_error("socket: " + std::to_string(WSAGetLastError()));
    try {
      if (::connect(fd_, reinterpret_cast<const sockaddr *>(&addr), sizeof(addr)) == SOCKET_ERROR) {
        throw std::runtime_error("connect: " + std::to_string(WSAGetLastError()));
      }
      send_line(secret.data(), secret.size());
    } catch (...) {
      close_socket();
      throw;
    }
  }

  ~unix_socket_client() { close_socket(); }
#else
  int fd_ = -1;

  /** Throw a std::runtime_error describing the current errno. */
  [[noreturn]] static void throw_errno(const std::string &what) {
    throw std::runtime_error(what + ": " + std::strerror(errno));
  }

#ifdef MSG_NOSIGNAL
  // Linux: suppress SIGPIPE per send() call (see SO_NOSIGPIPE for macOS).
  static constexpr int kSendFlags = MSG_NOSIGNAL;
#else
  static constexpr int kSendFlags = 0;
#endif

  /** Write all @p len bytes from @p data, blocking and tolerating partial writes. */
  void write_all(const char *data, std::size_t remaining) {
    while (remaining > 0) {
      ssize_t n = ::send(fd_, data, remaining, kSendFlags);
      if (n == -1) {
        if (errno == EINTR) {
          continue; // interrupted before sending anything; retry
        }
        throw_errno("send()");
      }
      data += n;
      remaining -= static_cast<std::size_t>(n);
    }
  }

public:
  /**
   * Connect to the Unix-domain socket at @p path.
   *
   * @param[in] path filesystem path of the listening socket
   * @throws std::runtime_error if the path is too long or the connection fails
   */
  explicit unix_socket_client(const std::string &path) {
    sockaddr_un addr{};
    addr.sun_family = AF_UNIX;
    // sun_path must hold the path plus a terminating NUL.
    if (path.size() >= sizeof(addr.sun_path)) {
      throw std::runtime_error("socket path too long: " + path);
    }
    std::memcpy(addr.sun_path, path.c_str(), path.size() + 1);

    fd_ = ::socket(AF_UNIX, SOCK_STREAM, 0);
    if (fd_ == -1) {
      throw_errno("socket()");
    }

#ifdef SO_NOSIGPIPE
    // macOS has no MSG_NOSIGNAL; ask the socket to report broken pipes as
    // EPIPE rather than raising SIGPIPE.
    int on = 1;
    ::setsockopt(fd_, SOL_SOCKET, SO_NOSIGPIPE, &on, sizeof(on));
#endif

    if (::connect(fd_, reinterpret_cast<const sockaddr *>(&addr), sizeof(addr)) == -1) {
      int saved_errno = errno;
      ::close(fd_);
      fd_ = -1;
      errno = saved_errno;
      throw_errno("connect(" + path + ")");
    }
  }

  ~unix_socket_client() {
    if (fd_ != -1) {
      ::close(fd_);
    }
  }

#endif

public:
  // Non-copyable and non-movable: the file descriptor is uniquely owned and the
  // client is only ever constructed in place.
  unix_socket_client(const unix_socket_client &) = delete;
  unix_socket_client &operator=(const unix_socket_client &) = delete;

  /**
   * Write @p len bytes from @p data followed by a single newline, blocking
   * until everything has been sent.
   *
   * @throws std::runtime_error on any write error
   */
  void send_line(const char *data, std::size_t len) {
    write_all(data, len);
    write_all("\n", 1);
  }
};

} // namespace httpstan

#endif // HTTPSTAN_UNIX_SOCKET_CLIENT_HPP
