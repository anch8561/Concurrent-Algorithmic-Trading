import config as c
import globalVariables as g
from algos import allAlgos
from allocate_buying_power import allocate_buying_power
from init_alpaca import init_alpaca
from init_logging import init_logging
from parse_args import parse_args
from populate_assets import populate_assets
from reset import reset
from streaming import stream
from tick_algos import tick_algos
from timing import init_timing, update_time

import sys
from datetime import timedelta
from logging import getLogger
from threading import Thread
from time import sleep

# parse arguments
args = parse_args(sys.argv[1:])

# init logging
init_logging(args.log, args.env)
log = getLogger()

# init alpaca
init_alpaca(args.env)
if args.reset: reset()

# init timing
init_timing()

# init streaming
populate_assets(args.numAssets)
Thread(target=stream, args=(g.connPaper)).start()

# init algos
allocate_buying_power()
for algo in allAlgos: # FIX: no performance data
    algo.buyPow['long'] = 5000
    algo.buyPow['short'] = 5000
log.warning('Starting active algos')
for algo in allAlgos:
    if algo.active: algo.start()

# main loop
log.warning('Entering main loop')
marketIsOpen = True
try:
    while True:
        update_time()

        if ( # market is open
            g.TTOpen < timedelta(0) and
            g.TTClose > timedelta(0)
        ):
            # update market state
            if not marketIsOpen:
                marketIsOpen = True
                log.warning('Market is open')

            # update new bar delay
            try: isAfterNewBarDelay = g.now - g.lastBarReceivedTime > c.tickDelay
            except Exception as e:
                if g.lastBarReceivedTime == None:isAfterNewBarDelay = False
                else: log.exception(e)
            
            if ( # new bars
                isAfterNewBarDelay and
                any(bars.ticked[-1] == False for bars in g.assets['min'].values())
            ):
                tick_algos()
                log.info('Waiting for bars')
        else:
            # update market state
            if marketIsOpen:
                marketIsOpen = False
                log.warning('Market is closed')

except BaseException as e:
    log.exception(e)

    log.warning('Stopping active algos')
    for algo in allAlgos:
        if algo.active: algo.stop()

    pass # removes need for double keyboard interrupt
