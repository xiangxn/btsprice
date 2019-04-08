import json
import requests

def orderbook_fubt(symbol):
    api_url = 'https://api.fubt.co/v1'
    endpoint = '/market/depth' #'/market/tickers'
    params = {
        "symbol": symbol,
        "accessKey": "NnAf9toGyV/iBbd5g/8HLObPHCZF2srAMgaP7zRIyAI=",
        "step":"STEP0"
    }
    
    rsp = requests.get(api_url +  endpoint, params=params)
    if rsp.status_code != 200:
        return None
    data = rsp.json()['data']
    order_book_ask = []
    order_book_bid = []
    for item in data['buy']:
        order_book_bid.append([item['price'],item['amount']])
    for item in data['sell']:
        order_book_ask.append([item['price'],item['amount']])

    da = {"bids": order_book_bid, "asks": order_book_ask}
    print(da)

def ticker_fubt(symbol):
    api_url = 'https://api.fubt.co/v1'
    endpoint = '/market/ticker'
    params = {
        "symbol": symbol,
        "accessKey": "NnAf9toGyV/iBbd5g/8HLObPHCZF2srAMgaP7zRIyAI="
    }

    rsp = requests.get(api_url +  endpoint, params=params)
    if rsp.status_code != 200:
        return None
    data = rsp.json()['data']
    print(data)

def orderbook_zb():
    url = "http://47.91.163.52/data/v1/depth"
    params = {
                "market": "bts_usdt",
                "size": 50
                }
    rsp = requests.get(url, params=params)
    print(rsp.json())


orderbook_fubt("BTSFBT")
ticker_fubt("BTSFBT")
#orderbook_zb()