import os
import collections
import argparse
import numpy as np
import pandas as pd
import statistics as stat
from datetime import datetime, timedelta, date

import plotly.graph_objects as go

import dash  # (version 1.12.0) pip install dash
import dash_table
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

from src.tos_api_calls import tos_search, tos_get_quotes, tos_get_option_chain, tos_get_price_hist
from src.gbm import prob_over, prob_under
from src.stats import get_hist_volatility, prob_cone

# app = dash.Dash(__name__)
app = dash.Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])

# Docker support
parser = argparse.ArgumentParser()
parser.add_argument("--docker", help="Change the default server host to 0.0.0.0", action='store_true')
args = parser.parse_args()

# API credentials 
API_KEY = os.environ.get('TOS_API_KEY')

# Data Table Properties
PAGE_SIZE = 30

PLOTLY_LOGO = "https://images.plot.ly/logo/new-branding/plotly-logomark.png"
# ------------------------------------------------------------------------------

# Define column names in Ticker Pandas Dataframe
ticker_df_columns = {
                    'Ticker':'ticker', 
                    '1Y Hist. Vol (%)':'hist_volatility_1Y', 
                    '3M Hist. Vol (%)':'hist_volatility_3m', 
                    '1M Hist. Vol (%)':'hist_volatility_1m',
                    'Skew Category':'skew_category', 
                    'Skew':'skew', 
                    'Liquidity':'liquidity'
                    }

# Define column names in Options Chain Pandas Dataframe
df_columns = {
                'Ticker':'ticker', 
                'Exp. Date (Local)':'exp_date', 
                'Option Type':'option_type', 
                'Strike ($)':'strike_price', 
                'Days to Exp':'exp_days', 
                'Delta':'delta', 
                'Open Interest':'open_interest', 
                'Total Vol':'total_volume',
                'Premium ($)':'premium', 
                'Bid Size':'bid_size', 
                'Ask Size':'ask_size', 
                'ROI (%)':'roi'
            }

# ------------------------------------------------------------------------------
# App layout

