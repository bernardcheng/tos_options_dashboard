import math
import numpy as np
import pandas as pd 
import scipy.stats as st

# Calculates the upper and lower bound for the underlying spot price based on volatility
# probability param: if probability=0.7, probability of stock price in prob_cone is 70%
def prob_cone(stock_price:float, volatility:float, days_ahead:int, probability=0.7, trading_periods:int=252) -> tuple:

    # z_score param indicates the number of std deviations from the mean (i.e. 1.5 std dev covers about 87%)
    # Source: https://stackoverflow.com/questions/20864847/probability-to-z-score-and-vice-versa
    z_score = st.norm.ppf(1-((1-probability)/2))

    # Source: https://www.biocrudetech.com/index.php?option=com_blankcomponent&view=default&Itemid=670
    std_dev = z_score * stock_price * volatility * math.sqrt(days_ahead/trading_periods)

    upper_bound = round(stock_price + std_dev, 2)
    lower_lound = round(stock_price - std_dev, 2)

    return (lower_lound,upper_bound)

def get_prob(stock_price:float, strike_price:float, volatility:float, days_ahead:int, trading_periods:int=252) -> float:

    if None or 0 not in (stock_price, strike_price, volatility, days_ahead):        

        z_score = abs(stock_price - strike_price)/(stock_price * volatility * math.sqrt(days_ahead/trading_periods))

        return 2 * st.norm.cdf(z_score) - 1
    else:
        return 0

# Calculates annualized historical volatility using log returns to return Pandas Series
def get_hist_volatility(price_df, window=30, estimator='log_returns', trading_periods:int=252, clean=True):

    if estimator =='log_returns':

        # price_ls = price_df['close'].tolist()
        # price_ls = price_ls[window:]
        
        # if None not in (price_ls):

        # # Source: https://goodcalculators.com/historical-volatility-calculator/ 
        # # Source: https://quantivity.wordpress.com/2011/02/21/why-log-returns/ 

        #     log_stock_returns = [math.log(price_ls[i+1]/price_ls[i]) for i in range(len(price_ls)-1)]

        #     if len(log_stock_returns) != 0:
        #         ave_log_return = sum(log_stock_returns)/len(log_stock_returns)
        #     else:
        #         ave_log_return = 0
            
        #     returns_diff = [(returns - ave_log_return)**2 for returns in log_stock_returns] 

        #     return math.sqrt(252) * math.sqrt(sum(returns_diff)/(len(returns_diff)-1))

        log_return = (price_df['close'] / price_df['close'].shift(1)).apply(np.log)

        result = log_return.rolling(
            window=window,
            center=False
        ).std() * math.sqrt(trading_periods)

    elif estimator =='garman_klass':
        log_hl = (price_df['high'] / price_df['low']).apply(np.log)
        log_co = (price_df['close'] / price_df['open']).apply(np.log)

        rs = 0.5 * log_hl**2 - (2*math.log(2)-1) * log_co**2
        
        def f(v):
            return (trading_periods * v.mean())**0.5
        
        result = rs.rolling(window=window, center=False).apply(func=f)

    elif estimator =='hodges_tompkins':
        log_return = (price_df['close'] / price_df['close'].shift(1)).apply(np.log)

        vol = log_return.rolling(
            window=window,
            center=False
        ).std() * math.sqrt(trading_periods)

        h = window
        n = (log_return.count() - h) + 1

        adj_factor = 1.0 / (1.0 - (h / n) + ((h**2 - 1) / (3 * n**2)))

        result = vol * adj_factor

    elif estimator =='parkinson':
        rs = (1.0 / (4.0 * math.log(2.0))) * ((price_df['high'] / price_df['low']).apply(np.log))**2.0

        def f(v):
            return (trading_periods * v.mean())**0.5
        
        result = rs.rolling(
            window=window,
            center=False
        ).apply(func=f)

    elif estimator =='rogers_satchell':
        log_ho = (price_df['high'] / price_df['open']).apply(np.log)
        log_lo = (price_df['low'] / price_df['open']).apply(np.log)
        log_co = (price_df['close'] / price_df['open']).apply(np.log)
        
        rs = log_ho * (log_ho - log_co) + log_lo * (log_lo - log_co)

        def f(v):
            return (trading_periods * v.mean())**0.5
        
        result = rs.rolling(
            window=window,
            center=False
        ).apply(func=f)

    elif estimator =='yang_zhang':
        log_ho = (price_df['high'] / price_df['open']).apply(np.log)
        log_lo = (price_df['low'] / price_df['open']).apply(np.log)
        log_co = (price_df['close'] / price_df['open']).apply(np.log)
        
        log_oc = (price_df['open'] / price_df['close'].shift(1)).apply(np.log)
        log_oc_sq = log_oc**2
        
        log_cc = (price_df['close'] / price_df['close'].shift(1)).apply(np.log)
        log_cc_sq = log_cc**2
        
        rs = log_ho * (log_ho - log_co) + log_lo * (log_lo - log_co)
        
        close_vol = log_cc_sq.rolling(
            window=window,
            center=False
        ).sum() * (1.0 / (window - 1.0))
        open_vol = log_oc_sq.rolling(
            window=window,
            center=False
        ).sum() * (1.0 / (window - 1.0))
        window_rs = rs.rolling(
            window=window,
            center=False
        ).sum() * (1.0 / (window - 1.0))

        k = 0.34 / (1.34 + (window + 1) / (window - 1))
        result = (open_vol + k * close_vol + (1 - k) * window_rs).apply(np.sqrt) * math.sqrt(trading_periods)

    if clean:
        return result.dropna()
    else:
        return result