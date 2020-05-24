# functions for navigating market hours, timezones, and holidays

from alpacaAPI import alpaca
from datetime import datetime, timedelta
from pytz import timezone

def marketWasOpenYesterday():
    # currently unused
    nyc = timezone('America/New_York')
    date = datetime.today().astimezone(nyc)

    yesterday = (date - timedelta(days=1)).strftime('%Y-%m-%d')
    calendar = alpaca.get_calendar(yesterday, yesterday)

    return calendar[0]._raw['date'] == yesterday
    
def isNewWeekSince(date):
    # date: string e.g. '2020-05-22'
    date = datetime.strptime(date, '%Y-%m-%d')
    today = getDate()
    monday = today - timedelta(today.weekday())
    return date < monday

def getTime():
    nyc = timezone('America/New_York')
    return datetime.today().astimezone(nyc).strftime('%H-%M-%S')

def getDate(dayOffset=0):
    nyc = timezone('America/New_York')
    today = datetime.today().astimezone(nyc)
    date = today + timedelta(dayOffset)
    return date.strftime('%Y-%m-%d')