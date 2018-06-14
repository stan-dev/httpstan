PYTHON_BIN ?= python
CYTHON_BIN ?= cython

default: protos cython

%.cpp: %.pyx
	$(CYTHON_BIN) -3 --cplus $<

cython: httpstan/stan.cpp httpstan/compile.cpp httpstan/spsc_queue.cpp

openapi: doc/source/openapi.json

protos: httpstan/callbacks_writer_pb2.py

httpstan/%_pb2.py: protos/%.proto
	$(PYTHON_BIN) -m grpc_tools.protoc -Iprotos --python_out=httpstan $<

doc/source/openapi.json: httpstan/routes.py httpstan/views.py
	@echo writing OpenAPI spec to $@
	@$(PYTHON_BIN) -c'from httpstan import routes; print(routes.openapi_spec())' > $@
