#ifndef HTTPSTAN_UNIX_SOCKET_CLIENT_HPP
#define HTTPSTAN_UNIX_SOCKET_CLIENT_HPP

#include <cerrno>
#include <cstddef>
#include <cstring>
#include <stdexcept>
#include <string>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

namespace httpstan {

/**
 * <code>unix_socket_client</code> owns a blocking, connected Unix-domain
 * (<code>AF_UNIX</code> / <code>SOCK_STREAM</code>) stream socket.
 *
 * It is a small RAII replacement for the sliver of <code>boost::asio</code>
 * that httpstan used: connect to a filesystem path, write newline-terminated
 * messages, and close on destruction. Only Linux and macOS are supported.
 */
class unix_socket_client {
private:
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
