import asyncio
import pandas as pd
from algoClasses import Algo
from warn import warn

def save_bar(barType, data):
    # barType: 'secBars', 'minBars', or 'dayBars'
    # data: raw stream data

    # check arguments
    if barType not in ('secBars', 'minBars', 'dayBars'):
        warn(f'unknown barType "{barType}"')
        return

    # copy bars to Algo.assets (needs to be initialized first)
    df = pd.DataFrame({
        'open': data.open,
        'high': data.high,
        'low': data.low,
        'close': data.close,
        'volume': data.volume,
    }, index=[data.start])
    Algo.assets[data.symbol][barType].append(df)

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

    @conn.on(r'trade_update')
    async def handle_trade_update(conn, channel, data):
        event = data.event
        orderID = data.order.id
    
        try:
            # paper / live
            if orderID in Algo.paperOrders:
                order = Algo.paperOrders[orderID]
                allOrders = Algo.paperOrders
                allPositions = Algo.paperPositions[data.symbol]
            elif orderID in Algo.liveOrders:
                order = Algo.liveOrders[orderID]
                allOrders = Algo.liveOrders
                allPositions = Algo.livePositions[data.symbol]
            else:
                print(f'Unknown order id: {orderID}')
            
            # check event 
            if event == 'fill':
                # get local data
                qty = order['qty']
                limit = order['limit']
                longShort = order['longShort']
                enterExit = order['enterExit']
                algo = order['algo']

                # get streamed data
                symbol = data.order.symbol
                fillQty = data.order.filled_qty
                if data.order.side == 'sell': fillQty *= -1
                fillPrice = data.order.filled_avg_price

                # update positions
                for positions in (allPositions, algo.positions):
                    oldBasis = positions[symbol]['basis']
                    oldQty = positions[symbol]['qty']
                    positions[symbol]['qty'] += fillQty
                    if positions[symbol]['qty'] == 0:
                        positions[symbol]['basis'] = 0
                    positions[symbol]['basis'] = ((oldBasis * oldQty) + (fillPrice * fillQty)) / (oldQty + fillQty)
                    # FIX: need FIFO

                # update buying power
                if enterExit == 'enter':
                    algo.buyPow[longShort] += abs(qty) * limit
                    algo.buyPow[longShort] -= abs(fillQty) * fillPrice
                elif enterExit == 'exit':
                    algo.buyPow[longShort] += abs(fillQty) * fillPrice

                # pop order
                allOrders.pop(orderID)
                algo.orders.pop(orderID)
            elif event in ('canceled', 'expired', 'rejected'):
                algo.cash += (data.order.price)*(data.order.qty)-(data.order.filled_avg_price)*(data.order.filled_qty)
                print(f'{orderID}: {event}')

        except:
            print(f'Invalid order id: {orderID}')

    async def periodic():
        while True:
            await asyncio.sleep(5)

    # start loop
    conn.loop.run_until_complete(asyncio.gather(
        conn.subscribe(channels),
        periodic()
    ))
    conn.loop.close()
