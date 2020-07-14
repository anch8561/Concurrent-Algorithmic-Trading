import g
from indicators import indicators
from warn import warn

import asyncio
import pandas as pd

trades = []

def process_bar(barFreq, data):
    # barFreq: 'sec', 'min', or 'day'
    # data: raw stream data

    # add bar to g.assets (needs to be initialized first)
    newBar = pd.DataFrame({
        'open': data.open,
        'high': data.high,
        'low': data.low,
        'close': data.close,
        'volume': data.volume,
        'processed': False
    }, index=[data.start])
    g.assets[data.symbol][barFreq] = \
        g.assets[data.symbol][barFreq].append(newBar)
    
    # get indicators
    for indicator in indicators[barFreq]:
        g.assets[data.symbol][barFreq][indicator.name][-1] = \
            indicator.get(g.assets[data.symbol][barFreq])

def process_trade(data):
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
            print(f'Unknown order id: {orderID}')
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
        except Exception as e: warn(f'{e}\n{data}\n{data}')
        
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

def process_all_trades():
    for trade in trades:
        process_trade(trade)

def stream(conn, channels):
    async def on_second(conn, channel, data):
        process_bar('sec', data)
    conn.register('A', on_second)

    async def on_minute(conn, channel, data):
        process_bar('min', data)
    conn.register('AM', on_minute)

    async def on_account_update(conn, channel, data):
        print(f'{data}')
    conn.register('account_updates', on_account_update)

    async def on_trade_update(conn, channel, data):
        if g.tickingAlgos: trades.append(data)
        else: process_trade(data)
    conn.register('trade_updates', on_trade_update)

    print(f'Streaming {len(channels)} channels')
    conn.run(channels)
