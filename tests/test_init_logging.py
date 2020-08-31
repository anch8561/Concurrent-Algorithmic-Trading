from algos import allAlgos
from init_logging import init_logging

import logging

def test_init_logging():
    init_logging('info', 'dev')
    log = logging.getLogger()
    assert log.level == logging.DEBUG
    assert len(log.handlers) == 3

    assert log.handlers[0].level == logging.INFO
    assert log.handlers[1].level == logging.DEBUG
    assert log.handlers[2].level == logging.WARNING

    assert logging.getLogger('stream').level == logging.DEBUG

    assert logging.getLogger('indicators').level == logging.DEBUG

    for algo in allAlgos:
        assert algo.log.level == logging.DEBUG
