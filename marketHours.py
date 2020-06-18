# functions for navigating market hours, timezones, and holidays
# all inputs and outputs are timezone-naive strings in NY timezone
# time strings are actually naive datetime strings in ISO format

from alpacaAPI import alpacaPaper
from warn import warn
from datetime import datetime, timedelta, timezone

nyc = timezone(timedelta(hours=-4))

# get calendar
calendar = alpacaPaper.get_calendar()
todayStr = datetime.now(nyc).strftime('%Y-%m-%d')
for ii, date in enumerate(calendar):
    if date._raw['date'] >= todayStr: # current or next market day
        i_today = ii
        break

# TODO: update calendar daily

def get_time():
    return datetime.now(nyc)

def get_open_time():
    # returns: e.g. '2020-06-16 19:01:26' (YYYY-MM-DD HH:MM:SS)
    time = calendar[i_today].open
    date = calendar[i_today].date
    return datetime.now(nyc).replace(
        year = date.year,
        month = date.month,
        day = date.day,
        hour = time.hour,
        minute = time.minute,
        second = time.second)
        
def get_close_time():
    # returns: e.g. '2020-06-16 19:01:26' (YYYY-MM-DD HH:MM:SS)
    time = calendar[i_today].close
    date = calendar[i_today].date
    return datetime.now(nyc).replace(
        year = date.year,
        month = date.month,
        day = date.day,
        hour = time.hour,
        minute = time.minute,
        second = time.second)

def get_date(offset=0):
    # offset: int, days relative to today (-1 is yesterday)
    # returns: e.g. '2020-05-28' (YYYY-MM-DD)
    date = datetime.now(nyc) + timedelta(offset)
    return date.strftime('%Y-%m-%d')

def get_market_date(offset=0):
    # offset: int, MARKET days relative to today (-1 is prev market day)
    # returns: e.g. '2020-05-28' (YYYY-MM-DD)
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
    
def is_new_week_since(dateStr):
    # dateStr: e.g. '2020-05-28' (YYYY-MM-DD)
    # returns: bool
    
    # check argument
    try: date = datetime.strptime(dateStr, '%Y-%m-%d').date()
    except:
        warn(f'{date} could not be parsed')
        return

    # get past/current Monday's date
    today = datetime.now(nyc).date()
    monday = today - timedelta(today.weekday())

    # was date before monday
    return date < monday
