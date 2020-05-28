# functions for navigating market hours, timezones, and holidays

from alpacaAPI import alpaca
from warn import warn
from datetime import datetime, timedelta
from pytz import timezone

def market_was_open_yesterday():
    # currently unused
    nyc = timezone('America/New_York')
    date = datetime.today().astimezone(nyc)

    yesterday = (date - timedelta(days=1)).strftime('%Y-%m-%d')
    calendar = alpaca.get_calendar(yesterday, yesterday)

    return calendar[0]._raw['date'] == yesterday
    
def is_new_week_since(date):
    # date: e.g. '2020-05-22'
    
    # check argument
    if date < '1' or date > '9999':
        warn(f'{date} is outside date bounds')
        return

    date = datetime.strptime(date, '%Y-%m-%d')
    today = get_date()
    monday = today - timedelta(today.weekday())
    return date < monday

def get_time():
    nyc = timezone('America/New_York')
    return datetime.today().astimezone(nyc).strftime('%H-%M-%S')

def get_date(dayOffset=0):
    nyc = timezone('America/New_York')
    today = datetime.today().astimezone(nyc)
    date = today + timedelta(dayOffset)
    return date.strftime('%Y-%m-%d')