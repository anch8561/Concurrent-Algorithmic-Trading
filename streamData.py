import asyncio, websocket, json, threading, requests, logging, nest_asyncio, sys 
import pandas as pd
from Algo import Algo
from alpacaAPI import alpaca, alpacaPaper, conn, connPaper
from update_assets import update_assets
from warn import warn
from time import sleep

#nest_asyncio.apply()
update_assets(Algo)

symbols = list(Algo.assets.keys())[:10]
logger = logging.getLogger()

fmt = '%(asctime)s:%(filename)s:%(lineno)d:%(levelname)s:%(name)s:%(message)s'
logging.basicConfig(level=logging.INFO, format=fmt)
fh = logging.FileHandler('console.log')
fh.setLevel(logging.INFO)
fh.setFormatter(logging.Formatter(fmt))
logger.addHandler(fh)

symbols = list(Algo.assets.keys())[:10]
# 	print(Algo.minBars)
# 	print("Tracking {} symbols.".format(len(symbols)))

@conn.on(r'^account_updates$')
async def on_account_updates(conn, channel, account):
	logger.info(f'account_updates {account}')
	#symbol = data.order['symbol']
	
# @conn.on(r'^A$')
# async def on_second(conn, channel, data):
# 	Algo.secBars.append(data)
# 	#symbol = data.symbol
# 	#print(symbol)

@conn.on(r'^AM$')
async def on_minute(conn, channel, data):
	if data.symbol in symbols:
		save_bars('minBars', data)


def save_bars(barType, data):
	# barType: 'secBars' or 'minBars'
	# data: raw stream data

	# start writing
	Algo.writing = True
	print(Algo.writing)
	# copy bars to Algo.assets
	Algo.minBars.append(pd.DataFrame({
            'open': data.open,
            'high': data.high,
            'low': data.low,
            'close': data.close,
            'volume': data.volume,
        }, index=[data.start]))
	
	bars = Algo.__getattribute__(barType)
	for bar in bars:
		assets = Algo.assets[bar.symbol][barType] 
		assets = assets.append(bar.df)
	logger.getChild(symbol).info(f'received bar start = {bar.start}, close = {bar.close}, len(bars) = {len(symbols)}')
	# Done writing
	Algo.writing = False


print("Tracking {} symbols.".format(len(symbols)))
channels = ['trade_updates','AM.*']

# Add symbols to minute data (AM) and second data (A) 
for symbol in symbols:
	symbol_channels = ['AM.{}'.format(symbol)]
	#symbol_channels = ['A.{}'.format(symbol) , 'AM.{}'.format(symbol)]
	channels += symbol_channels

# Defining the loop for the threads
async def periodic():
	while True:
		if not alpacaPaper.get_clock().is_open:
			logger.info('exit as market is not open')
			sys.exit(0)
		print(alpacaPaper.get_account())
		print(channels)
		await asyncio.sleep(30)


loop = conn.loop
loop.run_until_complete(asyncio.gather(
	conn.subscribe(channels),
	periodic()
))
loop.close()







