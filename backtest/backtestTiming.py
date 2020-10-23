import pytz
from datetime import datetime, timedelta

nyc = pytz.timezone('America/New_York')

def get_calendar_index(calendar: list, date: str) -> int:
    # calendar: alpaca.get_calendar()
    # date: e.g. '1996-02-13'
    for ii, day in enumerate(calendar):
        if day._raw['date'] == date:
            return ii

def get_calendar_date(calendar: list, dateIdx: int) -> datetime:
    return nyc.localize(calendar[dateIdx].date)

def get_market_open(calendar: list, dateIdx: int) -> datetime:
    # returns: nyc market open datetime
    return datetime.combine(
        date = calendar[dateIdx].date,
        time = calendar[dateIdx].open,
        tzinfo = nyc)

def get_market_close(calendar: list, dateIdx: int) -> datetime:
    # returns: nyc market close datetime
    return datetime.combine(
        date = calendar[dateIdx].date,
        time = calendar[dateIdx].close,
        tzinfo = nyc)

def update_time(now: datetime, calendar: list, dateIdx: int) -> (datetime, timedelta, timedelta):
    now += timedelta(minutes=1)
    TTOpen = get_market_open(calendar, dateIdx) - now
    TTClose = get_market_close(calendar, dateIdx) - now
    return now, TTOpen, TTClose

def get_time_str(assets: dict):
    symbol = list(assets.keys())[0]
    return assets['day'][symbol].index[-1].strftime('%H:%M:%S.%f')

def get_assets_date(assets: dict) -> str:
    symbol = list(assets.keys())[0]
    return assets['day'][symbol].index[-1].strftime('%Y-%m-%d')
