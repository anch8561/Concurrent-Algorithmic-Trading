import config as c
from parse_args import parse_args

from argparse import Namespace

def test_parse_args():
    # defaults
    argsIn = []
    argsOut = parse_args(argsIn)
    expectedArgs = Namespace(
        env = 'dev',
        log = c.defaultLogLevel,
        numAssets = c.numAssets,
        reset = False)
    assert argsOut == expectedArgs
    
    # arbitrary
    argsIn = ['test', '--log', 'debug', '--numAssets', '11', '--reset']
    argsOut = parse_args(argsIn)
    expectedArgs = Namespace(
        env = 'test',
        log = 'debug',
        numAssets = 11,
        reset = True)
    assert argsOut == expectedArgs
    