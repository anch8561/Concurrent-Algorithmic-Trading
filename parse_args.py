import config as c

from argparse import ArgumentParser

def parse_args(args):
    parser = ArgumentParser()
    parser.add_argument(
        'env',
        choices = ['dev', 'test', 'prod'],
        nargs = '?',
        default = 'dev',
        help = 'which credentials to use: development, testing, or production (default dev)')
    parser.add_argument(
        '--log',
        choices = ['debug', 'info', 'warn', 'warning', 'error', 'critical'],
        default = c.defaultLogLevel,
        help = f'logging level to display (default {c.defaultLogLevel})')
    parser.add_argument(
        '--numAssets',
        default = c.numAssets,
        type = int,
        help = f'number of symbols to stream (default {c.numAssets}, -1 means all)')
    parser.add_argument(
        '--reset',
        action = 'store_true',
        help = 'cancel orders and exit positions before starting')
    return parser.parse_args(args)
