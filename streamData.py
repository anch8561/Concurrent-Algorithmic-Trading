import asyncio, websocket, json, threading, requests, logging, nest_asyncio, sys 
import pandas as pd
from Algo import Algo
from alpacaAPI import alpaca, alpacaPaper, conn, connPaper
from update_assets import update_assets
from warn import warn
from time import sleep

#nest_asyncio.apply()
#fupdate_assets(Algo)

# logging.basicConfig()
# logging.getLogger().setLevel(logging.DEBUG)
# requests_log = logging.getLogger("requests.packages.urllib3")
# requests_log.setLevel(logging.DEBUG)
# requests_log.propagate = True

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
	print("In account")
	logger.info(f'account_updates {data}')
	symbol = data.order['symbol']
	
@conn.on(r'^A$')
async def on_second(conn, channel, data):
	Algo.secBars.append(data)
	#symbol = data.symbol
	#print(symbol)

@conn.on(r'^AM$')
async def on_minute(conn, channel, data):
	print("In minute")
	#Algo.minBars.append(data)
	#symbol = data.symbol
	#print(symbol)


def save_bars(barType, data):
	# barType: 'secBars', 'minBars', or 'dayBars'
	# data: raw stream data

	# set flag for threadlocking
	Algo.writing = True

	# copy bars to Algo.assets
	bars = Algo.__getattribute__(barType)
	for bar in bars:
		assets = Algo.assets[bar.symbol][barType] #pointer? 
		assets = assets.append(bar.df)
	
	# set flag for threadlocking
	Algo.writing = False


print("Tracking {} symbols.".format(len(symbols)))
#on_second = conn.on(r'A$')(on_second)
channels = ['trade_updates']
# for symbol in symbols:
# 	symbol_channels = ['A.{}'.format(symbol) , 'AM.{}'.format(symbol)]
# 	channels += symbol_channels
# print("Tracking {} symbols.".format(len(symbols)))


async def periodic():
	while True:
		if not alpaca.get_clock().is_open:
			logger.info('exit as market is not open')
			sys.exit(0)
		await asyncio.sleep(30)
		positions = alpaca.list_positions()
		for symbol in symbols:
			pos = [p for p in positions if p.symbol == symbol]
			#algo.checkup(pos[0] if len(pos) > 0 else None)
			Algo.writing = True
			symbol_channels = ['A.{}'.format(symbol) , 'AM.{}'.format(symbol)]
			print(symbol)
			#channels += symbol_channels
	# 	for symbol, algo in fleet.items():
	# 		pos = [p for p in positions if p.symbol == symbol]
	# 		algo.checkup(pos[0] if len(pos) > 0 else None)
	# channels = ['trade_updates'] + [
	# 	'AM.' + symbol for symbol in symbols
	# ]

# def run_ws(conn, channels):
# 	conn.run(channels)

loop = conn.loop
loop.run_until_complete(asyncio.gather(
	conn.subscribe(channels),
	periodic(),
))
loop.close()





# async def on_second(conn, channel, data):
# 	Algo.secBars.append(data)
# 	print(Algo.minBars)
	# if not Algo.writing:
	# 	Algo.secBars.append(data)

	# sleep(0.01)

# def save_bars(barType, data):
# 	# barType: 'secBars', 'minBars', or 'dayBars'
# 	# data: raw stream data

# 	# set flag for threadlocking
# 	Algo.writing = True

# 	# copy bars to Algo.assets
# 	bars = Algo.__getattribute__(barType)
# 	for bar in bars:
# 		assets = Algo.assets[bar.symbol][barType] #pointer? 
# 		assets = assets.append(bar.df)
	
# 	# set flag for threadlocking
# 	Algo.writing = False

# def ws_start():
# 	symbols = list(Algo.assets.keys())[:10]
# 	print(Algo.minBars)
# 	print("Tracking {} symbols.".format(len(symbols)))
# 	on_second = conn.on(r'A$')(on_second)
# 	conn.run(['AM.MSFT'])

# #start WebSocket in a thread
# ws_thread = threading.Thread(target=ws_start, daemon=True)
# ws_thread.start()

	
# # trade updates
# @conn.on(r'^trade_updates$')
# async def on_trade_updates(conn, channel, trade):
# 	Algo.orderUpdates.append(trade)
# 	# TODO: similar structure to save_bars