app.layout = html.Div([

    dcc.Store(id='storage-historical'),

    dbc.Navbar(
        [
            html.A(
                # Use row and col to control vertical alignment of logo / brand
                dbc.Row(
                    [
                        dbc.Col(html.Img(src=PLOTLY_LOGO, height="30px")),
                        dbc.Col(dbc.NavbarBrand("TOS Options Wheel Dashboard", className="ml-2")),
                    ],
                    align="center",
                    no_gutters=True,
                ),
                href="https://plot.ly",
            ),
        ],
        color="dark",
        dark=True,
    ),
    
    html.Div([
        # Dropdown field of available stock tickers based on description input 
        html.Div([
            dbc.Row([
                dbc.Col(html.H5("Stock Description(s):", style={'text-align': 'left'}), width="auto"),
                dbc.Col(
                    dbc.Checklist(
                        options=[
                            {"label": "Ticker Mode", "value": True},
                        ],
                        value=[],
                        id="ticker_switch__input",
                        inline=True,
                        switch=True,
                    )
                )
            ]),
            dcc.Dropdown(
                id="memory-ticker",
                placeholder="Enter a valid stock name.",
                multi=True,
                style={'width': "100%"} 
            ),
        ],
            style={
                'padding': '10px 5px'
            }
        ),       

        html.Div([
                dbc.Row(
                    [dbc.Col(
                            html.Div([
                                html.H5("ROI Range:"),
                                dcc.Dropdown(
                                        id="memory-roi",
                                        options=[
                                            {"label": "More than 0.5%", "value": 0.5},
                                            {"label": "More than 1%", "value": 1.00},
                                            {"label": "More than 2%", "value": 2.00},
                                            {"label": "More than 3%", "value": 3.00},
                                            {"label": "Ignore ROI", "value": 0.00}
                                        ],
                                        multi=False,
                                        value=1.00
                                    )
                                ],
                                # style={'width': '30%', 'float': 'left', 'display': 'inline-block'}
                            )
                        ),
                        dbc.Col(
                            html.Div([
                                html.H5("Delta Range:"),
                                dcc.Dropdown(
                                        id="memory-delta",
                                        options=[
                                            {"label": "Less than 0.2", "value": 0.2},
                                            {"label": "Less than 0.3", "value": 0.3},
                                            {"label": "Less than 0.4", "value": 0.4},
                                            {"label": "Ignore Delta", "value": 1.0}
                                        ],
                                        multi=False,
                                        value=1.00
                                    )
                                ],
                                # style={'width': '30%', 'display': 'inline-block'}
                            )
                        ),
                        dbc.Col(
                            html.Div([
                                html.H5("Option Contract Type:"),
                                dcc.Dropdown(
                                        id="memory-contract-type",
                                        options=[
                                            {"label": "Put", "value": "PUT"},
                                            {"label": "Call", "value": "CALL"},
                                            {"label": "All", "value": "ALL"}],
                                        multi=False,
                                        value="ALL"
                                    )
                                ],
                                # style={'width': '30%', 'float': 'right', 'display': 'inline-block'}
                                )
                        ),
                    ]
                ),          
        ],
        style={
            # 'borderBottom': 'thin lightgrey solid',
            'padding': '10px 5px'
        }
        ),

        html.Div([
                dbc.Row(
                    [dbc.Col(
                            html.Div([
                                html.H5("Day(s) to Expiration:"),
                                dcc.Dropdown(
                                        id="memory-expdays",
                                        options=[
                                            {"label": "0 - 7 days", "value": 7},
                                            {"label": "0 - 14 days", "value": 14},
                                            {"label": "0 - 21 days", "value": 21},
                                            {"label": "0 - 28 days", "value": 28},
                                            {"label": "0 - 35 days", "value": 35}
                                        ],
                                        multi=False,
                                        value=14.00
                                    )
                                ],
                                # style={'width': '30%', 'float': 'left', 'display': 'inline-block'}
                            )
                        ),
                        dbc.Col(
                            html.Div([
                                html.H5("Confidence Level:"),
                                dcc.Dropdown(
                                        id="memory-confidence",
                                        options=[
                                            {"label": "30% Confidence", "value": 0.3},
                                            {"label": "35% Confidence", "value": 0.35},
                                            {"label": "40% Confidence", "value": 0.4},
                                            {"label": "45% Confidence", "value": 0.45},
                                            {"label": "50% Confidence", "value": 0.5},
                                            {"label": "55% Confidence", "value": 0.55},
                                            {"label": "60% Confidence", "value": 0.6},
                                            {"label": "65% Confidence", "value": 0.65},
                                            {"label": "70% Confidence", "value": 0.7},
                                            {"label": "75% Confidence", "value": 0.75},
                                            {"label": "80% Confidence", "value": 0.8},
                                            {"label": "85% Confidence", "value": 0.85},
                                            {"label": "90% Confidence", "value": 0.9}
                                        ],
                                        multi=False,
                                        value=0.3
                                    )
                                ],
                                # style={'width': '30%', 'display': 'inline-block'}
                            )
                        ),
                        dbc.Col(
                            html.Div([
                                html.H5("Hist. Volatility Period:"),
                                dcc.Dropdown(
                                        id="memory-vol-period",
                                        options=[
                                            {"label": "1 Month", "value": "1M"},
                                            {"label": "3 Months", "value": "3M"},                                           
                                            {"label": "1 Year", "value": "1Y"}
                                        ],
                                        multi=False,
                                        value="1M"
                                    )
                                ],
                                # style={'width': '30%', 'display': 'inline-block'}
                            )
                        ),
                    ]
                ),          
        ],
        style={
            # 'borderBottom': 'thin lightgrey solid',
            'padding': '10px 5px'
        }
        ),

        html.Div([
            dbc.Button("Submit", id='submit-button-state', color="info")
            ],
            style={'margin-bottom': '10px',
                'textAlign':'center',
                'width': '220px',
                'margin':'auto'
                }
        ),
    ],
    className="pretty_container",
    # style={'padding-left': '50px',
    #         'padding-right': '50px',
    #     }
    ),

    html.Div([
        html.Div([
            dcc.Tabs(id='tabs_price_chart', value='price_tab_1', children=[
                dcc.Tab(label='1 Day', value='price_tab_1', className='custom-tab'),
                dcc.Tab(label='5 Days', value='price_tab_2', className='custom-tab'),
                dcc.Tab(label='1 Month', value='price_tab_3', className='custom-tab'),
                dcc.Tab(label='1 Year', value='price_tab_4', className='custom-tab'),
                dcc.Tab(label='5 Years', value='price_tab_5', className='custom-tab'),
            ]),
            dcc.Loading(
                id="loading_price_chart",
                type="default",
                children=html.Div([
                    dcc.Graph(
                        id='price_chart', 
                        figure={
                            'layout':{'title': {'text':'Price History'}}       
                        },
                        config={"displayModeBar": False, "scrollZoom": True}
                    )
                ])
            )
        ],
        className="pretty_container",
        style={'width': '48%', 'display': 'inline-block'}
        ),
        html.Div([ 
            dcc.Tabs(id='tabs_prob_chart', value='prob_tab_1', children=[
                dcc.Tab(label='Historical Volatility', value='prob_tab_1', className='custom-tab'),
                dcc.Tab(label='GBM Simulation', value='prob_tab_2', className='custom-tab'),
            ]),
            dcc.Loading(
                id="loading_prob_cone",
                type="default",
                children=html.Div([
                    dcc.Graph(
                        id='prob_cone_chart', 
                        figure={
                            'layout':{'title': {'text':'Probability Cone'}}       
                        },
                        config={"displayModeBar": False, "scrollZoom": True}
                    )
                ])
            )
        ],
        className="pretty_container",
        style={'width': '48%', 'float': 'right', 'display': 'inline-block'}
        )
    ]),

    html.Div([
        html.H5("Ticker Data \u2754", id='ticker_data'), # Source: https://unicode.org/emoji/charts/full-emoji-list.html
        dbc.Collapse(
            
            dbc.Card(dbc.CardBody(dcc.Markdown('''
            Call skew is defined as the price of 10% OTM calls/10% OTM puts for the next monthly option expiry.  \n
            A call skew of 1.3 means the 10% OTM call is 1.3x the price of 10% OTM put.  \n
            Potential Causes of Call Skew: 
            * Unusual and extreme speculation of stocks. Eg: TSLA battery day
            * Stocks with limited downside but very high upside. Eg: Bankrupt stock trading at a fraction of book value, or SPACs near PIPE value 
            * High demand/Low supply for calls, driving up call prices. 
            * Low demand/High supply for puts, driving down put prices.
              \n
            Put skew is defined as the price of 10% OTM puts/10% OTM calls for the next monthly option expiry.  \n
            A put skew of 2.1 means the 10% OTM put is 2.1x the price of 10% OTM call.  \n
            Potential Causes of Put Skew:
            * Insitutions using the Collar strategy, buying puts and selling calls to limit downside at the cost of upside.
            * High demand/Low supply for puts, driving up put prices. Usual occurence during bear markets.
            * Low demand/High supply for calls, driving down calls prices.
            * Stock had recent huge upward price movements and is grossly overvalued, shifting the supply/demand curve for puts.
            * Dividends contributes to put skew, especially if the dividend is a large percentage of stock price.
            '''))),
            id="ticker_table_collapse_content",
        ),
        dcc.Loading(
                id="loading_ticker-data-table",
                type="default",
                children=html.Div([
                    dash_table.DataTable(
                        id='ticker-data-table',
                        columns=[{'name': col, 'id': ticker_df_columns[col]} for col in ticker_df_columns],
                        page_current=0,
                        page_size=PAGE_SIZE,
                        page_action='custom',
                        sort_action='custom',
                        sort_mode='multi',
                        sort_by=[],
                        style_cell={'textAlign': 'left'},
                        style_data_conditional=[
                            {
                                'if': {
                                    # 'column_id': 'bid_size',
                                    'filter_query': '{liquidity} contains "FAILED"'
                                    },
                                'backgroundColor': '#FF4136',
                                'color': 'white',
                            }, 
                            {
                                'if': {'row_index': 'odd'},
                                'backgroundColor': 'rgb(248, 248, 248)'
                            }
                        ],
                        style_header={
                            'backgroundColor': 'rgb(230, 230, 230)',
                            'fontWeight': 'bold'
                        }
                    )
                ])
            ),
        ],
        style={
            'max-width': '1450px',
            'padding': '10px 5px',
            'margin': 'auto'
            }
    ),    

    html.Div([
        html.H5("Option Chain Data"),
        dcc.Loading(
                id="loading_option-chain-table",
                type="default",
                children=html.Div([
                    dash_table.DataTable(
                        id='option-chain-table',
                        columns=[{'name': col, 'id': df_columns[col]} for col in df_columns],
                        page_current=0,
                        page_size=PAGE_SIZE,
                        page_action='custom',
                        sort_action='custom',
                        sort_mode='multi',
                        sort_by=[],
                        style_cell={'textAlign': 'left'},
                        style_data_conditional=[
                            {
                                'if': {
                                    'column_id': 'bid_size',
                                    'filter_query': '{bid_size} < {ask_size}'
                                    },
                                'color': 'tomato',
                                'fontWeight': 'bold'
                            },
                            {
                                'if': {
                                    'column_id': 'total_volume',
                                    'filter_query': '{total_volume} > {open_interest}'
                                    },
                                'color': 'green',
                                'fontWeight': 'bold'
                            }, 
                            {
                                'if': {'row_index': 'odd'},
                                'backgroundColor': 'rgb(248, 248, 248)'
                            }
                        ],
                        style_header={
                            'backgroundColor': 'rgb(230, 230, 230)',
                            'fontWeight': 'bold'
                        }
                    )
                ])
            ),
        ],
        style={
            'max-width': '1450px',
            'padding': '10px 5px',
            'margin': 'auto'
            }
    )
])

