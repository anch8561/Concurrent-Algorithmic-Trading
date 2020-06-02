import websocket, json, threading
from pandas import pd
from Algo import Algo
from alpacaAPI import alpaca, alpacaPaper, conn, connPaper
from update_assets import update_assets
from marketHours import is_new_week_since, get_time_str, get_date_str
from warn import warn
from time import sleep

update_assets(Algo)

# minute bars
@conn.on(r'^AM$')
async def on_minute_bar(conn, channel, data):
	while True:
		if not Algo.writing:
			Algo.secBars.append(data)
			return
		sleep(0.01)

def save_bars(barType, data):
	# barType: 'secBars', 'minBars', or 'dayBars'
	# data: raw stream data

	# set flag for threadlocking
	Algo.writing = True

	# copy bars to Algo.assets
	bars = Algo.__getattribute__(barType)
	for bar in bars:
		assets = Algo.assets[bar.symbol][barType]
		assets = assets.append(bar.df)
	
	# set flag for threadlocking
	Algo.writing = False
    

# trade updates
@conn.on(r'^trade_updates$')
async def on_trade_updates(conn, channel, trade):
	Algo.orderUpdates.append(trade)
	# TODO: similar structure to save_bars

# account updates
@conn.on(r'^account_updates$')
async def on_account_updates(conn, channel, account):
	pass

def ws_start():
	conn.run(['AM.*', 'trade_updates', 'account_updates']) #executes the async functions above

def run_ws(conn, channels):
    try:
		#start WebSocket in a thread
        ws_thread = threading.Thread(target=ws_start, daemon=True) #calls ws_start
        ws_thread.start()
        sleep(10)
    except Exception as e:
        print(e)
        conn.close()
        run_ws(conn, channels)
 




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






