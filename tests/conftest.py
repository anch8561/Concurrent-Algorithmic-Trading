import globalVariables as g
from algoClasses import Algo

from importlib import reload
from pytest import fixture

@fixture(autouse=True)
def reloadGlobalVariables():
    reload(g)

@fixture
def algos():
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