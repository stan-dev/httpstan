#include <pybind11/pybind11.h>

void noop() { return; }

namespace py = pybind11;

PYBIND11_MODULE(empty, m) {
  m.doc() = R"pbdoc(
        Empty extension module.

        This module contains a single no-op function. It is compiled so that the wheel
        machinery recognizes the wheel as being a platform-specific wheel.
    )pbdoc";
  m.def("noop", &noop, "");
}
