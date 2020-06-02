import alpaca_trade_api as tradeapi
from credentials import paper
alpaca = tradeapi.REST(*paper.creds)
from datetime import datetime, timedelta, timezone

# pre-market: 04:00 - 09:30
# market: 09:30 - 16:00
# post-market: 16:00 - 20:00

# string dates
date = '2020-05-27'
date2 = '2020-05-28' # for get_aggs
print('date:', date)
print('date2:', date2)

# iso dates
nyc = timezone(timedelta(hours=-4))
dateISO = datetime.strptime(date, '%Y-%m-%d').astimezone(nyc).isoformat()
date2ISO = datetime.strptime(date2, '%Y-%m-%d').astimezone(nyc).isoformat()
print('date iso:', dateISO)
print('date2 iso:', date2ISO)


print('\npolygon.historic_agg_v2')
print('=======================')
minutes = alpaca.polygon.historic_agg_v2(
    symbol = 'AAPL',
    multiplier = 1,
    timespan = 'minute',
    _from =  date,
    to = date
)
print(len(minutes))
print(minutes[0])
print(minutes[0].timestamp)
print(minutes[-1].timestamp)
# 04:00:00 - 20:00:00 (full pre-post market hours)


print('\nalpaca.get_aggs')
print('=======================')
minutes = alpaca.get_aggs(
    symbol = 'AAPL',
    multiplier = 1,
    timespan = 'minute',
    _from =  date,
    to = date2
)
print(len(minutes))
print(minutes[0])
print(minutes[0].timestamp)
print(minutes[-1].timestamp)
# 07:00:00 - 16:00:00 (strange start time, market hours)
# error if _from == to


print('\nalpaca.get_barset (no date)')
print('=======================')
minutes = alpaca.get_barset(
    symbols = 'AAPL',
    timeframe = 'minute',
    limit = 1000
    )
print(len(minutes['AAPL']))
print(minutes['AAPL'][0])
print(minutes['AAPL'][0].t)
print(minutes['AAPL'][-1].t)
# past 1000 bars (market hours)
# only function with optional dates
# string dates ignored


print('\nalpaca.get_barset ISO')
print('=======================')
minutes = alpaca.get_barset(
    symbols = 'AAPL',
    timeframe = 'minute',
    start = dateISO,
    end = date2ISO,
    limit = 1000
    )
print(len(minutes['AAPL']))
print(minutes['AAPL'][0])
print(minutes['AAPL'][0].t)
print(minutes['AAPL'][-1].t)
# 07:00:00 - 16:00:00 (strange start time, market hours)
# error if start == end
