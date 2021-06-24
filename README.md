# ThinkOrSwim (TOS) Options Dashboard

## Project Description:

Interactive dashboard to filter and analyse stock options contracts (Built using data from ThinkOrSwim's Option Chain API and Plotly Dash components).

## Pre-requisites:

1. Set-up a TDAmeritrade Developer account to receive an API key. This key is necessary to authenticate each API call to extract the necessary data (e.g. stock quote date, option chain data) to required to perform financial analysis.

   * Refer to the docs:

   * Enter the API key into the config.yml file.

     ```yaml
     TOS_API:
         API_KEY: ENTER_TOS_API_KEY_HERE
     ```

     

2. Activate virtual environment in the directory of choice and install the necessary libraries outlined in requirements.txt . 

   ```python
   pip install -r requirements.txt
   ```

