import config as c
import globalVariables as g
import streaming
from tab import tab

import random
from logging import getLogger

log = getLogger('main')

# TODO: tick assets in order of volatility? (better use of BP but must use OrderedDict)

def set_order_qty(newQty, combinedOrder):
    # TODO: unit test (random seed)
    # newQty: int
    # combinedOrder: dict; {symbol, qty, price, algos}
    # returns: bool; success
    
    # unpack combined order
    symbol = combinedOrder['symbol']
    oldQty = combinedOrder['qty']
    price = combinedOrder['price']
    algos = combinedOrder['algos']

    # check newQty
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
                algo.buyPow += qty * price
            
            # cancel / reduce algo order
            if abs(algoQty) <= abs(delta): # zero crossing
                canceledAlgos.append(algoOrder) # cancel order
                delta += algoQty # reduce delta
            else:
                algoOrder += delta # reduce algo order
                combinedOrder['qty'] = newQty # update combined order
                break
    
    # remove canceled algos
    for algo in canceledAlgos:
        algos.pop(algo)

def get_price(symbol):
    # symbol: e.g. 'AAPL'

    try:
        return g.assets['min'][symbol].close[-1]
    except Exception as e:
        if (
            symbol in g.assets['min'] and # ignore missing key (old asset)
            len(g.assets['min'][symbol].index) # ignore empty dataframe (startup)
        ):
            log.exception(e, stack_info=True)
        else:
            log.debug(e)

def get_limit_price(symbol, side):
    # symbol: e.g. 'AAPL'
    # side: 'buy' or 'sell'
    
    try:
        price = get_price(symbol)
        if side == 'buy':
            return price * (1 + c.limitPriceFrac)
        elif side == 'sell':
            return price * (1 - c.limitPriceFrac)
        else:
            log.error(f'Unknown side: {side}')
    except Exception as e:
        if price == None: log.debug(e)
        else: log.exception(e, stack_info=True)
    
def submit_order(combinedOrder):
    # combinedOrder: dict; {symbol, qty, price, algos}

    # unpack combined order
    symbol = combinedOrder['symbol']
    orderQty = combinedOrder['qty']
    price = combinedOrder['price']
    algos = combinedOrder['algos']

    # log message
    positionQty = g.positions[symbol]
    logMsg = tab(symbol, 6) + 'Have ' + tab(positionQty, 6) + \
        'Ordering ' + tab(orderQty, 6) + f'@ {price}'
    for algo in algos:
        algoOrderQty = algo.queuedOrders[symbol]
        algoPositionQty = algo.positions[symbol]['qty']
        logMsg += tab(algo.name, 30) + 'Have ' + tab(algoPositionQty, 6) + \
            'Ordering ' + tab(algoOrderQty, 6)
    log.info(logMsg)

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
    for algo in algos:
        algo.pendingOrders[symbol] = algo.queuedOrders[symbol]

class TradeData: # for combinedOrders w/ zero qty
    def __init__(self, combinedOrder):
        # combinedOrder: dict; {symbol, qty, price, algoOrders}
        self.event = 'fill'
        self.order = {
            'id': 'internal',
            'side': 'buy', # zero
            'fillQty': 0}
        self.symbol = combinedOrder['symbol']
        self.price = combinedOrder['price']
        self.algoOrders = combinedOrder['algoOrders']

def process_queued_orders(allAlgos):
    # allAlgos: list of all algos

    log.info('Processing queued orders')

    # combine orders
    combinedOrders = {}
    for algo in allAlgos:
        for symbol, qty in algo.queuedOrders.items():
            if symbol in combinedOrders:
                combinedOrders[symbol]['qty'] += qty
                combinedOrders[symbol]['algos'].append(algo)
            else:
                combinedOrders[symbol] = {
                    'symbol': symbol,
                    'qty': qty,
                    'price': None, # don't know side yet
                    'algos': [algo]}

    # check for zero crossings
    for symbol, order in combinedOrders:
        try:
            orderQty = order['qty']
            positionQty = g.positions[symbol]
            if (positionQty + orderQty) * positionQty < 0: # zero crossing
                log.debug(f'{symbol}\tReducing order qty from {orderQty} to {-positionQty} (zero crossing)')
                orderQty = -positionQty
                # TODO: create follow-up order
        except Exception as e:
            log.exception(e)
            continue

        try: # update algo orders and submit
            if orderQty: # send to alpaca
                side = 'buy' if orderQty > 0 else 'sell'
                order['price'] = get_limit_price(symbol, side)
                random.shuffle(order['algos']) # for qty adjustments and partial fills
                set_order_qty(orderQty, order)
                submit_order(order)
            else: # process internally
                order['price'] = get_price(symbol)
                if order['price'] == None:
                    order['price'] = g.alpaca.get_last_trade(symbol).price
                streaming.process_trade(TradeData(order))
        except Exception as e:
            log.exception(e)
            continue

    # clear combinedOrders and queuedOrders
    combinedOrders.clear()
    for algo in allAlgos:
        algo.queuedOrders.clear()

def tick_algos(algos, indicators, state):
    # algos: dict of lists of algos; {intraday, overnight, multiday, all}
    # indicators: dict of lists of indicators; {sec, min, day, all}
    # state: str; 'day' or 'night'
    # returns: state

    g.lock.acquire()
    g.alpaca.cancel_all_orders()
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
