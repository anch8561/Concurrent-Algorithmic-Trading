from algos import allAlgos

import config as c
from credentials import email
from datetime import datetime
import logging, logging.handlers
from os import mkdir
from pytz import timezone

nyc = timezone('America/New_York')
def formatDatetime(record, datefmt=None):
    # pylint: disable=undefined-variable
    ct = datetime.fromtimestamp(record.created, nyc)
    if datefmt:
        s = ct.strftime(datefmt)
    else:
        t = ct.strftime(self.default_time_format)
        s = self.default_msec_format % (t, record.msecs)
    return s

def init_logging(args):
    # create logPath if needed
    try: mkdir(c.logPath)
    except Exception: pass

    # formatter
    formatter = logging.Formatter(
        fmt = f'\n%(asctime)s %(name)s\n%(levelname)s: %(message)s',
        datefmt = '%m-%d-%Y %H:%M:%S.%f')
    formatter.formatTime = formatDatetime

    # handlers
    consoleHdlr = logging.StreamHandler()
    consoleHdlr.setLevel(args.log.upper())
    consoleHdlr.setFormatter(formatter)

    debugHdlr = logging.FileHandler(c.logPath + 'debug.log')
    debugHdlr.setLevel(logging.DEBUG)
    debugHdlr.setFormatter(formatter)

    warningHdlr = logging.FileHandler(c.logPath + 'warning.log')
    warningHdlr.setLevel(logging.WARNING)
    warningHdlr.setFormatter(formatter)

    # toaddrs = c.criticalEmails if args.env == 'prod' else email.username
    # emailHdlr = logging.handlers.SMTPHandler(
    #     mailhost = ('smtp.gmail.com', 465),
    #     fromaddr = email.username,
    #     toaddrs = toaddrs,
    #     subject = 'SOCKS EMERGENCY',
    #     secure = (),
    #     timeout = 60)
    # emailHdlr.setFormatter(formatter)
    # emailHdlr.setLevel(logging.CRITICAL)

    # loggers
    logging.basicConfig(
        level = logging.DEBUG,
        handlers = [consoleHdlr, debugHdlr, warningHdlr])

    streamLog = logging.getLogger('stream')
    streamLog.setLevel(logging.DEBUG)

    indicatorsLog = logging.getLogger('indicators')
    indicatorsLog.setLevel(logging.DEBUG)

    # algos
    for algo in allAlgos:
        # handler
        logFileName = c.logPath + algo.name + '.log'
        hdlr = logging.FileHandler(logFileName)
        hdlr.setLevel(logging.DEBUG)
        hdlr.setFormatter(formatter)

        # logger
        algo.log.addHandler(hdlr)
        algo.log.setLevel(logging.DEBUG)
