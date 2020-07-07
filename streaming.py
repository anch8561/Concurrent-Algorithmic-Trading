import g
from warn import warn

import asyncio
import pandas as pd

def save_bar(barType, data):
    # barType: 'secBars', 'minBars', or 'dayBars'
    # data: raw stream data

    # check arguments
    if barType not in ('secBars', 'minBars', 'dayBars'):
        warn(f'unknown barType "{barType}"')
        return

    # copy bars to g.assets (needs to be initialized first)
    df = pd.DataFrame({
        'open': data.open,
        'high': data.high,
        'low': data.low,
        'close': data.close,
        'volume': data.volume,
    }, index=[data.start])
    g.assets[data.symbol][barType] = \
        g.assets[data.symbol][barType].append(df)

def stream(conn, channels):
    @conn.on(r'A')
    async def on_second(conn, channel, data):
        save_bar('secBars', data)

    @conn.on(r'AM')
    async def on_minute(conn, channel, data):
        save_bar('minBars', data)

    @conn.on(r'account_updates')
    async def on_account_updates(conn, channel, data):
        print(data)

    @conn.on(r'trade_updates')
    async def handle_trade_update(conn, channel, data):
        try:
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

    conn.run(channels)
