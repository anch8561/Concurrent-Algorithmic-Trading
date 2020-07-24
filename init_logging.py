from algos import allAlgos

import config as c
from credentials import email
from datetime import datetime
import logging, logging.handlers
import pytz
from time import time_ns

class LogRecord_ns(logging.LogRecord):
    def __init__(self, *args, **kwargs):
        self.created_ns = time_ns() # Fetch precise timestamp
        super().__init__(*args, **kwargs)

class Formatter_ns(logging.Formatter):
    default_nsec_format = '%s,%09d'
    def formatTime(self, record, datefmt=None):
        if datefmt is not None: # Do not handle custom formats here ...
            return super().formatTime(record, datefmt) # ... leave to original implementation
        ct = self.converter(record.created_ns / 1e9)
        t = ct.strftime(self.default_time_format)
        s = self.default_nsec_format % (t, record.created_ns - (record.created_ns // 10**9) * 10**9)
        return s
    
        ## ORIGINAL IMPLEMENTATION
        # ct = self.converter(record.created)
        # if datefmt:
        #     s = time.strftime(datefmt, ct)
        # else:
        #     t = time.strftime(self.default_time_format, ct)
        #     s = self.default_msec_format % (t, record.msecs)
        # return s


# formatter tab before msg, extra (possible list) below, ns timestamp

def init_logging(args):
    # handlers
    consoleHdlr = logging.StreamHandler()
    consoleHdlr.setLevel(args.log.upper())

    debugHdlr = logging.FileHandler('debug.log')
    debugHdlr.setLevel(logging.DEBUG)

    warningHdlr = logging.FileHandler('warning.log')
    warningHdlr.setLevel(logging.WARNING)

    # toaddrs = c.criticalEmails if args.env == 'prod' else email.username
    # emailHdlr = logging.handlers.SMTPHandler(
    #     mailhost = ('smtp.gmail.com', 465),
    #     fromaddr = email.username,
    #     toaddrs = toaddrs,
    #     subject = 'SOCKS EMERGENCY',
    #     secure = (),
    #     timeout = 60)
    # emailHdlr.setLevel(logging.CRITICAL)

    # loggers
    logging.basicConfig(
        level = logging.DEBUG,
        format = c.logFormat,
        datefmt = c.logDatefmt,
        handlers = [consoleHdlr, debugHdlr, warningHdlr])

    streamLog = logging.getLogger('stream')
    streamLog.setLevel(logging.DEBUG)

    indicatorsLog = logging.getLogger('indicators')
    indicatorsLog.setLevel(logging.DEBUG)

    for algo in allAlgos:
        algo.log.setLevel(logging.DEBUG)
        logFileName = c.algoPath + algo.name + '.log'
        hdlr = logging.FileHandler(logFileName)
        algo.log.addHandler(hdlr)
