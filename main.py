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

from argparse import ArgumentParser
from datetime import timedelta
from logging import getLogger
from threading import Thread
from time import sleep

# get arguments
parser = ArgumentParser()
parser.add_argument(
    'env',
    choices = ['dev', 'test', 'prod'],
    nargs = '?',
    default = 'dev',
    help = 'which credentials to use: development, testing, or production (default dev)')
parser.add_argument(
    '--log',
    choices = ['debug', 'info', 'warn', 'warning', 'error', 'critical'],
    default = c.defaultLogLevel,
    help = f'logging level to display (default {c.defaultLogLevel})')
parser.add_argument(
    '--numAssets',
    default = c.numAssets,
    help = f'number of symbols to stream (default {c.numAssets}, None means all)')
parser.add_argument(
    '--reset',
    action = 'store_true',
    help = 'cancel orders and exit positions before starting')
args = parser.parse_args()

# initialize
init_logging(args)
init_alpaca(args.env)
init_timing()
log = getLogger()

# reset accounts and algos
if args.reset:
    log.warning('Cancelling orders and closing positions')
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
populate_assets()

# start streaming
channels = ['account_updates', 'trade_updates']
for symbol in g.assets['min']:
    channels += [f'AM.{symbol}']
Thread(target=stream, args=(g.connPaper, channels)).start()

# start active algos
log.warning('Starting active algos')
for algo in allAlgos:
    if algo.active: algo.start()

# main loop
log.warning('Entering main loop')
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
                log.warning('Market is open')

            # check for new minute bars
            try: pastNewBarDelay = now - g.lastBarReceivedTime > c.tickDelay
            except Exception as e:
                if g.lastBarReceivedTime == None: pastNewBarDelay = False
                else: log.exception(e)
            if (
                pastNewBarDelay and
                any(bars.ticked[-1] == False for bars in g.assets['min'].values())
            ):
                closingSoon = g.TTClose <= c.marketCloseTransitionPeriod

                # tick algos
                log.info('Ticking algos')
                try:
                    if state == 'night' and not closingSoon:
                        log.warning('Deactivating overnight algos')
                        for algo in overnightAlgos: algo.deactivate()
                        
                        if not any(algo.active for algo in overnightAlgos):
                            log.warning('Activating intraday algos')
                            for algo in intradayAlgos: algo.activate()
                            state = 'day'

                    elif state == 'day' and not closingSoon:
                        for algo in intradayAlgos: algo.tick() # TODO: parallel

                    elif state == 'day' and closingSoon:
                        log.warning('Deactivating intraday algos')
                        for algo in intradayAlgos: algo.deactivate()
                        
                        if not any(algo.active for algo in intradayAlgos):
                            log.warning('Activating overnight algos')
                            for algo in overnightAlgos: algo.activate()
                            state = 'night'
                            compile_day_bars()

                    elif state == 'night' and closingSoon:
                        for algo in overnightAlgos: algo.tick() # TODO: parallel
                        for algo in multidayAlgos: algo.tick() # TODO: parallel
                except Exception as e: log.exception(e)

                # set ticked
                for bars in g.assets['min'].values():
                    try: # won't work if no bars
                        jj = bars.columns.get_loc('ticked')
                        bars.iloc[-1, jj] = True
                    except Exception as e: log.exception(e)

                # process trade update backlog
                log.info('Processing trade update backlog')
                process_all_trades()

                log.info('Waiting for bars')
        else:
            if marketIsOpen:
                marketIsOpen = False
                log.warning('Market is closed')

except BaseException as e:
    log.warning('Stopping active algos')
    for algo in allAlgos:
        if algo.active:
            log.info(f'\tStopping {algo.name}')
            algo.stop()

    log.exception(e)
    pass
