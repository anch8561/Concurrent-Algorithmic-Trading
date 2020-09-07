import config as c
import globalVariables as g
import init_logs
from algos import init_algos
from allocate_buying_power import allocate_buying_power
from init_alpaca import init_alpaca
from init_assets import init_assets
from parse_args import parse_args
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

# init logs
logFormatter = init_logs.init_formatter()
init_logs.init_primary_logs(args.log, args.env, logFormatter)
log = getLogger()

# init alpaca and timing
init_alpaca(args.env)
init_timing()

# init algos
algos = init_algos()
init_logs.init_algo_logs(algos['all'], logFormatter)
# TODO: update global positions
allocate_buying_power(algos)
for algo in algos['all']: # FIX: no performance data
    algo.buyPow['long'] = 5000
    algo.buyPow['short'] = 5000
if args.reset: reset(algos['all'])
log.warning('Starting active algos')
for algo in algos['all']:
    if algo.active: algo.start()

# init assets and stream
init_assets(args.numAssets, algos['all'])
Thread(target=stream, args=(g.connPaper, algos['all'])).start()

# main loop
log.warning('Entering main loop')
state = 'night'
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
                state = tick_algos(algos, state)
                log.info('Waiting for bars')
        else:
            # update market state
            if marketIsOpen:
                marketIsOpen = False
                log.warning('Market is closed')

except BaseException as e:
    log.exception(e)

    log.warning('Stopping active algos')
    for algo in algos['all']:
        if algo.active: algo.stop()

    pass # removes need for double keyboard interrupt
