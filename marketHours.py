# functions for navigating market hours, timezones, and holidays

from alpacaAPI import alpaca
from warn import warn
from datetime import datetime, timedelta, timezone

nyc = timezone(timedelta(hours=-4))

def market_was_open_yesterday():
    # currently unused
    today = datetime.today().astimezone(nyc)
    yesterday = (today - timedelta(1)).strftime('%Y-%m-%d')
    calendar = alpaca.get_calendar(yesterday, yesterday)
    return calendar[0]._raw['date'] == yesterday
    
def is_new_week_since(dateStr):
    # dateStr: string e.g. '2020-05-28'
    
    # check argument
    try: date = datetime.strptime(dateStr, '%Y-%m-%d').date()
    except:
        warn(f'{date} could not be parsed')
        return

    # get past/current Monday's date
    today = datetime.today().astimezone(nyc).date()
    monday = today - timedelta(today.weekday())

    # was date before monday
    return date < monday

def get_time_str():
    today = datetime.today().astimezone(nyc)
    return today.strftime('%H-%M-%S')

def get_date_str(offset=0):
    today = datetime.today().astimezone(nyc)
    date = today + timedelta(offset)
    return date.strftime('%Y-%m-%d')