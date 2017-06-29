"""Test services function argument lookups."""
import json

import aiohttp
import appdirs
import lmdb

import httpstan.program
import httpstan.services.arguments as arguments


host, port = '127.0.0.1', 8080
programs_url = 'http://{}:{}/v1/programs'.format(host, port)
program_code = 'parameters {real y;} model {y ~ normal(0,1);}'
headers = {'content-type': 'application/json'}


def test_lookup_default():
    """Test argument default value lookup."""
    expected = 1000
    assert expected == arguments.lookup_default(arguments.Method.SAMPLE, 'num_samples')
    expected = 0.05
    assert expected == arguments.lookup_default(arguments.Method.SAMPLE, 'gamma')


def test_function_arguments(loop_with_server):
    """Test function argument name lookup."""
    # function_arguments needs compiled module, so we have to get one
    async def main():
        async with aiohttp.ClientSession() as session:
            data = {'program_code': program_code}
            async with session.post(programs_url, data=json.dumps(data), headers=headers) as resp:
                assert resp.status == 200
                program_id = (await resp.json())['id']

        # get a reference to the program_module
        cache_path = appdirs.user_cache_dir('httpstan')
        db = lmdb.Environment(cache_path, map_size=httpstan.cache.HTTPSTAN_LMDB_MAP_SIZE)
        module_bytes = await httpstan.cache.load_program_extension_module(program_id, db)
        assert module_bytes is not None
        program_module = httpstan.program.load_program_extension_module(program_id, module_bytes)

        expected = ['random_seed', 'chain', 'init_radius', 'num_warmup', 'num_samples']
        assert expected == arguments.function_arguments('hmc_nuts_diag_e', program_module)

    loop_with_server.run_until_complete(main())
