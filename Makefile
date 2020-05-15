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

PROTOBUF_VERSION := 3.11.3
STAN_VERSION := 2.23.0
MATH_VERSION := 3.2.0
BOOST_VERSION := 1.72.0
EIGEN_VERSION := 3.3.3
SUNDIALS_VERSION := 5.2.0
TBB_VERSION := 2019_U8

PROTOBUF_ARCHIVE := build/archives/protobuf-cpp-$(PROTOBUF_VERSION).tar.gz
STAN_ARCHIVE := build/archives/stan-v$(STAN_VERSION).tar.gz
MATH_ARCHIVE := build/archives/math-v$(MATH_VERSION).tar.gz
HTTP_ARCHIVES := $(PROTOBUF_ARCHIVE) $(STAN_ARCHIVE) $(MATH_ARCHIVE)
HTTP_ARCHIVES_EXPANDED := build/protobuf-$(PROTOBUF_VERSION) build/stan-$(STAN_VERSION) build/math-$(MATH_VERSION)

PROTOBUF_FILES := httpstan/callbacks_writer_pb2.py httpstan/callbacks_writer.pb.cc
STUB_FILES := httpstan/callbacks_writer_pb2.pyi
SUNDIALS_LIBRARIES := httpstan/lib/libsundials_nvecserial.a httpstan/lib/libsundials_cvodes.a httpstan/lib/libsundials_idas.a httpstan/lib/libsundials_kinsol.a
TBB_LIBRARIES := httpstan/lib/libtbb.so
ifeq ($(shell uname -s),Darwin)
  TBB_LIBRARIES += httpstan/lib/libtbbmalloc.so httpstan/lib/libtbbmalloc_proxy.so
endif
STAN_LIBRARIES := $(SUNDIALS_LIBRARIES) $(TBB_LIBRARIES)
LIBRARIES := httpstan/lib/libprotobuf-lite.so $(STAN_LIBRARIES)
INCLUDES_STAN_MATH_LIBS := httpstan/include/lib/boost_$(BOOST_VERSION) httpstan/include/lib/eigen_$(EIGEN_VERSION) httpstan/include/lib/sundials_$(SUNDIALS_VERSION) httpstan/include/lib/tbb_$(TBB_VERSION)
INCLUDES_STAN := httpstan/include/stan httpstan/include/stan/math $(INCLUDES_STAN_MATH_LIBS)
INCLUDES := httpstan/include/google/protobuf $(INCLUDES_STAN)


default: $(PROTOBUF_FILES) $(STUB_FILES) $(LIBRARIES) $(INCLUDES)


###############################################################################
# Download archives via HTTP and extract them
###############################################################################

$(PROTOBUF_ARCHIVE): build/archives
	@mkdir -p build/archives
	@echo downloading archive $@
	@curl --silent --location https://github.com/protocolbuffers/protobuf/releases/download/v$(PROTOBUF_VERSION)/protobuf-cpp-3.11.3.tar.gz -o $@

$(STAN_ARCHIVE): build/archives
	@mkdir -p build/archives
	@echo downloading archive $@
	@curl --silent --location https://github.com/stan-dev/stan/archive/v$(STAN_VERSION).tar.gz -o $@

$(MATH_ARCHIVE): build/archives
	@mkdir -p build/archives
	@echo downloading archive $@
	@curl --silent --location https://github.com/stan-dev/math/archive/v$(MATH_VERSION).tar.gz -o $@

build/protobuf-$(PROTOBUF_VERSION): $(PROTOBUF_ARCHIVE)
build/stan-$(STAN_VERSION): $(STAN_ARCHIVE)
build/math-$(MATH_VERSION): $(MATH_ARCHIVE)

$(HTTP_ARCHIVES_EXPANDED):
	@echo extracting archive $<
	tar -C build -zxf $<
	touch $@

###############################################################################
# Protocol Buffers library and generated files
###############################################################################

httpstan/include/google: build/protobuf-$(PROTOBUF_VERSION)/src/google build/protobuf-$(PROTOBUF_VERSION)
	@mkdir -p httpstan/include
	@rm -rf $@
	cp -r $< $@

httpstan/lib/libprotobuf-lite.so httpstan/bin/protoc: build/protobuf-$(PROTOBUF_VERSION)
	@echo compiling with -D_GLIBCXX_USE_CXX11_ABI=0 for manylinux2014 wheel compatibility
	cd build/protobuf-$(PROTOBUF_VERSION) && ./configure --prefix="$(shell pwd)/httpstan" CXXFLAGS="-D_GLIBCXX_USE_CXX11_ABI=0" && make -j 8 install

