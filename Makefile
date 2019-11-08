PYTHON ?= python
CYTHON ?= cython
PROTOBUF_FILES := httpstan/callbacks_writer_pb2.py
STUB_FILES := httpstan/callbacks_writer_pb2.pyi
CPP_FILES := httpstan/stan.cpp httpstan/compile.cpp

ifeq '$(findstring ;,$(PATH))' ';'
    UNAME := Windows
else
    UNAME := $(shell uname 2>/dev/null || echo Unknown)
    UNAME := $(patsubst CYGWIN%,Cygwin,$(UNAME))
    UNAME := $(patsubst MSYS%,MSYS,$(UNAME))
    UNAME := $(patsubst MINGW%,MSYS,$(UNAME))
endif

default: $(PROTOBUF_FILES) $(STUB_FILES) $(CPP_FILES)

%.cpp: %.pyx
	$(CYTHON) -3 --cplus $<

httpstan/%_pb2.py: protos/%.proto
	$(PYTHON) -m grpc_tools.protoc -Iprotos --python_out=httpstan $<

httpstan/%_pb2.pyi: protos/%.proto
ifneq ($(UNAME),Windows)
	$(PYTHON) -m grpc_tools.protoc -Iprotos --mypy_out=httpstan $<
else
	@echo not generating stub files on Windows, avoids error about protoc-gen-mypy not being found
endif

httpstan/%_pb.hpp: protos/%.proto
	$(PYTHON) -m grpc_tools.protoc -Iprotos --cpp_out=httpstan $<

openapi: doc/source/openapi.json

doc/source/openapi.json: httpstan/routes.py httpstan/views.py
	@echo writing OpenAPI spec to $@
	@python3 -c'from httpstan import routes; print(routes.openapi_spec())' > $@

apidoc:
	@echo excluding ``httpstan/views.py`` as Sphinx cannot process the the OpenAPI YAML 
	@echo excluding ``httpstan/routes.py`` as useless without ``views.py``
	sphinx-apidoc --ext-autodoc --force --no-toc -o doc/source httpstan httpstan/views.py httpstan/routes.py
