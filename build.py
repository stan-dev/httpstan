from distutils.extension import Extension

from Cython.Build import cythonize

# empty extension module so build machinery recognizes package as platform-specific
extensions = [Extension("httpstan.empty", sources=["httpstan/empty.pyx"])]


def build(setup_kwargs):
    setup_kwargs.update({"ext_modules": cythonize(extensions)})
