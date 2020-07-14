import g
from alpacaAPI import alpacaPaper as alpaca
from warn import warn

from datetime import datetime, timedelta
from pytz import timezone

nyc = None # timezone and daylight savings
calendar = None # from alpaca
i_today = None # calendar index
lastCalendarUpdate = '0000-00-00' # date string

def update_timing():
    global nyc, calendar, i_today, lastCalendarUpdate

    # update calendar
    if lastCalendarUpdate < get_date():
        nyc = timezone('America/New_York')
        calendar = alpaca.get_calendar()
        todayStr = datetime.now(nyc).strftime('%Y-%m-%d')
        for ii, date in enumerate(calendar):
            if date._raw['date'] >= todayStr: # current or next market day
                i_today = ii
                break
        lastCalendarUpdate = get_date()
    
    # update market time
    time = datetime.now(nyc)
    g.TTOpen = get_open_time() - time
    g.TTClose = get_close_time() - time

def get_time(): return datetime.now(nyc).strftime('%H:%M:%S.%f')

def get_open_time():
    # returns: nyc datetime
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
    # returns: nyc datetime
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
    # offset: int, market days relative to today (-1 is prev market day)
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

update_timing()
