#ifndef HTTPSTAN_SOCKET_LOGGER_HPP
#define HTTPSTAN_SOCKET_LOGGER_HPP

#include "callbacks_writer.pb.h"
#include <boost/asio.hpp>
#include <google/protobuf/io/coded_stream.h>
#include <google/protobuf/io/zero_copy_stream_impl.h>
#include <iostream>
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
  boost::asio::io_service io_service;
  boost::asio::local::stream_protocol::socket socket;

  /**
   * Channel name with which to prefix strings sent to the socket.
   */
  std::string message_prefix_;

  /**
   * Send a protocol buffer message to a socket using length-prefix encoding.
   */
  size_t send_message(const stan::WriterMessage &message, boost::asio::local::stream_protocol::socket &socket) {
    boost::asio::streambuf stream_buffer;
    std::ostream output_stream(&stream_buffer);
    {
      ::google::protobuf::io::OstreamOutputStream raw_output_stream(&output_stream);
      ::google::protobuf::io::CodedOutputStream coded_output_stream(&raw_output_stream);
      coded_output_stream.WriteVarint32(message.ByteSizeLong());
      message.SerializeToCodedStream(&coded_output_stream);
      // IMPORTANT: In order to flush a CodedOutputStream it must be deleted.
    }
    return socket.send(stream_buffer.data());
  }

public:
  /**
   * Constructs a logger with an output socket
   * and an optional prefix for comments.
   *
   * @param[in, out] output socket
   * @param[in] message_prefix will be prefixed to each string which is sent to the socket. Default is "".
   */
  explicit socket_logger(const std::string &socket_filename, const std::string &message_prefix = "")
      : socket(io_service), message_prefix_(message_prefix) {
    boost::asio::local::stream_protocol::endpoint ep(socket_filename);
    socket.connect(ep);
  }

  /**
   * Destructor
   */
  ~socket_logger() { socket.close(); }

  /**
   * Logs a message with debug log level
   *
   * @param[in] message message
   */
  void debug(const std::string &message) {
    stan::WriterMessage writer_message;
    writer_message.set_topic(stan::WriterMessage_Topic_LOGGER);

    stan::WriterMessage_Feature *feature = writer_message.add_feature();
    stan::WriterMessage_StringList *string_list = new stan::WriterMessage_StringList;
    string_list->add_value(std::string("debug:") + message);
    feature->set_allocated_string_list(string_list);

    send_message(writer_message, socket);
  }

  /**
   * Logs a message with debug log level.
   *
   * @param[in] message message
   */
  void debug(const std::stringstream &message) {
    stan::WriterMessage writer_message;
    writer_message.set_topic(stan::WriterMessage_Topic_LOGGER);

    stan::WriterMessage_Feature *feature = writer_message.add_feature();
    stan::WriterMessage_StringList *string_list = new stan::WriterMessage_StringList;
    string_list->add_value(std::string("debug:") + message.str());
    feature->set_allocated_string_list(string_list);

    send_message(writer_message, socket);
  }

  void info(const std::string &message) {
    stan::WriterMessage writer_message;
    writer_message.set_topic(stan::WriterMessage_Topic_LOGGER);

    stan::WriterMessage_Feature *feature = writer_message.add_feature();
    stan::WriterMessage_StringList *string_list = new stan::WriterMessage_StringList;
    string_list->add_value(std::string("info:") + message);
    feature->set_allocated_string_list(string_list);

    send_message(writer_message, socket);
  }

  void info(const std::stringstream &message) {
    stan::WriterMessage writer_message;
    writer_message.set_topic(stan::WriterMessage_Topic_LOGGER);

    stan::WriterMessage_Feature *feature = writer_message.add_feature();
    stan::WriterMessage_StringList *string_list = new stan::WriterMessage_StringList;
    string_list->add_value(std::string("info:") + message.str());
    feature->set_allocated_string_list(string_list);

    send_message(writer_message, socket);
  }

  void warn(const std::string &message) {
    stan::WriterMessage writer_message;
    writer_message.set_topic(stan::WriterMessage_Topic_LOGGER);

    stan::WriterMessage_Feature *feature = writer_message.add_feature();
    stan::WriterMessage_StringList *string_list = new stan::WriterMessage_StringList;
    string_list->add_value(std::string("warn:") + message);
    feature->set_allocated_string_list(string_list);

    send_message(writer_message, socket);
  }

  void warn(const std::stringstream &message) {
    stan::WriterMessage writer_message;
    writer_message.set_topic(stan::WriterMessage_Topic_LOGGER);

    stan::WriterMessage_Feature *feature = writer_message.add_feature();
    stan::WriterMessage_StringList *string_list = new stan::WriterMessage_StringList;
    string_list->add_value(std::string("warn:") + message.str());
    feature->set_allocated_string_list(string_list);

    send_message(writer_message, socket);
  }

  void error(const std::string &message) {
    stan::WriterMessage writer_message;
    writer_message.set_topic(stan::WriterMessage_Topic_LOGGER);

    stan::WriterMessage_Feature *feature = writer_message.add_feature();
    stan::WriterMessage_StringList *string_list = new stan::WriterMessage_StringList;
    string_list->add_value(std::string("error:") + message);
    feature->set_allocated_string_list(string_list);

    send_message(writer_message, socket);
  }

  void error(const std::stringstream &message) {
    stan::WriterMessage writer_message;
    writer_message.set_topic(stan::WriterMessage_Topic_LOGGER);

    stan::WriterMessage_Feature *feature = writer_message.add_feature();
    stan::WriterMessage_StringList *string_list = new stan::WriterMessage_StringList;
    string_list->add_value(std::string("error:") + message.str());
    feature->set_allocated_string_list(string_list);

    send_message(writer_message, socket);
  }

  void fatal(const std::string &message) {
    stan::WriterMessage writer_message;
    writer_message.set_topic(stan::WriterMessage_Topic_LOGGER);

    stan::WriterMessage_Feature *feature = writer_message.add_feature();
    stan::WriterMessage_StringList *string_list = new stan::WriterMessage_StringList;
    string_list->add_value(std::string("fatal:") + message);
    feature->set_allocated_string_list(string_list);

    send_message(writer_message, socket);
  }

  void fatal(const std::stringstream &message) {
    stan::WriterMessage writer_message;
    writer_message.set_topic(stan::WriterMessage_Topic_LOGGER);

    stan::WriterMessage_Feature *feature = writer_message.add_feature();
    stan::WriterMessage_StringList *string_list = new stan::WriterMessage_StringList;
    string_list->add_value(std::string("fatal:") + message.str());
    feature->set_allocated_string_list(string_list);

    send_message(writer_message, socket);
  }
};

} // namespace callbacks
} // namespace stan
#endif // HTTPSTAN_SOCKET_LOGGER_HPP
