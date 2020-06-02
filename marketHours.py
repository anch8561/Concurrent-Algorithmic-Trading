# functions for navigating market hours, timezones, and holidays

from alpacaAPI import alpaca
from warn import warn
from datetime import datetime, timedelta, timezone

nyc = timezone(timedelta(hours=-4))

def get_time(offset=0):
    # offset: int, offset in hours relative to today (-1 is yesterday)
    # returns: e.g. '19:01:26' (HH:MM:SS)
    time = datetime.now(nyc) + timedelta(hours=offset)
    return time.strftime('%H:%M:%S')

def get_date(offset=0):
    # offset: int, offset in days relative to today (-1 is yesterday)
    # returns: e.g. '2020-05-28' (YYYY-MM-DD)
    date = datetime.now(nyc) + timedelta(offset)
    return date.strftime('%Y-%m-%d')

def get_market_open():
    # returns: e.g. '19:01:26' (HH:MM:SS)
    todayStr = get_date()
    calendar = alpaca.get_calendar(todayStr, todayStr)[0]
    return datetime.now().replace(
        hour=calendar.open.hour,
        minute=calendar.open.minute,
        second=0
    ).astimezone(nyc).strftime('%H:%M:%S')

def get_market_close():
    # returns: e.g. '19:01:26' (HH:MM:SS)
    todayStr = get_date()
    calendar = alpaca.get_calendar(todayStr, todayStr)[0]
    return datetime.now().replace(
        hour=calendar.close.hour,
        minute=calendar.close.minute,
        second=0
    ).astimezone(nyc).strftime('%H:%M:%S')

def is_market_day(offset=0):
    # offset: int, offset in days relative to today (-1 is yesterday)
    # returns: bool
    dateStr = get_date(offset)
    calendarDateStr = alpaca.get_calendar(dateStr, dateStr)[0]._raw['date']
    return calendarDateStr == dateStr

def get_last_market_day():
    # currently unused
    # returns: e.g. '2020-05-28' (YYYY-MM-DD)
    for offset in range(-1, -7, -1):
        if is_market_day(offset):
            return get_date(offset)
    
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