# ------------------------------------------------------------------------------
# Connect the Plotly graphs with Dash Components

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
def get_historical_prices(n_clicks, ticker_ls):

    if ticker_ls is None:
        raise PreventUpdate 

    json_data = {}

    for ticker in ticker_ls:
        json_data[ticker] = tos_get_price_hist(ticker, apiKey=API_KEY)  

    return json_data

# Update Ticker Table from API Response call
@app.callback(Output('ticker-data-table', 'data'),
              [Input('submit-button-state', 'n_clicks'), Input('storage-historical', 'data'), Input('ticker-data-table', "page_current"), Input('ticker-data-table', "page_size"), Input('ticker-data-table', "sort_by")],
              [State('memory-ticker', 'value')])
def on_data_set_ticker_table(n_clicks, hist_data, page_current, page_size, sort_by, ticker_ls):
    
    # Define empty list to be accumulate into Pandas dataframe (Source: https://stackoverflow.com/questions/10715965/add-one-row-to-pandas-dataframe)
    insert = []

    if ticker_ls is None:
        raise PreventUpdate 

    for ticker in ticker_ls: 
        option_chain_response = tos_get_option_chain(ticker, contractType='ALL', rangeType='ALL', apiKey=API_KEY)  
        hist_price = hist_data[ticker]

        # Sanity check on API response data
        if option_chain_response is None or list(option_chain_response.keys())[0] == "error":
            raise PreventUpdate 

        # Create and append a list of historical share prices of specified ticker
        PRICE_LS =[]
        for candle in hist_price['candles']:
            PRICE_LS.append(candle['close'])

        trailing_3mth_price_hist = PRICE_LS[-90:]
        trailing_1mth_price_list = PRICE_LS[-30:]

        hist_volatility_1Y = round(get_hist_volatility(PRICE_LS) * 100.0, 3)
        hist_volatility_3m = round(get_hist_volatility(trailing_3mth_price_hist) * 100.0, 3)
        hist_volatility_1m = round(get_hist_volatility(trailing_1mth_price_list) * 100.0, 3)

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

        insert.append([ticker, hist_volatility_1Y, hist_volatility_3m, hist_volatility_1m, skew_category, skew, liquidity])
    
    # Create Empty Dataframe to be populated
    df = pd.DataFrame(insert, columns=list(ticker_df_columns.values()))

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

