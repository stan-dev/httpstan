PYTHON ?= python
CYTHON ?= cython
PROTOBUF_FILES := httpstan/callbacks_writer_pb2.py
CPP_FILES := httpstan/stan.cpp httpstan/compile.cpp

default: $(PROTOBUF_FILES) $(CPP_FILES)

%.cpp: %.pyx
	$(CYTHON) -3 --cplus $<

httpstan/%_pb2.py: protos/%.proto
	$(PYTHON) -m grpc_tools.protoc -Iprotos --python_out=httpstan $<

httpstan/%_pb.hpp: protos/%.proto
	$(PYTHON) -m grpc_tools.protoc -Iprotos --cpp_out=httpstan $<
