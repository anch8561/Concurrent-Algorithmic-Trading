import config as c
import globalVariables as g
from algos import allAlgos
from indicators import indicators
from timing import get_time, get_market_open, get_time_str

from datetime import timedelta
from logging import getLogger
from pandas import DataFrame

log = getLogger('stream')
trades = []

def process_bar(barFreq, data):
    # barFreq: 'sec', 'min', or 'day'
    # data: raw stream data

    try: # add bar to g.assets (needs to be initialized first)
        newBar = DataFrame({
            'open': data.open,
            'high': data.high,
            'low': data.low,
            'close': data.close,
            'volume': data.volume,
            'ticked': False
        }, index=[data.start])
        bars = g.assets[barFreq][data.symbol].append(newBar)
        log.debug(newBar)
    except Exception as e: log.exception(e, extra=data)
    
    try: # get indicators
        for indicator in indicators[barFreq]:
            jj = bars.columns.get_loc(indicator.name)
            bars.iloc[-1, jj] = indicator.get(bars)
    except Exception as e: log.exception(e, extra=data)
    
    try: # save bars
        g.assets[barFreq][data.symbol] = bars
        g.lastBarReceivedTime = get_time()
    except Exception as e: log.exception(e, extra=data)

def compile_day_bars():
    log.warning('Compiling day bars')
    openTime = get_market_open()
    for ii, (symbol, minBars) in enumerate(g.assets['min'].items()):
        log.info(f'Compiling bar {ii+1} / {len(g.assets["min"])}\t{symbol}')
        minBars = minBars.loc[openTime:]

        try: # compile bar
            newDayBar = {}
            newDayBar['open'] = minBars.open.iloc[0]
            newDayBar['high'] = minBars.high.max()
            newDayBar['low'] = minBars.low.min()
            newDayBar['close'] = minBars.close.iloc[-1]
            newDayBar['volume'] = minBars.volume.sum()
            newDayBar['ticked'] = False
        except Exception as e: log.exception(e)

        try: # add bar to g.assets
            date = openTime.replace(hour=0, minute=0)
            newDayBar = DataFrame(newDayBar, index=[date])
            dayBars = g.assets['day'][symbol].append(newDayBar)
        except Exception as e: log.exception(e)
        
        try: # get indicators
            for indicator in indicators['day']:
                jj = dayBars.columns.get_loc(indicator.name)
                dayBars.iloc[-1, jj] = indicator.get(dayBars)
        except Exception as e: log.exception(e)
        
        try: # save bars
            g.assets['day'][symbol] = dayBars
        except Exception as e: log.exception(e)

def process_trade(data):
    g.processingTrade = True
    # log.debug('processingTrade = True')
    
    try: # get trade info
        event = data.event
        orderID = data.order['id']
        symbol = data.order['symbol']
        side = data.order['side']
        qty = int(data.order['qty'])
        fillQty = int(data.order['filled_qty'])
        try: limit = float(data.order['limit_price'])
        except Exception as e:
            if 'limit_price' not in data.order: limit = None
            else: log.exception(e)
    except Exception as e: log.exception(e, extra=data)

    try: # paper / live
        if orderID in g.paperOrders:
            order = g.paperOrders[orderID]
            allOrders = g.paperOrders
            allPositions = g.paperPositions
        elif orderID in g.liveOrders:
            order = g.liveOrders[orderID]
            allOrders = g.liveOrders
            allPositions = g.livePositions
        else:
            log.warning('Unknown order id', extra=data)
            return
    except Exception as e: log.exception(e, extra=data)
        
    try: # get local data
        longShort = order['longShort']
        enterExit = order['enterExit']
        algo = order['algo']
    except Exception as e: log.exception(e, extra=data)

    # check event
    if event == 'fill':
        try: # get streamed data
            if side == 'sell': fillQty *= -1
            fillPrice = float(data.order['filled_avg_price'])
        except Exception as e: log.exception(e, extra=data)

        try: # update position basis
            for positions in (allPositions, algo.positions):
                oldQty = positions[symbol]['qty']
                if oldQty + fillQty == 0:
                    positions[symbol]['basis'] = 0
                else:
                    oldBasis = positions[symbol]['basis']
                    positions[symbol]['basis'] = \
                        ((oldBasis * oldQty) + (fillPrice * fillQty)) / (oldQty + fillQty)
        except Exception as e: log.exception(e, extra=data)
        
        try: # update position qty
            allPositions[symbol]['qty'] += fillQty
            algo.positions[symbol]['qty'] += fillQty
        except Exception as e: log.exception(e, extra=data)

        try: # update buying power
            if enterExit == 'enter':
                algo.buyPow[longShort] -= abs(fillQty) * fillPrice
                algo.buyPow[longShort] += abs(qty) * limit
            elif enterExit == 'exit':
                algo.buyPow[longShort] += abs(fillQty) * fillPrice
        except Exception as e: log.exception(e, extra=data)

        try: # pop order
            allOrders.pop(orderID)
            algo.orders.pop(orderID)
        except Exception as e: log.exception(e, extra=data)
        
    elif event in ('canceled', 'expired', 'rejected'):
        log.info(f'{orderID}: {event}')

        try: # update buying power
            if enterExit == 'enter':
                algo.buyPow[longShort] -= abs(fillQty) * fillPrice
                algo.buyPow[longShort] += abs(qty) * limit
            elif enterExit == 'exit':
                algo.buyPow[longShort] += abs(fillQty) * fillPrice
        except Exception as e: log.exception(e, extra=data)

        try: # pop order
            allOrders.pop(orderID)
            algo.orders.pop(orderID)
        except Exception as e: log.exception(e, extra=data)

    g.processingTrade = False
    # log.debug('processingTrade = False')

def process_all_trades():
    global trades
    for trade in trades:
        process_trade(trade)
    trades = []

def stream(conn, channels):
    async def on_second(conn, channel, data):
        process_bar('sec', data)
    conn.register('A', on_second)

    async def on_minute(conn, channel, data):
        process_bar('min', data)
    conn.register(r'^AM$', on_minute)

    async def on_account_update(conn, channel, data):
        log.warning(data)
    conn.register('account_updates', on_account_update)

    async def on_trade_update(conn, channel, data):
        if any(algo.ticking for algo in allAlgos):
            trades.append(data)
        else:
            process_trade(data)
    conn.register('trade_updates', on_trade_update)

    log.warning(f'Streaming {len(channels)} channels')
    conn.run(channels)
