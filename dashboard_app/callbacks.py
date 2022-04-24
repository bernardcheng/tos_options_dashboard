import collections
import numpy as np
import pandas as pd
import statistics as stat
from datetime import datetime, timedelta, date

import plotly.graph_objects as go

from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from dashboard_app.layout import ticker_df_columns, option_chain_df_columns
from lib.tos_api_calls import tos_search, tos_get_quotes, tos_get_option_chain, tos_get_price_hist
from lib.tos_helper import create_pricelist
from lib.gbm import prob_over, prob_under
from lib.stats import get_hist_volatility, prob_cone, get_prob

def register_callbacks(app, API_KEY):

    # Toggle collapsable content for ticker_data HTML element
    @app.callback(
        Output("ticker_table_collapse_content", "is_open"),
        [Input("ticker_data", "n_clicks")],
        [State("ticker_table_collapse_content", "is_open")],
    )
    def toggle_collapse(n, is_open):
        if n:
            return not is_open
        return is_open

    # Update Search bar to return possible listed equity options based on input value as a list
    @app.callback(Output('memory-ticker', 'options'),
                [Input('memory-ticker', 'search_value'), Input('ticker_switch__input','value')],
                [State('memory-ticker', 'value')]
    )
    def update_search(search_value, ticker_switch, value):  

        if not search_value:
            raise PreventUpdate
        
        if ticker_switch:
            json_data = tos_search(search_value, projection='symbol-search', apiKey=API_KEY)
        else:
            json_data = tos_search(search_value, projection='desc-search', apiKey=API_KEY)
        
        try:
            #To-do: Dynamic Options (https://dash.plotly.com/dash-core-components/dropdown)
            options = [{"label": dict_item['description'] + ' (Symbol: ' + dict_item['symbol'] + ')', "value": dict_item['symbol']} for dict_item in json_data.values()]
            if value is not None:
                for selection in value:
                    options.append({"label":selection, "value":selection})
            return options        
        except:
            return []
        

    # Temporarily stores JSON data in the browser (generally safe to store up to 2MB of data)
    @app.callback(Output('storage-historical', 'data'),
                [Input('submit-button-state', 'n_clicks')],
                [State('memory-ticker', 'value')])
    def get_historical_prices(n_clicks, ticker):

        if ticker is None:
            raise PreventUpdate 

        json_data = {}
        json_data[ticker] = tos_get_price_hist(ticker, apiKey=API_KEY)

        return json_data

    # Temporarily stores JSON data in the browser (generally safe to store up to 2MB of data)
    @app.callback(Output('storage-quotes', 'data'),
                [Input('submit-button-state', 'n_clicks')],
                [State('memory-ticker', 'value')])
    def get_price_quotes(n_clicks, ticker):

        if ticker is None:
            raise PreventUpdate          

        return tos_get_quotes(ticker, apiKey=API_KEY)

    # Temporarily stores JSON data in the browser (generally safe to store up to 2MB of data)
    @app.callback(Output('storage-option-chain-all', 'data'),
                [Input('submit-button-state', 'n_clicks'), Input('storage-historical', 'data'), Input('storage-quotes', 'data')],
                [State('memory-ticker', 'value'), State('memory-expdays','value'), State('memory-vol-period','value'), State('memory-confidence','value')])
    def get_option_chain_all(n_clicks, hist_data, quotes_data, ticker, expday_range, volatility_period, confidence_lvl):

        if ticker is None:
            raise PreventUpdate 

        json_data = tos_get_option_chain(ticker, contractType='ALL', rangeType='ALL', apiKey=API_KEY)

        insert = []
        current_date = datetime.now()
        hist_price = hist_data[ticker]

        # Create and append a list of historical share prices of specified ticker
        PRICE_LS = create_pricelist(hist_price)

        trailing_3mth_price_hist = PRICE_LS[-90:]
        trailing_1mth_price_hist = PRICE_LS[-30:]
        trailing_2wk_price_hist = PRICE_LS[-14:]

        current_date = datetime.now()
        
        if volatility_period == "1Y":
            hist_volatility = get_hist_volatility(PRICE_LS)
        elif volatility_period == "3M":
            hist_volatility = get_hist_volatility(trailing_3mth_price_hist)
        elif volatility_period == "1M":
            hist_volatility = get_hist_volatility(trailing_1mth_price_hist)
        elif volatility_period == "2W":
            hist_volatility = get_hist_volatility(trailing_2wk_price_hist)

        stock_price = quotes_data[ticker]['lastPrice']

        # Process API response data from https://developer.tdameritrade.com/option-chains/apis/get/marketdata/chains into Dataframe
        for option_chain_type in ['call','put']:
            for exp_date in json_data[f'{option_chain_type}ExpDateMap'].values():
                for strike in exp_date.values():

                    expiry_date = datetime.fromtimestamp(strike[0]["expirationDate"]/1000.0)
                    option_type = strike[0]['putCall']
                    strike_price = strike[0]['strikePrice']
                    bid_size = strike[0]['bidSize']  
                    ask_size = strike[0]['askSize']  
                    delta_val = strike[0]['delta']
                    total_volume = strike[0]['totalVolume']  
                    open_interest= strike[0]['openInterest']  

                    # strike[0]['daysToExpiration'] can return negative numbers to mess up prob_cone calculations
                    # day_diff = strike[0]['daysToExpiration']                     
                    day_diff = (expiry_date - current_date).days
                    if day_diff < 0:
                        continue
                    elif day_diff > expday_range:
                        break

                    option_premium = round(strike[0]['bid'] * strike[0]['multiplier'],2)
                    roi_val = round(option_premium/(strike_price*100)*100,2)

                    # Option leverage: https://www.reddit.com/r/thetagang/comments/pq1v2v/using_delta_to_calculate_an_options_leverage/
                    if delta_val == 'NaN' or option_premium == 0:
                        option_leverage = 0.0
                    else:
                        option_leverage = round((abs(float(delta_val))*stock_price)/option_premium,3)

                    if day_diff > 0:
                        prob_val = get_prob(stock_price, strike_price, hist_volatility, day_diff)
                    else:
                        prob_val = 0.0

                    lower_bound, upper_bound = prob_cone(PRICE_LS, stock_price, hist_volatility, day_diff, probability=confidence_lvl)

                    option_chain_row = [ticker, expiry_date, option_type, strike_price, day_diff, delta_val, prob_val, open_interest, total_volume, option_premium, option_leverage, bid_size, ask_size, roi_val]
                    insert.append(option_chain_row)

        # Create Empty Dataframe to be populated
        df = pd.DataFrame(insert, columns=[column['name'] for column in option_chain_df_columns])   

        return df.to_json(orient='split')

    # Update Ticker Table from API Response call
    @app.callback(Output('ticker-data-table', 'data'),
                [Input('submit-button-state', 'n_clicks'), Input('storage-historical', 'data'), Input('storage-option-chain-all', 'data'), Input('ticker-data-table', "page_current"), Input('ticker-data-table', "page_size"), Input('ticker-data-table', "sort_by")],
                [State('memory-ticker', 'value')])
    def on_data_set_ticker_table(n_clicks, hist_data, optionchain_data, page_current, page_size, sort_by, ticker):
        
        # Define empty list to be accumulate into Pandas dataframe (Source: https://stackoverflow.com/questions/10715965/add-one-row-to-pandas-dataframe)
        insert = []

        if ticker is None:
            raise PreventUpdate 

        option_chain_response = tos_get_option_chain(ticker, contractType='ALL', rangeType='ALL', apiKey=API_KEY) 
        hist_price = hist_data[ticker]

        # Sanity check on API response data
        if option_chain_response is None or list(option_chain_response.keys())[0] == "error":
            raise PreventUpdate 

        # Create and append a list of historical share prices of specified ticker
        PRICE_LS = create_pricelist(hist_price)

        trailing_3mth_price_hist = PRICE_LS[-90:]
        trailing_1mth_price_hist = PRICE_LS[-30:]
        trailing_2wks_price_hist = PRICE_LS[-14:]

        hist_volatility_1Y = get_hist_volatility(PRICE_LS)
        hist_volatility_3m = get_hist_volatility(trailing_3mth_price_hist)
        hist_volatility_1m = get_hist_volatility(trailing_1mth_price_hist)
        hist_volatility_2w = get_hist_volatility(trailing_2wks_price_hist)

        stock_price = option_chain_response['underlyingPrice']
        stock_price_110percent = stock_price * 1.1
        stock_price_90percent = stock_price * 0.9

        # Process API response data from https://developer.tdameritrade.com/option-chains/apis/get/marketdata/chains into Dataframe
        # Calculation for put call skew: https://app.fdscanner.com/aboutskew 
        low_call_strike, high_call_strike, low_put_strike, high_put_strike = None, None, None, None

        for option_chain_type in ['call','put']:
            for exp_date in option_chain_response[f'{option_chain_type}ExpDateMap'].keys():
                
                # Note: example of exp_date is '2020-12-24:8' where 8 is the days to expiry
                day_diff = int(exp_date.split(':')[1])
                if day_diff < 28 or day_diff >= 35:
                    continue

                # Define boolean variables because option chain is read in acsending order based on strike price
                high_call_strike_found = False
                high_put_strike_found = False

                for strike in option_chain_response[f'{option_chain_type}ExpDateMap'][exp_date].values():

                    strike_price = strike[0]['strikePrice']

                    if option_chain_type == 'call':
                        if strike_price < stock_price_90percent:
                                low_call_strike = strike_price
                                low_call_strike_bid = strike[0]['bid']
                                low_call_strike_ask = strike[0]['ask']
                        elif strike_price > stock_price_110percent:
                            if not high_call_strike_found:
                                high_call_strike = strike_price
                                high_call_strike_bid = strike[0]['bid']
                                high_call_strike_ask = strike[0]['ask']
                                high_call_strike_found = True
                        
                    elif option_chain_type == 'put':
                        if strike_price < stock_price_90percent:
                                low_put_strike = strike_price
                                low_put_strike_bid = strike[0]['bid']
                                low_put_strike_ask = strike[0]['ask']
                        elif strike_price > stock_price_110percent:
                            if not high_put_strike_found:
                                high_put_strike = strike_price
                                high_put_strike_bid = strike[0]['bid']
                                high_put_strike_ask = strike[0]['ask']
                                high_put_strike_found = True                        

        # Ensure if there is an error, will not be displayed
        strike_checklist = [low_call_strike, high_call_strike, low_put_strike, high_put_strike]
        if (all(item is None for item in strike_checklist)):
            raise PreventUpdate

        # Ensuring options pass liquidity checks
        prevent_zero_div = lambda x, y: 0 if (y == 0 or y == None) else x/y
        high_call_strike_askbid = prevent_zero_div(high_call_strike_ask, high_call_strike_bid)
        high_put_strike_askbid = prevent_zero_div(high_put_strike_ask, high_put_strike_bid)
        low_call_strike_askbid = prevent_zero_div(low_call_strike_ask, low_call_strike_bid)
        low_put_strike_askbid = prevent_zero_div(low_put_strike_ask, low_put_strike_bid)

        askbid_checklist = [high_call_strike_askbid, high_put_strike_askbid, low_call_strike_askbid, low_put_strike_askbid]

        liquidity_check = all(askbid > 1.25 for askbid in askbid_checklist)
        if liquidity_check:
            liquidity = 'FAILED'
        else:
            liquidity = 'PASSED'

        # Computing option midpoints
        high_call_strike_midpoint = (high_call_strike_bid + high_call_strike_ask)/2
        high_put_strike_midpoint = (high_put_strike_bid + high_put_strike_ask)/2
        low_call_strike_midpoint = (low_call_strike_bid + low_call_strike_ask)/2
        low_put_strike_midpoint = (low_put_strike_bid + low_put_strike_ask)/2        

        # Computing Interpolated Price
        call_110percent_price = low_call_strike_midpoint - (low_call_strike_midpoint - high_call_strike_midpoint)/(high_call_strike-low_call_strike) * (stock_price_110percent-low_call_strike)
        put_90percent_price = low_put_strike_midpoint + (high_put_strike_midpoint - low_put_strike_midpoint)/(high_put_strike - low_put_strike) * (stock_price_90percent - low_put_strike)

        # Calculate Skew
        if put_90percent_price > call_110percent_price:
            skew_category = 'Put Skew'
            skew = round(put_90percent_price/call_110percent_price,3)
        else:
            skew_category = 'Call Skew'
            skew = round(call_110percent_price/put_90percent_price,3)

        insert.append([ticker, hist_volatility_1Y, hist_volatility_3m, hist_volatility_1m, hist_volatility_2w, skew_category, skew, liquidity])
    
        # Create Empty Dataframe to be populated
        df = pd.DataFrame(insert, columns=[column['id'] for column in ticker_df_columns])

        if len(sort_by):
            dff = df.sort_values(
                [col['column_id'] for col in sort_by],
                ascending=[
                    col['direction'] == 'asc'
                    for col in sort_by
                ],
                inplace=False
            )
        else:
            # No sort is applied
            dff = df

        return dff.iloc[
            page_current*page_size:(page_current+ 1)*page_size
        ].to_dict('records')

    # Update Option Chain Table based on stored JSON value from API Response call 
    @app.callback(Output('option-chain-table', 'data'),
                [Input('submit-button-state', 'n_clicks'), Input('storage-option-chain-all', 'data'), Input('storage-historical', 'data'), Input('storage-quotes', 'data'), Input('option-chain-table', "page_current"), Input('option-chain-table', "page_size"), Input('option-chain-table', "sort_by")],
                [State('memory-ticker', 'value'), State('memory-contract-type','value'), State('memory-roi', 'value'), State('memory-delta', 'value'),  State('memory-expdays','value'), State('memory-confidence','value'), State('memory-vol-period','value')])
    def on_data_set_table(n_clicks, optionchain_data, hist_data, quotes_data, page_current, page_size, sort_by, ticker, contract_type, roi_selection, delta_range, expday_range, confidence_lvl, volatility_period):
        
        # Define empty list to be accumulate into Pandas dataframe (Source: https://stackoverflow.com/questions/10715965/add-one-row-to-pandas-dataframe)
        insert = []

        if hist_data is None:
            raise PreventUpdate 

        # optionchain_df = pd.read_json(optionchain_data, orient='split')
        # df = optionchain_df.loc[(optionchain_df['ROI']>=roi_selection) & (optionchain_df['Delta'].abs()<=delta_range)]
        # df = df.drop(['Lower Bound', 'Upper Bound'], axis=1)
        # df = df.loc[((df['Option Type']=='CALL') & (df['Strike'] >= df['Upper'])) | ((df['Option Type']=='PUT') & (df['Strike'] <= df['Lower']))]
        # print(df)

        option_chain_response = tos_get_option_chain(ticker, contractType=contract_type, apiKey=API_KEY)  
        hist_price = hist_data[ticker]

        # Sanity check on API response data
        if option_chain_response is None or list(option_chain_response.keys())[0] == "error":
            raise PreventUpdate    

        # Create and append a list of historical share prices of specified ticker
        PRICE_LS = create_pricelist(hist_price)

        trailing_3mth_price_hist = PRICE_LS[-90:]
        trailing_1mth_price_hist = PRICE_LS[-30:]
        trailing_2wk_price_hist = PRICE_LS[-14:]

        current_date = datetime.now()

        # hist_volatility = max([get_hist_volatility(PRICE_LS), get_hist_volatility(trailing_3mth_price_hist), get_hist_volatility(trailing_1mth_price_list)])
        if volatility_period == "1Y":
            hist_volatility = get_hist_volatility(PRICE_LS)
        elif volatility_period == "3M":
            hist_volatility = get_hist_volatility(trailing_3mth_price_hist)
        elif volatility_period == "1M":
            hist_volatility = get_hist_volatility(trailing_1mth_price_hist)
        elif volatility_period == "2W":
            hist_volatility = get_hist_volatility(trailing_2wk_price_hist)

        stock_price = quotes_data[ticker]['lastPrice']

        # Process API response data from https://developer.tdameritrade.com/option-chains/apis/get/marketdata/chains into Dataframe
        for option_chain_type in ['call','put']:
            for exp_date in option_chain_response[f'{option_chain_type}ExpDateMap'].values():
                for strike in exp_date.values():

                    expiry_date = datetime.fromtimestamp(strike[0]["expirationDate"]/1000.0)
                    option_type = strike[0]['putCall']
                    strike_price = strike[0]['strikePrice']
                    bid_size = strike[0]['bidSize']  
                    ask_size = strike[0]['askSize']  
                    delta_val = strike[0]['delta']
                    total_volume = strike[0]['totalVolume']  
                    open_interest= strike[0]['openInterest']  

                    # strike[0]['daysToExpiration'] can return negative numbers to mess up prob_cone calculations
                    # day_diff = strike[0]['daysToExpiration']                     
                    day_diff = (expiry_date - current_date).days
                    if day_diff < 0:
                        continue
                    elif day_diff > expday_range:
                        break

                    option_premium = round(strike[0]['bid'] * strike[0]['multiplier'],2)
                    roi_val = round(option_premium/(strike_price*100)*100,2)

                    # Option leverage: https://www.reddit.com/r/thetagang/comments/pq1v2v/using_delta_to_calculate_an_options_leverage/
                    if delta_val == 'NaN' or option_premium == 0:
                        option_leverage = 0.0
                    else:
                        option_leverage = round((abs(float(delta_val))*stock_price)/option_premium,3)

                    lower_bound, upper_bound = prob_cone(PRICE_LS, stock_price, hist_volatility, day_diff, probability=confidence_lvl)

                    if day_diff > 0:
                        prob_val = get_prob(stock_price, strike_price, hist_volatility, day_diff)
                    else:
                        prob_val = 0.0

                    if roi_val >= roi_selection and (abs(delta_val) <= delta_range):
                        if (option_type=='CALL' and strike_price >= upper_bound) or (option_type == "PUT" and strike_price <= lower_bound):
                            option_chain_row = [ticker, expiry_date, option_type, strike_price, day_diff, delta_val, prob_val, open_interest, total_volume, option_premium, option_leverage, bid_size, ask_size, roi_val]
                            if all(col != None for col in option_chain_row):
                                insert.append(option_chain_row)
                        else:
                            continue
                    else:
                        continue

        # Create Empty Dataframe to be populated
        df = pd.DataFrame(insert, columns=[column['id'] for column in option_chain_df_columns])

        if len(sort_by):
            dff = df.sort_values(
                [col['column_id'] for col in sort_by],
                ascending=[
                    col['direction'] == 'asc'
                    for col in sort_by
                ],
                inplace=False
            )
        else:
            # No sort is applied
            dff = df

        return dff.iloc[
            page_current*page_size:(page_current+ 1)*page_size
        ].to_dict('records')

    # Update Price History Graph based on stored JSON value from API Response call 
    @app.callback(Output('price_chart', 'figure'),
                [Input('storage-historical', 'data'), Input('tabs_price_chart', 'value')],
                [State('memory-ticker', 'value')])
    def on_data_set_price_history(hist_data, tab, ticker):

        # Create a Python dict in which a new item will be created upon search (if it doesn't exist before)
        # Source: https://stackoverflow.com/questions/5900578/how-does-collections-defaultdict-work
        aggregation = collections.defaultdict(
            lambda: collections.defaultdict(list)
        )        

        if ticker is None:
            raise PreventUpdate 

        if tab == 'price_tab_1': # 1 Day
            hist_price = tos_get_price_hist(ticker, periodType='day', period=1, frequencyType='minute', frequency=1, apiKey=API_KEY)  
        elif tab == 'price_tab_2': # 5 Days
            hist_price = tos_get_price_hist(ticker, periodType='day', period=5, frequencyType='minute', frequency=5, apiKey=API_KEY)
        elif tab == 'price_tab_3': # 1 Month
            hist_price = tos_get_price_hist(ticker, periodType='month', period=1, frequencyType='daily', frequency=1, apiKey=API_KEY)
        elif tab == 'price_tab_4': # 1 Year
            hist_price = hist_data[ticker]

            if hist_price is None:
                raise PreventUpdate   
        elif tab == 'price_tab_5': # 5 Years
            hist_price = tos_get_price_hist(ticker, periodType='year', period=5, frequencyType='daily', frequency=1, apiKey=API_KEY)  

        for candle in hist_price['candles']:

            a = aggregation[str(ticker)]
            
            a['name'] = str(ticker)
            a['mode'] = 'lines'

            # Price on y-axis, Time on x-axis
            a['y'].append(candle['close'])
            a['x'].append(datetime.fromtimestamp(candle['datetime']/1000.0)) 
        
        return {
            'layout':{'title': {'text':'Price History'}},
            'data': [x for x in aggregation.values()]
        }

    # Update Prob Cone Graph based on stored JSON value from API Response call 
    @app.callback(Output('prob_cone_chart', 'figure'),
                [Input('storage-option-chain-all', 'data'), Input('storage-historical', 'data'), Input('storage-quotes', 'data'), Input('tabs_prob_chart', 'value')],
                [State('memory-ticker', 'value'), State('memory-expdays','value'), State('memory-confidence','value')])
    def on_data_set_prob_cone(optionchain_data, hist_data, quotes_data, tab, ticker, expday_range, confidence_lvl):
        
        # Define empty list to be accumulate into Pandas dataframe (Source: https://stackoverflow.com/questions/10715965/add-one-row-to-pandas-dataframe)
        insert = []   
        data = []

        if hist_data is None or quotes_data is None:
            raise PreventUpdate 

        optionchain_df = pd.read_json(optionchain_data, orient='split')
        mkt_pressure_df = optionchain_df.filter(['Ticker', 'Exp. Date (Local)', 'Option Type', 'Exp. Days', 'Strike', 'Open Int.', 'Total Vol.'])
        mkt_pressure_df['Day'] = mkt_pressure_df['Exp. Days'].apply(lambda x: date.today() + timedelta(days=x))
        mkt_pressure_df['StrikeOpenInterest'] = mkt_pressure_df['Strike'] * mkt_pressure_df['Open Int.']
        mkt_pressure_df['StrikeTotalVolume'] = mkt_pressure_df['Strike'] * mkt_pressure_df['Total Vol.']

        hist_price = hist_data[ticker]   

        # Create and append a list of historical share prices of specified ticker
        PRICE_LS = create_pricelist(hist_price)

        hist_volatility = get_hist_volatility(PRICE_LS)
        stock_price = quotes_data[ticker]['lastPrice']

        if tab == 'prob_cone_tab': # Historical Volatlity            

            for i_day in range(expday_range + 1):

                lower_bound, upper_bound = prob_cone(PRICE_LS, stock_price, hist_volatility, i_day, probability=confidence_lvl)

                insert.append([ticker, (date.today() + timedelta(days=i_day)), stock_price, lower_bound, upper_bound, i_day])

            agg_mkt_pressure_df = mkt_pressure_df.groupby('Day').sum()
            agg_mkt_pressure_df = agg_mkt_pressure_df.reset_index()
            agg_mkt_pressure_df['MktPressOpenInterest'] = agg_mkt_pressure_df['StrikeOpenInterest']/agg_mkt_pressure_df['Open Int.']
            agg_mkt_pressure_df['MktPressTotalVolume'] = agg_mkt_pressure_df['StrikeTotalVolume']/agg_mkt_pressure_df['Total Vol.']
        
        elif tab == 'gbm_sim_tab': # GBM Simulation

            bin_size = 10

            x_ls, y_ls = [], []

            # Using pop stdev is correct: We have the entire popn data for N, thus we dont have to use sample std dev
            std_dev = stat.pstdev(PRICE_LS)
            step = int((std_dev * 2)//bin_size)

            # GBM Variables 
            S = stock_price #price today
            T = expday_range/252 # one year , for one month 1/12, 2months = 2/12 etc
            r = 0.01 # riskfree rate: https://www.treasury.gov/resource-center/data-chart-center/interest-rates/pages/TextView.aspx?data=billrates
            q = 0.007 # dividend rate
            sigma = hist_volatility # annualized volatility
            steps = 1 # no need to have more than 1 for non-path dependent security
            N = 1000000 # larger the better

            for price in np.arange(start=stock_price-std_dev, stop=stock_price, step=step).tolist():
                prob_val = prob_under(price, S, T, r, q, sigma, steps, N, show_plot=False)
                x_ls.append(price)
                y_ls.append(round(prob_val*100,1))

            for price in np.arange(start=stock_price, stop=stock_price+std_dev, step=step).tolist():
                prob_val = prob_over(price, S, T, r, q, sigma, steps, N, show_plot=False)
                x_ls.append(price)
                y_ls.append(round(prob_val*100,1))

            data.append(go.Scatter(x=x_ls, y=y_ls, name='Price Probability', mode='lines+markers', line_shape='spline'))    

        if tab == 'prob_cone_tab': # Historical Volatility
            df_cols = ['Ticker Symbol', 'Day', 'Stock Price', 'Lower Bound', 'Upper Bound', 'Days to Expiry']
            df = pd.DataFrame(insert, columns=df_cols)

            fig = go.Figure()
            # Note: .squeeze() is to convert Dataframe into Series format after df.loc()
            fig.add_trace(go.Scatter(
                        x=df.loc[df['Ticker Symbol']==ticker,['Day']].squeeze(), 
                        y=df.loc[df['Ticker Symbol']==ticker,['Upper Bound']].squeeze(),
                        mode='lines+markers',
                        name=f'{ticker} - Upper Bound',
                        line_shape='spline')
                    )
            fig.add_trace(go.Scatter(
                        x=df.loc[df['Ticker Symbol']==ticker,['Day']].squeeze(), 
                        y=df.loc[df['Ticker Symbol']==ticker,['Lower Bound']].squeeze(),
                        mode='lines+markers',
                        name=f'{ticker} - Lower Bound',
                        line_shape='spline')
                    )
            fig.add_trace(go.Scatter(
                        x=agg_mkt_pressure_df['Day'].squeeze(), 
                        y=agg_mkt_pressure_df['MktPressOpenInterest'].squeeze(),
                        mode='lines+markers',
                        name=f'{ticker} - Market Pressure (Open Interest)',
                        line_shape='spline')
                    )
            fig.add_trace(go.Scatter(
                        x=agg_mkt_pressure_df['Day'].squeeze(), 
                        y=agg_mkt_pressure_df['MktPressTotalVolume'].squeeze(),
                        mode='lines+markers',
                        name=f'{ticker} - Market Pressure (Total Volume)',
                        line_shape='spline')
                    )

            fig.update_layout(
                title=f'Probability Cone ({confidence_lvl*100}% Confidence)',
                title_x=0.5, # Centre the title text
                yaxis_title='Stock Price',
                plot_bgcolor='rgb(256,256,256)' # White Plot background
            )
        elif tab == 'gbm_sim_tab': # GBM Simulation
            fig = go.Figure(data=data)
            fig.update_layout(
                title='Probability Distribution',
                title_x=0.5, # Centre the title text
                yaxis_title='Probability (%)',
                plot_bgcolor='rgb(256,256,256)' # White Plot background
            )

        fig.update_xaxes(showgrid=True, gridcolor='LightGrey')
        fig.update_yaxes(showgrid=True, gridcolor='LightGrey')

        return fig

    # Update Open Interest/Volume Graph based on stored JSON value from API Response call (does not work with multiple tickers selected)
    @app.callback([Output('open_ir_vol', 'figure'),Output('memory_exp_day_graph', 'options')],
                [Input('storage-option-chain-all', 'data')],
                [State('memory-ticker', 'value'), State('memory-expdays','value'), State('memory_exp_day_graph','value')])
    def on_data_set_open_interest_vol(optionchain_data, ticker, expday_range, expday_graph_selection):
        
        if optionchain_data is None:
            raise PreventUpdate
        
        insert = []
        current_date = datetime.now()

        optionchain_df = pd.read_json(optionchain_data, orient='split')
        df = optionchain_df.filter(['Ticker', 'Exp. Date (Local)', 'Option Type', 'Exp. Days', 'Strike', 'Open Int.', 'Total Vol.'])

        # For filtering open i/r graph base on expday options
        expday_options_ls = df['Exp. Days'].unique()
        expday_options = [{"label": f"Strike Date: {(datetime.now()+timedelta(days=days_to_exp.item())).date()} (Days to Expiry: {days_to_exp})", 
                            "value": days_to_exp} for days_to_exp in list(expday_options_ls)]

        fig = go.Figure()

        exp_days_ls = df['Exp. Days'].to_list()
        
        if expday_graph_selection is None:
            expday_select = max(exp_days_ls)
        else:
            expday_select = expday_graph_selection

        # Note: .squeeze() is to convert Dataframe into Series format after df.loc()
        # Colour options: https://developer.mozilla.org/en-US/docs/Web/CSS/color_value
        for option_type in ('PUT','CALL'):
            if option_type == 'PUT':
                bar_color = 'indianred'
            else:
                bar_color = 'lightseagreen'
            fig.add_trace(go.Scatter(
                        x=df.loc[(df['Option Type']==option_type) & (df['Exp. Days']==expday_select),['Strike']].squeeze(), 
                        y=df.loc[(df['Option Type']==option_type) & (df['Exp. Days']==expday_select),['Total Vol.']].squeeze(),
                        mode='lines+markers',
                        name=f'{ticker} - Total {option_type} Volume',
                        line_shape='spline',
                        marker_color=bar_color)
                        )
            fig.add_trace(go.Bar(
                        x=df.loc[(df['Ticker']==ticker) & (df['Option Type']==option_type) & (df['Exp. Days']==expday_select),['Strike']].squeeze(),
                        y=df.loc[(df['Ticker']==ticker) & (df['Option Type']==option_type) & (df['Exp. Days']==expday_select),['Open Int.']].squeeze(),
                        name=f'{ticker} - Open {option_type} Interest',
                        marker_color=bar_color,
                        opacity=0.5)
                    )    
        fig.update_layout(
            title=f'Open Interest/Volume',
            title_x=0.5, # Centre the title text
            xaxis_title='Strike Price',
            yaxis_title='No. of Contracts',
            plot_bgcolor='rgb(256,256,256)' # White Plot background
        )

        return fig, expday_options