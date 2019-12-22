#ifndef STAN_CALLBACKS_QUEUE_WRITER_HPP
#define STAN_CALLBACKS_QUEUE_WRITER_HPP

#include <boost/lockfree/spsc_queue.hpp>
#include <google/protobuf/util/delimited_message_util.h>
#include <google/protobuf/wrappers.pb.h>
#include <stan/callbacks/writer.hpp>
#include <ostream>
#include <vector>
#include <string>


namespace stan {
  namespace callbacks {

    /**
     * <code>queue_writer</code> is an implementation
     * of <code>writer</code> that writes Protobuf-encoded values to a queue.
     */
    class queue_writer : public writer {
    public:
      /**
       * Constructs a writer with an output queue
       * and an optional prefix for comments.
       *
       * @param[in, out] output queues to write
       * @param[in] message_prefix will be prefixed to each string which is added to the queue. Default is "".
       */
      queue_writer(boost::lockfree::spsc_queue<std::string> * output, const std::string& message_prefix = ""):
        output_(output), message_prefix_(message_prefix) {}

      /**
       * Virtual destructor
       */
      virtual ~queue_writer() {}

      /**
       * Writes a sequence of names.
       *
       * NOTE: The use of `SerializeDelimitedToOstream` is required. You cannot
       * use `message.SerializeToOstream`. The reason for this becomes apparent
       * when you try to serialize a default value ("" for a `StringValue`, 0.0
       * for a `DoubleValue`). Serializing a default value yields an empty
       * string. In order to distinguish between, say, [3.0, 0.0, 9.0] and
       * [3.0, 9.0, 0.0] (in the case of a series of `DoubleValue`s) you need
       * to use length-prefixing (i.e., use `SerializeDelimitedToOstream`).
       *
       * @param[in] names Names in a std::vector
       */
      void operator()(const std::vector<std::string>& names) {
        if (names.empty()) return;

        std::vector<std::string>::const_iterator last = names.end();

        std::ostringstream ss;
        ss << message_prefix_;
        google::protobuf::StringValue s;
        for (std::vector<std::string>::const_iterator it = names.begin();
             it != last; ++it) {
          s.set_value(*it);
          google::protobuf::util::SerializeDelimitedToOstream(s, &ss);
        }
        output_->push(ss.str());
      }

      /**
       * Writes a set of values.
       *
       * NOTE: The use of `SerializeDelimitedToOstream` is required. You cannot
       * use `message.SerializeToOstream`. The reason for this becomes apparent
       * when you try to serialize a default value ("" for a `StringValue`, 0.0
       * for a `DoubleValue`). Serializing a default value yields an empty
       * string. In order to distinguish between, say, [3.0, 0.0, 9.0] and
       * [3.0, 9.0, 0.0] (in the case of a series of `DoubleValue`s) you need
       * to use length-prefixing (i.e., use `SerializeDelimitedToOstream`).
       *
       * @param[in] state Values in a std::vector
       */
      void operator()(const std::vector<double>& state) {
        if (state.empty()) return;

        std::vector<double>::const_iterator last = state.end();

        std::ostringstream ss;
        ss << message_prefix_;
        google::protobuf::DoubleValue v;
        for (std::vector<double>::const_iterator it = state.begin();
             it != last; ++it) {
          v.set_value(*it);
          google::protobuf::util::SerializeDelimitedToOstream(v, &ss);
        }
        output_->push(ss.str());
      }

      /**
       * Writes the message_prefix to the stream followed by a newline.
       */
      void operator()() {
        std::ostringstream ss;
        ss << message_prefix_ << std::endl;
        output_->push(ss.str());
      }

      /**
       * Writes the message_prefix then the message.
       *
       * @param[in] message A string
       */
      void operator()(const std::string& message) {
        if (message.size() == 0) return;
        google::protobuf::StringValue s;
        s.set_value(message);

        std::ostringstream ss;
        ss << message_prefix_;
        google::protobuf::util::SerializeDelimitedToOstream(s, &ss);
        output_->push(ss.str());
      }

    private:
      /**
       * Output queue
       */

      boost::lockfree::spsc_queue<std::string> * output_;

      /**
       * Channel name with which to prefix strings added to the queue.
       */
      std::string message_prefix_;
    };

  }
}
#endif
