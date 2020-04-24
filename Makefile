PYTHON ?= python
PROTOBUF_FILES := httpstan/callbacks_writer_pb2.py httpstan/callbacks_writer.pb.cc
STUB_FILES := httpstan/callbacks_writer_pb2.pyi
LIBRARIES := httpstan/lib/libprotobuf-lite.so
INCLUDES := httpstan/include/google/protobuf httpstan/include/stan httpstan/include/stan/math
INCLUDES_STAN_MATH_LIBS := httpstan/include/lib/boost_1.69.0 httpstan/include/lib/eigen_3.3.3 httpstan/include/lib/sundials_4.1.0


default: $(PROTOBUF_FILES) $(STUB_FILES) $(LIBRARIES) $(INCLUDES) $(INCLUDES_STAN_MATH_LIBS)


build/protobuf-3.11.3:
	mkdir -p build
	curl --silent --location https://github.com/protocolbuffers/protobuf/releases/download/v3.11.3/protobuf-cpp-3.11.3.tar.gz | tar -C build -zxf -

httpstan/include/google/protobuf httpstan/lib/libprotobuf-lite.so httpstan/bin/protoc: build/protobuf-3.11.3
	@echo compiling with -D_GLIBCXX_USE_CXX11_ABI=0 for manylinux2014 wheel compatibility
	cd build/protobuf-3.11.3 && ./configure --prefix="$(shell pwd)/httpstan" CXXFLAGS="-D_GLIBCXX_USE_CXX11_ABI=0" && make -j 8 install
	@echo deleting unused files which are installed by make install

httpstan/%.pb.cc: protos/%.proto httpstan/bin/protoc
	LD_LIBRARY_PATH="httpstan/lib:${LD_LIBRARY_PATH}" httpstan/bin/protoc -Iprotos --cpp_out=httpstan $<

httpstan/%_pb2.py: protos/%.proto httpstan/bin/protoc
	LD_LIBRARY_PATH="httpstan/lib:${LD_LIBRARY_PATH}" httpstan/bin/protoc -Iprotos --python_out=httpstan $<

# requires protoc-gen-mypy:
httpstan/%_pb2.pyi: protos/%.proto httpstan/bin/protoc
	LD_LIBRARY_PATH="httpstan/lib:${LD_LIBRARY_PATH}" httpstan/bin/protoc -Iprotos --mypy_out=httpstan $<

build/stan-2.19.1:
	mkdir -p build
	curl --silent --location https://github.com/stan-dev/stan/archive/v2.19.1.tar.gz	| tar -C build -zxf -

httpstan/include/stan: build/stan-2.19.1
	mkdir -p httpstan/include
	cp -r build/stan-2.19.1/src/stan $@
	@echo delete all Python files in the include directory. These files are unused and they confuse the Python build tool.
	find httpstan/include/stan -iname '*.py' -delete

build/math-2.19.1:
	mkdir -p build
	curl --silent --location https://github.com/stan-dev/math/archive/v2.19.1.tar.gz | tar -C build -zxf -

