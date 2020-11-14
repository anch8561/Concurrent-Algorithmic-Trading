import config as c
import globalVariables as g
import streaming
from tab import tab

import random
from logging import getLogger
from threading import Thread

log = getLogger('main')

# TODO: tick assets in order of volatility? (better use of BP but must use OrderedDict)

def update_algo_orders(combinedOrder):
    # combinedOrder: dict; {symbol, qty, price, algos}
    
    # unpack combined order
    symbol = combinedOrder['symbol']
    newQty = combinedOrder['qty']
    algos = combinedOrder['algos']

    # check newQty
    oldQty = sum([algo.queuedOrders[symbol]['qty'] for algo in algos])
    if newQty == oldQty: return
    elif (
        newQty * oldQty < 0 or # opposite signs
        abs(oldQty) < abs(newQty) # zero crossing
    ):
        log.error(f'Cannot change combined order qty to {newQty}\n{combinedOrder}')
        return

    # reduce random algo orders until combined qty == newQty
    delta = newQty - oldQty
    canceledAlgos = []
    for algo in algos:
        algoOrder = algo.queuedOrders[symbol]
        algoQty = algoOrder['qty']
        if algoQty * delta < 0: # opposite signs (can reduce algo order)
            # restore buying power
            if ( # enter
                algoQty > 0 and
                algo.longShort == 'long'
            ) or (
                algoQty < 0 and
                algo.longShort == 'short'
            ):
                qty = min(abs(delta), abs(algoQty))
                algo.buyPow += qty * algoOrder['price']
            
            # cancel / reduce algo order
            if abs(algoQty) <= abs(delta): # zero crossing
                canceledAlgos.append(algo) # cancel order
                delta += algoQty # reduce delta
            else:
                algoOrder['qty'] += delta # reduce algo order
                combinedOrder['qty'] = newQty # update combined order
                break
    
    # remove canceled algos
    for algo in canceledAlgos:
        algos.remove(algo)

def get_price(symbol):
    # symbol: e.g. 'AAPL'

    try:
        return g.assets['min'][symbol].close[-1]
    except Exception as e:
        if symbol in g.assets['min']:
            log.exception(e, stack_info=True)
        else:
            log.debug(e, stack_info=True)

def get_limit_price(symbol, side):
    # symbol: e.g. 'AAPL'
    # side: 'buy' or 'sell'
    
    try:
        price = get_price(symbol)
        if side == 'buy':
            price *= (1 + c.limitPriceFrac)
        elif side == 'sell':
            price *= (1 - c.limitPriceFrac)
        else:
            log.error(f'Unknown side: {side}')
        return round(price, 2)
    except Exception as e:
        if price == None:
            log.debug(e, stack_info=True)
        else:
            log.exception(e, stack_info=True)
    
def submit_order(combinedOrder):
    # combinedOrder: dict; {symbol, qty, price, algos}

    # unpack combined order
    symbol = combinedOrder['symbol']
    orderQty = combinedOrder['qty']
    price = combinedOrder['price']
    algos = combinedOrder['algos']

    # submit order
    side = 'buy' if orderQty > 0 else 'sell'
    if price == None:
        order = g.alpaca.submit_order(
            symbol = symbol,
            qty = abs(orderQty),
            side = side,
            type = 'market',
            time_in_force = 'day')
    else:
        order = g.alpaca.submit_order(
            symbol = symbol,
            qty = abs(orderQty),
            side = side,
            type = 'limit',
            time_in_force = 'day',
            limit_price = price)

    # add to orders list
    g.orders[order.id] = {
        'symbol': symbol,
        'qty': orderQty,
        'price': price,
        'algos': algos}

    # log message
    positionQty = g.positions[symbol]
    logMsg = f'Order: {order.id}\n' + \
        'Symbol: ' + tab(symbol, 6) + 'Have: ' + tab(positionQty, 6) + \
        'Ordering: ' + tab(orderQty, 6) + f'@ {price}\n'
    for algo in algos:
        algoOrderQty = algo.queuedOrders[symbol]['qty']
        algoOrderPrice = algo.queuedOrders[symbol]['price']
        algoPositionQty = algo.positions[symbol]['qty']
        logMsg += tab(algo.name, 40) + 'Have: ' + tab(algoPositionQty, 6) + \
            'Ordering: ' + tab(algoOrderQty, 6) + f'@ {algoOrderPrice}\n'
    log.debug(logMsg)

