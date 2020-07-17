import config as c
import globalVariables as g
from algos import allAlgos
from indicators import indicators
from timing import get_time, get_market_open, get_time_str
from warn import warn

# import asyncio
from datetime import timedelta
from pandas import DataFrame

trades = []

def process_bar(barFreq, data):
    # barFreq: 'sec', 'min', or 'day'
    # data: raw stream data

    print(f'{get_time_str()}\t{data.symbol}\tNew bar\t{data.start}')

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
    except Exception as e: warn(e, data)
    
    try: # get indicators
        for indicator in indicators[barFreq]:
            jj = bars.columns.get_loc(indicator.name)
            bars.iloc[-1, jj] = indicator.get(bars)
    except Exception as e: warn(e, data)
    
    try: # save bars
        g.assets[barFreq][data.symbol] = bars
        g.lastBarProcessTime = get_time()
    except Exception as e: warn(e, data)

def compile_day_bars():
    print('Compiling day bars')
    openTime = get_market_open()
    for ii, (symbol, minBars) in enumerate(g.assets['min'].items()):
        print(f'Compiling bar {ii+1} / {len(g.assets["min"])}\t{symbol}')
        minBars = minBars.loc[openTime:]

        try: # compile bar
            newDayBar = {}
            newDayBar['open'] = minBars.open.iloc[0]
            newDayBar['high'] = minBars.high.max()
            newDayBar['low'] = minBars.low.min()
            newDayBar['close'] = minBars.close.iloc[-1]
            newDayBar['volume'] = minBars.volume.sum()
            newDayBar['ticked'] = False
        except Exception as e: warn(e)

        try: # add bar to g.assets
            date = openTime.replace(hour=0, minute=0)
            newDayBar = DataFrame(newDayBar, index=[date])
            dayBars = g.assets['day'][symbol].append(newDayBar)
        except Exception as e: warn(e)
        
        try: # get indicators
            for indicator in indicators['day']:
                jj = dayBars.columns.get_loc(indicator.name)
                dayBars.iloc[-1, jj] = indicator.get(dayBars)
        except Exception as e: warn(e)
        
        try: # save bars
            g.assets['day'][symbol] = dayBars
        except Exception as e: warn(e)

def process_trade(data):
    g.processingTrade = True
    # print('processingTrade = True')
    
    try: # get trade info
        event = data.event
        orderID = data.order['id']
        symbol = data.order['symbol']
    except Exception as e: warn(f'{e}', f'{data}')

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
            print(f'Unknown order id: {orderID} Event: {event}')
            return
    except Exception as e: warn(f'{e}', f'{data}')
        
    try: # get local data
        qty = order['qty']
        limit = order['limit']
        longShort = order['longShort']
        enterExit = order['enterExit']
        algo = order['algo']
    except Exception as e: warn(f'{e}', f'{data}')

    # check event
    if event == 'fill':
        try: # get streamed data
            fillQty = int(data.order['filled_qty'])
            if data.order['side'] == 'sell': fillQty *= -1
            fillPrice = float(data.order['filled_avg_price'])
        except Exception as e: warn(f'{e}', f'{data}')

        try: # update position basis
            for positions in (allPositions, algo.positions):
                oldQty = positions[symbol]['qty']
                if oldQty + fillQty == 0:
                    positions[symbol]['basis'] = 0
                else:
                    oldBasis = positions[symbol]['basis']
                    positions[symbol]['basis'] = \
                        ((oldBasis * oldQty) + (fillPrice * fillQty)) / (oldQty + fillQty)
        except Exception as e: warn(f'{e}\n{data}')
        
        try: # update position qty
            allPositions[symbol]['qty'] += fillQty
            algo.positions[symbol]['qty'] += fillQty
        except Exception as e: warn(f'{e}', f'{data}')

        try: # update buying power
            if enterExit == 'enter':
                algo.buyPow[longShort] += abs(qty) * limit
                algo.buyPow[longShort] -= abs(fillQty) * fillPrice
            elif enterExit == 'exit':
                algo.buyPow[longShort] += abs(fillQty) * fillPrice
        except Exception as e: warn(f'{e}', f'{data}')

        try: # pop order
            allOrders.pop(orderID)
            algo.orders.pop(orderID)
        except Exception as e: warn(f'{e}', f'{data}')
        
    elif event in ('canceled', 'expired', 'rejected'):
        print(f'{orderID}: {event}')

        try: # update buying power
            if enterExit == 'enter':
                algo.buyPow[longShort] += abs(qty) * limit
                algo.buyPow[longShort] -= abs(fillQty) * fillPrice
            elif enterExit == 'exit':
                algo.buyPow[longShort] += abs(fillQty) * fillPrice
        except Exception as e: warn(f'{e}', f'{data}')

        try: # pop order
            allOrders.pop(orderID)
            algo.orders.pop(orderID)
        except Exception as e: warn(f'{e}', f'{data}')

    g.processingTrade = False
    # print('processingTrade = False')

def process_all_trades():
    for trade in trades:
        process_trade(trade)

def stream(conn, channels):
    async def on_second(conn, channel, data):
        process_bar('sec', data)
    conn.register('A', on_second)

    async def on_minute(conn, channel, data):
        process_bar('min', data)
    conn.register(r'^AM$', on_minute)

    async def on_account_update(conn, channel, data):
        print(f'{data}')
    conn.register('account_updates', on_account_update)

    async def on_trade_update(conn, channel, data):
        if any(algo.ticking for algo in allAlgos):
            trades.append(data)
        else:
            process_trade(data)
    conn.register('trade_updates', on_trade_update)

    print(f'Streaming {len(channels)} channels')
    conn.run(channels)