httpstan/include/stan/math: build/math-2.19.1 httpstan/include/stan/version.hpp
	cp -r build/math-2.19.1/stan/* httpstan/include/stan
	@echo delete all Python files in the include directory. These files are unused and they confuse the Python build tool.
	find httpstan/include/stan -iname '*.py' -delete

httpstan/include/lib/boost_1.69.0 httpstan/include/lib/eigen_3.3.3 httpstan/include/lib/sundials_4.1.0: build/math-2.19.1
	mkdir -p httpstan/include/lib
	cp -r build/math-2.19.1/lib/boost_1.69.0 httpstan/include/lib/boost_1.69.0
	cp -r build/math-2.19.1/lib/eigen_3.3.3 httpstan/include/lib/eigen_3.3.3
	cp -r build/math-2.19.1/lib/sundials_4.1.0 httpstan/include/lib/sundials_4.1.0
	@echo delete all Python files in the include directory. These files are unused and they confuse the Python build tool.
	find httpstan/include/lib -iname '*.py' -delete
	@echo deleting unused boost and eigen files. This step can be removed when httpstan uses Stan 2.20 or higher.
	find httpstan/include/lib/boost_1.69.0/doc -delete
	find httpstan/include/lib/boost_1.69.0/libs -delete
	find httpstan/include/lib/boost_1.69.0/more -delete
	find httpstan/include/lib/boost_1.69.0/status -delete
	find httpstan/include/lib/boost_1.69.0/tools -delete
	find httpstan/include/lib/eigen_3.3.3/unsupported/doc -delete

###############################################################################
# libsundials
###############################################################################

CXXFLAGS_SUNDIALS ?= -fPIC
MATH ?= build/math-2.19.1/
SUNDIALS ?= $(MATH)lib/sundials_4.1.0
# INC_SUNDIALS is defined in `stan/lib/stan_math/make/compiler_flags`
INC_SUNDIALS ?= -I $(SUNDIALS)/include

# The following section is mostly the same as a section in `stan/lib/stan_math/make/libraries`

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

SUNDIALS_NVECSERIAL := $(patsubst %.c,%.o,\
  $(addprefix $(SUNDIALS)/src/, nvector/serial/nvector_serial.c sundials/sundials_math.c))

$(sort $(SUNDIALS_CVODES) $(SUNDIALS_IDAS) $(SUNDIALS_NVECSERIAL)) : CXXFLAGS = $(CXXFLAGS_SUNDIALS) $(CXXFLAGS_OS) -O$(O) $(INC_SUNDIALS)
$(sort $(SUNDIALS_CVODES) $(SUNDIALS_IDAS) $(SUNDIALS_NVECSERIAL)) : CPPFLAGS = $(CPPFLAGS_SUNDIALS) $(CPPFLAGS_OS)
$(sort $(SUNDIALS_CVODES) $(SUNDIALS_IDAS) $(SUNDIALS_NVECSERIAL)) : %.o : %.c
	@mkdir -p $(dir $@)
	$(COMPILE.cpp) -x c -include $(SUNDIALS)/include/stan_sundials_printf_override.hpp $< $(OUTPUT_OPTION)

$(SUNDIALS)/lib/libsundials_cvodes.a: $(SUNDIALS_CVODES)
	@mkdir -p $(dir $@)
	$(AR) -rs $@ $^

$(SUNDIALS)/lib/libsundials_idas.a: $(SUNDIALS_IDAS)
	@mkdir -p $(dir $@)
	$(AR) -rs $@ $^

$(SUNDIALS)/lib/libsundials_nvecserial.a: $(SUNDIALS_NVECSERIAL)
	@mkdir -p $(dir $@)
	$(AR) -rs $@ $^

LIBSUNDIALS := $(SUNDIALS)/lib/libsundials_nvecserial.a $(SUNDIALS)/lib/libsundials_cvodes.a $(SUNDIALS)/lib/libsundials_idas.a

STAN_SUNDIALS_HEADERS := $(shell find $(MATH)stan -name *cvodes*.hpp) $(shell find $(MATH)stan -name *idas*.hpp)
$(STAN_SUNDIALS_HEADERS) : $(LIBSUNDIALS)

clean-sundials:
	@echo '  cleaning sundials targets'
	$(RM) $(wildcard $(sort $(SUNDIALS_CVODES) $(SUNDIALS_IDAS) $(SUNDIALS_NVECSERIAL) $(LIBSUNDIALS)))


###############################################################################
# httpstan-specific libsundials
###############################################################################

#httpstan/lib/libsundials_nvecserial.a: $(LIBSUNDIALS)
httpstan/lib/libsundials_nvecserial.a httpstan/lib/libsundials_cvodes.a httpstan/lib/libsundials_idas.a: $(LIBSUNDIALS)
	cp $(LIBSUNDIALS) httpstan/lib
