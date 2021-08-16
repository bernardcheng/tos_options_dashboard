# ThinkOrSwim (TOS) Options Dashboard

## Project Description:

An interactive dashboard to filter and analyze stock options contracts (Built using data from ThinkOrSwim's Option Chain API and Plotly Dash components). It is useful for quickly scanning option chains to look for individual profitable options contracts to trade on. 

Filter options include:

* Return of Investment (ROI) Range: Percentage of premium received (by selling an contract) over the underlying amount (strike price * 100)
* Delta Range: Represents current probability that the option contract will expire [in-the-money](https://www.investopedia.com/terms/i/inthemoney.asp) (i.e. Option is exercised)
* Option Contract Type: Call/Put/All (both call and put options)
* Days to expiration: No. of days till options contract is set to expire

## Pre-requisites:

1. Set-up a TDAmeritrade Developer account to receive an API key. This key is necessary to authenticate each API call to extract the necessary data (e.g. stock quote date, option chain data) to required to perform financial analysis.

   * [TOS Developers Home Page](https://developer.tdameritrade.com/)

   * [Reddit: Guide to TOS Developer App set-up](https://www.reddit.com/r/algotrading/comments/914q22/successful_access_to_td_ameritrade_api/)

   * If you are using Docker, proceed to step 1a), else go to step 1b). 

     a) Enter the API key into the Dockerfile.

     ```dockerfile
     ARG api_key = ENTER_API_KEY_HERE
     ```

     b) Set the API key as an environment variable (it should be named TOS_API_KEY). 

     * [Environment Variables in Windows](https://www.youtube.com/watch?v=IolxqkL7cD8&t=136s)
     * [Environment Variables in Mac/Linux](https://www.youtube.com/watch?v=5iWhQWVXosU)

2. Activate virtual environment in the directory of choice and install the necessary libraries outlined in requirements.txt . 

   ```python
   pip install -r requirements.txt
   ```

3. [Docker Option] To build and run the docker container, run the following lines in the terminal/command prompt. After running docker run, proceed with step 2 of the Usage section.

   	* [Docker Troubleshooting](https://www.thegeekdiary.com/docker-troubleshooting-conflict-unable-to-delete-image-is-being-used-by-running-container/)

   ```terminal
   docker build -t tos_options_dashboard .
   docker run -p 8050:8050 tos_options_dashboard
   ```
   
   * Note: You can override the default value of the TOS API Key set in Dockerfile by running the following command during build
   
     ```dockerfile
     docker build --build-arg api_key=<NEW_API_KEY> -t tos_options_dashboard .
     ```

## Usage:

1. Run the python file dashboard.py

   ```python
   python dashboard.py
   ```

2. The Dashboard would be running on local host (Port: 8050) by default. Open the web browser and enter the corresponding localhost address (http://127.0.0.1:8050/) to view the Dashboard.

3. To start using the Dashboard, activate Ticker mode before entering the stock ticker of interest (e.g. AAPL for Apple Inc. stock).

   There are several options characteristic filter options to choose from:

   * Return on Investment (ROI) Range: (Default: More than 1%)
   * Delta Range: (Default: Ignore Delta value)
   * Option Contract Type: Call/Put/All (Default: All)
   * Day(s) to Expiration: 0-100 days (Default: 14 days)

   To proceed with the search function, select on the **Submit** button.

   ![step3-search](/doc_img/step3-search.png)

4. The corresponding historical price charts for the specified stock ticker is generated along with the associated cone of probability (Default: 70% confidence level).

   ![step4-results](/doc_img/step4-results.png)

5. The dashboard also measures the Call / Put skew of the specified ticker, as well as listing the option contracts that matches the filter requirements in Step 3.

   * Put Skew: Defined as the price of 10% OTM puts/10% OTM calls for the next monthly option expiry
   * Call Skew: Defined as the price of 10% OTM calls/10% OTM puts for the next monthly option expiry.

   ![step5-results](/doc_img/step5-results.png)
