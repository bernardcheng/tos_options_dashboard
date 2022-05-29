import requests
import datetime

# TOS API call to get close 1Y price history of specified ticker symbol, outputs list of close prices 
def tos_get_price_hist(ticker_symbol:str, period=1, periodType='year', frequencyType='daily', frequency=1, startDate=None, endDate=None, apiKey=None):

    if apiKey is None:
        raise ValueError("TOS Option API Key is not defined.")

    # Price History
    endpoint = f'https://api.tdameritrade.com/v1/marketdata/{ticker_symbol}/pricehistory'

    if isinstance(startDate,datetime.datetime) and isinstance(endDate,datetime.datetime):
        startDate = startDate.timestamp() * 1000 # convert date time object into milliseconds before epoch format
        endDate = endDate.timestamp() * 1000  

    payload = {'apikey':apiKey, 
                'periodType':periodType,                   # Values: day (default), month, year, or ytd (year to date)
                'period':period,                           # Values: (periodType = 'day') 1, 2, 3, 4, 5, 10* (periodType = 'month') 1*, 2, 3, 6 (periodType = 'year') 1*, 2, 3, 5, 10, 15, 20 (periodType = 'ytd') 1*
                'frequencyType':frequencyType,             # Values: (periodType = 'day') minute*, (periodType = 'month') daily, weekly*, (periodType = 'year') daily, weekly, monthly*, (periodType = 'ytd') daily, weekly*
                'frequency':frequency,                     # Values: (frequencyType = 'minute') 1*, 5, 10, 15, 30, (frequencyType = 'daily') 1*, (frequencyType = 'weekly') 1*, (frequencyType = 'monthly') 1*
                'endDate':startDate,                       # in milliseconds since epoch
                'startDate':endDate,                       # in milliseconds since epoch
                'needExtendedHoursData': True
                }

    # Make a request
    content = requests.get(url = endpoint, params = payload)

    return content.json()

# TOS API call to get real-time quote data for multiple tickers
def tos_get_quotes(ticker_symbols:str, apiKey=None): 

    if apiKey is None:
        raise ValueError("TOS Option API Key is not defined.")

    # Get Quotes
    endpoint = 'https://api.tdameritrade.com/v1/marketdata/quotes'

    payload = {
        'apikey':apiKey,
        'symbol':ticker_symbols
    }

     # Make a request
    content = requests.get(url = endpoint, params = payload)

    return content.json()

# TOS API call to search or retrieve instrument data, including fundamental data.
def tos_search(symbol:str, projection='desc-search', apiKey=None): 

    if apiKey is None:
        raise ValueError("TOS Option API Key is not defined.")

    # Get Quotes
    endpoint = 'https://api.tdameritrade.com/v1/instruments'

    payload = {
        'apikey':apiKey,
        'symbol':symbol,
        'projection': projection
    }

     # Make a request
    content = requests.get(url = endpoint, params = payload)

    return content.json()

# Makes API call and returns a list of historical prices of the specified ticker
def tos_load_price_hist(ticker_symbol:str, period=1, startDate=None, endDate=None, apiKey=None) -> list:

    if apiKey is None:
            raise ValueError("TOS Option API Key is not defined.")

    price_ls = []

    data = tos_get_price_hist(ticker_symbol, period=period, startDate=startDate, endDate=endDate, apiKey=apiKey)

    for candle in data['candles']:
        price_ls.append(candle['close'])

    return price_ls

# TOS API call to get OTM option type (Call/Put)
def tos_get_option_chain(ticker_symbol:str, contractType='ALL', rangeType='OTM', apiKey=None):

    if apiKey is None:
        raise ValueError("TOS Option API Key is not defined.")

    # Price History
    endpoint = 'https://api.tdameritrade.com/v1/marketdata/chains'

    payload = {'apikey':apiKey, 
                'symbol':ticker_symbol,
                'contractType':contractType,               # Values: CALL, PUT, ALL*
                'strikeCount': None,
                'strategy':'SINGLE',                        # Values: SINGLE, ANALYTICAL, COVERED, VERTICAL, CALENDAR, STRANGLE, STRADDLE, BUTTERFLY, CONDOR, DIAGONAL, COLLAR, ROLL
                'range':rangeType,                             # Values: ITM, NTM (Near-the-money), OTM, SAK (Strikes Above Market), SBK (Strikes Below Market), SNK (Strikes Near Market), ALL (All Strikes)
                'fromDate':None,                           # Values: Valid ISO-8601 formats are: yyyy-MM-dd and yyyy-MM-dd'T'HH:mm:ssz.'
                'toDate':None,                             # Values: Valid ISO-8601 formats are: yyyy-MM-dd and yyyy-MM-dd'T'HH:mm:ssz.'
                'expMonth':'ALL',                          # Values: (frequencyType = 'minute') 1*, 5, 10, 15, 30, (frequencyType = 'daily') 1*, (frequencyType = 'weekly') 1*, (frequencyType = 'monthly') 1*
                'optionType':'S'                           # Values: S (Standard contracts), NS (Non-standard contracts), ALL (All contracts)
                }

    # Make a request
    content = requests.get(url = endpoint, params = payload)

    return content.json()    

# TOS API call to get fundamental data using Ticker symbol 
def tos_get_fundamental_data(ticker_symbol:str, apiKey=None, search='fundamental', raw=False):

    if apiKey is None:
        raise ValueError("TOS Option API Key is not defined.")

    # Search instruments
    endpoint = 'https://api.tdameritrade.com/v1/instruments'

    payload = {'apikey':apiKey, 
                'symbol':ticker_symbol,
                'projection':search,               # Values: symbol-search, symbol-regex, desc-search, desc-regex, fundamental
                }
    
    # Make a request
    content = requests.get(url = endpoint, params = payload)

    if raw:
        return content
    else:
        return content.json() 
    



