import init_logs

import logging
from datetime import datetime
from pytest import fixture
from pytz import timezone

@fixture
def formatter():
    return init_logs.init_formatter()

def test_init_formatter():
    # setup
    fmtr = init_logs.init_formatter()
    record = logging.LogRecord(
        name = 'test',
        level = logging.DEBUG,
        pathname = 'NA',
        lineno = 0,
        msg = 'debug message',
        args = None,
        exc_info = None)
    den = timezone('America/Denver')
    ct = datetime(2020, 7, 26, 11, 2, 14, 536232).astimezone(den)
    record.created = ct.timestamp()
    
    # test
    expected = '\n07-26-2020 13:02:14.536232 test\nDEBUG: debug message'
    assert fmtr.format(record) == expected


def test_init_primary_logs(formatter):
    init_logs.init_primary_logs('info', 'dev', formatter)

    # root log
    log = logging.getLogger()
    assert log.level == logging.DEBUG
    assert len(log.handlers) == 3
    assert log.handlers[0].level == logging.INFO
    assert log.handlers[1].level == logging.DEBUG
    assert log.handlers[2].level == logging.WARNING
    for hdlr in log.handlers:
        assert hdlr.formatter == formatter

    # stream log
    log = logging.getLogger('stream')
    assert log.level == logging.DEBUG
    assert log.handlers == []

    # indicators log
    log = logging.getLogger('indicators')
    assert log.level == logging.DEBUG
    assert log.handlers == []

def test_init_algo_logs(formatter, allAlgos):
    init_logs.init_algo_logs(allAlgos, formatter)
    for algo in allAlgos:
        assert algo.log.level == logging.DEBUG
        assert len(algo.log.handlers) == 1
        assert algo.log.handlers[0].level == logging.DEBUG
        assert algo.log.handlers[0].formatter == formatter
