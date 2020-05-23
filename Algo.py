from datetime import datetime, timedelta
from pytz import timezone

class Algo:
    stocks = {}

    def __init__(self, cash=10000, maxPositionFraction=0.01):
        self.cash = cash
        self.maxPositionFraction = maxPositionFraction
        self.positions = {} # {symbol: quantity}
        self.orders = [] # [order_id]

        self.log = ''

        self.alpha = 0
        self.beta = 0
        self.allocationFraction = 0
    
    def marketWasOpenYesterday(self):
        # currently unused
        nyc = timezone('America/New_York')
        date = datetime.today().astimezone(nyc)

        yesterday = (date - timedelta(days=1)).strftime('%Y-%m-%d')
        calendar = alpaca.get_calendar(yesterday, yesterday)

        return calendar[0]._raw['date'] == yesterday
        
    def isNewWeekSince(self, date):
        # date: string e.g. '2020-05-22'
        date = datetime.strptime(date, '%Y-%m-%d')
        today = self.getDate()
        monday = today - timedelta(today.weekday())
        return date < monday

    def getTime(self):
        nyc = timezone('America/New_York')
        return datetime.today().astimezone(nyc).strftime('%H-%M-%S')

    def getDate(self, dayOffset=0):
        nyc = timezone('America/New_York')
        today = datetime.today().astimezone(nyc)
        date = today + timedelta(dayOffset)
        return date.strftime('%Y-%m-%d')