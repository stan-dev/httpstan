"""Parse CmdStan 'help-all' output into machine readable JSON."""
import argparse
import collections
import json
import re

METHODS = {'sample', 'optimize', 'variational', 'diagnose'}
OPTIMIZE_ALGORITHMS = {'bfgs', 'lbfgs', 'newton'}

parser = argparse.ArgumentParser(description="Parse CmdStan 'help-all' text.")
parser.add_argument('input_filename', help="Filename containing 'help-all' output.")


def _split_cmdstan_help(text):
    """Break CmdStan help text into logical parts."""
    parts = {'method': collections.defaultdict(dict), 'output': ''}
    for chunk in re.split(r'\n  (?=\w+\n)', text):
        if chunk.lstrip().startswith('method'):
            for subchunk in re.split(r'\n    (?=\w+\n)', chunk):
                header = subchunk.lstrip().split()[0]
                if header in METHODS:
                    if header == 'optimize':
                        for optchunk in re.split(r'\n        (?=\w+\n)', subchunk):
                            algo = optchunk.lstrip().split()[0]
                            if algo in OPTIMIZE_ALGORITHMS:
                                parts['method'][header][algo] = optchunk
                    else:
                        parts['method'][header] = subchunk
        elif chunk.lstrip().startswith('output'):
            parts['output'] = chunk
    assert 'refresh' in parts['output']
    return parts


def _extract_defaults(text):
    regex = r'\s(\w+)=<([^>]+)>.*?Defaults to ([^\n]+)'
    for name, type, default in re.findall(regex, text, re.DOTALL):
        yield {'name': name, 'type': type, 'default': default}


def parse_cmdstan_help(text):
    """Parse output of CmdStan `help-all`."""
    parts = _split_cmdstan_help(text)

    def walk(node, visit_func):
        node = node.copy()
        for key, item in node.items():
            if isinstance(item, dict):
                node[key] = walk(item, visit_func)
            else:
                node[key] = visit_func(item)
        return node

    return walk(parts, lambda text: list(_extract_defaults(text)))


if __name__ == '__main__':
    args = parser.parse_args()
    with open(args.input_filename) as fh:
        parsed = parse_cmdstan_help(fh.read())
    print(json.dumps(parsed, indent=2))
