import asyncio, websocket, json, threading, requests, logging, nest_asyncio, sys 
import pandas as pd
from Algo import Algo
from alpacaAPI import alpaca, alpacaPaper, conn, connPaper
from update_assets import update_assets
from warn import warn
from time import sleep


update_assets(Algo)
symbols = list(Algo.assets.keys())[:10]


@conn.on(r'account_updates')
async def on_account_updates(conn, channel, account):
	print(f'{alpacaPaper.get_account()}')
	#symbol = data.order['symbol']
	
# @conn.on(r'^A$')
# async def on_second(conn, channel, data):
# 	Algo.secBars.append(data)
# 	#symbol = data.symbol
# 	#print(symbol)

@conn.on(r'AM')
async def on_minute(conn, channel, data):
	#logger.info(f'{data}')
	print(f'{data.symbol} Data: \n {data}')
	#if data.symbol in symbols:
	save_bars('minBars', data)


def save_bars(barType, data):
	# barType: 'secBars' or 'minBars'
	# data: raw stream data
	df = pd.DataFrame({
            'open': data.open,
            'high': data.high,
            'low': data.low,
            'close': data.close,
            'volume': data.volume,
        }, index=[data.start])
	# copy bars to Algo.assets
	Algo.minBars.append(df)
	print(f'Saving bar for {data.symbol}')
	print(f'{df}')
	print(f'-------------------------------------------------------------')
	print(f'{Algo.minBars}')
	# for bar in bars:
	# 	assets = Algo.assets[bar.symbol][barType] 
	# 	assets = assets.append(bar.df)
	# logger.info(f'received bar start = {bar.start}, close = {bar.close}, len(bars) = {len(symbols)}')




print("Tracking {} symbols.".format(len(symbols)))
channels = ['trade_updates','AM.SPY']

# Add symbols to minute data (AM) and second data (A) 
# for symbol in symbols:
# 	symbol_channels = ['AM.{}'.format(symbol)]
# 	#symbol_channels = ['A.{}'.format(symbol) , 'AM.{}'.format(symbol)]
# 	channels += symbol_channels

# Defining the loop for the threads
async def periodic():
	while True:
		if not alpacaPaper.get_clock().is_open:
			print(f'Market is not open.')
			sys.exit(0)
		#print(alpacaPaper.get_account())
		await asyncio.sleep(10)


loop = conn.loop
loop.run_until_complete(asyncio.gather(
	conn.subscribe(channels),
	periodic()
))
loop.close()







