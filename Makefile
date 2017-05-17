PYTHON ?= python
CYTHON ?= cython

%.cpp: %.pyx httpstan/*.pxd
	$(CYTHON) -3 --cplus $<

cython: httpstan/stan.cpp httpstan/compile.cpp httpstan/spsc_queue.cpp

openapi: doc/source/openapi.json

doc/source/openapi.json: httpstan/routes.py httpstan/views.py
	@echo writing OpenAPI spec to $@
	@python -c'from httpstan import routes; print(routes.openapi_spec())' > $@
