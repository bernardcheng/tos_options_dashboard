def create_pricelist(hist_price):
    output_ls = []
    for candle in hist_price['candles']:
        output_ls.append(candle['close'])    
    return output_ls