# Update Table based on stored JSON value from API Response call 
@app.callback(Output('option-chain-table', 'data'),
              [Input('submit-button-state', 'n_clicks'), Input('storage-historical', 'data'), Input('option-chain-table', "page_current"), Input('option-chain-table', "page_size"), Input('option-chain-table', "sort_by")],
              [State('memory-ticker', 'value'), State('memory-contract-type','value'), State('memory-roi', 'value'), State('memory-delta', 'value'),  State('memory-expdays','value'), State('memory-confidence','value'), State('memory-vol-period','value')])
def on_data_set_table(n_clicks, hist_data, page_current, page_size, sort_by, ticker_ls, contract_type, roi_selection, delta_range, expday_range, confidence_lvl, volatility_period):
    
    # Define empty list to be accumulate into Pandas dataframe (Source: https://stackoverflow.com/questions/10715965/add-one-row-to-pandas-dataframe)
    insert = []

    if hist_data is None:
        raise PreventUpdate 

    for ticker in ticker_ls: 
        option_chain_response = tos_get_option_chain(ticker, contractType=contract_type, apiKey=API_KEY)  
        hist_price = hist_data[ticker]

        # Sanity check on API response data
        if option_chain_response is None or list(option_chain_response.keys())[0] == "error":
            raise PreventUpdate    

        # Create and append a list of historical share prices of specified ticker
        PRICE_LS =[]
        for candle in hist_price['candles']:
            PRICE_LS.append(candle['close'])

        trailing_3mth_price_hist = PRICE_LS[-90:]
        trailing_1mth_price_list = PRICE_LS[-30:]

        # hist_volatility = max([get_hist_volatility(PRICE_LS), get_hist_volatility(trailing_3mth_price_hist), get_hist_volatility(trailing_1mth_price_list)])
        if volatility_period == "1Y":
            hist_volatility = get_hist_volatility(PRICE_LS)
        elif volatility_period == "3M":
            hist_volatility = get_hist_volatility(trailing_3mth_price_hist)
        elif volatility_period == "1M":
            hist_volatility = get_hist_volatility(trailing_1mth_price_list)

        ## Comment-out original stockprice method due to incorrect actual price quotes (intraday)
        # stock_price = option_chain_response['underlyingPrice']
        stock_price = tos_get_quotes(ticker, apiKey=API_KEY)[ticker]['lastPrice']

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
                    current_date = datetime.now()
                    day_diff = (expiry_date - current_date).days
                    if day_diff < 0:
                        continue

                    option_premium = round(strike[0]['bid'] * strike[0]['multiplier'],2)
                    roi_val = round((option_premium/(strike_price*100)) *100,2)

                    lower_bound, upper_bound = prob_cone(PRICE_LS, stock_price, hist_volatility, day_diff, probability=confidence_lvl)
                    if day_diff <= expday_range:
                        if roi_val >= roi_selection and (abs(delta_val) <= delta_range):
                            if (option_type=='CALL' and strike_price >= upper_bound) or (option_type == "PUT" and strike_price <= lower_bound):
                                option_chain_row = [ticker, expiry_date, option_type, strike_price, day_diff, delta_val, open_interest, total_volume, option_premium, bid_size, ask_size, roi_val]
                                if all(col != None for col in option_chain_row):
                                    insert.append(option_chain_row)

    # Create Empty Dataframe to be populated
    df = pd.DataFrame(insert, columns=list(df_columns.values()))

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
def on_data_set_graph(hist_data, tab, ticker_ls):

    # Create a Python dict in which a new item will be created upon search (if it doesn't exist before)
    # Source: https://stackoverflow.com/questions/5900578/how-does-collections-defaultdict-work
    aggregation = collections.defaultdict(
        lambda: collections.defaultdict(list)
    )        

    if ticker_ls is None:
        raise PreventUpdate 

    for ticker in ticker_ls:

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
              [Input('storage-historical', 'data'), Input('tabs_prob_chart', 'value')],
              [State('memory-ticker', 'value'), State('memory-contract-type','value'),  State('memory-expdays','value'), State('memory-confidence','value')])
