import config as c
import globalVariables as g
import timing

import asyncio
from datetime import timedelta
from logging import getLogger
from pandas import DataFrame
from threading import Lock

log = getLogger('stream')

# buffers for when global resources are locked
barsBacklog = {'sec': [], 'min': []}
tradesBacklog = []
backlogLock = Lock()

def process_bar(barFreq, data, indicators):
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
        log.debug(f'New {data.symbol} bar:\n{newBar}')
    except Exception as e: log.exception(f'{e}\n{data}')
    
    try: # get indicators
        for indicator in indicators[barFreq]:
            jj = bars.columns.get_loc(indicator.name)
            bars.iloc[-1, jj] = indicator.get(bars)
    except Exception as e: log.exception(f'{e}\n{data}')
    
    try: # save bars
        g.assets[barFreq][data.symbol] = bars
        g.lastBarReceivedTime = timing.get_time()
    except Exception as e: log.exception(f'{e}\n{data}')

def compile_day_bars(indicators):
    log.warning('Compiling day bars')
    openTime = timing.get_market_open()
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
    # NOTE: ignore 'new', 'partial_fill', 'done_for_day', and 'replaced' events

    try: # get trade info
        event = data.event
        orderID = data.order['id']
        side = data.order['side']
        log.info(f'Order {orderID} {event}')
    except Exception as e: log.exception(f'{e}\n{data}')

    try: # get paper / live, algo, and enterExit
        if orderID in g.paperOrders:
            order = g.paperOrders[orderID]
            allOrders = g.paperOrders
            allPositions = g.paperPositions
        elif orderID in g.liveOrders:
            order = g.liveOrders[orderID]
            allOrders = g.liveOrders
            allPositions = g.livePositions
        else:
            log.warning(f'Unknown order id\n{data}')
            return
        algo = order['algo']
        enterExit = order['enterExit']
    except Exception as e: log.exception(f'{e}\n{data}')

    try: # process filled order
        if event == 'fill':
            # get symbol, fill qty, and price
            symbol = data.order['symbol']
            fillQty = int(data.order['filled_qty'])
            if side == 'sell': fillQty *= -1
            fillPrice = float(data.order['filled_avg_price'])

            # update positions
            for positions in (allPositions, algo.positions):
                # update basis
                oldQty = positions[symbol]['qty']
                if oldQty + fillQty == 0:
                    positions[symbol]['basis'] = 0
                else:
                    oldBasis = positions[symbol]['basis']
                    positions[symbol]['basis'] = \
                        ((oldQty * oldBasis) + (fillQty * fillPrice)) / (oldQty + fillQty)
                
                # update qty
                positions[symbol]['qty'] += fillQty
        
            # update buying power
            if enterExit == 'enter':
                longShort = 'long' if side == 'buy' else 'short'
                algo.buyPow[longShort] += abs(fillQty) * (order['limit'] - fillPrice)
            elif enterExit == 'exit':
                longShort = 'long' if side == 'sell' else 'short'
                algo.buyPow[longShort] += abs(fillQty) * fillPrice
            else: log.error(f'Unknown enterExit {enterExit}')
    except Exception as e: log.exception(f'{e}\n{data}')

    try: # process terminated order
        if event in ('canceled', 'expired', 'rejected'):
            if enterExit == 'enter':
                longShort = 'long' if side == 'buy' else 'short'
                algo.buyPow[longShort] += abs(order['qty']) * order['limit']
    except Exception as e: log.exception(f'{e}\n{data}')

    try: # remove completed order
        if event in ('fill', 'canceled', 'expired', 'rejected'):
            allOrders.pop(orderID)
            algo.orders.pop(orderID)
    except Exception as e: log.exception(f'{e}\n{data}')

def process_bars_backlog(indicators):
    # indicators: dict of lists of indicators (keys: 'sec', 'min', 'day', 'all')
    global barsBacklog
    for barFreq in ('sec', 'min'):
        for bar in barsBacklog[barFreq]:
            process_bar(barFreq, bar, indicators)
        barsBacklog[barFreq][:] = []

def process_trades_backlog():
    global tradesBacklog
    for trade in tradesBacklog:
        process_trade(trade)
    tradesBacklog[:] = []

def process_backlogs(indicators):
    backlogLock.acquire()
    process_bars_backlog(indicators)
    process_trades_backlog()
    backlogLock.release()

def stream(conn, allAlgos, indicators):
    # conn: alpaca_trade_api.StreamConn instance
    # allAlgos: list of all algos
    # indicators: dict of lists of indicators (keys: 'sec', 'min', 'day', 'all')

    channels = ['account_updates', 'trade_updates']
    for symbol in g.assets['min']:
        channels += [f'AM.{symbol}']
    
    async def acquire_thread_lock():
        await conn.loop.run_in_executor(None, g.lock.acquire())

    async def release_thread_lock():
        await conn.loop.run_in_executor(None, g.lock.release())

    async def acquire_backlog_lock():
        await conn.loop.run_in_executor(None, backlogLock.acquire())

    async def release_backlog_lock():
        await conn.loop.run_in_executor(None, backlogLock.release())

    # pylint: disable=unused-variable
    @conn.on('A')
    async def on_second(conn, channel, data):
        if g.lock.locked():
            acquire_backlog_lock()
            barsBacklog['sec'].append(data)
            release_backlog_lock()
        else:
            acquire_thread_lock()
            process_bar('sec', data, indicators)
            release_thread_lock()

    @conn.on('AM')
    async def on_minute(conn, channel, data):
        if g.lock.locked():
            acquire_backlog_lock()
            barsBacklog['min'].append(data)
            release_backlog_lock()
        else:
            acquire_thread_lock()
            process_bar('min', data, indicators)
            release_thread_lock()

    @conn.on('account_updates')
    async def on_account_update(conn, channel, data):
        log.warning(data)

    @conn.on('trade_updates')
    async def on_trade_update(conn, channel, data):
        if g.lock.locked():
            acquire_backlog_lock()
            tradesBacklog.append(data)
            release_backlog_lock()
        else:
            acquire_thread_lock()
            process_trade(data)
            release_thread_lock()

    log.warning(f'Streaming {len(channels)} channels')
    conn.run(channels)
