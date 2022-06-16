# Makefile for httpstan
#
# This Makefile generates code and builds the libraries used by httpstan
#
# Code generation rules appear in this Makefile. One httpstan-specific library
# is built using rules defined in this Makefile. Other libraries used by all
# Stan interfaces are built using rules defined in `Makefile.libraries`.  This
# Makefile calls `make` to run `Makefile.libraries`. Note that some rules in
# this Makefile copy libraries built by the other Makefile into their
# httpstan-specific directories.

PYBIND11_VERSION := 2.9.2
RAPIDJSON_VERSION := 1.1.0
STAN_VERSION := 2.29.2
STANC_VERSION := 2.29.2
MATH_VERSION := 4.3.2
# NOTE: boost, eigen, sundials, and tbb versions must match those found in Stan Math
BOOST_VERSION := 1.75.0
EIGEN_VERSION := 3.3.9
SUNDIALS_VERSION := 6.0.0
TBB_VERSION := 2021.6
PYBIND11_ARCHIVE := build/archives/pybind11-$(PYBIND11_VERSION).tar.gz
RAPIDJSON_ARCHIVE := build/archives/rapidjson-$(RAPIDJSON_VERSION).tar.gz

STAN_ARCHIVE := build/archives/stan-v$(STAN_VERSION).tar.gz
MATH_ARCHIVE := build/archives/math-v$(MATH_VERSION).tar.gz
HTTP_ARCHIVES := $(STAN_ARCHIVE) $(MATH_ARCHIVE) $(PYBIND11_ARCHIVE) $(RAPIDJSON_ARCHIVE)
HTTP_ARCHIVES_EXPANDED := build/stan-$(STAN_VERSION) build/math-$(MATH_VERSION) build/pybind11-$(PYBIND11_VERSION) build/rapidjson-$(RAPIDJSON_VERSION)

SUNDIALS_LIBRARIES := httpstan/lib/libsundials_nvecserial.a httpstan/lib/libsundials_cvodes.a httpstan/lib/libsundials_idas.a httpstan/lib/libsundials_kinsol.a
TBB_LIBRARIES := httpstan/lib/libtbb.so
ifeq ($(shell uname -s),Darwin)
  TBB_LIBRARIES += httpstan/lib/libtbbmalloc.so httpstan/lib/libtbbmalloc_proxy.so
endif
STAN_LIBRARIES := $(SUNDIALS_LIBRARIES) $(TBB_LIBRARIES)
LIBRARIES := $(STAN_LIBRARIES)
INCLUDES_STAN_MATH_LIBS := httpstan/include/boost httpstan/include/Eigen httpstan/include/sundials httpstan/include/tbb
INCLUDES_STAN := httpstan/include/stan httpstan/include/stan/math $(INCLUDES_STAN_MATH_LIBS)
INCLUDES := httpstan/include/pybind11 httpstan/include/rapidjson $(INCLUDES_STAN)
STANC := httpstan/stanc
PRECOMPILED_OBJECTS = httpstan/stan_services.o

default: $(LIBRARIES) $(INCLUDES) $(STANC) $(PRECOMPILED_OBJECTS)


###############################################################################
# Download archives via HTTP and extract them
###############################################################################
build/archives:
	@mkdir -p build/archives

$(PYBIND11_ARCHIVE): | build/archives
	@echo downloading $@
	curl --silent --location https://github.com/pybind/pybind11/archive/v$(PYBIND11_VERSION).tar.gz -o $@

$(RAPIDJSON_ARCHIVE): | build/archives
	@echo downloading $@
	@curl --silent --location https://github.com/Tencent/rapidjson/archive/v$(RAPIDJSON_VERSION).tar.gz -o $@

$(STAN_ARCHIVE): | build/archives
	@echo downloading $@
	@curl --silent --location https://github.com/stan-dev/stan/archive/v$(STAN_VERSION).tar.gz -o $@

$(MATH_ARCHIVE): | build/archives
	@echo downloading $@
	@curl --silent --location https://github.com/stan-dev/math/archive/v$(MATH_VERSION).tar.gz -o $@

build/pybind11-$(PYBIND11_VERSION): $(PYBIND11_ARCHIVE)
build/rapidjson-$(RAPIDJSON_VERSION): $(RAPIDJSON_ARCHIVE)
build/stan-$(STAN_VERSION): $(STAN_ARCHIVE)
build/math-$(MATH_VERSION): $(MATH_ARCHIVE)

$(HTTP_ARCHIVES_EXPANDED):
	@echo extracting archive $<
	tar -C build -zxf $<
	touch $@

