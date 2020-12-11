import config as c
import globalVariables as g
import timing
from tab import tab

import asyncio, functools
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
            'vwap': data.vwap,
            'ticked': False
        }, index=[data.start])
        bars = g.assets[barFreq][data.symbol].append(newBar)
        log.debug(f'New {data.symbol} bar:\n{newBar}')
    except Exception as e: log.exception(f'{e}\n{data}')
    
    try: # get indicators
        for indicator in indicators[barFreq]: # TODO: parallel
            jj = bars.columns.get_loc(indicator.name)
            bars.iloc[-1, jj] = indicator.get(bars)
    except Exception as e: log.exception(f'{e}\n{data}')
    
    try: # save bars
        g.assets[barFreq][data.symbol] = bars
        g.lastBarReceivedTime = timing.get_time()
    except Exception as e: log.exception(f'{e}\n{data}')

def compile_day_bars(indicators):
    # indicators: dict of lists of indicators; {sec, min, day, all}

    log.warning('Compiling day bars')
    openTime = timing.get_market_open()
    for ii, (symbol, minBars) in enumerate(g.assets['min'].items()):
        log.info(f'Compiling bar {ii+1} / {len(g.assets["min"])}\t{symbol}')
        minBars = minBars.loc[openTime:]

        try: # compile bar
            newDayBar = {}
            newDayBar['open'] = minBars.open[0]
            newDayBar['high'] = minBars.high.max()
            newDayBar['low'] = minBars.low.min()
            newDayBar['close'] = minBars.close[-1]
            newDayBar['volume'] = minBars.volume.sum()
            newDayBar['vwap'] = round((minBars.vwap * minBars.volume).sum() / newDayBar['volume'], 3)
            newDayBar['ticked'] = False
        except Exception as e: log.exception(e)

        try: # add bar to g.assets
            date = openTime.replace(hour=0, minute=0)
            newDayBar = DataFrame(newDayBar, index=[date])
            dayBars = g.assets['day'][symbol].append(newDayBar)
        except Exception as e: log.exception(e)
        
        try: # get indicators
            for indicator in indicators['day']: # TODO: parallel
                jj = dayBars.columns.get_loc(indicator.name)
                dayBars.iloc[-1, jj] = indicator.get(dayBars)
        except Exception as e: log.exception(e)
        
        try: # save bars
            g.assets['day'][symbol] = dayBars
        except Exception as e: log.exception(e)

def process_algo_trade(symbol, algo, fillQty, fillPrice):
    # symbol: e.g. 'AAPL'
    # algo: Algo object w/ pending order for symbol
    # fillQty: int; signed # of shares filled
    # fillPrice: float

    try: # get order
        order = algo.pendingOrders[symbol]
        algoQty = order['qty']
        algoPrice = order['price']
    except Exception as e: log.exception(e)

    try: # reduce fillQty to algoQty
        if (
            fillQty * algoQty < 0 or # opposite side
            abs(fillQty) > abs(algoQty) # fill
        ):
            fillQty = algoQty
    except Exception as e: log.exception(e)

    try: # update position
        oldQty = algo.positions[symbol]['qty']
        algo.positions[symbol]['qty'] += fillQty
    except Exception as e: log.exception(e)

    try: # update buying power and basis
        basis = algo.positions[symbol]['basis']
        if ( # enter
            algoQty > 0 and
            algo.longShort == 'long'
        ) or (
            algoQty < 0 and
            algo.longShort == 'short'
        ):
            # buying power
            algo.buyPow += abs(algoQty) * algoPrice - abs(fillQty) * fillPrice

            # basis
            if oldQty + fillQty: # avoid division by zero
                algo.positions[symbol]['basis'] = \
                    (abs(oldQty) * basis + abs(fillQty) * fillPrice) / abs(oldQty + fillQty)
            
        else: # exit
            # buying power
            algo.buyPow += abs(fillQty) * basis + fillQty * (basis - fillPrice)
            # long (unsigned qty): fillQty * fillPrice
            # short (unsigned qty): fillQty * (2 * basis - fillPrice)

            # basis
            if algo.positions[symbol]['qty'] == 0:
                algo.positions[symbol]['basis'] = 0
    except Exception as e: log.exception(e)
    
    algo.log.debug(tab(symbol, 6) + 'filled ' + tab(fillQty, 6) + '/ ' + tab(algoQty, 6) + f'@ {fillPrice}')