def on_data_set_graph2(hist_data, tab, ticker_ls, contract_type, expday_range, confidence_lvl):
    
    # Define empty list to be accumulate into Pandas dataframe (Source: https://stackoverflow.com/questions/10715965/add-one-row-to-pandas-dataframe)
    insert = []   
    data = [] 

    if hist_data is None:
        raise PreventUpdate 

    for ticker in ticker_ls: 
        option_chain_response = tos_get_option_chain(ticker, contractType=contract_type, apiKey=API_KEY)  
        hist_price = hist_data[ticker]

        # Sanity check on API response data
        if option_chain_response is None or list(option_chain_response.keys())[0] == "error":
            raise PreventUpdate    

        # Create and append a list of historical share prices of specified ticker
        PRICE_LS =[]
        for candle in hist_price['candles']:
            PRICE_LS.append(candle['close'])

        hist_volatility = get_hist_volatility(PRICE_LS)

        ## Comment-out original stockprice method due to incorrect actual price quotes (intraday)
        # stock_price = option_chain_response['underlyingPrice']
        stock_price = tos_get_quotes(ticker, apiKey=API_KEY)[ticker]['lastPrice']

        if tab == 'prob_tab_1': # Historical Volatlity

            df_cols = ['Ticker Symbol', 'Day', 'Stock Price', 'Lower Bound', 'Upper Bound', 'Days to Expiry']

            for i_day in range(expday_range + 1):

                lower_bound, upper_bound = prob_cone(PRICE_LS, stock_price, hist_volatility, i_day, probability=confidence_lvl)

                insert.append([ticker, (date.today() + timedelta(days=i_day)), stock_price, lower_bound, upper_bound, i_day])

        elif tab == 'prob_tab_2': # GBM Simulation

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

            data.append(go.Bar(name=ticker, x=x_ls, y=y_ls))    

    if tab == 'prob_tab_1': # Historical Volatility
        df = pd.DataFrame(insert, columns=df_cols)
        # fig = go.Figure(
        #         data=[go.Candlestick(
        #             x=df['Day'],
        #             open=df['Stock Price'],
        #             high=df['Upper Bound'],
        #             low=df['Lower Bound'],
        #             close=df['Stock Price']
        #         )]).update_layout(xaxis_rangeslider_visible=False)

        fig = go.Figure()
        for ticker in ticker_ls: 
            # Note: .squeeze() is to convert DAtaframe into Series format after df.loc()
            fig.add_trace(go.Scatter(
                        x=df['Day'], 
                        y=df.loc[df['Ticker Symbol']==ticker,['Upper Bound']].squeeze(),
                        mode='lines+markers',
                        name=f'{ticker} - Upper Bound',
                        line_shape='spline')
                    )
            fig.add_trace(go.Scatter(
                        x=df['Day'], 
                        y=df.loc[df['Ticker Symbol']==ticker,['Lower Bound']].squeeze(),
                        mode='lines+markers',
                        name=f'{ticker} - Lower Bound',
                        line_shape='spline')
                    )

        fig.update_layout(
            title=f'Probability Cone ({confidence_lvl*100}% Confidence)',
            title_x=0.5, # Centre the title text
            yaxis_title='Stock Price',
            plot_bgcolor='rgb(256,256,256)' # White Plot background
        )
    elif tab == 'prob_tab_2': # GBM Simulation
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


if __name__ == '__main__':
    if args.docker:
        app.run_server(host='0.0.0.0', debug=True)
    else:
        app.run_server(debug=True)