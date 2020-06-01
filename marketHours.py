# functions for navigating market hours, timezones, and holidays

from alpacaAPI import alpaca
from warn import warn
from datetime import datetime, timedelta, timezone

nyc = timezone(timedelta(hours=-4))

def market_was_open_yesterday():
    # currently unused
    today = datetime.now(nyc)
    yesterday = (today - timedelta(1)).strftime('%Y-%m-%d')
    calendar = alpaca.get_calendar(yesterday, yesterday)
    return calendar[0]._raw['date'] == yesterday
    
def is_new_week_since(dateStr):
    # dateStr: e.g. '2020-05-28' (yr-mo-day)
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

def get_time_str():
    # returns: e.g. '19-01-26' (hr-min-sec)
    now = datetime.now(nyc)
    return now.strftime('%H-%M-%S')

def get_date_str(offset=0):
    # returns: e.g. '2020-05-28' (yr-mo-day)
    today = datetime.now(nyc)
    date = today + timedelta(offset)
    return date.strftime('%Y-%m-%d')

def get_market_open():
    # returns: e.g. '09-30-00' (hr-min-sec)
    todayStr = get_date_str()
    calendar = alpaca.get_calendar(todayStr, todayStr)[0]
    return datetime.now().replace(
        hour=calendar.open.hour,
        minute=calendar.open.minute,
        second=0
    ).astimezone(nyc).strftime('%H-%M-%S')

def get_market_close():
    # returns: e.g. '16-00-00' (hr-min-sec)
    todayStr = get_date_str()
    calendar = alpaca.get_calendar(todayStr, todayStr)[0]
    return datetime.now().replace(
        hour=calendar.close.hour,
        minute=calendar.close.minute,
        second=0
    ).astimezone(nyc).strftime('%H-%M-%S')
