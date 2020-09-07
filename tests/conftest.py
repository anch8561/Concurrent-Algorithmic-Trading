import globalVariables as g
from algoClasses import Algo

import logging
from importlib import reload
from pytest import fixture

logging.basicConfig(level=logging.DEBUG)

# NOTE: be careful of Mock scope
# NOTE: be careful of fixture order
# TODO: patch config

@fixture(autouse=True)
def reloadGlobalVariables():
    # NOTE: reload does not update existing objects
    reload(g)

@fixture
def algos(reloadGlobalVariables):
    intraday = [
        Algo(print, False, n=0),
        Algo(print, False, n=1)]
    overnight = [
        Algo(print, False, n=2),
        Algo(print, False, n=3),
        Algo(print, False, n=4)]
    multiday = [
        Algo(print, False, n=5),
        Algo(print, False, n=6),
        Algo(print, False, n=7),
        Algo(print, False, n=8)]
    return {
        'intraday': intraday,
        'overnight': overnight,
        'multiday': multiday,
        'all': intraday + overnight + multiday}

@fixture
def allAlgos(algos):
    return algos['all']