class TradeData: # for combinedOrders w/ zero qty
    def __init__(self, combinedOrder):
        # combinedOrder: dict; {symbol, qty, price, algoOrders}

        g.orders['internal'] = {
            'symbol': combinedOrder['symbol'], # unused
            'qty': combinedOrder['qty'], # unused
            'price': combinedOrder['price'], # unused
            'algos': combinedOrder['algos']}

        self.event = 'fill'
        self.order = {
            'id': 'internal',
            'symbol': combinedOrder['symbol'],
            'side': 'buy', # zero
            'filled_avg_price': combinedOrder['price'],
            'filled_qty': 0}
        self.algos = combinedOrder['algos']

def process_queued_orders(allAlgos):
    # allAlgos: list of all algos

    log.info('Processing queued orders')

    # combine orders
    combinedOrders = {}
    for algo in allAlgos:
        for symbol, order in algo.queuedOrders.items():
            if symbol in combinedOrders:
                combinedOrders[symbol]['qty'] += order['qty']
                combinedOrders[symbol]['algos'].append(algo)
            else:
                combinedOrders[symbol] = {
                    'symbol': symbol,
                    'qty': order['qty'],
                    'price': None, # don't know side yet
                    'algos': [algo]}

    # submit orders
    threads = []
    for symbol, order in combinedOrders.items():
        try: # check for zero crossings
            positionQty = g.positions[symbol]
            if (positionQty + order['qty']) * positionQty < 0: # zero crossing
                log.debug(f"{symbol}\tReducing order qty from {order['qty']} to {-positionQty} (zero crossing)")
                order['qty'] = -positionQty
                # TODO: create follow-up order
        except Exception as e:
            log.exception(e)
            continue

        try: # update algos
            random.shuffle(order['algos']) # shuffle algos for qty adjustments and partial fills
            update_algo_orders(order) # adjust algo order qty to match combined order qty
            for algo in order['algos']: # add pending orders
                algo.pendingOrders[symbol] = algo.queuedOrders[symbol]
        except Exception as e:
            log.exception(e)
            continue
    
        try: # get price and submit
            if order['qty']: # send to alpaca
                side = 'buy' if order['qty'] > 0 else 'sell'
                order['price'] = get_limit_price(symbol, side)
                threads.append(Thread(target=submit_order, args=[order])) # submit order in new thread
            else: # process internally
                order['price'] = get_price(symbol)
                if order['price'] == None:
                    order['price'] = g.alpaca.get_last_trade(symbol).price
                streaming.process_trade(TradeData(order))
        except Exception as e:
            log.exception(e)
            continue
    for thread in threads: thread.start()
    for thread in threads: thread.join()

    # clear queuedOrders
    for algo in allAlgos:
        algo.queuedOrders.clear()

def tick_algos(algos, indicators, state):
    # algos: dict of lists of algos; {day, night, all}
    # indicators: dict of lists of indicators; {sec, min, day, all}
    # state: str; 'day' or 'night'
    # returns: state

    # TODO: allow night algos to wait for best price
    # TODO: allow internal trades during transitions

    g.lock.acquire()
    g.alpaca.cancel_all_orders()
    closingSoon = g.TTClose <= c.marketCloseTransitionPeriod

    # tick algos
    try:
        if (
            state == 'day' and
            not closingSoon
        ) or (
            state == 'night' and
            closingSoon
        ):
            log.info(f'Ticking {state} algos')
            for algo in algos[state]: algo.tick() # TODO: parallel
        
        elif (
            state == 'day' and
            closingSoon
        ) or (
            state == 'night' and
            not closingSoon
        ):
            log.warning(f'Deactivating {state} algos')
            for algo in algos[state]:
                if algo.active: algo.deactivate()
            
            if any(algo.active for algo in algos[state]):
                log.info(f'Some {state} algos are still active')
                # TODO: partial handoff in case algo can't deactivate
            else:
                log.info(f'All {state} algos are deactivated')
                state = 'night' if state == 'day' else 'day' # swap state
                log.warning(f'Activating {state} algos')
                for algo in algos[state]: algo.activate()
                if state == 'night':
                    streaming.compile_day_bars(indicators)

        process_queued_orders(algos['all'])
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
