import websocket, json, threading
from time import *
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
symbols = list(Algo.assets.keys())[:10]

conn = tradeapi.stream2.StreamConn(paper.apiKey, paper.secretKey, endpoint)

trade_msg = []
order_msg = []
past_trades = []

searching_for_trade = False
order_sent = False
order_submitted = False
active_trade = False
done_for_the_day = False

#check if market is open
alpaca.cancel_all_orders()
clock = alpaca.get_clock()


if clock.is_open:
	pass
else:
	time_to_open = clock.next_open - clock.timestamp
	sleep(time_to_open.total_seconds())

if len(alpaca.list_positions()) == 0:
	searching_for_trade = True
else:
	active_trade = True


@conn.on(r'^account_updates$')
async def on_account_updates(conn, channel, account):
	order_msg.append(account)

@conn.on(r'^trade_updates$')
async def on_trade_updates(conn, channel, trade):
	trade_msg.append(trade)
	if 'fill' in trade.event:
		past_trades.append([trade.order['updated_at'], trade.order['symbol'], trade.order['side'], 
			trade.order['filled_qty'], trade.order['filled_avg_price']])
		with open('past_trades.csv', 'w') as f:
			json.dump(past_trades, f, indent=4) 
		print(past_trades[-1])

def ws_start():
	conn.run(['account_updates', 'trade_updates']) #executes the async functions above

#start WebSocket in a thread
ws_thread = threading.Thread(target=ws_start, daemon=True) #calls ws_start
ws_thread.start()
sleep(10)



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






