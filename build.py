from setuptools.extension import Extension

# empty extension module so build machinery recognizes package as platform-specific
extensions = [
    Extension(
        "httpstan.empty",
        sources=["httpstan/empty.cpp"],
        # `make` will download and place `pybind11` in `httpstan/include`
        include_dirs=["httpstan/include"],
        language="c++",
        # -fvisibility=hidden required by pybind11
        extra_compile_args=["-fvisibility=hidden", "-std=c++14"],
    )
]


def build(setup_kwargs):
    setup_kwargs.update({"ext_modules": extensions})
