import config as c
import globalVariables as g
from credentials import email
from datetime import datetime

import logging, logging.handlers
from os import mkdir
from pytz import timezone

def init_formatter():
    def formatDatetime(record, datefmt=None):
        # pylint: disable=undefined-variable
        ct = datetime.fromtimestamp(record.created, g.nyc)
        if datefmt:
            s = ct.strftime(datefmt)
        else:
            t = ct.strftime(self.default_time_format)
            s = self.default_msec_format % (t, record.msecs)
        return s

    fmtr = logging.Formatter(
        fmt = f'\n%(asctime)s %(name)s\n%(levelname)s: %(message)s',
        datefmt = '%m-%d-%Y %H:%M:%S.%f')
    fmtr.formatTime = formatDatetime
    return fmtr

def init_primary_logs(logLevel, env, fmtr):
    # logLevel: string; logging level to print to terminal
    # env: string; environment (only send alert emails if env == 'prod')
    # fmtr: logging.formatter instance

    # create logPath if needed
    try: mkdir(c.logPath)
    except Exception: pass

    # handlers
    consoleHdlr = logging.StreamHandler()
    consoleHdlr.setLevel(logLevel.upper())
    consoleHdlr.setFormatter(fmtr)

    debugHdlr = logging.FileHandler(c.logPath + 'debug.log')
    debugHdlr.setLevel(logging.DEBUG)
    debugHdlr.setFormatter(fmtr)

    warningHdlr = logging.FileHandler(c.logPath + 'warning.log')
    warningHdlr.setLevel(logging.WARNING)
    warningHdlr.setFormatter(fmtr)

    # toaddrs = c.criticalEmails if env == 'prod' else email.username
    # emailHdlr = logging.handlers.SMTPHandler(
    #     mailhost = ('smtp.gmail.com', 465),
    #     fromaddr = email.username,
    #     toaddrs = toaddrs,
    #     subject = 'SOCKS EMERGENCY',
    #     secure = (),
    #     timeout = 60)
    # emailHdlr.setFormatter(fmtr)
    # emailHdlr.setLevel(logging.CRITICAL)

    # loggers
    logging.basicConfig(
        level = logging.DEBUG,
        handlers = [consoleHdlr, debugHdlr, warningHdlr],
        force = True)

    streamLog = logging.getLogger('main')
    streamLog.setLevel(logging.DEBUG)

    streamLog = logging.getLogger('stream')
    streamLog.setLevel(logging.DEBUG)

    indicatorsLog = logging.getLogger('indicators')
    indicatorsLog.setLevel(logging.DEBUG)

def init_algo_logs(allAlgos, fmtr):
    # fmtr: logging.formatter instance

    for algo in allAlgos:
        # handler
        logFileName = c.logPath + algo.name + '.log'
        hdlr = logging.FileHandler(logFileName)
        hdlr.setLevel(logging.DEBUG)
        hdlr.setFormatter(fmtr)

        # logger
        algo.log.addHandler(hdlr)
        algo.log.setLevel(logging.DEBUG)