###############################################################################
# Download and install stanc
###############################################################################
ifeq ($(shell uname -s),Darwin)
build/stanc:
	curl --location https://github.com/stan-dev/stanc3/releases/download/v$(STANC_VERSION)/mac-stanc -o $@ --retry 5 --fail
else
build/stanc:
	curl --location https://github.com/stan-dev/stanc3/releases/download/v$(STANC_VERSION)/linux-stanc -o $@ --retry 5 --fail
endif

$(STANC): build/stanc
	rm -f $@ && cp -r $< $@ && chmod u+x $@

###############################################################################
# pybind11
###############################################################################
httpstan/include/pybind11: build/pybind11-$(PYBIND11_VERSION)/include/pybind11 | build/pybind11-$(PYBIND11_VERSION)
	@mkdir -p httpstan/include
	@rm -rf $@
	cp -r $< $@

build/pybind11-$(PYBIND11_VERSION)/include/pybind11: | build/pybind11-$(PYBIND11_VERSION)

###############################################################################
# rapidjson
###############################################################################
httpstan/include/rapidjson: build/rapidjson-$(RAPIDJSON_VERSION)/include/rapidjson | build/rapidjson-$(RAPIDJSON_VERSION)
	@mkdir -p httpstan/include
	@rm -rf $@
	cp -r $< $@

build/rapidjson-$(RAPIDJSON_VERSION)/include/rapidjson: | build/rapidjson-$(RAPIDJSON_VERSION)

###############################################################################
# Make local copies of C++ source code used by Stan
###############################################################################

httpstan/include/stan: | build/stan-$(STAN_VERSION)
	@mkdir -p httpstan/include
	@rm -rf $@
	cp -r build/stan-$(STAN_VERSION)/src/stan $@

httpstan/include/stan/math: | build/math-$(MATH_VERSION)
	@mkdir -p httpstan/include/stan
	@rm -rf $@ httpstan/include/stan/math.hpp httpstan/include/stan/math
	cp build/math-$(MATH_VERSION)/stan/math.hpp httpstan/include/stan
	cp -r build/math-$(MATH_VERSION)/stan/math httpstan/include/stan

httpstan/include/boost: | build/math-$(MATH_VERSION)
	@mkdir -p httpstan/include
	@rm -rf $@
	cp -r build/math-$(MATH_VERSION)/lib/boost_$(BOOST_VERSION)/boost $@

EIGEN_INCLUDES := Eigen unsupported
httpstan/include/Eigen: | build/math-$(MATH_VERSION)
	@mkdir -p httpstan/include
	@rm -rf $(addprefix httpstan/include/,$(EIGEN_INCLUDES))
	cp -r $(addprefix build/math-$(MATH_VERSION)/lib/eigen_$(EIGEN_VERSION)/,$(EIGEN_INCLUDES)) httpstan/include

SUNDIALS_INCLUDES := cvodes idas kinsol nvector sundials sunlinsol sunmatrix sunmemory sunnonlinsol stan_sundials_printf_override.hpp sundials_debug.h
httpstan/include/sundials: | build/math-$(MATH_VERSION)
	@mkdir -p httpstan/include
	@rm -rf $(addprefix httpstan/include/,$(SUNDIALS_INCLUDES))
	cp -r $(addprefix build/math-$(MATH_VERSION)/lib/sundials_$(SUNDIALS_VERSION)/include/,$(SUNDIALS_INCLUDES)) httpstan/include

httpstan/include/tbb: | build/math-$(MATH_VERSION)
	@mkdir -p httpstan/include
	@rm -rf tbb
	cp -r build/math-$(MATH_VERSION)/lib/tbb_$(TBB_VERSION)/include/tbb httpstan/include

###############################################################################
# Make local copies of shared libraries built by Stan Math's Makefile rules
###############################################################################

httpstan/lib/%: build/math-$(MATH_VERSION)/lib/sundials_$(SUNDIALS_VERSION)/lib/%
	mkdir -p httpstan/lib
	cp $< $@

# Stan Math builds a library with suffix .so.2 by default. Python prefers .so.
# Do not use symlinks since these will be ignored by Python wheel builders
# WISHLIST: Understand why Python needs both .so and .so.2.
ifeq ($(shell uname -s),Darwin)
httpstan/lib/libtbb.so: build/math-$(MATH_VERSION)/lib/tbb/libtbb.dylib
	cp $< httpstan/lib/$(notdir $<)
	@rm -f $@
	cd $(dir $@) && cp $(notdir $<) $(notdir $@)

httpstan/lib/libtbb%.so: build/math-$(MATH_VERSION)/lib/tbb/libtbb%.dylib
	cp $< httpstan/lib/$(notdir $<)
	@rm -f $@
	cd $(dir $@) && cp $(notdir $<) $(notdir $@)
