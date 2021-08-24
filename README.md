# Leveraged-grid-trading-bot

The code is designed to perform infinity [grid trading](https://www.gridtradingcourse.com/articles/what-is-grid-trading.php) strategy in [FTX exchange](https://ftx.com/).

The basic trader named ***Gridtrader.py*** control the number of grids dynamically using the setting in JSON file.

***asyncGridtrader.py*** will do the same job [asynchronously](https://docs.python.org/3/library/asyncio.html).

Trader with database support, ***Gridtrader_with_db.py*** and ***asyncGridtrader_with_db.py***, will store the transaction info in database via mysql.

If the trader termineated accidentally, the next execution of trader will follow the history stored in the database. 

> It is recommended to execeute the code in Linux system with Python version 3.7+.

The bot will show the following information in log file:

1. Cash flow
2. Realized profit, averaged profit per day (Not including fee)
3. Total volume, averaged volume per day
4. Maker ratio in filled orders
5. Number of filled orders
6. Transaction fee

## How leveraged?

Most of the funds is locked in normal grid trading bot, while this bot will only create limit orders near the market price (controlled by parameters in setting file). Under this circumstance, the profit can be much greater for short-term price volatility by increasing the transaction frequency. The funds may not be enough to afford the infinity grid trading under the same parameter settings, so it can be regarded as leveraged grid trading.

# Reguired packages

- [simplejson](https://pypi.org/project/simplejson/)
- [CCXT](https://github.com/ccxt/ccxt)
- [pytz](https://pypi.org/project/pytz/)

For async-supported version:

- [asyncio](https://pypi.org/project/asyncio/)
- [CCXT Pro](https://github.com/ccxt/ccxt/wiki/ccxt.pro) (Paid)

For database-supported version:

- [mysql-connector-python](https://pypi.org/project/mysql-connector-python/)

## Cheatsheet

`pip install pytz ccxt simplejson asyncio mysql-connector-python`

## Setting.json

This grid trader will create at least ***grid_level*** and at most 2x ***grid_level*** numerber of grids for buy/sell, respectively. That is, the trader will make sure the number of orders for buy and sell are both not less than ***grid_level*** and also not greater than 2x ***grid_level***.

The price difference of grids is set as ***interval_prof*** . For each transaction, the amount is set as ***amount***.

# Getting started

1. Rename `setting.json.sample` to `setting.json` (Not required).
2. Edit the parameters in `setting.json`
3. Run the command (See examples).

## Cautions

```diff
- It is recommended to create a subaccount to use this trading bot,
to avoid your orders being cancelled by the bot at the beginning.
```
# Examples

## Without async support and without database

`python3 GridTrader.py your.setting.json`

This command execute GridTrader.py with json file named ***your.setting.json***.

`python3 GridTrader.py`

This command execute GridTrader.py with json file named ***setting.json***. 

> For other version of trader, change the `Gridtrader.py` to others in above commands.

## Log snapshots (ETH/USD)

```
Aug 05 2021 17:37:11, ##########.Trading Info.##########
Trade balance: -218.06 USD, +0.1000 ETH
Return: 54.3300 USD, 20.6422 USD/Day
Volume: 93891.71 USD, 35673.27 USD/Day
Maker ratio: 96.50%, Total: 3681
Fee: 2.12847845 USD, 0.00000000 ETH
##########.##########.##########.##########.##########
Aug 05 2021 17:37:34, buy at 2588.4, place new sell at 2591.4.
Aug 05 2021 17:37:35, Enlarge grid for buy at 2468.4
Aug 05 2021 17:37:35, ##########.Trading Info.##########
Trade balance: -243.94 USD, +0.1100 ETH
Return: 54.3300 USD, 20.6401 USD/Day
Volume: 93917.59 USD, 35679.49 USD/Day
Maker ratio: 96.50%, Total: 3682
Fee: 2.12847845 USD, 0.00000000 ETH
##########.##########.##########.##########.##########
Aug 05 2021 17:37:39, buy at 2585.4, place new sell at 2588.4.
Aug 05 2021 17:37:39, Enlarge grid for buy at 2465.4
Aug 05 2021 17:37:44, buy at 2582.4, place new sell at 2585.4.
Aug 05 2021 17:37:44, Enlarge grid for buy at 2462.4
Aug 05 2021 17:37:53, sell at 2585.4, place new buy at 2582.4.
```

# Buy me a coffee

BTC address: `bc1qdqw277tqsqv0jqsc3hk4h2rwfa6zvfel2j09xe`

ETH address: `0xCD5ea947424EaC5c277AbA8EcEDB1Ee760aBd265`
