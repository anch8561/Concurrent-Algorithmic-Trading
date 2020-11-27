import config as c
import globalVariables as g
from credentials import email
from datetime import datetime

import logging, logging.handlers
import pandas as pd
from os import mkdir
from pytz import timezone

def init_log_formatter():
    def formatDatetime(record, datefmt=None) -> logging.Formatter:
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
        datefmt = '%Y-%m-%d %H:%M:%S.%f')
    fmtr.formatTime = formatDatetime
    return fmtr

def init_primary_logs(logLevel: str, env: str, fmtr: logging.Formatter):
    # logLevel: e.g. 'info'; logging level to print to terminal
    # env: environment; only send alert emails if env == 'prod'
    # fmtr: for custom log formatting

    # create logPath if needed
    try: mkdir(c.logPath)
    except: pass

    # display full dataframes
    pd.set_option("display.max_rows", None, "display.max_columns", None)

    # handlers
    consoleHdlr = logging.StreamHandler()
    consoleHdlr.setLevel(logLevel.upper())
    consoleHdlr.setFormatter(fmtr)

    warningHdlr = logging.FileHandler(c.logPath + 'warning.log')
    warningHdlr.setLevel(logging.WARNING)
    warningHdlr.setFormatter(fmtr)

    mainHdlr = logging.FileHandler(c.logPath + 'main.log')
    mainHdlr.setLevel(logging.DEBUG)
    mainHdlr.setFormatter(fmtr)
    
    streamHdlr = logging.FileHandler(c.logPath + 'stream.log')
    streamHdlr.setLevel(logging.DEBUG)
    streamHdlr.setFormatter(fmtr)
    
    indicatorsHdlr = logging.FileHandler(c.logPath + 'indicators.log')
    indicatorsHdlr.setLevel(logging.DEBUG)
    indicatorsHdlr.setFormatter(fmtr)


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
        handlers = [consoleHdlr, warningHdlr],
        force = True)

    mainLog = logging.getLogger('main')
    mainLog.setLevel(logging.DEBUG)
    log.addHandler(mainHdlr)

    streamLog = logging.getLogger('stream')
    streamLog.setLevel(logging.DEBUG)
    log.addHandler(streamHdlr)

    indicatorsLog = logging.getLogger('indicators')
    indicatorsLog.setLevel(logging.DEBUG)
    log.addHandler(indicatorsHdlr)

def init_algo_logs(allAlgos, fmtr: logging.Formatter):
    # allAlgos: list of all algos
    # fmtr: for custom log formatting

    for algo in allAlgos:
        # handler
        logFileName = c.logPath + algo.name + '.log'
        hdlr = logging.FileHandler(logFileName)
        hdlr.setLevel(logging.DEBUG)
        hdlr.setFormatter(fmtr)

        # logger
        algo.log.setLevel(logging.DEBUG)
        algo.log.addHandler(hdlr)
