import asyncio, sys
import pandas as pd
from algoClasses import Algo
from alpacaAPI import conn, connPaper
from marketHours import get_time, get_open_time, get_close_time
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

def stream():
    @conn.on(r'A')
    async def on_second(conn, channel, data):
        save_bar('secBars', data)

    @conn.on(r'AM')
    async def on_minute(conn, channel, data):
        save_bar('minBars', data)

    @conn.on(r'account_updates')
    async def on_account_updates(conn, channel, account):
        print(account)

    @conn.on(r'trade_update')
    async def handle_trade_update(conn, channel, data):
        event = data.event
        orderID = data.order.id
    
        try:
            # set orders and positions to live or paper
            if orderID in Algo.liveOrders:
                orders = Algo.liveOrders
                positions = Algo.livePositions[data.symbol]
            elif orderID in Algo.paperOrders:
                orders = Algo.paperOrders
                positions = Algo.paperPositions[data.symbol]
            else:
                print(f'Unknown order id: {orderID}')
            #TODO: Fix algo.cash
            #check event 
            if event == 'fill':
                positions[orderID] = orderID
                algo.cash += data.order.price * data.order.qty - data.order.filled_avg_price * data.order.filled_qty
                orders.pop(orderID)
            elif event == 'partial_fill': #TODO: make sure this is the right equation for partial and expired
                algo.cash += (data.order.price)*(data.order.qty) - (data.order.filled_avg_price)*(data.order.filled_qty)
            elif event == 'expired':
                algo.cash += (data.order.price)*(data.order.qty)-(data.order.filled_avg_price)*(data.order.filled_qty)
            elif event == 'canceled' or event == 'rejected':
                print(f'Order canceled or rejected')
            else:
                warn(f'Unknown event: {event}')

        except:
            print(f'Invalid order id: {orderID}')

    async def periodic():
        while True:
            await asyncio.sleep(5)

    symbols = list(Algo.assets.keys())
    print("Tracking {} symbols.".format(len(symbols)))
    channels = ['account_updates', 'trade_update']

    # subscribe to channels
    for symbol in symbols:
        channels += ['A.{}'.format(symbol) , 'AM.{}'.format(symbol)]

    loop = conn.loop
    loop.run_until_complete(asyncio.gather(
        conn.subscribe(channels),
        periodic()
    ))
    loop.close()
