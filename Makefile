PYTHON ?= python
PROTOBUF_FILES := httpstan/callbacks_writer_pb2.py httpstan/callbacks_writer.pb.cc
STUB_FILES := httpstan/callbacks_writer_pb2.pyi
LIBRARIES := httpstan/lib/libprotobuf-lite.so httpstan/lib/libsundials_nvecserial.a httpstan/lib/libsundials_cvodes.a httpstan/lib/libsundials_idas.a httpstan/lib/libsundials_kinsol.a
INCLUDES := httpstan/include/google/protobuf httpstan/include/stan httpstan/include/stan/math
INCLUDES_STAN_MATH_LIBS := httpstan/include/lib/boost_1.72.0 httpstan/include/lib/eigen_3.3.3 httpstan/include/lib/sundials_4.1.0 httpstan/include/lib/tbb_2019_U8
MATH ?= build/math-3.1.1/
TBB ?= $(MATH)lib/tbb_2019_U8

default: all

build/protobuf-3.11.3:
	@mkdir -p build
	curl --silent --location https://github.com/protocolbuffers/protobuf/releases/download/v3.11.3/protobuf-cpp-3.11.3.tar.gz | tar -C build -zxf -

httpstan/include/google/protobuf httpstan/lib/libprotobuf-lite.so httpstan/bin/protoc: build/protobuf-3.11.3
	@echo compiling with -D_GLIBCXX_USE_CXX11_ABI=0 for manylinux2014 wheel compatibility
	cd build/protobuf-3.11.3 && ./configure --prefix="$(shell pwd)/httpstan" CXXFLAGS="-D_GLIBCXX_USE_CXX11_ABI=0" && make -j 8 install

httpstan/%.pb.cc: protos/%.proto httpstan/bin/protoc
	LD_LIBRARY_PATH="httpstan/lib:${LD_LIBRARY_PATH}" httpstan/bin/protoc -Iprotos --cpp_out=httpstan $<

httpstan/%_pb2.py: protos/%.proto httpstan/bin/protoc
	LD_LIBRARY_PATH="httpstan/lib:${LD_LIBRARY_PATH}" httpstan/bin/protoc -Iprotos --python_out=httpstan $<

# requires protoc-gen-mypy:
httpstan/%_pb2.pyi: protos/%.proto httpstan/bin/protoc
	LD_LIBRARY_PATH="httpstan/lib:${LD_LIBRARY_PATH}" httpstan/bin/protoc -Iprotos --mypy_out=httpstan $<

build/stan-2.22.1:
	@mkdir -p build
	curl --silent --location https://github.com/stan-dev/stan/archive/v2.22.1.tar.gz	| tar -C build -zxf -

httpstan/include/stan: build/stan-2.22.1
	@mkdir -p httpstan/include
	cp -r build/stan-2.22.1/src/stan $@
	@echo delete all Python files in the include directory. These files are unused and they confuse the Python build tool.
	find httpstan/include/stan -iname '*.py' -delete

$(MATH):
	@mkdir -p build
	curl --silent --location https://github.com/stan-dev/math/archive/v3.1.1.tar.gz | tar -C build -zxf -

