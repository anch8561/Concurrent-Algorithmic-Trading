import globalVariables as g
from importlib import reload
from pytest import fixture

@fixture(autouse=True)
def reloadGlobalVariables():
    reload(g)
