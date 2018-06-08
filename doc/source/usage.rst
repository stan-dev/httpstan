Usage
=====

After installing ``httpstan``, running the module will begin listening on
localhost, port 8080::

    python3 -m httpstan

If you have interacted with a `Web API`_ elsewhere on the Internet, you likely
want to stop here and read the `OpenAPI documentation for httpstan`_ for a full
description of the HTTP requests you can make to ``httpstan``. The remainder of
this page illustrates how to interact with the server using  ``curl``.

In practice, HTTP requests would be composed using a software package such as
requests_ (Python) or httr_ (R). ``curl`` is used here as it is installed by
default on a wide range of systems.

While ``python3 -m httpstan`` is running, making a POST request (likely in a different terminal) to
``http://localhost:8080/v1/models`` with Stan Program code will compile a model.

Begin by assigning the Stan program code to a variable ``PROGRAM_CODE``. The following variable
definition will work if you use the bash_ shell and may work in other settings.

::

    PROGRAM_CODE="
        data {
            int<lower=0> N;
            int<lower=0,upper=1> y[N];
        }
        parameters {
            real<lower=0,upper=1> theta;
        }
        model {
            theta ~ beta(1,1);
            for (n in 1:N)
            y[n] ~ bernoulli(theta);
        }
    "
    PROGRAM_CODE=$(echo -n $PROGRAM_CODE | tr -d "\n")

(The ``tr -d "\n"`` removes newlines from the string as required by ``curl``.)

With the program code available in an environment variable, make an HTTP request
to compile the model::

    curl -X POST -H "Content-Type: application/json" -d "{\"program_code\":\"$PROGRAM_CODE\"}" http://localhost:8080/v1/models

which will return a model ``id`` such as ``150384037eefeb670b31c4bd91920c2c6bda6cfc05623d79867b9579a99575d9``.

Data is provided using JSON arrays. The form will be familiar if you have used any of the Stan
interfaces (CmdStan, PyStan, RStan).

::

    curl -X POST -H "Content-Type: application/json" \
        -d '{"type":"stan::services::sample::hmc_nuts_diag_e_adapt","data":{"N":10,"y":[0, 1, 0, 1, 0, 0, 0, 0, 0, 0]}}' \
        http://localhost:8080/v1/models/150384037eefeb670b31c4bd91920c2c6bda6cfc05623d79867b9579a99575d9/actions


.. _`Web API`: https://en.wikipedia.org/wiki/Web_API
.. _OpenAPI documentation for httpstan: api.html
.. _bash: https://en.wikipedia.org/wiki/Bash_%28Unix_shell%29
.. _requests: https://github.com/kennethreitz/requests
.. _httr: https://github.com/hadley/httr
