import pytz
from datetime import datetime, timedelta

nyc = pytz.timezone('America/New_York')

def get_calendar_index(calendar: list, date: str) -> (int, str):
    # calendar: alpaca.get_calendar()
    # date: e.g. '1996-02-13'
    # returns:
    #   index: calendar index of date (or next market day if date is not in calendar)
    #   date: calendar date (same as date arg unless date is not in calendar)
    for ii, day in enumerate(calendar):
        if day._raw['date'] >= date: return ii, day._raw['date']

def get_calendar_date(calendar: list, dateIdx: int) -> datetime:
    return nyc.localize(calendar[dateIdx].date)

def get_market_open(calendar: list, dateIdx: int) -> datetime:
    # returns: nyc market open datetime
    return nyc.localize(datetime.combine(
        date = calendar[dateIdx].date,
        time = calendar[dateIdx].open))

def get_market_close(calendar: list, dateIdx: int) -> datetime:
    # returns: nyc market close datetime
    return nyc.localize(datetime.combine(
        date = calendar[dateIdx].date,
        time = calendar[dateIdx].close))

def update_time(now: datetime, calendar: list, dateIdx: int) -> (datetime, timedelta, timedelta):
    now += timedelta(minutes=1)
    TTOpen = get_market_open(calendar, dateIdx) - now
    TTClose = get_market_close(calendar, dateIdx) - now
    return now, TTOpen, TTClose

def get_time_str(g):
    return g.now.strftime('%H:%M:%S.%f')

def get_assets_date(g) -> str:
    return g.now.strftime('%Y-%m-%d')
