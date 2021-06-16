# Concurrent-Algorithmic-Trading (CAT)
The Concurrent Algorithmic Trading (CAT) package allows an algorithmic trader to run multiple concurrent and independent trading strategies while efficiently sharing resources to minimize processing load and limited Alpaca API calls. A buying power optimizer will distribute buying power accross strategies to maximize profit and minimize risk. Additionally there is a full backtesting framework (see backtesting branch) with summarized results and plotting.

### Motivation
Any trader who suggested holding a single position worth 100% of their portfolio would be laughed out of the room. Everyone knows that portfolios should be diversified to avoid excessive risk. Why then do traders employ a single strategy for their entire portfolio? What happens when markets change and that strategy is no longer profitable? They will continuously lose money or have to sit out of the market until they develop a new profitable strategy.

Now imagine that you run dozens, hundreds, or even thousands of strategies concurrently. They are managed by a system that automatically distributes buying power among them, giving more cash to profitable strategies and taking money away from losers, all while adhering to strict risk management constraints. Welcome to the Concurrent Algorithmic Trading framework.

### Challenges
This project was born of an idea, that portfolios should diversify strategies in the same way they diversify positions, and two limitations of the alpaca.markets platform:
1. There is no way to track multiple portfolios on the same account
2. Users are limited to 200 API calls per minute

To solve these limitations, we created a system that tracks buying power, orders, and positions for any number of unique strategies independently while sharing as many resources (including API calls) as possible.

## Requirements
Dependencies can be installed from requirements.txt

You will additionally need an alpaca.markets account with Polygon data access. You will have to create a new file named credentials.py which will contain your Alpaca API key, secret key, and endpoint (paper or live) for up to 3 environments (dev, test, and prod). The format for that file can be copied from credentialsTemplate.py

## Getting Started
The following is a brief description of the overarching structure of the program. Individual variables and functions generally have comments or hints describing their purpose and expected inputs and outputs.

_NOTE: The backtesting branch has improved type hints and function comments which have not yet made it to the master branch. It also contains improvements to Indicator and Algo constructors detailed below._

### Market Data
Price and volume data (bars) are streamed from Polygon. When a new bar arrives, it is added to a pandas DataFrame (see assets in globalVariables.py) and all the relevant indicators calculate updated values which are stored in the same DataFrame on the same row as the new bar (see process_bar in streaming.py).

Market data and order update websockets run in a separate thread from indicators and algos so that they don't miss network events (see streaming.py)

### Indicators
An indicator is used to calculate a value (e.g. a moving average) which will be used by one or more algos and/or other indicators (see indicators.py).

The Indicator constructor takes three positional arguments (see Indicator in indicators.py):
1. numBars: The number of bars to use for calculations
2. barFreq: The frequency of the bars to use for calculations (1-second bars ['sec'], 1-minute bars ['min'], or 1-day bars ['day'])
3. func: A function that returns a value when called with the indicator instance and the bars DataFrame as arguments

You can add any kwargs you want as variables for your function. All constructor arguments are saved as member variables. The function can access all these member variables since the indicator instance is passed to the function as an argument when it is called.

With an indicator function written, the next step lies within the init_indicators function. An indicator instance should be created and added to the appropriate list within the indicators Dict (see init_indicators in indicators.py).

An indicator's name is procedurally generated based on its construction arguments (see Indicator in indicators.py). This name is assigned to a column in each DataFrame in g.assets[barFreq] so that the indicator can be accessed by algos or other indicators through its name (see add_asset in init_assets.py).

An indicator (A) can access another indicator (B) by looking it up in a bars DataFrame. Just make sure that A and B are in the same indicator list and that B appears before A in the list (so B processes first).

#### Backtesting Branch
The way indicators are constructed was revamped in the backtesting branch and has not yet been merged to the master branch.

The Indicator constructor only requires a function. The barFreq parameter is implied from the indicators Dict key. The numBars parameter can be added as a kwarg if needed.

Indicators are constructed prior to algo construction and are passed to the Algo constructor (see init_intraday_algos in algos.py). The indicators Dict is then populated automatically (see init_indicators in indicators.py).

### Algos
Algos "tick" after new bars have been received and indicators have updated for each equity asset the program is watching. They take the data stored in the bars DataFrame (including indicator values) and apply logic to determine whether to buy or sell an asset. Algos track positions and open orders, calculate price limits and trade quantities, and submit orders internally so you don't have to worry about it (see AlgoClasses.py, tick_algos.py, and process_trade in streaming.py).

The Algo constructor takes a function as an argument along with any kwargs you want as variables for your function. The function should take only one argument, an algo instance (giving access to the enter_position and exit_position methods as well as any kwargs passed to the Algo constructor). The function should use the bars stored in g.assets to make decisions to call the enter_position and exit_position Algo methods (see algos.py). This is purposefully open-ended to allow for a broad range of trading strategies.

With an algo function written, the next step is to add it to the init_intraday_algos, init_overnight_algos, or init_multiday_algos functions (see algos.py). Intraday algos exit their positions before market close to release buying power and allow overnight algos to enter overnight positions. Simply pass your function and any kwargs to the DayAlgo (for intraday or multiday) or NightAlgo (for overnight) constructor, and add the algo to the respective list (see init_intraday_algos, init_overnight_algos, and init_multiday_algos in algos.py).

#### Backtesting Branch
The way algos are constructed was reworked in the backtesting branch and has not yet been merged to the master branch.

The enter_position and exit_position methods have been replaced with the queue_order method.

init_multiday_algos has been removed. init_intraday_algos and init_overnight_algos take loadData as an argument that should be passed on to Algo constructors (see init_intraday_algos and init_overnight_algos in algos.py).

The DayAlgo and NightAlgo constructors are gone. Simply use the Algo constructor. AlgoClasses.py has been renamed AlgoClass.py

The Algo constructor requires 5 positional arguments (see Algo in algoClass.py):
1. barFreq: Same as indicators on the master branch
2. func: The funcion that is the only required argument on the master branch
3. indicators: A list of indicators that the algo will use
4. longShort: Whether the algo will take long or short positions
5. loadData: Whether the algo should load saved data

### python main.py
Once you've set up indicators and algos, you're ready to run them.

Run `python main.py -h` to see command line arguments. Various settings and defaults can be tweaked in config.py

## Backtesting
In the backtesting branch, run `python backtest.py -h` to see command line arguments. Various settings and defaults can be tweaked in backtesting/config.py

After running a backtest, a results.txt summary file will be created in the backtest directory (backtesting/backtests/backtestname by default). The backtest directory will also have all the raw data: algo data, market data, and log files. The following code can be used to reproduce and sort results (see backtesting/results.py):
```
import backtesting.results as results
import pandas as pd

history = results.get_backtest_history(backtestName)
metrics = results.get_metrics(history)

pd.set_option("display.max_rows", None, "display.max_columns", None)
print(metrics.sort_values('mean', ascending=False))
```

You can plot backtest results using the following code (see backtesting/plotting.py):
```
import matplotlib.pyplot as plt
import backtesting.plotting as plotting

figures, barsets = plotting.plot_backtest(backtestName, barFreq, algoNames, symbols, dates)
plotting.plot_indicators(figures, barsets, indicators)

plt.show()
```

## Unit Testing
You can run unit tests with the `pytest` command
