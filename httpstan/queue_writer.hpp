#ifndef STAN_CALLBACKS_QUEUE_WRITER_HPP
#define STAN_CALLBACKS_QUEUE_WRITER_HPP

#include <boost/lockfree/spsc_queue.hpp>
#include <stan/callbacks/writer.hpp>
#include <ostream>
#include <vector>
#include <string>

namespace stan {
  namespace callbacks {

    /**
     * <code>queue_writer</code> is an implementation
     * of <code>writer</code> that writes to a queue.
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
       * Writes a set of names on a single line in csv format followed
       * by a newline.
       *
       * Note: the names are not escaped.
       *
       * @param[in] names Names in a std::vector
       */
      void operator()(const std::vector<std::string>& names) {
        if (names.empty()) return;

        std::vector<std::string>::const_iterator last = names.end();
        --last;

        std::stringstream ss;
        ss << message_prefix_;
        ss << "[";
        for (std::vector<std::string>::const_iterator it = names.begin();
             it != last; ++it)
          ss << "\"" << *it << "\",";
        ss << "\"" << names.back() << "\"]" << std::endl;
        output_->push(ss.str());
      }

      /**
       * Writes a set of values in csv format followed by a newline.
       *
       * Note: the precision of the output is determined by the settings
       *  of the stream on construction.
       *
       * @param[in] state Values in a std::vector
       */
      void operator()(const std::vector<double>& state) {
        write_vector(state);
      }

      /**
       * Writes the message_prefix to the stream followed by a newline.
       */
      void operator()() {
        std::stringstream ss;
        ss << message_prefix_ << std::endl;
        output_->push(ss.str());
      }

      /**
       * Writes the message_prefix then the message followed by a newline.
       *
       * @param[in] message A string
       */
      void operator()(const std::string& message) {
        std::stringstream ss;
        ss << message_prefix_ << message << std::endl;
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

      /**
       * Writes a set of values in csv format followed by a newline.
       *
       * Note: the precision of the output is determined by the settings
       *  of the stream on construction.
       *
       * @param[in] v Values in a std::vector
       */
      template <class T>
      void write_vector(const std::vector<T>& v) {
        if (v.empty()) return;

        typename std::vector<T>::const_iterator last = v.end();
        --last;

        std::stringstream ss;
        ss << message_prefix_;
        ss << "[";
        for (typename std::vector<T>::const_iterator it = v.begin();
             it != last; ++it)
          ss << *it << ",";
        ss << v.back() << "]" << std::endl;
        output_->push(ss.str());
      }
    };

  }
}
#endif
