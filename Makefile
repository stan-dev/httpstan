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
	cd build/protobuf-3.11.3 && ./configure --prefix="$(shell pwd)/httpstan" && make -j 8 install
	@echo deleting unused files which are installed by make install

httpstan/%.pb.cc: protos/%.proto httpstan/bin/protoc
	LD_LIBRARY_PATH=httpstan/lib httpstan/bin/protoc -Iprotos --cpp_out=httpstan $<

httpstan/%_pb2.py: protos/%.proto httpstan/bin/protoc
	LD_LIBRARY_PATH=httpstan/lib httpstan/bin/protoc -Iprotos --python_out=httpstan $<

# requires protoc-gen-mypy:
httpstan/%_pb2.pyi: protos/%.proto httpstan/bin/protoc
	LD_LIBRARY_PATH=httpstan/lib httpstan/bin/protoc -Iprotos --mypy_out=httpstan $<


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