else
httpstan/lib/libtbb.so: build/math-$(MATH_VERSION)/lib/tbb/libtbb.so.2
	cp $< httpstan/lib/$(notdir $<)
	@rm -f $@
	cd $(dir $@) && cp $(notdir $<) $(notdir $@)

httpstan/lib/libtbb%.so: build/math-$(MATH_VERSION)/lib/tbb/libtbb%.so.2
	cp $< httpstan/lib/$(notdir $<)
	@rm -f $@
	cd $(dir $@) && cp $(notdir $<) $(notdir $@)
endif

###############################################################################
# Build Stan-related shared libraries using Stan Math's Makefile rules
###############################################################################
# The file `Makefile.libraries` is a trimmed version of Stan Math's `makefile`,
# which uses the `include` directive to add rules from the `make/libraries`
# file (in Stan Math). `make/libraries` has all the rules required to build
# libsundials, libtbb, etc.
export MATH_VERSION

# locations where Stan Math's Makefile expects to output the shared libraries
SUNDIALS_LIBRARIES_BUILD_LOCATIONS := $(addprefix build/math-$(MATH_VERSION)/lib/sundials_$(SUNDIALS_VERSION)/lib/,$(notdir $(SUNDIALS_LIBRARIES)))
ifeq ($(shell uname -s),Darwin)
  TBB_LIBRARIES_BUILD_LOCATIONS := build/math-$(MATH_VERSION)/lib/tbb/libtbb.dylib build/math-$(MATH_VERSION)/lib/tbb/libtbbmalloc.dylib build/math-$(MATH_VERSION)/lib/tbb/libtbbmalloc_proxy.dylib
else
  TBB_LIBRARIES_BUILD_LOCATIONS := build/math-$(MATH_VERSION)/lib/tbb/libtbb.so.2 build/math-$(MATH_VERSION)/lib/tbb/libtbbmalloc.so.2 build/math-$(MATH_VERSION)/lib/tbb/libtbbmalloc_proxy.so.2
endif

$(TBB_LIBRARIES_BUILD_LOCATIONS) $(SUNDIALS_LIBRARIES_BUILD_LOCATIONS): | build/math-$(MATH_VERSION)
	$(MAKE) -f Makefile.libraries $@

# the following rule is required for parallel make
build/math-$(MATH_VERSION)/lib/tbb/libtbbmalloc_proxy.dylib: build/math-$(MATH_VERSION)/lib/tbb/libtbbmalloc.dylib

###############################################################################
# Precompile httpstan-related objects, eventually linked in httpstan/models.py
###############################################################################


PYTHON_CFLAGS ?= $(shell python3 -c 'import sysconfig;print(" ".join(sysconfig.get_config_vars("CFLAGS")))')
PYTHON_CCSHARED ?= $(shell python3 -c 'import sysconfig;print(" ".join(sysconfig.get_config_vars("CCSHARED")))')
PYTHON_INCLUDE ?= -I$(shell python3 -c'import sysconfig;print(sysconfig.get_path("include"))')
PYTHON_PLATINCLUDE ?= -I$(shell python3 -c'import sysconfig;print(sysconfig.get_path("platinclude"))')

# the following variables should match those in httpstan/models.py
# One include directory is absent: `model_directory_path` as this only
# exists when the extension module is ready to be linked
HTTPSTAN_EXTRA_COMPILE_ARGS ?= -O3 -std=c++14
HTTPSTAN_MACROS = -DBOOST_DISABLE_ASSERTS -DBOOST_PHOENIX_NO_VARIADIC_EXPRESSION -DSTAN_THREADS -D_REENTRANT -D_GLIBCXX_USE_CXX11_ABI=0 -DTBB_INTERFACE_NEW
HTTPSTAN_INCLUDE_DIRS = -Ihttpstan -Ihttpstan/include

httpstan/stan_services.o: httpstan/stan_services.cpp httpstan/socket_logger.hpp httpstan/socket_writer.hpp | $(INCLUDES)

httpstan/stan_services.o:
	# -fvisibility=hidden required by pybind11
	$(CXX) \
		$(PYTHON_CFLAGS) \
		$(PYTHON_CCSHARED) \
		$(HTTPSTAN_MACROS) \
		$(HTTPSTAN_INCLUDE_DIRS) \
		$(PYTHON_INCLUDE) \
		$(PYTHON_PLATINCLUDE) \
		-fvisibility=hidden \
		-c $< -o $@ \
		$(HTTPSTAN_EXTRA_COMPILE_ARGS)
