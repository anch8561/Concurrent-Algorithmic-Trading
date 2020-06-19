# alpaca.get_barset is useful for defining specific hours
# polygon.historic_agg_v2 is useful for pre-post market hours

import alpaca_trade_api as tradeapi
from credentials import paper
alpaca = tradeapi.REST(*paper.creds)
from datetime import datetime

# pre-market: 04:00 - 09:30
# market: 09:30 - 16:00
# post-market: 16:00 - 20:00

# simple date(s)
date = '2020-05-27'
date2 = '2020-05-28'

# iso dates
dateISO = date + 'T00:00:00-04:00' # add midnight time and NY timezone
date2ISO = date2 + 'T00:00:00-04:00'

# iso datetimes
date3ISO = '2020-05-27T09:30:00-04:00' # add market open and close
date4ISO = '2020-05-27T16:00:00-04:00'


print('\npolygon.historic_agg_v2')
print('=======================')
minutes = alpaca.polygon.historic_agg_v2(
    symbol = 'AAPL',
    multiplier = 1,
    timespan = 'minute',
    _from =  date3ISO,
    to = date4ISO
)
print(len(minutes))
print(minutes[0])
print(minutes[0].timestamp)
print(minutes[-1].timestamp)
# 04:00:00 - 20:00:00 (full pre-post market hours)
# date - date2 gives data for both days
# ignores ISO times, treats like simple dates
# does not work with datetimes (only strings)


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
# only accepts simple dates (YYYY-MM-DD)


print('\nalpaca.get_barset')
print('=======================')
minutes = alpaca.get_barset(
    symbols = 'AAPL',
    timeframe = 'minute',
    start = date3ISO,
    end = date4ISO,
    limit = 1000
    )
print(len(minutes['AAPL']))
print(minutes['AAPL'][0])
print(minutes['AAPL'][0].t)
print(minutes['AAPL'][-1].t)
# optional dates (no dates returns most recent bars)
# 07:00:00 - 16:00:00 (strange start time, market hours)
# can define hours (09:30:00 - 16:00:00, market hours)
# error if start == end
# only accepts ISO datetimes