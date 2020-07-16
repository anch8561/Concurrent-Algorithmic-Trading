import globalVariables as g
from alpacaAPI import alpacaPaper as alpaca
from warn import warn

from datetime import datetime, timedelta
from pytz import timezone

nyc = timezone('America/New_York')
calendar = alpaca.get_calendar()
todayStr = datetime.now(nyc).strftime('%Y-%m-%d')
for ii, date in enumerate(calendar):
    if date._raw['date'] >= todayStr: # current or next market day
        i_today = ii
        break

def update_time():
    now = datetime.now(nyc)
    date = calendar[i_today].date

    # update time til open
    openTime = datetime.combine(
        date = date,
        time = calendar[i_today].open,
        tzinfo = now.tzinfo)
    g.TTOpen = openTime - now

    # update time til close
    closeTime = datetime.combine(
        date = date,
        time = calendar[i_today].close,
        tzinfo = now.tzinfo)
    g.TTClose = closeTime - now

    return now, openTime, closeTime

def get_time():
    # returns: nyc time str; e.g. '08:35:41.736216' (HH:MM:SS.US)
    return datetime.now(nyc).strftime('%H:%M:%S.%f')

def get_date(offset=0):
    # offset: int, days relative to today (-1 is yesterday)
    # returns: nyc date str; e.g. '2020-05-28' (YYYY-MM-DD)
    date = datetime.now(nyc) + timedelta(offset)
    return date.strftime('%Y-%m-%d')

def get_market_date(offset=0):
    # offset: int, market days relative to today (-1 is prev market day)
    # returns: nyc date str; e.g. '2020-05-28' (YYYY-MM-DD)
    if offset > 0 and not is_market_day(): offset -= 1
    return calendar[i_today + offset].date.strftime('%Y-%m-%d')

def is_market_day(offset=0):
    # offset: int, days relative to today (-1 is yesterday)
    # returns: bool

    # get date
    dateStr = get_date(offset)

    # past day
    if offset < 0:
        for ii in range(-1, offset-1, -1):
            calDateStr = calendar[i_today + ii]._raw['date']
            if dateStr == calDateStr: return True
            if dateStr > calDateStr: return False

    # future day
    if offset > 0:
        for ii in range(1, offset+1, 1):
            calDateStr = calendar[i_today + ii]._raw['date']
            if dateStr == calDateStr: return True
            if dateStr < calDateStr: return False

    # today
    return dateStr == calendar[i_today]._raw['date']
