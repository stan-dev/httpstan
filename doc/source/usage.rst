=====
Usage
=====

After installing ``httpstan``, running the module will begin listening on
localhost, port 8080::

    python3 -m httpstan

In a different terminal, make a POST request to
``http://localhost:8080/v1/models`` with Stan program code to compile the
program::

    curl -X POST -H "Content-Type: application/json" \
        -d '{"program_code":"parameters {real y;} model {y ~ normal(0,1);}"}' \
        http://localhost:8080/v1/models

This request will return a model name along with all the compiler output::

    {"name": "models/89c4e75a2c", "compiler_output": "..."}

(The model ``name`` depends on the platform and the version of Stan.)

To draw samples from this model using default settings, we first make the
following request::

    curl -X POST -H "Content-Type: application/json" \
        -d '{"function":"stan::services::sample::hmc_nuts_diag_e_adapt"}' \
        http://localhost:8080/v1/models/e1ca9f7ac7/fits

This request instructs ``httpstan`` to draw samples from the normal
distribution. The function name picks out a specific function in the Stan C++
library (see the Stan C++ documentation for details).  This request will return
immediately with a reference to the long-running fit operation::

    {"done": false, "name": "operations/9f9d701294", "metadata": {"fit": {"name": "models/e1ca9f7ac7/fits/9f9d701294"}}}

Once the operation is completed, the "fit" can be retrieved. The name of the fit,
``models/e1ca9f7ac7/fits/9f9d701294``, is included in the ``metadata`` field above.
The fit is saved as sequence of Protocol Buffer messages. These messages are strung together
using `length-prefix encoding
<https://eli.thegreenplace.net/2011/08/02/length-prefix-framing-for-protocol-buffers>`_.  To
retrieve these messages, saving them in the file ``myfit.bin``, make the following request::

    curl http://localhost:8080/v1/models/e1ca9f7ac7/fits/9f9d701294 > myfit.bin

To read the messages you will need a library for reading the encoding that
Protocol Buffer messages use.  In this example we will read the first message
in the stream using the Protocol Buffer compiler tool ``protoc``. (On
Debian-based Linux you can find this tool in the ``protobuf-compiler``
package.) The following command skips the message length (one byte)
and then decodes the message (which is 48 bytes in length)::

    dd bs=1 skip=1 if=myfit.bin 2>/dev/null | head -c 48 | \
      protoc --decode stan.WriterMessage protos/callbacks_writer.proto

Running the command above decodes the first message in the stream. The
decoded message should resemble the following::

    topic: LOGGER
    feature {
      string_list {
        value: "Gradient evaluation took 1.3e-05 seconds"
      }
    }
