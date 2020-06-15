import asyncio, sys
import pandas as pd
from Algo import Algo
from alpacaAPI import conn, connPaper
from get_tradable_assets import get_tradable_assets
from marketHours import get_time, get_open_time, get_close_time
from warn import warn

def save_bar(barType, data):
    # barType: 'secBars', 'minBars', or 'dayBars'
    # data: raw stream data

    # check arguments
    if barType not in ('secBars', 'minBars', 'dayBars'):
        warn(f'barType "{barType}" not recognized')
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

def run():

    @conn.on(r'account_updates')
    async def on_account_updates(conn, channel, account):
        print(account)

    @conn.on(r'A')
    async def on_second(conn, channel, data):
        save_bar('secBars', data)

    @conn.on(r'AM')
    async def on_minute(conn, channel, data):
        save_bar('minBars', data)

    async def periodic():
        while True:
            if (
                get_time() < get_open_time() or
                get_time() > get_close_time()
            ):
                print(f'Market is closed')
                sys.exit(0) # FIX: closes program
            else:
                await asyncio.sleep(5)

    symbols = list(Algo.assets.keys())
    print("Tracking {} symbols.".format(len(symbols)))
    channels = ['account_updates']

    # Add symbols to minute data (AM) and second data (A) to subscribe to channels
    for symbol in symbols:
        channels += ['A.{}'.format(symbol) , 'AM.{}'.format(symbol)]

    loop = conn.loop
    loop.run_until_complete(asyncio.gather(
        conn.subscribe(channels),
        periodic()
    ))
    loop.close()
