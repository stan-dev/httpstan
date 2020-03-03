PYTHON ?= python
PROTOC ?= protoc
PROTOBUF_FILES_PYTHON := httpstan/callbacks_writer_pb2.py
PROTOBUF_FILES_CPP := httpstan/callbacks_writer.pb.cc
STUB_FILES := httpstan/callbacks_writer_pb2.pyi

ifeq '$(findstring ;,$(PATH))' ';'
    UNAME := Windows
else
    UNAME := $(shell uname 2>/dev/null || echo Unknown)
    UNAME := $(patsubst CYGWIN%,Cygwin,$(UNAME))
    UNAME := $(patsubst MSYS%,MSYS,$(UNAME))
    UNAME := $(patsubst MINGW%,MSYS,$(UNAME))
endif

default: $(PROTOBUF_FILES_PYTHON) $(PROTOBUF_FILES_CPP) $(STUB_FILES)

httpstan/%.pb.cc: protos/%.proto
	$(PROTOC) -Iprotos --cpp_out=httpstan $<

httpstan/%_pb2.py: protos/%.proto
	$(PROTOC) -Iprotos --python_out=httpstan $<

httpstan/%_pb2.pyi: protos/%.proto
ifneq ($(UNAME),Windows)
	$(PROTOC) -Iprotos --mypy_out=httpstan $<
else
	@echo not generating stub files on Windows, avoids error about protoc-gen-mypy not being found
endif
