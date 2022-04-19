import dash_table
from dash_table.Format import Format
from dash_table import FormatTemplate
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc

# Data Table Properties
PAGE_SIZE = 30

# Dash table value formatting
money = FormatTemplate.money(0)
money_full=FormatTemplate.money(2)
percentage = FormatTemplate.percentage(2)

# Define column names in Ticker Pandas Dataframe
ticker_df_columns=[
    dict(id='ticker', name='Ticker'),
    dict(id='hist_volatility_1Y', name='1Y Hist. Vol', type='numeric', format=percentage),
    dict(id='hist_volatility_3m', name='3M Hist. Vol', type='numeric', format=percentage),
    dict(id='hist_volatility_1m', name='1M Hist. Vol', type='numeric', format=percentage),
    dict(id='hist_volatility_2w', name='2w Hist. Vol', type='numeric', format=percentage),
    dict(id='skew_category', name='Skew Category'),
    dict(id='skew', name='Skew'),
    dict(id='liquidity', name='Liquidity'),
]

# Define column names in Options Chain Pandas Dataframe
option_chain_df_columns=[
    dict(id='ticker', name='Ticker'),
    dict(id='exp_date', name='Exp. Date (Local)'),
    dict(id='option_type', name='Option Type'),
    dict(id='strike_price', name='Strike', type='numeric', format=money_full),
    dict(id='exp_days', name='Exp. Days'),
    dict(id='delta', name='Delta'),
    dict(id='prob_val', name='Conf. Prob', type='numeric', format=percentage),
    dict(id='open_interest', name='Open Int.', type='numeric', format=Format().group(True)),
    dict(id='total_volume', name='Total Vol.', type='numeric', format=Format().group(True)),
    dict(id='premium', name='Premium', type='numeric', format=money),
    dict(id='option_leverage', name='Leverage'),
    dict(id='bid_size', name='Bid Size', type='numeric', format=Format().group(True)),
    dict(id='ask_size', name='Ask Size', type='numeric', format=Format().group(True)),
    dict(id='roi_val', name='ROI')
]

# ------------------------------------------------------------------------------
# App layout

app_layout = html.Div([

    dcc.Store(id='storage-historical'),
    dcc.Store(id='storage-quotes'),
    dcc.Store(id='storage-option-chain-all'),
    dbc.Navbar(
        [
            html.A(
                # Use row and col to control vertical alignment of logo / brand
                dbc.Row(
                    [
                        dbc.Col(dbc.NavbarBrand("TOS Options Wheel Dashboard", className="ml-2")),
                    ],
                    align="center",
                    no_gutters=True,
                ),
                href="#",
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
                                            {"label": "0 - 35 days", "value": 35},
                                            {"label": "0 - 42 days", "value": 42},
                                            {"label": "0 - 49 days", "value": 49},
                                            {"label": "0 - 56 days", "value": 56}
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
                                            {"label": "2 Weeks", "value": "2W"},
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
            dcc.Tabs(id='tabs_prob_chart', value='prob_cone_tab', children=[
                dcc.Tab(label='Historical Volatility', value='prob_cone_tab', className='custom-tab'), 
                dcc.Tab(label='GBM Simulation', value='gbm_sim_tab', className='custom-tab'),
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
        dcc.Dropdown(
            id="memory_exp_day_graph",
            placeholder="Select expiration date after entering the above fields.",
            multi=False,
            style={'width': "100%", 'padding-bottom': '10px',} 
        ),              
        dcc.Loading(
            id="loading_open_ir_vol",
            type="default",
            children=html.Div([
                dcc.Graph(
                    id='open_ir_vol', 
                    figure={
                        'layout':{'title': {'text':'Open Interest/Volume Plot'}}       
                    },
                    config={"displayModeBar": False, "scrollZoom": True}
                )
            ])
        ),               
    ], 
    className="pretty_container",
    ),

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
                        columns=ticker_df_columns,
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
                        columns=option_chain_df_columns,
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