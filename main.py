import config as c
import globalVariables as g
from algos import init_algos
from allocate_buying_power import allocate_buying_power
from indicators import init_indicators
from init_alpaca import init_alpaca
from init_assets import init_assets
from init_logs import init_log_formatter, init_primary_logs
from parse_args import parse_args
from reset import reset
from streaming import stream
from tick_algos import tick_algos
from timing import init_timing, update_time

import sys
from datetime import timedelta
from logging import getLogger
from threading import Thread

# parse arguments
args = parse_args(sys.argv[1:])

# init logs
logFmtr = init_log_formatter()
init_primary_logs(args.log, args.env, logFmtr)
log = getLogger('main')

# init alpaca
init_alpaca(args.env)

# init timing
init_timing()

# init algos
algos = init_algos(True, logFmtr)
if args.reset: reset(algos['all'])
allocate_buying_power(algos) # TODO: subtract positions
for algo in algos['all']: algo.buyPow = 5000 # FIX: no performance data

# init indicators
indicators = init_indicators(algos['all'])

# init assets
init_assets(args.numAssets, algos['all'], indicators)

# init streaming
Thread(target=stream, args=[g.conn, algos['all'], indicators]).start()
# NOTE: begin using g.lock
# TODO: update global positions (careful of add_asset)
# TODO: use barFreq to get price

# start algos
log.warning('Starting active algos')
for algo in algos['all']:
    if algo.active: algo.start()

# main loop
log.warning('Entering main loop')
state = 'overnight'
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
                if g.lastBarReceivedTime == None: # no bars received yet
                    isAfterNewBarDelay = False
                else: log.exception(e)
            
            try: # check for unticked bars
                if (
                    isAfterNewBarDelay and
                    any(bars.ticked[-1] == False for bars in g.assets['min'].values())
                ):
                    state = tick_algos(algos, indicators, state)
                    log.info('Waiting for bars')
            except Exception as e: log.exception(e)

        else:
            # update market state
            if marketIsOpen:
                marketIsOpen = False
                log.warning('Market is closed')

except BaseException as e:
    log.exception(e)

    g.lock.acquire()
    log.warning('Stopping active algos')
    for algo in algos['all']:
        if algo.active: algo.stop()
    g.lock.release()

    pass # removes need for double keyboard interrupt
