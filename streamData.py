import websocket, json, threading
from time import *
from pandas import pd
from Algo import Algo
import alpaca_trade_api as tradeapi
from alpacaAPI import alpaca, alpacaPaper 
from update_assets import update_assets
from credentials import paper
from marketHours import is_new_week_since, get_time_str, get_date_str
from warn import warn


alpaca = tradeapi.REST(*paper.creds)
endpoint = "wss://alpaca.socket.polygon.io/stocks" 

update_assets(Algo)
#symbols = list(Algo.assets.keys())[:10]

conn = tradeapi.StreamConn(paper.apiKey, paper.secretKey, endpoint)


#check if market is open
alpaca.cancel_all_orders()
clock = alpaca.get_clock()

def get_tickers():
    print('Getting current ticker data...')
    tickers = alpaca.polygon.all_tickers()
    print('Success.')
    assets = Algo.assets
    symbols = list(Algo.assets.keys())
    return [ticker for ticker in tickers if (
        ticker.ticker in symbols and
        ticker.lastTrade['p'] >= min_share_price and
        ticker.lastTrade['p'] <= max_share_price and
        ticker.prevDay['v'] * ticker.lastTrade['p'] > min_last_dv and
        ticker.todaysChangePerc >= 3.5
    )]

# Replace aggregated 1s bars with incoming 1m bars
@conn.on(r'A$')
async def handle_second_bar(conn, channel, data):
	Algo.assets[symbol][secBars] = pd.dataframe(data)
	for Algo in Algos:
		tick()

@conn.on(r'AM$')
async def handle_minute_bar(conn, channel, data):
    Algo.assets[symbol][minBars] = pd.dataframe(data)

@conn.on(r'^account_updates$')
async def on_account_updates(conn, channel, account):
	order_msg.append(account)

@conn.on(r'^trade_updates$')
async def on_trade_updates(conn, channel, trade):
	trade_msg.append(trade)


def ws_start():
	conn.run(['account_updates', 'trade_updates']) #executes the async functions above

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






