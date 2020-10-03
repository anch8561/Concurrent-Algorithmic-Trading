import config as c
import globalVariables as g
import streaming


import random
from logging import getLogger

log = getLogger('main')

def set_order_qty(newQty,combinedOrder):
    # TODO: unit test (random seed)
    # newQty: int
    # combinedOrder: dict; {symbol: str, qty: int, algos: list}
    # returns: bool; success
    
    # unpack order
    symbol = combinedOrder['symbol']
    oldQty = combinedOrder['qty']
    algos = combinedOrder['algos'].copy()
    random.shuffle(algos)

    # check newQty
    if (
        newQty * oldQty < 0 or # opposite signs
        abs(oldQty) < abs(newQty) # zero crossing
    ):
        log.error(f'Cannot change combined order qty to {newQty}\n' +
            f'{symbol}: {combinedOrder}')
        return False

    # reduce random order qty until combined order qty == newQty
    delta = newQty - oldQty
    for algo in algos:
        algoQty = algo.orders[symbol]['qty']
        if algoQty * delta < 0: # opposite signs
            if abs(algoQty) < abs(delta): # zero crossing
                algo.orders[symbol]['qty'] = 0
                delta += algoQty
            else:
                algo.orders[symbol]['qty'] += delta
                combinedOrder['qty'] = newQty
                return True
    
    # TODO: update algo.buyPow
    # TODO: tick assets in order of volatility? (better use of BP but must use OrderedDict)

def submit_order(order):
    # order: dict; {symbol
    orderQty = order['qty']

    # get limit price
    price = get_limit_price(symbol, side)


def process_queued_orders(algos):
    # TODO: sec and min
    barFreq = 'min'

    # combine orders
    globalOrderQueue = {}
    for algo in algos:
        for algoOrder in algo.orderQueue:
            symbol = algoOrder['symbol']
            if symbol in globalOrderQueue:
                globalOrderQueue[symbol]['qty'] += algoOrder['qty']
                globalOrderQueue[symbol]['algos'].append(algo)
            else:
                globalOrderQueue[symbol] = {
                    'symbol': symbol,
                    'qty': algoOrder['qty'],
                    'algos': [algo]}

    # check order qty
    cancelledOrders = []
    for symbol, order in globalOrderQueue:
        orderQty = order['qty']
        positionQty = g.positions[symbol]['qty']

        try: # check for volume limit
            volumeLimit = g.assets[barFreq][symbol].volume[-1] * c.volumeLimitMult
            if abs(orderQty) > volumeLimit:
                log.debug(f'{symbol}\tReducing order qty from {orderQty} to {volumeLimit} (volume limit)')
                orderQty = volumeLimit
        except Exception as e:
            log.exception(e)
            continue

        try: # check for zero crossing
            if (positionQty + orderQty) * positionQty < 0: # zero crossing
                log.debug(f'{symbol}\tReducing order qty from {orderQty} to {-positionQty} (zero crossing)')
                orderQty = -positionQty
        except Exception as e:
            log.exception(e)
            continue
            
        try: # check for opposing short
            if ( # buying from zero position
                orderQty > 0 and
                positionQty == 0
            ):
                for pendingOrderID, pendingOrder in g.orders.items():
                    if ( # pending short
                        pendingOrder['symbol'] == symbol and
                        pendingOrder['qty'] < 0
                    ):
                        log.debug(f'{algo.name}\t{symbol}\n' +
                            f'Reducing order qty from {orderQty} to 0 (pending short {pendingOrderID})')
                        orderQty = 0
        except Exception as e:
            log.exception(e)
            continue

        # update orders
        set_order_qty(orderQty, order)

        # submit orders
        if orderQty == 0:
            cancelledOrders.append(symbol)
        else:
            submit_order(order)
       
        
    
    # remove cancelled orders
    for symbol in cancelledOrders:
        globalOrderQueue.pop(symbol)
        # TODO: process algo trades
        # TODO: check that real trades work with circular (algo to algo) trades
        

def tick_algos(algos, indicators, state):
    g.lock.acquire()
    closingSoon = g.TTClose <= c.marketCloseTransitionPeriod

    # tick algos
    try:
        if state == 'night' and not closingSoon:
            log.warning('Deactivating overnight algos')
            for algo in algos['overnight']: algo.deactivate()
            
            if any(algo.active for algo in algos['overnight']):
                log.info('Some overnight algos are still active')
            else:
                log.info('All overnight algos are deactivated')
                log.warning('Activating intraday algos')
                for algo in algos['intraday']: algo.activate()
                state = 'day'

        elif state == 'day' and not closingSoon:
            log.info('Ticking intraday algos')
            for algo in algos['intraday']: algo.tick() # TODO: parallel

        elif state == 'day' and closingSoon:
            log.warning('Deactivating intraday algos')
            for algo in algos['intraday']: algo.deactivate()
            
            if any(algo.active for algo in algos['intraday']):
                log.info('Some intraday algos are still active')
            else:
                log.info('All intraday algos are deactivated')
                log.warning('Activating overnight algos')
                for algo in algos['overnight']: algo.activate()
                state = 'night'
                streaming.compile_day_bars(indicators)

        elif state == 'night' and closingSoon:
            log.info('Ticking overnight algos')
            for algo in algos['overnight']: algo.tick() # TODO: parallel
        
        
        log.info('Ticking multiday algos')
        for algo in algos['multiday']: algo.tick() # TODO: parallel
    except Exception as e: log.exception(e)

    # set bars ticked
    for bars in g.assets['min'].values():
        try: # won't work if no bars
            jj = bars.columns.get_loc('ticked')
            bars.iloc[-1, jj] = True
        except Exception as e: log.exception(e)

    # process stream backlog
    log.info('Processing stream backlog')
    streaming.process_backlogs(indicators)

    # exit
    g.lock.release()
    return state
