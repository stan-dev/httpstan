#ifndef HTTPSTAN_SOCKET_LOGGER_HPP
#define HTTPSTAN_SOCKET_LOGGER_HPP

#include "unix_socket_client.hpp"
#include <cstddef>
#include <rapidjson/stringbuffer.h>
#include <rapidjson/writer.h>
#include <sstream>
#include <stan/callbacks/logger.hpp>
#include <string>

/**
 * NOTE: httpstan makes an unorthodox use of `message_prefix`!
 *
 * See discussion in httpstan/socket_writer.hpp
 *
 */

namespace stan {
namespace callbacks {

/**
 * <code>socket_logger</code> is an implementation
 * of <code>logger</code> that writes to a socket.
 */
class socket_logger : public logger {
private:
  /**
   * Output socket
   */
  httpstan::unix_socket_client socket_;

  /**
   * Channel name with which to prefix strings sent to the socket.
   */
  std::string message_prefix_;

  /**
   * Send a JSON message followed by a newline to the socket.
   */
  void send_message(const rapidjson::StringBuffer &buffer) {
    socket_.send_line(buffer.GetString(), buffer.GetSize());
  }

public:
  /**
   * Constructs a logger with an output socket
   * and an optional prefix for comments.
   *
   * @param[in] socket_filename path of the Unix-domain socket to connect to
   * @param[in] message_prefix will be prefixed to each string which is sent to the socket. Default is "".
   */
  explicit socket_logger(const std::string &socket_filename, const std::string &message_prefix = "")
      : socket_(socket_filename), message_prefix_(message_prefix) {}

  /**
   * Logs a message with debug log level
   *
   * @param[in] message message
   */
  void debug(const std::string &message) {
    rapidjson::StringBuffer buffer;
    rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);

    writer.StartObject();

    writer.String("version");
    writer.Int(1);
    writer.String("topic");
    writer.String("logger");

    writer.String("values");
    writer.StartArray();
    writer.String((std::string("debug:") + message).c_str());
    writer.EndArray();

    writer.EndObject();

    send_message(buffer);
  }

  /**
   * Logs a message with debug log level.
   *
   * @param[in] message message
   */
  void debug(const std::stringstream &message) {
    rapidjson::StringBuffer buffer;
    rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);

    writer.StartObject();

    writer.String("version");
    writer.Int(1);
    writer.String("topic");
    writer.String("logger");

    writer.String("values");
    writer.StartArray();
    writer.String((std::string("debug:") + message.str()).c_str());
    writer.EndArray();

    writer.EndObject();

    send_message(buffer);
  }

  void info(const std::string &message) {
    rapidjson::StringBuffer buffer;
    rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);

    writer.StartObject();

    writer.String("version");
    writer.Int(1);
    writer.String("topic");
    writer.String("logger");

    writer.String("values");
    writer.StartArray();
    writer.String((std::string("info:") + message).c_str());
    writer.EndArray();

    writer.EndObject();

    send_message(buffer);
  }

  void info(const std::stringstream &message) {
    rapidjson::StringBuffer buffer;
    rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);

    writer.StartObject();

    writer.String("version");
    writer.Int(1);
    writer.String("topic");
    writer.String("logger");

    writer.String("values");
    writer.StartArray();
    writer.String((std::string("info:") + message.str()).c_str());
    writer.EndArray();

    writer.EndObject();

    send_message(buffer);
  }

  void warn(const std::string &message) {
    rapidjson::StringBuffer buffer;
    rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);

    writer.StartObject();

    writer.String("version");
    writer.Int(1);
    writer.String("topic");
    writer.String("logger");

    writer.String("values");
    writer.StartArray();
    writer.String((std::string("warn:") + message).c_str());
    writer.EndArray();

    writer.EndObject();

    send_message(buffer);
  }

  void warn(const std::stringstream &message) {
    rapidjson::StringBuffer buffer;
    rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);

    writer.StartObject();

    writer.String("version");
    writer.Int(1);
    writer.String("topic");
    writer.String("logger");

    writer.String("values");
    writer.StartArray();
    writer.String((std::string("warn:") + message.str()).c_str());
    writer.EndArray();

    writer.EndObject();

    send_message(buffer);
  }

  void error(const std::string &message) {
    rapidjson::StringBuffer buffer;
    rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);

    writer.StartObject();

    writer.String("version");
    writer.Int(1);
    writer.String("topic");
    writer.String("logger");

    writer.String("values");
    writer.StartArray();
    writer.String((std::string("error:") + message).c_str());
    writer.EndArray();

    writer.EndObject();

    send_message(buffer);
  }

  void error(const std::stringstream &message) {
    rapidjson::StringBuffer buffer;
    rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);

    writer.StartObject();

    writer.String("version");
    writer.Int(1);
    writer.String("topic");
    writer.String("logger");

    writer.String("values");
    writer.StartArray();
    writer.String((std::string("error:") + message.str()).c_str());
    writer.EndArray();

    writer.EndObject();

    send_message(buffer);
  }

  void fatal(const std::string &message) {
    rapidjson::StringBuffer buffer;
    rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);

    writer.StartObject();

    writer.String("version");
    writer.Int(1);
    writer.String("topic");
    writer.String("logger");

    writer.String("values");
    writer.StartArray();
    writer.String((std::string("fatal:") + message).c_str());
    writer.EndArray();

    writer.EndObject();

    send_message(buffer);
  }

  void fatal(const std::stringstream &message) {
    rapidjson::StringBuffer buffer;
    rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);

    writer.StartObject();

    writer.String("version");
    writer.Int(1);
    writer.String("topic");
    writer.String("logger");

    writer.String("values");
    writer.StartArray();
    writer.String((std::string("fatal:") + message.str()).c_str());
    writer.EndArray();

    writer.EndObject();

    send_message(buffer);
  }
};

} // namespace callbacks
} // namespace stan
#endif // HTTPSTAN_SOCKET_LOGGER_HPP
