import config as c
import globalVariables as g
from algos import intradayAlgos, overnightAlgos, multidayAlgos
from streaming import process_all_trades, compile_day_bars

from logging import getLogger

log = getLogger()

state = 'night'

def tick_algos():
    global state
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

    # set bars ticked
    for bars in g.assets['min'].values():
        try: # won't work if no bars
            jj = bars.columns.get_loc('ticked')
            bars.iloc[-1, jj] = True
        except Exception as e: log.exception(e)

    # process trade update backlog
    log.info('Processing trade update backlog')
    process_all_trades()
