import asyncio, sys 
import pandas as pd
from Algo import Algo
from ReturnsReversion import ReturnsReversion
from alpacaAPI import alpaca, alpacaPaper, conn, connPaper
from get_tradable_assets import get_tradable_assets
from warn import warn
from time import sleep

def save_bars(barType, data):
	# barType: 'secBars' or 'minBars'
	# data: raw stream data
	if barType not in ('secBars', 'minBars', 'dayBars'):
		warn(f'barType "{barType}" not recognized')
		return
	df = pd.DataFrame({
            'open': data.open,
            'high': data.high,
            'low': data.low,
            'close': data.close,
            'volume': data.volume,
        }, index=[data.start])
	# TODO: add dayBars 

	# copy bars to Algo.assets (needs to be initialized first)
	Algo.assets[data.symbol][barType].append(df) 

	print(f'Saving {barType} for {data.symbol}')
	print(f'-------------------------------------------------------------')

def run():

	@conn.on(r'account_updates')
	async def on_account_updates(conn, channel, account):
		print(f'{alpacaPaper.get_account()}')

	# @conn.on(r'A')
	# async def on_second(conn, channel, data):
	# 	save_bars('secBars', data)

	@conn.on(r'AM')
	async def on_minute(conn, channel, data):
		save_bars('minBars', data)

	async def periodic():
		while True:
			if not alpacaPaper.get_clock().is_open:
				print(f'Market is not open.')
				sys.exit(0)
			await asyncio.sleep(5)

	returnsReversion = ReturnsReversion(1000)
	algos = [returnsReversion]

	get_tradable_assets(algos, debugging=True)
	symbols = list(Algo.assets.keys())

	print("Tracking {} symbols.".format(len(symbols)))
	channels = ['account_updates','AM.*', 'A.*']

	# Add symbols to minute data (AM) and second data (A) to subscribe to channels
	for symbol in symbols:
		symbol_channels = ['AM.{}'.format(symbol)]
		#symbol_channels = ['A.{}'.format(symbol) , 'AM.{}'.format(symbol)]
		channels += symbol_channels

	loop = conn.loop
	loop.run_until_complete(asyncio.gather(
		conn.subscribe(channels),
		periodic()
	))
	loop.close()

run()





