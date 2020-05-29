import websocket, json
from Algo import Algo 
import alpaca_trade_api as tradeapi
from alpacaAPI import alpaca, alpacaPaper 
from update_assets import update_assets
from credentials import paper
from marketHours import is_new_week_since, get_time_str, get_date_str
from warn import warn

alpaca = tradeapi.REST(*paper.creds)
update_assets(Algo)
symbols = list(Algo.assets.keys())[:10]
print(symbols)
def on_open(ws, symbols):
    
    try: 
        ws.send(json.dumps({"action": "authenticate","data": {"key_id": paper.apiKey, "secret_key": paper.secretKey}}))
        print("Account authenticated.")
    except: 
        print("Failed to authenticate account.")
    
    listen_message = {"action": "listen", "data": {"streams": ["T."+symbol for symbol in symbols]}}

    ws.send(json.dumps(listen_message))
   

def on_message(ws, message):
    print(message) 
 

socket = "wss://data.alpaca.markets/stream"

ws = websocket.WebSocketApp(socket, on_open=on_open, on_message=on_message)
ws.run_forever()




    

#alpacaPaper = tradeapi.REST(*paper.creds)


###
# Functionality: 

# Account Updates- 
# Changes to flags, status, or multiplier should throw warnings
#     - may or may not need equity, margins, buying power, etc...


# Order Updates- 

# Algo.paperOrders and Algo.liveOrders will have an algo field with a pointer to the algo that placed the order
# When orders fill they should be removed from (Algo.paperOrders or Algo.liveOrders) and algo.orders (the algo that placed the order)
# I don't think we care about partial fills unless they expire
# Expired partial fills should update the algo's buying power and positions accordingly
# Filled orders should be added to (Algo.paperPositions or Algo.livePositions) and algo.positions (the algo that placed the order)


# Second and minute bars from polygon- 
#     info for any symbols in algo.assets should be aggregated into Algo.assets

# Tick() all algos after saving data from each second bar
# Later we will tick different algos at different intervals
###




### Get socket 

    # account_blocked: False
    # multiplier: x
    # pattern_day_trader: False
    # shorting enabled: True
    # status: ACTIVE
    # trade_suspended_by_user: False
    # trading_blocked: False
    # transfers_blocked: False









