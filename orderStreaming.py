import asyncio, sys
import pandas as pd
from algoClasses import Algo
from alpacaAPI import conn, connPaper
from update_tradable_assets import update_tradable_assets
from marketHours import get_time, get_open_time, get_close_time
from warn import warn

def stream():
   
    @conn.on(r'trade_update')
    async def handle_trade_update(conn, channel, data):
        event = data.event
        id = data.order.id
    
        try:
            #set orders and positions to live or paper
            if id in Algo.liveOrders:
                orders = Algo.liveOrders
                positions = Algo.livePositions[data.symbol]
            elif id in Algo.paperOrders:
                orders = Algo.paperOrders
                positions = Algo.paperPositions[data.symbol]
            
            #check event 
            if event == 'fill':
                orders.pop(orderID)
                positions[orderID] = orderID
                algo.cash += (data.order.price)*(data.order.qty)-(data.order.filled_avg_price)*(data.order.filled_qty)
            elif event == 'partial_fill': #TODO: make sure this is the right equation for partial and expired
                algo.cash += (data.order.price)*(data.order.qty)-(data.order.filled_avg_price)*(data.order.filled_qty)
            elif event == 'expired':
                algo.cash += (data.order.price)*(data.order.qty)-(data.order.filled_avg_price)*(data.order.filled_qty)
            elif event == 'canceled' or event == 'rejected':
                print(f'Order canceled or rejected')
            else:
                warn(f'Unrecognized event')

        except:
            print(f'Invalid order id: {id}')


    async def periodic():
        while True:
            if (
                get_time() < get_open_time() or
                get_time() > get_close_time()
            ):
                print(f'Market is closed')
                sys.exit(0) # FIX: closes program
            else:
                loop.stop
                #await asyncio.sleep(5)

    channels = ['trade_update']


    loop = conn.loop
    loop.run_until_complete(asyncio.gather(
        conn.subscribe(channels),
        periodic()
    ))
    loop.close()

stream()