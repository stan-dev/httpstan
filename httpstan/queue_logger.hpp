#ifndef HTTPSTAN_QUEUE_LOGGER_HPP
#define HTTPSTAN_QUEUE_LOGGER_HPP

#include <ostream>
#include <sstream>
#include <string>
#include <boost/lockfree/spsc_queue.hpp>
#include <stan/callbacks/logger.hpp>
#include "callbacks_writer.pb.h"

/**
 * NOTE: httpstan makes an unorthodox use of `message_prefix`!
 * 
 * See discussion in httpstan/queue_writer.hpp
 *
 */

namespace stan {
namespace callbacks {

/**
 * <code>queue_logger</code> is an implementation
 * of <code>logger</code> that writes to a queue.
 */
class queue_logger : public logger {
 private:
  /**
   * Output queue
   */

  boost::lockfree::spsc_queue<std::string> * output_;

  /**
   * Channel name with which to prefix strings added to the queue.
   */
  std::string message_prefix_;

 public:
  /**
   * Constructs a logger with an output queue
   * and an optional prefix for comments.
   *
   * @param[in, out] output queues to write
   * @param[in] message_prefix will be prefixed to each string which is added to the queue. Default is "".
   */
  explicit queue_logger(boost::lockfree::spsc_queue<std::string> * output, const std::string& message_prefix = ""):
    output_(output), message_prefix_(message_prefix) {}

  /**
   * Logs a message with debug log level
   *
   * @param[in] message message
   */
  void debug(const std::string& message) {
    stan::WriterMessage writer_message;
    writer_message.set_topic(stan::WriterMessage_Topic_LOGGER);

    stan::WriterMessage_Feature * feature = writer_message.add_feature();
    stan::WriterMessage_StringList * string_list = new stan::WriterMessage_StringList;
    string_list->add_value(std::string("debug:") + message);
    feature->set_allocated_string_list(string_list);

    std::string serialized;
    writer_message.SerializeToString(&serialized);
    output_->push(serialized);
  }

  /**
   * Logs a message with debug log level.
   *
   * @param[in] message message
   */
  void debug(const std::stringstream& message) {
    stan::WriterMessage writer_message;
    writer_message.set_topic(stan::WriterMessage_Topic_LOGGER);

    stan::WriterMessage_Feature * feature = writer_message.add_feature();
    stan::WriterMessage_StringList * string_list = new stan::WriterMessage_StringList;
    string_list->add_value(std::string("debug:") + message.str());
    feature->set_allocated_string_list(string_list);

    std::string serialized;
    writer_message.SerializeToString(&serialized);
    output_->push(serialized);
  }

  void info(const std::string& message) {
    stan::WriterMessage writer_message;
    writer_message.set_topic(stan::WriterMessage_Topic_LOGGER);

    stan::WriterMessage_Feature * feature = writer_message.add_feature();
    stan::WriterMessage_StringList * string_list = new stan::WriterMessage_StringList;
    string_list->add_value(std::string("info:") + message);
    feature->set_allocated_string_list(string_list);

    std::string serialized;
    writer_message.SerializeToString(&serialized);
    output_->push(serialized);
  }

  void info(const std::stringstream& message) {
    stan::WriterMessage writer_message;
    writer_message.set_topic(stan::WriterMessage_Topic_LOGGER);

    stan::WriterMessage_Feature * feature = writer_message.add_feature();
    stan::WriterMessage_StringList * string_list = new stan::WriterMessage_StringList;
    string_list->add_value(std::string("info:") + message.str());
    feature->set_allocated_string_list(string_list);

    std::string serialized;
    writer_message.SerializeToString(&serialized);
    output_->push(serialized);
  }

  void warn(const std::string& message) {
    stan::WriterMessage writer_message;
    writer_message.set_topic(stan::WriterMessage_Topic_LOGGER);

    stan::WriterMessage_Feature * feature = writer_message.add_feature();
    stan::WriterMessage_StringList * string_list = new stan::WriterMessage_StringList;
    string_list->add_value(std::string("warn:") + message);
    feature->set_allocated_string_list(string_list);

    std::string serialized;
    writer_message.SerializeToString(&serialized);
    output_->push(serialized);
  }

  void warn(const std::stringstream& message) {
    stan::WriterMessage writer_message;
    writer_message.set_topic(stan::WriterMessage_Topic_LOGGER);

    stan::WriterMessage_Feature * feature = writer_message.add_feature();
    stan::WriterMessage_StringList * string_list = new stan::WriterMessage_StringList;
    string_list->add_value(std::string("warn:") + message.str());
    feature->set_allocated_string_list(string_list);

    std::string serialized;
    writer_message.SerializeToString(&serialized);
    output_->push(serialized);
  }

  void error(const std::string& message) {
    stan::WriterMessage writer_message;
    writer_message.set_topic(stan::WriterMessage_Topic_LOGGER);

    stan::WriterMessage_Feature * feature = writer_message.add_feature();
    stan::WriterMessage_StringList * string_list = new stan::WriterMessage_StringList;
    string_list->add_value(std::string("error:") + message);
    feature->set_allocated_string_list(string_list);

    std::string serialized;
    writer_message.SerializeToString(&serialized);
    output_->push(serialized);
  }

  void error(const std::stringstream& message) {
    stan::WriterMessage writer_message;
    writer_message.set_topic(stan::WriterMessage_Topic_LOGGER);

    stan::WriterMessage_Feature * feature = writer_message.add_feature();
    stan::WriterMessage_StringList * string_list = new stan::WriterMessage_StringList;
    string_list->add_value(std::string("error:") + message.str());
    feature->set_allocated_string_list(string_list);

    std::string serialized;
    writer_message.SerializeToString(&serialized);
    output_->push(serialized);
  }

  void fatal(const std::string& message) {
    stan::WriterMessage writer_message;
    writer_message.set_topic(stan::WriterMessage_Topic_LOGGER);

    stan::WriterMessage_Feature * feature = writer_message.add_feature();
    stan::WriterMessage_StringList * string_list = new stan::WriterMessage_StringList;
    string_list->add_value(std::string("fatal:") + message);
    feature->set_allocated_string_list(string_list);

    std::string serialized;
    writer_message.SerializeToString(&serialized);
    output_->push(serialized);
  }

  void fatal(const std::stringstream& message) {
    stan::WriterMessage writer_message;
    writer_message.set_topic(stan::WriterMessage_Topic_LOGGER);

    stan::WriterMessage_Feature * feature = writer_message.add_feature();
    stan::WriterMessage_StringList * string_list = new stan::WriterMessage_StringList;
    string_list->add_value(std::string("fatal:") + message.str());
    feature->set_allocated_string_list(string_list);

    std::string serialized;
    writer_message.SerializeToString(&serialized);
    output_->push(serialized);
  }
};

}  // namespace callbacks
}  // namespace stan
#endif  // HTTPSTAN_QUEUE_LOGGER_HPP
