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

def process_algo_trade(algoOrder, symbol, orderPrice, fillPrice):
    # unpack algo order
    algo = algoOrder['algo']
    longShort = algoOrder['longShort']
    algoQty = algoOrder['qty']

    # update algo position
    algo.positions[symbol] += algoQty

    # update algo buying power
    if (( # enter
        algoQty > 0 and
        longShort == 'long'
    ) or (
        algoQty < 0 and
        longShort == 'short'
    )):
        algo.buyPow[longShort] += abs(algoQty) * (orderPrice - fillPrice)
    else: # exit
        algo.buyPow[longShort] += abs(algoQty) * fillPrice

def process_trade(data):
    # NOTE: ignore 'new', 'partial_fill', 'done_for_day', and 'replaced' events

    try: # get trade info
        event = data.event
        orderID = data.order['id']
        side = data.order['side']
        fillQty = int(data.order['filled_qty'])
        if side == 'sell': fillQty *= -1
        fillPrice = float(data.order['filled_avg_price'])
        log.info(f'Order {orderID} {event}')
    except Exception as e:
        log.exception(f'{e}\n{data}')
        return

    if event in ('fill', 'canceled', 'expired', 'rejected'):
        try: # get order info
            order = g.orders[orderID]
            symbol = order['symbol']
            orderPrice = order['price']
            algoOrders = order['algoOrders']
        except:
            if orderID == 'internal':
                symbol = data.symbol
                orderPrice = data.price
                algoOrders = data.algoOrders
            else:
                log.warning(f'Unknown order id\n{data}')
                return

        try: # update global position
            g.positions[symbol] += fillQty
        except:
            log.exception(f'{e}\n{data}')
            return
            
        try: # add opposing trades to fill qty
            for algoOrder in algoOrders:
                algoQty = algoOrder['qty']
                if algoQty * fillQty < 0: # opposite side
                    fillQty -= algoQty # increase fill qty
                    process_algo_trade(algoOrder, symbol, orderPrice, fillPrice)
        except:
            log.exception(f'{e}\n{data}')
            return
            
        try: # process all trades
            for algoOrder in algoOrders:
                # process remaining trades
                algoQty = algoOrder['qty']
                if algoQty * fillQty > 0: # same side (and fillQty != 0)
                    if abs(algoQty) > abs(fillQty): # zero crossing
                        algoOrder['qty'] = fillQty
                        fillQty = 0
                    else:
                        fillQty -= algoQty
                    process_algo_trade(algoOrder, symbol, orderPrice, fillPrice)
                
                # remove algo orders
                algo = algoOrder['algo']
                longShort = algoOrder['longShort']
                algo.pendingOrders[longShort].pop(symbol)
        except Exception as e:
            log.exception(f'{e}\n{data}')
            return

        try: # remove order
            g.orders.pop(orderID)
        except Exception as e:
            if orderID != 'internal':
                log.exception(f'{e}\n{data}')
                return

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
    async def on_second(conn, channel, data):
        if g.lock.locked():
            await acquire_backlog_lock()
            barsBacklog['sec'].append(data)
            await release_backlog_lock()
        else:
            await acquire_thread_lock()
            process_bar('sec', data, indicators)
            await release_thread_lock()

    @conn.on('AM')
    async def on_minute(conn, channel, data):
        if g.lock.locked():
            await acquire_backlog_lock()
            barsBacklog['min'].append(data)
            await release_backlog_lock()
        else:
            await acquire_thread_lock()
            process_bar('min', data, indicators)
            await release_thread_lock()

    @conn.on('account_updates')
    async def on_account_update(conn, channel, data):
        log.warning(data)

    @conn.on('trade_updates')
    async def on_trade_update(conn, channel, data):
        if g.lock.locked():
            await acquire_backlog_lock()
            tradesBacklog.append(data)
            await release_backlog_lock()
        else:
            await acquire_thread_lock()
            process_trade(data)
            await release_thread_lock()

    log.warning(f'Streaming {len(channels)} channels')
    conn.run(channels)
