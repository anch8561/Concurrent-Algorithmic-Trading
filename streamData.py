import asyncio, websocket, json, threading, requests, logging, nest_asyncio 
import pandas as pd
from Algo import Algo
from alpacaAPI import alpaca, alpacaPaper, conn, connPaper
from update_assets import update_assets
from warn import warn
from time import sleep

#nest_asyncio.apply()
update_assets(Algo)

# logging.basicConfig()
# logging.getLogger().setLevel(logging.DEBUG)
# requests_log = logging.getLogger("requests.packages.urllib3")
# requests_log.setLevel(logging.DEBUG)
# requests_log.propagate = True

symbols = list(Algo.assets.keys())[:10]

logging.basicConfig(filename='errlog.log',level=logging.WARNING,  format='%(asctime)s:%(levelname)s:%(message)s')
data_msg = []
order_msg = []
past_trades = []


symbols = list(Algo.assets.keys())[:10]
# 	print(Algo.minBars)
# 	print("Tracking {} symbols.".format(len(symbols)))

@conn.on(r'^account_updates$')
async def on_account_updates(conn, channel, account):
	order_msg.append(account)


@conn.on(r'^A$')
async def on_second(conn, channel, data):
	Algo.secBars.append(data)
	#symbol = data.symbol
	#print(symbol)

@conn.on(r'^AM$')
async def on_minute(conn, channel, data):
	data_msg.append(data)
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
for symbol in symbols:
	symbol_channels = ['A.{}'.format(symbol) , 'AM.{}'.format(symbol)]
	channels += symbol_channels
print("Tracking {} symbols.".format(len(symbols)))


def run_ws(conn, channels):
	try:
		conn.run(channels)
	except Exception as e:
		print(e)
		conn.close()
		run_ws(conn, channels)

	

	
while True:
	run_ws(conn, channels)	








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



#ws_start()

# account updates
# @conn.on(r'^account_updates$')
# async def on_account_updates(conn, channel, account):
# 	print("pass")

# def ws_start():
# 	connPaper.run(['AM.*', 'trade_updates', 'account_updates']) #List of channels to run (AM.* - minute data on * symbols)

# def run_ws(conn, channels):
#     try:
# 		#start WebSocket in a thread
#         ws_thread = threading.Thread(target=ws_start, daemon=True) #calls ws_start
#         ws_thread.start()
#         sleep(10)
#     except Exception as e:
#         print(e)
#         connPaper.close()
#         run_ws(connPaper, channels)
 
# ws_start()

# def run():
#     conn = alpaca.StreamConn("wss://alpaca.socket.polygon.io/stocks", paper.apiKey, paper.secretKey)

# def on_open(ws, symbols):
#     ws.send(json.dumps({"action": "authenticate","data": {"key_id": paper.apiKey, "secret_key": paper.secretKey}}))
#     #Establish connection
#     try: 
#         ws.send(json.dumps({"action": "authenticate","data": {"key_id": paper.apiKey, "secret_key": paper.secretKey}}))
#         print(f"Account authenticated.")
#     except: 
#         print(f"Failed to authenticate account.")
    


#     listen_message = {"action": "listen", "data": {"streams": ["T."+symbol for symbol in symbols]}}

#     ws.send(json.dumps(listen_message))
   

# def on_message(ws, message):
#     print(message) 
 
# socket = "wss://alpaca.socket.polygon.io/stocks"
# #socket = "wss://data.alpaca.markets/stream"

# ws = websocket.WebSocketApp(socket, on_open=on_open, on_message=on_message)
# ws.run_forever()






