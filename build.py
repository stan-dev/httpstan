from distutils.extension import Extension

from Cython.Build import cythonize

# when updating library paths, remember to update them in httpstan/models.py
include_dirs = [
    "httpstan",
    "httpstan/include",
    "httpstan/include/lib/eigen_3.3.3",
    "httpstan/include/lib/boost_1.72.0",
    "httpstan/include/lib/sundials_4.1.0/include",
    "httpstan/include/lib/tbb_2019_U8",
]
extra_compile_args = ["-O3", "-std=c++14"]


extensions = [
    Extension(
        "httpstan.stan",
        sources=["httpstan/stan.pyx"],
        include_dirs=include_dirs,
        extra_compile_args=extra_compile_args,
    ),
    Extension(
        "httpstan.compile",
        sources=[
            "httpstan/compile.pyx",
            "httpstan/include/stan/lang/ast_def.cpp",
            "httpstan/include/stan/lang/grammars/bare_type_grammar_inst.cpp",
            "httpstan/include/stan/lang/grammars/block_var_decls_grammar_inst.cpp",
            "httpstan/include/stan/lang/grammars/expression07_grammar_inst.cpp",
            "httpstan/include/stan/lang/grammars/expression_grammar_inst.cpp",
            "httpstan/include/stan/lang/grammars/functions_grammar_inst.cpp",
            "httpstan/include/stan/lang/grammars/indexes_grammar_inst.cpp",
            "httpstan/include/stan/lang/grammars/local_var_decls_grammar_inst.cpp",
            "httpstan/include/stan/lang/grammars/program_grammar_inst.cpp",
            "httpstan/include/stan/lang/grammars/semantic_actions_def.cpp",
            "httpstan/include/stan/lang/grammars/statement_2_grammar_inst.cpp",
            "httpstan/include/stan/lang/grammars/statement_grammar_inst.cpp",
            "httpstan/include/stan/lang/grammars/term_grammar_inst.cpp",
            "httpstan/include/stan/lang/grammars/whitespace_grammar_inst.cpp",
        ],
        include_dirs=include_dirs,
        extra_compile_args=extra_compile_args,
        define_macros=[
            ("BOOST_DISABLE_ASSERTS", None),
            ("BOOST_PHOENIX_NO_VARIADIC_EXPRESSION", None),
        ],
    ),
]


def build(setup_kwargs):
    # TODO: raise exception if httpstan/include and httpstan/lib not found
    setup_kwargs.update({"ext_modules": cythonize(extensions)})
