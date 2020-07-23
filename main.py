import config as c
import globalVariables as g
from algos import intradayAlgos, overnightAlgos, multidayAlgos, allAlgos
from allocate_buying_power import allocate_buying_power
from indicators import indicators
from init_alpaca import init_alpaca
from init_logging import init_logging
from populate_assets import populate_assets
from streaming import stream, process_all_trades, compile_day_bars
from timing import init_timing, get_time, get_market_open, get_market_close, get_time_str, get_date
from warn import warn

import argparse, logging
from datetime import timedelta
from threading import Thread
from time import sleep

# get arguments
parser = argparse.ArgumentParser()
parser.add_argument(
    'env',
    choices = ['dev', 'test', 'prod'],
    nargs = '?',
    default = 'dev',
    help = 'which credentials to use: development, testing, or production')
parser.add_argument(
    "--log",
    choices = ['debug', 'info', 'warn', 'warning', 'error', 'critical'],
    default = c.defaultLogLevel,
    help = "logging level")
parser.add_argument(
    '--reset',
    action = 'store_true',
    help = 'whether to load algo positions or reset and start from scratch')
args = parser.parse_args()

# initialize
init_logging(args)
init_alpaca(args.env)
init_timing()

# reset accounts and algos
if args.reset:
    if c.verbose: print('Cancelling orders and closing positions')
    # reset account orders and positions
    for alpaca in (g.alpacaLive, g.alpacaPaper):
        alpaca.cancel_all_orders()
        alpaca.close_all_positions()
    
    # reset algo orders and positions
    for algo in allAlgos:
        algo.orders = {}
        algo.positions = {}

    # reset global orders and positions
    g.liveOrders = {}
    g.paperOrders = {}

    g.livePositions = {}
    g.paperPositions = {}

# allocate buying power
allocate_buying_power()
for algo in allAlgos: # FIX: no performance data
    algo.buyPow['long'] = 5000
    algo.buyPow['short'] = 5000

# populate assets
populate_assets(100)

# start streaming
channels = ['account_updates', 'trade_updates']
for symbol in g.assets['min']:
    channels += [f'AM.{symbol}']
Thread(target=stream, args=(g.connPaper, channels)).start()

# start active algos
print('Starting active algos')
for algo in allAlgos:
    if algo.active: algo.start()

# main loop
print('Entering main loop')
marketIsOpen = True
state = 'night'
try:
    while True:
        # update time
        now = get_time()
        g.TTOpen = get_market_open() - now
        g.TTClose = get_market_close() - now

        if ( # market is open
            g.TTOpen < timedelta(0) and
            g.TTClose > timedelta(0)
        ):
            if not marketIsOpen:
                marketIsOpen = True
                print('Market is open')

            # check for new minute bars
            try: newBarDelay = now - g.lastBarReceivedTime > c.tickDelay
            except: newBarDelay = False
            if (
                newBarDelay and
                any(bars.ticked[-1] == False for bars in g.assets['min'].values())
            ):
                closingSoon = g.TTClose <= c.marketCloseTransitionPeriod

                # tick algos
                print('Ticking algos')
                try:
                    if state == 'night' and not closingSoon:
                        print('Deactivating overnight algos')
                        for algo in overnightAlgos: algo.deactivate()
                        
                        if not any(algo.active for algo in overnightAlgos):
                            print('Activating intraday algos')
                            for algo in intradayAlgos: algo.activate()
                            state = 'day'

                    elif state == 'day' and not closingSoon:
                        for algo in intradayAlgos: algo.tick() # TODO: parallel

                    elif state == 'day' and closingSoon:
                        print('Deactivating intraday algos')
                        for algo in intradayAlgos: algo.deactivate()
                        
                        if not any(algo.active for algo in intradayAlgos):
                            print('Activating overnight algos')
                            for algo in overnightAlgos: algo.activate()
                            state = 'night'
                            compile_day_bars()

                    elif state == 'night' and closingSoon:
                        for algo in overnightAlgos: algo.tick() # TODO: parallel
                        for algo in multidayAlgos: algo.tick() # TODO: parallel
                except Exception as e: warn(e)

                # set ticked
                for bars in g.assets['min'].values():
                    try: # won't work if no bars
                        jj = bars.columns.get_loc('ticked')
                        bars.iloc[-1, jj] = True
                    except Exception as e: warn(e)

                # process trade update backlog
                print('Processing trade update backlog')
                process_all_trades()

                print('Waiting for bars')
        else:
            if marketIsOpen:
                marketIsOpen = False
                print('Market is closed')

        sleep(1)

except Exception as e: # stop active algos
    # FIX: not working
    print('Stopping active algos')
    for algo in allAlgos:
        if algo.active:
            print(f'\tStopping {algo.name}')
            algo.stop()
    warn(e)
    pass