def process_trade(data):
    # NOTE: ignore 'new', 'partial_fill', 'done_for_day', and 'replaced' events

    event = data.event
    if event in ('fill', 'canceled', 'expired', 'rejected'):
        try: # get trade info
            orderID = data.order['id']
            symbol = data.order['symbol']
            side = data.order['side']
            fillQty = int(data.order['filled_qty'])
            if side == 'sell': fillQty *= -1
            if fillQty:
                fillPrice = float(data.order['filled_avg_price'])
            else:
                fillPrice = 0
            log.debug(f'Order {orderID} {event}\n' + \
                tab(symbol, 6) + tab(fillQty, 6) + f'@ {fillPrice}')
        except Exception as e:
            log.exception(f'{e}\n{data}')
            return

        try: # get order info
            algos = g.orders[orderID]['algos']
        except Exception as e:
            log.exception(e)
            return

        try: # update global position and remove order
            g.positions[symbol] += fillQty
            g.orders.pop(orderID)
        except Exception as e:
            log.exception(f'{e}\n{data}')

        for algo in algos:
            try: # process opposing algo trades
                algoQty = algo.pendingOrders[symbol]['qty']
                if algoQty * fillQty < 0: # opposite side
                    process_algo_trade(symbol, algo, fillQty, fillPrice)
                    fillQty -= algoQty # increase fill qty
            except Exception as e:
                log.exception(f'{e}\n{data}')

        for algo in algos:
            try: # process remaining algo trades
                algoQty = algo.pendingOrders[symbol]['qty']
                if algoQty * fillQty >= 0: # same side or zero
                    process_algo_trade(symbol, algo, fillQty, fillPrice)
                    if abs(algoQty) > abs(fillQty): # zero crossing
                        fillQty = 0
                    else:
                        fillQty -= algoQty
            except Exception as e:
                log.exception(f'{e}\n{data}')

        for algo in algos:
            try: # remove pending orders
                algo.pendingOrders.pop(symbol)
            except Exception as e:
                log.exception(f'{e}\n{data}')

def process_bars_backlog(indicators):
    # indicators: dict of lists of indicators; {sec, min, day, all}
    global barsBacklog
    for barFreq in ('sec', 'min'):
        for bar in barsBacklog[barFreq]:
            process_bar(barFreq, bar, indicators)
        barsBacklog[barFreq].clear()

def process_trades_backlog():
    global tradesBacklog
    for trade in tradesBacklog:
        process_trade(trade)
    tradesBacklog.clear()

def process_backlogs(indicators):
    backlogLock.acquire()
    process_bars_backlog(indicators)
    process_trades_backlog()
    backlogLock.release()

# TODO: move process_trade/bar to executors while ensuring threadlock
def stream(conn, allAlgos, indicators):
    # conn: alpaca_trade_api.StreamConn instance
    # allAlgos: list of all algos
    # indicators: dict of lists of indicators; {sec, min, day, all}

    channels = ['account_updates', 'trade_updates']
    for symbol in g.assets['min']:
        channels += [f'AM.{symbol}']
    
    async def acquire_thread_lock():
        await conn.loop.run_in_executor(None, g.lock.acquire)

    async def release_thread_lock():
        await conn.loop.run_in_executor(None, g.lock.release)

    async def acquire_backlog_lock():
        await conn.loop.run_in_executor(None, backlogLock.acquire)

    async def release_backlog_lock():
        await conn.loop.run_in_executor(None, backlogLock.release)

    # pylint: disable=unused-variable
    @conn.on('A')
    async def on_second(_conn, channel, data):
        if g.lock.locked():
            await acquire_backlog_lock()
            barsBacklog['sec'].append(data)
            await release_backlog_lock()
        else:
            await acquire_thread_lock()
            await conn.loop.run_in_executor(None, functools.partial(
                process_bar, 'sec', data, indicators))
            await release_thread_lock()

    @conn.on('AM')
    async def on_minute(_conn, channel, data):
        if g.lock.locked():
            await acquire_backlog_lock()
            barsBacklog['min'].append(data)
            await release_backlog_lock()
        else:
            await acquire_thread_lock()
            await conn.loop.run_in_executor(None, functools.partial(
                process_bar, 'min', data, indicators))
            await release_thread_lock()

    @conn.on('account_updates')
    async def on_account_update(_conn, channel, data):
        log.warning(data)

    @conn.on('trade_updates')
    async def on_trade_update(_conn, channel, data):
        if g.lock.locked():
            await acquire_backlog_lock()
            tradesBacklog.append(data)
            await release_backlog_lock()
        else:
            await acquire_thread_lock()
            await conn.loop.run_in_executor(None, process_trade, data)
            await release_thread_lock()

    log.warning(f'Streaming {len(channels)} channels')
    conn.run(channels)
