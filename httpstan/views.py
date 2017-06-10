"""HTTP request handlers for httpstan.

Handlers are separated from the endpoint names. Endpoints are defined in
`httpstan.routes`.
"""
import json
import logging
import random

import aiohttp.web
import google.protobuf.json_format
import marshmallow
import marshmallow.fields as fields
import marshmallow.validate as validate
import webargs.aiohttpparser

import httpstan.cache
import httpstan.program
import httpstan.services_stub as services_stub


logger = logging.getLogger('httpstan')


def json_error(message):  # noqa
    return aiohttp.web.Response(body=json.dumps({'error': message}).encode('utf-8'),
                                content_type='application/json')


programs_args = {
    'program_code': fields.Str(required=True),
}


class ProgramSchema(marshmallow.Schema):  # noqa
    id = fields.String(required=True)

    class Meta:  # noqa
        strict = True


async def handle_programs(request):
    """Compile Stan Program.

    ---
    post:
        description: Compile a Stan Program
        consumes:
            - application/json
        produces:
            - application/json
        parameters:
            - in: body
              name: body
              description: Stan Program code to compile
              required: true
              schema:
                  type: object
                  properties:
                      program_code:
                          type: string
        responses:
            200:
              description: Compiled Stan Program
              schema:
                 $ref: '#/definitions/Program'
    """
    args = await webargs.aiohttpparser.parser.parse(programs_args, request)
    program_code = args['program_code']
    program_id = httpstan.program.calculate_program_id(program_code)
    try:
        module_bytes = await httpstan.cache.load_program_extension_module(program_id, request.app['db'])
    except KeyError:
        logger.info('Compiling Stan Program. Program id is {}.'.format(program_id))
        module_bytes = await httpstan.program.compile_program_extension_module(program_code)
        await httpstan.cache.dump_program_extension_module(program_id, module_bytes, request.app['db'])
    else:
        logger.info('Found Stan Program in cache. Program id is {}.'.format(program_id))
    return aiohttp.web.json_response(ProgramSchema(strict=True).dump({'id': program_id}).data)


# TODO(AR): remove defaults, must be provided explicitly
SAMPLE_ALGOS = frozenset({'hmc_nuts_diag_e', 'hmc_nuts_diag_e_adapt'})
class ProgramActionSchema(marshmallow.Schema):  # noqa
    type = fields.String(required=True, validate=validate.OneOf(SAMPLE_ALGOS))
    data = fields.Dict(missing={})
    random_seed = fields.Integer(missing=random.randrange(2 ** 31))
    chain = fields.Integer(missing=1)
    init_radius = fields.Float(missing=2.0)
    num_warmup = fields.Integer(missing=1000)
    num_samples = fields.Integer(missing=1000)

    class Meta:  # noqa
        strict = True


async def handle_programs_actions(request):
    """Call function defined in stan::services.

    ---
    post:
        summary: Call function defined in stan::services.
        description: >
            The action `type` indicates the name of the stan::services function
            which should be called given the Stan Program associated with the id
            `program_id`.  For example, if sampling using
            ``stan::services::hmc_nuts_diag_e`` the action `type` is the
            function name ``hmc_nuts_diag_e``.
        consumes:
            - application/json
        produces:
            - application/x-ndjson
        parameters:
            - name: program_id
              in: path
              description: ID of Stan Program to use
              required: true
              type: string
            - name: body
              in: body
              description: "'Action' specifying stan::services function to call with Stan Program."
              required: true
              schema:
                 $ref: '#/definitions/ProgramAction'
        responses:
            200:
                description: Stream of newline-delimited JSON.
    """
    program_id = request.match_info['program_id']
    args = await webargs.aiohttpparser.parser.parse(ProgramActionSchema(), request)

    module_bytes = await httpstan.cache.load_program_extension_module(program_id, request.app['db'])
    if module_bytes is None:
        return json_error('Stan Program with id `{}` not found.'.format(program_id))
    program_module = httpstan.program.load_program_extension_module(program_id, module_bytes)

    # setup streaming response
    stream = aiohttp.web.StreamResponse()
    stream.content_type = 'application/json'
    stream.charset = 'utf-8'
    stream.enable_chunked_encoding()
    await stream.prepare(request)
    # exclusive lock needed until thread_local option available for autodiff.
    # See https://github.com/stan-dev/math/issues/551
    with await request.app['sample_lock']:
        async for message in services_stub.call_sample(args['type'], program_module, args['data'], args['random_seed'],
                                                       args['chain'], args['init_radius'],
                                                       args['num_warmup'], args['num_samples']):
            assert message is not None, message
            stream.write(google.protobuf.json_format.MessageToJson(message).encode().replace(b'\n', b''))
            stream.write(b'\n')
    return stream