# This is a phony dependency to avoid problems with parallel make
httpstan/bin/protoc: httpstan/lib/libprotobuf-lite.so

httpstan/%.pb.cc: protos/%.proto httpstan/bin/protoc
	LD_LIBRARY_PATH="httpstan/lib:${LD_LIBRARY_PATH}" httpstan/bin/protoc -Iprotos --cpp_out=httpstan $<

httpstan/%_pb2.py: protos/%.proto httpstan/bin/protoc
	LD_LIBRARY_PATH="httpstan/lib:${LD_LIBRARY_PATH}" httpstan/bin/protoc -Iprotos --python_out=httpstan $<

# requires protoc-gen-mypy:
httpstan/%_pb2.pyi: protos/%.proto httpstan/bin/protoc
	LD_LIBRARY_PATH="httpstan/lib:${LD_LIBRARY_PATH}" httpstan/bin/protoc -Iprotos --mypy_out=httpstan $<

###############################################################################
# Make local copies of C++ source code used by Stan
###############################################################################

httpstan/include/stan: build/stan-$(STAN_VERSION)/src/stan build/stan-$(STAN_VERSION)
	@mkdir -p httpstan/include
	@rm -rf $@
	cp -r $< $@
	# delete all Python files in the include directory. These files are unused and they confuse the Python build tool.
	@find httpstan/include/stan -iname '*.py' -delete

build/stan-$(STAN_VERSION)/src/stan: build/stan-$(STAN_VERSION)

httpstan/include/stan/math: build/math-$(MATH_VERSION)/stan httpstan/include/stan
	@mkdir -p httpstan/include/stan
	@rm -rf $@
	cp -r $</math $</math.hpp httpstan/include/stan
	# delete all Python files in the include directory. These files are unused and they confuse the Python build tool.
	@find httpstan/include/stan -iname '*.py' -delete

httpstan/include/lib/boost_$(BOOST_VERSION): build/math-$(MATH_VERSION)/lib/boost_$(BOOST_VERSION)
httpstan/include/lib/eigen_$(EIGEN_VERSION): build/math-$(MATH_VERSION)/lib/eigen_$(EIGEN_VERSION)
httpstan/include/lib/sundials_$(SUNDIALS_VERSION): build/math-$(MATH_VERSION)/lib/sundials_$(SUNDIALS_VERSION)
httpstan/include/lib/tbb_$(TBB_VERSION): build/math-$(MATH_VERSION)/lib/tbb_$(TBB_VERSION)

$(INCLUDES_STAN_MATH_LIBS):
	@mkdir -p httpstan/include/lib
	cp -r build/math-$(MATH_VERSION)/lib/$(notdir $@) $@
	@echo delete all Python files in the include directory. These files are unused and they confuse the Python build tool.
	find $@ -iname '*.py' -delete

###############################################################################
# Make local copies of shared libraries built by Stan Math's Makefile rules
###############################################################################

httpstan/lib/%: build/math-$(MATH_VERSION)/lib/sundials_$(SUNDIALS_VERSION)/lib/%
	cp $< $@

# Stan Math builds a library with suffix .so.2 by default. Python prefers .so.
httpstan/lib/libtbb.so: build/math-$(MATH_VERSION)/lib/tbb/libtbb.so.2
	cp $< httpstan/lib/$(notdir $<)
	@rm -f $@
	cd $(dir $@) && ln -s $(notdir $<) $(notdir $@)

httpstan/lib/libtbb%.so: build/math-$(MATH_VERSION)/lib/tbb/libtbb%.so.2
	cp $< httpstan/lib/$(notdir $<)
	@rm -f $@
	cd $(dir $@) && ln -s $(notdir $<) $(notdir $@)

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
TBB_LIBRARIES_BUILD_LOCATIONS := $(addprefix build/math-$(MATH_VERSION)/lib/tbb/,$(notdir $(TBB_LIBRARIES)).2)

$(TBB_LIBRARIES_BUILD_LOCATIONS) $(SUNDIALS_LIBRARIES_BUILD_LOCATIONS): build/math-$(MATH_VERSION)
	$(MAKE) -f Makefile.libraries $@