httpstan/include/stan/math: build/math-3.1.1 httpstan/include/stan/version.hpp
	cp -r build/math-3.1.1/stan/* httpstan/include/stan
	@echo delete all Python files in the include directory. These files are unused and they confuse the Python build tool.
	find httpstan/include/stan -iname '*.py' -delete

$(INCLUDES_STAN_MATH_LIBS): build/math-3.1.1
	@mkdir -p httpstan/include/lib
	cp -r build/math-3.1.1/lib/boost_1.72.0 httpstan/include/lib/boost_1.72.0
	cp -r build/math-3.1.1/lib/eigen_3.3.3 httpstan/include/lib/eigen_3.3.3
	cp -r build/math-3.1.1/lib/sundials_4.1.0 httpstan/include/lib/sundials_4.1.0
	cp -r build/math-3.1.1/lib/tbb_2019_U8/include httpstan/include/lib/tbb_2019_U8
	@echo delete all Python files in the include directory. These files are unused and they confuse the Python build tool.
	find httpstan/include/lib -iname '*.py' -delete

###############################################################################
# libsundials
###############################################################################

CXXFLAGS_SUNDIALS ?= -fPIC
SUNDIALS ?= $(MATH)lib/sundials_4.1.0
INC_SUNDIALS ?= -I $(SUNDIALS)/include

# DO NOT MANUALLY EDIT THE FOLLOWING SECTION. Makefile-writing is delegated to CmdStan
# The following section is identical to a section in `stan/lib/stan_math/make/libraries`
################################################################################
# SUNDIALS build rules
# Note: Files starting with f* are by SUNDIALS convention files needed for
#       Fortran bindings which we do not need for stan-math. Thus these targets
#       are ignored here. This convention was introduced with 4.0.
##

SUNDIALS_CVODES := $(patsubst %.c,%.o,\
  $(wildcard $(SUNDIALS)/src/cvodes/*.c) \
  $(wildcard $(SUNDIALS)/src/sundials/*.c) \
  $(wildcard $(SUNDIALS)/src/sunmatrix/band/[^f]*.c) \
  $(wildcard $(SUNDIALS)/src/sunmatrix/dense/[^f]*.c) \
  $(wildcard $(SUNDIALS)/src/sunlinsol/band/[^f]*.c) \
  $(wildcard $(SUNDIALS)/src/sunlinsol/dense/[^f]*.c) \
  $(wildcard $(SUNDIALS)/src/sunnonlinsol/newton/[^f]*.c) \
  $(wildcard $(SUNDIALS)/src/sunnonlinsol/fixedpoint/[^f]*.c))

SUNDIALS_IDAS := $(patsubst %.c,%.o,\
  $(wildcard $(SUNDIALS)/src/idas/*.c) \
  $(wildcard $(SUNDIALS)/src/sundials/*.c) \
  $(wildcard $(SUNDIALS)/src/sunmatrix/band/[^f]*.c) \
  $(wildcard $(SUNDIALS)/src/sunmatrix/dense/[^f]*.c) \
  $(wildcard $(SUNDIALS)/src/sunlinsol/band/[^f]*.c) \
  $(wildcard $(SUNDIALS)/src/sunlinsol/dense/[^f]*.c) \
  $(wildcard $(SUNDIALS)/src/sunnonlinsol/newton/[^f]*.c) \
  $(wildcard $(SUNDIALS)/src/sunnonlinsol/fixedpoint/[^f]*.c))

SUNDIALS_KINSOL := $(patsubst %.c,%.o, \
  $(wildcard $(SUNDIALS)/src/kinsol/*.c) \
  $(wildcard $(SUNDIALS)/src/sundials/*.c) \
  $(wildcard $(SUNDIALS)/src/sunmatrix/band/[^f]*.c) \
  $(wildcard $(SUNDIALS)/src/sunmatrix/dense/[^f]*.c) \
  $(wildcard $(SUNDIALS)/src/sunlinsol/band/[^f]*.c) \
  $(wildcard $(SUNDIALS)/src/sunlinsol/dense/[^f]*.c) \
  $(wildcard $(SUNDIALS)/src/sunnonlinsol/newton/[^f]*.c) \
  $(wildcard $(SUNDIALS)/src/sunnonlinsol/fixedpoint/[^f]*.c))

SUNDIALS_NVECSERIAL := $(patsubst %.c,%.o,\
  $(addprefix $(SUNDIALS)/src/, nvector/serial/nvector_serial.c sundials/sundials_math.c))

$(sort $(SUNDIALS_CVODES) $(SUNDIALS_IDAS) $(SUNDIALS_KINSOL) $(SUNDIALS_NVECSERIAL)) : CXXFLAGS = $(CXXFLAGS_SUNDIALS) $(CXXFLAGS_OS) -O$(O) $(INC_SUNDIALS)
$(sort $(SUNDIALS_CVODES) $(SUNDIALS_IDAS) $(SUNDIALS_KINSOL) $(SUNDIALS_NVECSERIAL)) : CPPFLAGS = $(CPPFLAGS_SUNDIALS) $(CPPFLAGS_OS)
$(sort $(SUNDIALS_CVODES) $(SUNDIALS_IDAS) $(SUNDIALS_KINSOL) $(SUNDIALS_NVECSERIAL)) : %.o : %.c
	@mkdir -p $(dir $@)
	$(COMPILE.cpp) -x c -include $(SUNDIALS)/include/stan_sundials_printf_override.hpp $< $(OUTPUT_OPTION)

$(SUNDIALS)/lib/libsundials_cvodes.a: $(SUNDIALS_CVODES)
	@mkdir -p $(dir $@)
	$(AR) -rs $@ $^

$(SUNDIALS)/lib/libsundials_idas.a: $(SUNDIALS_IDAS)
	@mkdir -p $(dir $@)
	$(AR) -rs $@ $^

$(SUNDIALS)/lib/libsundials_kinsol.a: $(SUNDIALS_KINSOL)
	@mkdir -p $(dir $@)
	$(AR) -rs $@ $^

$(SUNDIALS)/lib/libsundials_nvecserial.a: $(SUNDIALS_NVECSERIAL)
	@mkdir -p $(dir $@)
	$(AR) -rs $@ $^

LIBSUNDIALS := $(SUNDIALS)/lib/libsundials_nvecserial.a $(SUNDIALS)/lib/libsundials_cvodes.a $(SUNDIALS)/lib/libsundials_idas.a $(SUNDIALS)/lib/libsundials_kinsol.a

STAN_SUNDIALS_HEADERS := $(shell find $(MATH)stan -name *cvodes*.hpp) $(shell find $(MATH)stan -name *idas*.hpp) $(shell find $(MATH)stan -name *kinsol*.hpp)
$(STAN_SUNDIALS_HEADERS) : $(LIBSUNDIALS)

clean-sundials:
	@echo '  cleaning sundials targets'
	$(RM) $(wildcard $(sort $(SUNDIALS_CVODES) $(SUNDIALS_IDAS) $(SUNDIALS_KINSOL) $(SUNDIALS_NVECSERIAL) $(LIBSUNDIALS)))


###############################################################################
# httpstan-specific libsundials rules
###############################################################################

# this rule is required for the math tarball to be extracted
$(SUNDIALS)/src/nvector/serial/nvector_serial.c: $(MATH)

$(subst $(SUNDIALS)/lib,httpstan/lib,$(LIBSUNDIALS)): $(LIBSUNDIALS)
	cp $^ httpstan/lib


# DO NOT MANUALLY EDIT THE FOLLOWING SECTION. Makefile-writing is delegated to CmdStan
# The following section is identical to a section in `stan/lib/stan_math/make/compiler_flags`
###############################################################################
# Intel TBB
###############################################################################

## Detect operating system
ifneq ($(OS),Windows_NT)
  OS := $(shell uname -s)
endif

## Set OS specific library filename extensions
ifeq ($(OS),Windows_NT)
  LIBRARY_SUFFIX ?= .dll
endif

ifeq ($(OS),Darwin)
  LIBRARY_SUFFIX ?= .dylib
endif

ifeq ($(OS),Linux)
  LIBRARY_SUFFIX ?= .so
endif

## Set default compiler
ifeq (default,$(origin CXX))
  ifeq ($(OS),Darwin)  ## Darwin is Mac OS X
    CXX := clang++
  endif
  ifeq ($(OS),Linux)
    CXX := g++
  endif
  ifeq ($(OS),Windows_NT)
    CXX := g++
  endif
endif

# Detect compiler type
# - CXX_TYPE: {gcc, clang, mingw32-gcc, other}
# - CXX_MAJOR: major version of CXX
# - CXX_MINOR: minor version of CXX
ifneq (,$(findstring clang,$(CXX)))
  CXX_TYPE ?= clang
endif
ifneq (,$(findstring mingw32-g,$(CXX)))
  CXX_TYPE ?= mingw32-gcc
endif
ifneq (,$(findstring gcc,$(CXX)))
  CXX_TYPE ?= gcc
endif
ifneq (,$(findstring g++,$(CXX)))
  CXX_TYPE ?= gcc
endif
CXX_TYPE ?= other
CXX_MAJOR := $(shell $(CXX) -dumpversion 2>&1 | cut -d'.' -f1)
CXX_MINOR := $(shell $(CXX) -dumpversion 2>&1 | cut -d'.' -f2)

################################################################################
# Set default compiler flags
#
# The options that have been commented are things that the user can set.
# They are commented because in make, undefined is different than empty;
# we can test for that everywhere, but it's a lot easier using the set if
# unassigned operator (`?=`) when it's not set.
##
O ?= 3

# DO NOT MANUALLY EDIT THE FOLLOWING SECTION. Makefile-writing is delegated to CmdStan
# The following section is identical to a section in `stan/lib/stan_math/make/compiler_flags`
################################################################################
# Setup Intel TBB
#
# Sets up TBB CXXFLAGS_TBB and LDFLAGS_TBB to compile and link to TBB
#
# The tbbmalloc and tbbmalloc_proxy libraries are optionally included
# as targets. By default these are included on MacOS only. This behavior
# can be altered by explicitly setting the TBB_LIBRARIES variable which
# should contain "tbb" or "tbb tbbmalloc tbbmalloc_proxy". Setting the
# TBB_LIBRARIES variable overrides the default.

TBB_BIN ?= $(MATH)lib/tbb
TBB_RELATIVE_PATH ?= ../$(notdir $(TBB))
TBB_BIN_ABSOLUTE_PATH = $(abspath $(TBB_BIN))
TBB_ABSOLUTE_PATH = $(abspath $(TBB))

ifeq ($(OS),Darwin)
  TBB_LIBRARIES ?= tbb tbbmalloc tbbmalloc_proxy
else
  TBB_LIBRARIES ?= tbb
endif

ifeq ($(OS),Windows_NT)
  TBB_TARGETS ?= $(addprefix $(TBB_BIN)/,$(addsuffix $(LIBRARY_SUFFIX),$(TBB_LIBRARIES)))
endif
ifeq ($(OS),Darwin)
  TBB_TARGETS ?= $(addprefix $(TBB_BIN)/lib,$(addsuffix $(LIBRARY_SUFFIX), $(TBB_LIBRARIES)))
endif
ifeq ($(OS),Linux)
  TBB_TARGETS ?= $(addprefix $(TBB_BIN)/lib,$(addsuffix $(LIBRARY_SUFFIX).2,$(TBB_LIBRARIES)))
endif


CXXFLAGS_TBB ?= -I $(TBB)/include
LDFLAGS_TBB ?= -Wl,-L,"$(TBB_BIN_ABSOLUTE_PATH)" -Wl,-rpath,"$(TBB_BIN_ABSOLUTE_PATH)"
LDLIBS_TBB ?=


# DO NOT MANUALLY EDIT THE FOLLOWING SECTION. Makefile-writing is delegated to CmdStan
# The following section is identical to a section in `stan/lib/stan_math/make/libraries`
############################################################
# TBB build rules
#
# TBB_CXX_TYPE can be icl, icc, gcc or clang; See tbb documentation for more info.
# For gcc and clang this is derived from stan makefile defaults automatically.
#
# TBB_CC is the C compiler to be used, which is by default derived here from the
# defined C++ compiler type. In case neither clang or gcc is used, then the CC
# variable is used if defined.
#
# Note that the tbb targets must not be build in parallel (so no concurrent
# build of tbb and tbbmalloc, for example). This is ensured here with proper 
# dependencies.
#
# On windows the mingw32-make (part of RTools, for example) is required to build
# the TBB as this make has proper POSIX extensions needed by the used downstream
# TBB makefiles.

ifeq ($(CXX_TYPE),mingw32-gcc)
  TBB_CXX_TYPE ?= gcc
endif
ifeq ($(CXX_TYPE),other)
  ifeq (,$(TBB_CXX_TYPE))
    $(error "Need to set TBB_CXX_TYPE for non-standard compiler other than gcc or clang.")
  endif
endif
TBB_CXX_TYPE ?= $(CXX_TYPE)

# Set c compiler used for the TBB
ifeq (clang,$(CXX_TYPE))
  TBB_CC ?= $(subst clang++,clang,$(CXX))
endif
ifeq (gcc,$(CXX_TYPE))
  TBB_CC ?= $(subst g++,gcc,$(CXX))
endif
TBB_CC ?= $(CC)

ifeq (,$(TBB_CC))
  $(error "Need to set TBB_CC to C compiler command for non-standard compiler other than gcc or clang.")
endif

$(TBB_BIN)/tbb-make-check:
	@if [[ $(OS) == Windows_NT ]]; then \
		if ! [[ $(MAKE) =~ mingw32 ]]; then \
			echo "ERROR: Please use mingw32-make on Windows to build the Intel TBB library."; \
			echo "This is packaged with RTools, for example."; \
			exit 1; \
		fi \
	fi
	@mkdir -p $(TBB_BIN)
	touch $(TBB_BIN)/tbb-make-check

$(TBB_BIN)/tbb.def: $(TBB_BIN)/tbb-make-check $(TBB_BIN)/tbbmalloc.def
	@mkdir -p $(TBB_BIN)
	touch $(TBB_BIN)/version_$(notdir $(TBB))
	tbb_root="$(TBB_RELATIVE_PATH)" CXX="$(CXX)" CC="$(TBB_CC)" LDFLAGS='$(LDFLAGS_TBB)' $(MAKE) -C "$(TBB_BIN)" -r -f "$(TBB_ABSOLUTE_PATH)/build/Makefile.tbb" compiler=$(TBB_CXX_TYPE) cfg=release stdver=c++1y

$(TBB_BIN)/tbbmalloc.def: $(TBB_BIN)/tbb-make-check
	@mkdir -p $(TBB_BIN)
	tbb_root="$(TBB_RELATIVE_PATH)" CXX="$(CXX)" CC="$(TBB_CC)" LDFLAGS='$(LDFLAGS_TBB)' $(MAKE) -C "$(TBB_BIN)" -r -f "$(TBB_ABSOLUTE_PATH)/build/Makefile.tbbmalloc" compiler=$(TBB_CXX_TYPE) cfg=release stdver=c++1y malloc

$(TBB_BIN)/libtbb.dylib: $(TBB_BIN)/tbb.def
$(TBB_BIN)/libtbbmalloc.dylib: $(TBB_BIN)/tbbmalloc.def
$(TBB_BIN)/libtbbmalloc_proxy.dylib: $(TBB_BIN)/tbbmalloc.def

$(TBB_BIN)/libtbb.so.2: $(TBB_BIN)/tbb.def
$(TBB_BIN)/libtbbmalloc.so.2: $(TBB_BIN)/tbbmalloc.def
$(TBB_BIN)/libtbbmalloc_proxy.so.2: $(TBB_BIN)/tbbmalloc.def

$(TBB_BIN)/tbb.dll: $(TBB_BIN)/tbb.def
$(TBB_BIN)/tbbmalloc.dll: $(TBB_BIN)/tbbmalloc.def
$(TBB_BIN)/tbbmalloc_proxy.dll: $(TBB_BIN)/tbbmalloc.def

clean-tbb:
	@echo '  cleaning Intel TBB targets'
	$(RM) -rf $(TBB_BIN)


###############################################################################
# httpstan-specific libtbb rules
###############################################################################

# The linker under Linux seems to want .so and .so.2, even if one references the other
TBB_TARGETS_EXTRA := $(TBB_TARGETS) $(subst so.2,so,$(TBB_TARGETS))
HTTPSTAN_TBB_TARGETS := $(subst $(TBB_BIN),httpstan/lib,$(TBB_TARGETS_EXTRA))
LIBRARIES += $(HTTPSTAN_TBB_TARGETS)

$(HTTPSTAN_TBB_TARGETS): $(TBB_TARGETS_EXTRA)
	cp $^ httpstan/lib


###############################################################################
# default build rule
###############################################################################
all: $(PROTOBUF_FILES) $(STUB_FILES) $(LIBRARIES) $(INCLUDES) $(INCLUDES_STAN_MATH_LIBS)
