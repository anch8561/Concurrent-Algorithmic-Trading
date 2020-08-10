import globalVariables as g

from datetime import datetime, timedelta
from logging import getLogger
from pytz import timezone

log = getLogger()

def init_timing():
    global nyc, calendar, i_today
    nyc = timezone('America/New_York')
    calendar = g.alpacaPaper.get_calendar()
    todayStr = datetime.now(nyc).strftime('%Y-%m-%d')
    for ii, date in enumerate(calendar):
        if date._raw['date'] >= todayStr: # current or next market day
            i_today = ii
            break

def get_time():
    # returns: current nyc datetime
    return datetime.now(nyc)

def get_time_str():
    # returns: nyc time str; e.g. '08:35:41.736216' (HH:MM:SS.US)
    return get_time().strftime('%H:%M:%S.%f')

def get_market_open():
    # returns: nyc market open datetime
    return datetime.combine(
        date = calendar[i_today].date,
        time = calendar[i_today].open,
        tzinfo = get_time().tzinfo)

def get_market_close():
    # returns: nyc market close datetime
    return datetime.combine(
        date = calendar[i_today].date,
        time = calendar[i_today].close,
        tzinfo = get_time().tzinfo)

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
