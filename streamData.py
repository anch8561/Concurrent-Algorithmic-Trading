import alpaca_trade_api as tradeapi
import requests
import time
from ta import macd
import numpy as np
from datetime import datetime, timedelta
from pytz import timezone
from alpacaAPI import alpaca, alpacaPaper 


alpaca = tradeapi.REST(*liveTest.creds)
alpacaPaper = tradeapi.REST(*paperTest.creds)

###
Example from StreamConn readme

conn = StreamConn()

@conn.on(r'^trade_updates$')
async def on_account_updates(conn, channel, account):
    print('account', account)

@conn.on(r'^status$')
async def on_status(conn, channel, data):
    print('polygon status update', data)

@conn.on(r'^AM$')
async def on_minute_bars(conn, channel, bar):
    print('bars', bar)

@conn.on(r'^A$')
async def on_second_bars(conn, channel, bar):
    print('bars', bar)

# blocks forever
conn.run(['trade_updates', 'AM.*'])

# if Data API streaming is enabled
# conn.run(['trade_updates', 'alpacadatav1/AM.SPY'])
###

### Momentum Trading Example

session = requests.session()

# We only consider stocks with per-share prices inside this range
min_share_price = 2.0
max_share_price = 13.0
# Minimum previous-day dollar volume for a stock we might consider
min_last_dv = 500000
# Stop limit to default to
default_stop = .95
# How much of our portfolio to allocate to any one position
risk = 0.001


def get_1000m_history_data(symbols):
    print('Getting historical data...')
    minute_history = {}
    c = 0
    for symbol in symbols:
        minute_history[symbol] = api.polygon.historic_agg(
            size="minute", symbol=symbol, limit=1000
        ).df
        c += 1
        print('{}/{}'.format(c, len(symbols)))
    print('Success.')
    return minute_history


def get_tickers():
    print('Getting current ticker data...')
    tickers = api.polygon.all_tickers()
    print('Success.')
    assets = api.list_assets()
    symbols = [asset.symbol for asset in assets if asset.tradable]
    return [ticker for ticker in tickers if (
        ticker.ticker in symbols and
        ticker.lastTrade['p'] >= min_share_price and
        ticker.lastTrade['p'] <= max_share_price and
        ticker.prevDay['v'] * ticker.lastTrade['p'] > min_last_dv and
        ticker.todaysChangePerc >= 3.5
    )]


def find_stop(current_value, minute_history, now):
    series = minute_history['low'][-100:] \
                .dropna().resample('5min').min()
    series = series[now.floor('1D'):]
    diff = np.diff(series.values)
    low_index = np.where((diff[:-1] <= 0) & (diff[1:] > 0))[0] + 1
    if len(low_index) > 0:
        return series[low_index[-1]] - 0.01
