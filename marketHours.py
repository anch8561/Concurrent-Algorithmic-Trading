# functions for navigating market hours, timezones, and holidays

from alpacaAPI import alpaca
from warn import warn
from datetime import datetime, timedelta, timezone

nyc = timezone(timedelta(hours=-4))

def get_time(offset=0):
    # offset: int, hours relative to now (-1 is an hour ago)
    # returns: e.g. '19:01:26' (HH:MM:SS)
    time = datetime.now(nyc) + timedelta(hours=offset)
    return time.strftime('%H:%M:%S')

def get_date(offset=0):
    # offset: int, days relative to today (-1 is yesterday)
    # returns: e.g. '2020-05-28' (YYYY-MM-DD)
    date = datetime.now(nyc) + timedelta(offset)
    return date.strftime('%Y-%m-%d')

def get_open_time():
    # returns: e.g. '19:01:26' (HH:MM:SS)
    todayStr = get_date()
    calendar = alpaca.get_calendar(todayStr, todayStr)[0]
    return datetime.now().replace(
        hour=calendar.open.hour,
        minute=calendar.open.minute,
        second=0
    ).astimezone(nyc).strftime('%H:%M:%S')

def get_close_time():
    # returns: e.g. '19:01:26' (HH:MM:SS)
    todayStr = get_date()
    calendar = alpaca.get_calendar(todayStr, todayStr)[0]
    return datetime.now().replace(
        hour=calendar.close.hour,
        minute=calendar.close.minute,
        second=0
    ).astimezone(nyc).strftime('%H:%M:%S')

def is_market_day(offset=0):
    # offset: int, days relative to today (-1 is yesterday)
    # returns: bool
    dateStr = get_date(offset)
    calendarDateStr = alpaca.get_calendar(dateStr, dateStr)[0]._raw['date']
    return calendarDateStr == dateStr

def get_n_market_days_ago(n=1):
    # n: pos int, 
    # returns: e.g. '2020-05-28' (YYYY-MM-DD)

    # check arguments
    if n <= 0:
        warn(f'{n} <= 0')
        return

    # check each previous day until n market days are found
    offset = -1
    count = 0
    while True:
        if is_market_day(offset):
            count += 1
            if count == n:
                return get_date(offset)
        offset -= 1
    
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
