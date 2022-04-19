import os
import argparse
import dash  # (version 1.12.0) pip install dash
import dash_bootstrap_components as dbc

# Source guide: Callbacks layout separation (https://community.plotly.com/t/dash-callback-in-a-separate-file/14122/16)
from dashboard_app.layout import app_layout
from dashboard_app.callbacks import register_callbacks

# app = dash.Dash(__name__)
app = dash.Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])

# Docker support
parser = argparse.ArgumentParser()
parser.add_argument("--docker", help="Change the default server host to 0.0.0.0", action='store_true')
args = parser.parse_args()

# API credentials 
API_KEY = os.environ.get('TOS_API_KEY')

# ------------------------------------------------------------------------------
# App layout
app.layout = app_layout

# ------------------------------------------------------------------------------
# Connect the Plotly graphs with Dash Components
register_callbacks(app, API_KEY)

if __name__ == '__main__':
    if args.docker:
        app.run_server(host='0.0.0.0', debug=True)
    else:
        app.run_server(debug=True)