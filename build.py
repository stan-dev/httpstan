from distutils.extension import Extension

# empty extension module so build machinery recognizes package as platform-specific
extensions = [
    Extension(
        "httpstan.empty",
        sources=["httpstan/empty.cpp"],
        # `make` will download and place `pybind11` in `httpstan/include`
        include_dirs=["httpstan/include"],
        language="c++",
        extra_compile_args=["-std=c++14"],
    )
]


def build(setup_kwargs):
    setup_kwargs.update({"ext_modules": extensions})
