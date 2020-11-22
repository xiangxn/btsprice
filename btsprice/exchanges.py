# -*- coding: utf-8 -*-
import json
import asyncio
import aiohttp
import datetime
import time


class Exchanges():
    def __init__(self, config=None):
        header = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36',
            'Accept': '*/*'
        }

        self.session = aiohttp.ClientSession(headers=header)
        self.order_types = ["bids", "asks"]
        self.config = config

    @asyncio.coroutine
    def orderbook_aex(self, quote="cnc", base="bts"):
        # print("fetching book from aex!", quote, base)
        try:
            url = "http://api.aex.zone/v3/depth.php"
            params = {'coinname': base, 'mk_type': quote}
            # print("params: ",params)
            response = yield from asyncio.wait_for(self.session.get(url, params=params), 120)
            # response = yield from response.read()
            # result = json.loads(response.decode("utf-8-sig"))
            result = yield from response.json()
            result = result['data']
            for order_type in self.order_types:
                for order in result[order_type]:
                    order[0] = float(order[0])
                    order[1] = float(order[1])
            order_book_ask = sorted(result["asks"])
            order_book_bid = sorted(result["bids"], reverse=True)
            return {"bids": order_book_bid, "asks": order_book_ask}
        except Exception as e:
            print("Error fetching book from aex!", e)

    @asyncio.coroutine
    def orderbook_fubt(self, quote="FBT", base="BTS"):
        try:
            url = "https://api.fubt.co/v1/market/depth"
            params = {'symbol': base + quote, 'step': 'STEP0', 'accessKey': self.config['fubt_key']}
            response = yield from asyncio.wait_for(self.session.get(url, params=params), 120)
            result = yield from response.json()
            order_book_ask = []
            order_book_bid = []
            for item in result['data']['buy']:
                order_book_bid.append([item['price'], item['amount']])
            for item in result['data']['sell']:
                order_book_ask.append([item['price'], item['amount']])
            order_book_ask = sorted(order_book_ask)
            order_book_bid = sorted(order_book_bid, reverse=True)

            return {"bids": order_book_bid, "asks": order_book_ask}
        except Exception as e:
            print("Error fetching book from fubt!", e)

    @asyncio.coroutine
    def orderbook_bter(self, quote="cny", base="bts"):
        try:
            url = "http://data.bter.com/api/1/depth/%s_%s" % (base, quote)
            response = yield from asyncio.wait_for(self.session.get(url), 120)
            result = yield from response.json()
            for order_type in self.order_types:
                for order in result[order_type]:
                    order[0] = float(order[0])
                    order[1] = float(order[1])
            order_book_ask = sorted(result["asks"])
            order_book_bid = sorted(result["bids"], reverse=True)
            return {"bids": order_book_bid, "asks": order_book_ask}
        except:
            print("Error fetching book from bter!")

    @asyncio.coroutine
    def orderbook_yunbi(self, quote="cny", base="bts"):
        try:
            url = "https://yunbi.com/api/v2/depth.json"
            params = {'market': base + quote, 'limit': 20}
            response = yield from asyncio.wait_for(self.session.get(url, params=params), 120)
            result = yield from response.json()
            for order_type in self.order_types:
                for order in result[order_type]:
                    order[0] = float(order[0])
                    order[1] = float(order[1])
            order_book_ask = sorted(result["asks"])
            order_book_bid = sorted(result["bids"], reverse=True)
            time = int(result["timestamp"])
            return {"bids": order_book_bid, "asks": order_book_ask, "time": time}
        except:
            print("Error fetching book from yunbi!")

    @asyncio.coroutine
    def orderbook_btsbots(self, quote="CNY", base="BTS"):
        try:
            #url = "https://btsbots.com/api/order?max_results=100&where="
            # url = "http://localhost:5000/api/order?max_results=30&where="
            url = "https://s3.amazonaws.com/roelandp-nl/btsbots-api-result/"
            #params = "a_s==%s;a_b==%s" % (base, quote);
            params = "%s-%s.json" % (base, quote)
            response = yield from asyncio.wait_for(self.session.get(url + params), 120)
            result = yield from response.json()
            order_book_ask = []
            for _o in result["_items"]:
                order_book_ask.append([_o['p'], _o['b_s']])
            #params = "a_s==%s;a_b==%s" % (quote, base)
            params = "%s-%s.json" % (quote, base)
            response = yield from asyncio.wait_for(self.session.get(url + params), 120)
            result = yield from response.json()
            order_book_bid = []
            for _o in result["_items"]:
                order_book_bid.append([1 / _o['p'], _o['b_b']])
            return {"bids": order_book_bid, "asks": order_book_ask}
        except:
            print("Error fetching book from btsbots - roelandp mod ! - " + quote)

    @asyncio.coroutine
    def orderbook_poloniex(self, quote="btc", base="bts"):
        try:
            quote = quote.upper()
            base = base.upper()
            url = "http://poloniex.com/public"
            params = {"command": "returnOrderBook", "currencyPair": "%s_%s" % (quote, base), "depth": 150}

            response = yield from asyncio.wait_for(self.session.get(url, params=params), 120)
            result = yield from response.json()
            for order_type in self.order_types:
                for order in result[order_type]:
                    order[0] = float(order[0])
                    order[1] = float(order[1])
            order_book_ask = sorted(result["asks"])
            order_book_bid = sorted(result["bids"], reverse=True)
            return {"bids": order_book_bid, "asks": order_book_ask}
        except Exception as e:
            print("Error fetching book from poloniex!")

    @asyncio.coroutine
    def orderbook_bittrex(self, quote="btc", base="bts"):
        try:
            quote = quote.upper()
            base = base.upper()
            url = "https://bittrex.com/api/v1.1/public/getorderbook"
            params = {"type": "both", "market": "%s-%s" % (quote, base)}

            response = yield from asyncio.wait_for(self.session.get(url, params=params), 120)
            result = yield from response.json()
            result = result['result']
            order_book_ask = []
            order_book_bid = []
            for order in result['buy']:
                order_book_bid.append([float(order['Rate']), float(order['Quantity'])])
            for order in result['sell']:
                order_book_ask.append([float(order['Rate']), float(order['Quantity'])])
            order_book_ask = sorted(order_book_ask)
            order_book_bid = sorted(order_book_bid, reverse=True)
            return {"bids": order_book_bid, "asks": order_book_ask}
        except Exception as e:
            print("Error fetching book from bittrex!")

    @asyncio.coroutine
    def orderbook_zb(self, quote="btc", base="bts"):
        try:
            quote = quote.lower()
            base = base.lower()
            url = "http://api.zb.cn/data/v1/depth"
            params = {"market": "%s_%s" % (base, quote), "size": 50}
            response = yield from asyncio.wait_for(self.session.get(url, params=params), 120)
            response = yield from response.read()
            result = json.loads(response.decode("utf-8-sig"))
            for order_type in self.order_types:
                for order in result[order_type]:
                    order[0] = float(order[0])
                    order[1] = float(order[1])
            order_book_ask = sorted(result["asks"])
            order_book_bid = sorted(result["bids"], reverse=True)
            return {"bids": order_book_bid, "asks": order_book_ask}
        except Exception as e:
            print("Error fetching book from zb!", e)

    @asyncio.coroutine
    def orderbook_lbank(self, quote="btc", base="bts"):
        try:
            quote = quote.lower()
            base = base.lower()
            url = "https://api.lbank.info/v1/depth.do"
            params = {"symbol": "%s_%s" % (base, quote), "size": 60}
            response = yield from asyncio.wait_for(self.session.get(url, params=params), 120)
            response = yield from response.read()
            result = json.loads(response.decode("utf-8-sig"))
            for order_type in self.order_types:
                for order in result[order_type]:
                    order[0] = float(order[0])
                    order[1] = float(order[1])
            order_book_ask = sorted(result["asks"])
            order_book_bid = sorted(result["bids"], reverse=True)
            return {"bids": order_book_bid, "asks": order_book_ask}
        except Exception as e:
            print("Error fetching book from lbank!", e)

    @asyncio.coroutine
    def orderbook_binance(self, quote="BTC", base="BTS"):
        try:
            quote = quote.upper()
            base = base.upper()
            url = "https://api.binance.com/api/v3/depth"
            params = {"symbol": "%s%s" % (base, quote)}
            response = yield from asyncio.wait_for(self.session.get(url, params=params), 120)
            response = yield from response.read()
            result = json.loads(response.decode("utf-8-sig"))
            for order_type in self.order_types:
                for idx, val in enumerate(result[order_type]):
                    result[order_type][idx] = [float(val[0]), float(val[1])]
            order_book_ask = sorted(result["asks"])
            order_book_bid = sorted(result["bids"], reverse=True)
            return {"bids": order_book_bid, "asks": order_book_ask}
        except Exception as e:
            print("Error fetching book from binance!", e)

    @asyncio.coroutine
    def orderbook_jubi(self, quote="cny", base="bts"):
        try:
            quote = quote.lower()
            base = base.lower()
            url = "https://www.jubi.com/api/v1/depth"
            params = {"coin": "%s" % (base)}
            response = yield from asyncio.wait_for(self.session.get(url, params=params), 120)
            response = yield from response.read()
            result = json.loads(response.decode("utf-8-sig"))
            for order_type in self.order_types:
                for order in result[order_type]:
                    order[0] = float(order[0])
                    order[1] = float(order[1])
            order_book_ask = sorted(result["asks"])
            order_book_bid = sorted(result["bids"], reverse=True)
            return {"bids": order_book_bid, "asks": order_book_ask}
        except Exception as e:
            print("Error fetching book from jubi!", e)

    @asyncio.coroutine
    def orderbook_19800(self, quote="cny", base="bts"):
        try:
            quote = quote.lower()
            base = base.lower()
            url = "https://www.19800.com/api/v1/depth"
            params = {"market": "%s_%s" % (quote, base)}
            response = yield from asyncio.wait_for(self.session.get(url, params=params), 120)
            response = yield from response.read()
            result = json.loads(response.decode("utf-8-sig"))
            result = result['data']
            order_book_ask = []
            order_book_bid = []
            for order in result['bids']:
                order_book_bid.append([float(order['Price']), float(order['Volume'])])
            for order in result['asks']:
                order_book_ask.append([float(order['Price']), float(order['Volume'])])
            order_book_ask = sorted(order_book_ask)
            order_book_bid = sorted(order_book_bid, reverse=True)
            return {"bids": order_book_bid, "asks": order_book_ask}
        except Exception as e:
            print("Error fetching book from 19800!", e)

    @asyncio.coroutine
    def ticker_fubt(self, quote="FBT", base="BTS"):
        try:
            url = "https://api.fubt.co/v1/market/ticker"
            params = {"symbol": base + quote, "accessKey": self.config['fubt_key']}
            response = yield from asyncio.wait_for(self.session.get(url, params=params), 120)
            result = yield from response.json()
            _ticker = {}
            _ticker["last"] = result['data']["last"]
            _ticker["vol"] = result['data']["vol24hour"]
            _ticker["buy"] = result['data']["buy"]
            _ticker["sell"] = result['data']["sell"]
            _ticker["low"] = result['data']["low"]
            _ticker["high"] = result['data']["high"]
            for key in _ticker:
                _ticker[key] = float(_ticker[key])
            _ticker["time"] = int(time.time())
            _ticker["name"] = "fubt.co"
            return _ticker
        except Exception as e:
            print("Error fetching ticker from fubt.co!", e)

    @asyncio.coroutine
    def ticker_btc38(self, quote="cny", base="bts"):
        try:
            url = "http://api.btc38.com/v1/ticker.php?c=%s&mk_type=%s" % (base, quote)
            response = yield from asyncio.wait_for(self.session.get(url), 120)
            response = yield from response.read()
            result = json.loads(response.decode("utf-8-sig"))
            _ticker = {}
            _ticker["last"] = result['ticker']["last"]
            _ticker["vol"] = result['ticker']["vol"]
            _ticker["buy"] = result['ticker']["buy"]
            _ticker["sell"] = result['ticker']["sell"]
            _ticker["low"] = result['ticker']["low"]
            _ticker["high"] = result['ticker']["high"]
            for key in _ticker:
                _ticker[key] = float(_ticker[key])
            _ticker["name"] = "btc38"
            return _ticker
        except Exception as e:
            print("Error fetching ticker from btc38!", e)

    @asyncio.coroutine
    def ticker_poloniex(self, quote="USDT", base="BTC"):
        try:

            url = "https://poloniex.com/public?command=returnTicker"
            response = yield from asyncio.wait_for(self.session.get(url), 120)
            response = yield from response.read()
            result = json.loads(response.decode("utf-8-sig"))["%s_%s" % (quote, base)]
            _ticker = {}
            _ticker["last"] = result["last"]
            _ticker["vol"] = result["baseVolume"]
            _ticker["buy"] = result["highestBid"]
            _ticker["sell"] = result["lowestAsk"]
            _ticker["low"] = result["low24hr"]
            _ticker["high"] = result["high24hr"]
            for key in _ticker:
                _ticker[key] = float(_ticker[key])
            _ticker["name"] = "poloniex"
            return _ticker
        except Exception as e:
            print("Error fetching ticker from poloniex!", e)

    @asyncio.coroutine
    def ticker_binance(self, quote="USDT", base="BTC"):
        try:

            url = "https://www.binance.com/api/v1/ticker/24hr"
            params = {"symbol": "%s%s" % (base, quote)}
            response = yield from asyncio.wait_for(self.session.get(url, params=params), 120)
            response = yield from response.read()
            result = json.loads(response.decode("utf-8-sig"))
            _ticker = {}
            _ticker["last"] = result["lastPrice"]
            _ticker["vol"] = result["volume"]
            _ticker["buy"] = result["bidPrice"]
            _ticker["sell"] = result["askPrice"]
            _ticker["low"] = result["lowPrice"]
            _ticker["high"] = result["highPrice"]
            for key in _ticker:
                _ticker[key] = float(_ticker[key])
            _ticker["name"] = "binance"
            return _ticker
        except Exception as e:
            print("Error fetching ticker from binance!", e)

    @asyncio.coroutine
    def ticker_btcchina(self, quote="cny", base="btc"):
        try:
            url = "https://data.btcchina.com/data/ticker?market=%s%s" % (base, quote)
            response = yield from asyncio.wait_for(self.session.get(url), 120)
            response = yield from response.read()
            result = json.loads(response.decode("utf-8-sig"))
            _ticker = {}
            _ticker["last"] = result['ticker']["last"]
            _ticker["vol"] = result['ticker']["vol"]
            _ticker["buy"] = result['ticker']["buy"]
            _ticker["sell"] = result['ticker']["sell"]
            _ticker["low"] = result['ticker']["low"]
            _ticker["high"] = result['ticker']["high"]
            for key in _ticker:
                _ticker[key] = float(_ticker[key])
            _ticker["time"] = int(result['ticker']["date"])
            _ticker["name"] = "btcchina"
            return _ticker
        except Exception as e:
            print("Error fetching ticker from btcchina!", e)

    @asyncio.coroutine
    def ticker_huobi(self, base="btc"):
        try:
            url = "http://api.huobi.com/staticmarket/ticker_%s_json.js" % base
            response = yield from asyncio.wait_for(self.session.get(url), 120)
            response = yield from response.read()
            result = json.loads(response.decode("utf-8-sig"))
            _ticker = {}
            _ticker["last"] = result['ticker']["last"]
            _ticker["vol"] = result['ticker']["vol"]
            _ticker["buy"] = result['ticker']["buy"]
            _ticker["sell"] = result['ticker']["sell"]
            _ticker["low"] = result['ticker']["low"]
            _ticker["high"] = result['ticker']["high"]
            for key in _ticker:
                _ticker[key] = float(_ticker[key])
            _ticker["time"] = int(result['time'])
            _ticker["name"] = "huobi"
            return _ticker
        except Exception as e:
            print("Error fetching ticker from huobi!", e)

    @asyncio.coroutine
    def ticker_okcoin_cn(self, quote="cny", base="btc"):
        try:
            url = "https://www.okcoin.cn/api/ticker.do?symbol=%s_%s" % (base, quote)
            response = yield from asyncio.wait_for(self.session.get(url), 120)
            response = yield from response.read()
            result = json.loads(response.decode("utf-8-sig"))
            _ticker = {}
            _ticker["last"] = result['ticker']["last"]
            _ticker["vol"] = result['ticker']["vol"]
            _ticker["buy"] = result['ticker']["buy"]
            _ticker["sell"] = result['ticker']["sell"]
            _ticker["low"] = result['ticker']["low"]
            _ticker["high"] = result['ticker']["high"]
            for key in _ticker:
                _ticker[key] = float(_ticker[key])
            _ticker["time"] = int(result['date'])
            _ticker["name"] = "okcoin.cn"
            return _ticker
        except Exception as e:
            print("Error fetching ticker from okcoin cn!", e)

    @asyncio.coroutine
    def ticker_okcoin_com(self, quote="usd", base="btc"):
        try:
            url = "https://www.okcoin.com/api/spot/v3/instruments/%s-%s/ticker" % (base, quote)
            response = yield from asyncio.wait_for(self.session.get(url), 120)
            response = yield from response.read()
            result = json.loads(response.decode("utf-8-sig"))
            _ticker = {}
            _ticker["last"] = result["last"]
            _ticker["vol"] = result["base_volume_24h"]
            _ticker["buy"] = result["ask"]
            _ticker["sell"] = result["bid"]
            _ticker["low"] = result["low_24h"]
            _ticker["high"] = result["high_24h"]
            for key in _ticker:
                _ticker[key] = float(_ticker[key])
            _ticker["time"] = int(time.mktime(time.strptime(result['timestamp'],"%Y-%m-%dT%H:%M:%S.%fZ")))
            _ticker['name'] = 'okcoin.com'
            return _ticker
        except Exception as e:
            print("Error fetching ticker from okcoin.com!", base, quote, e)

    @asyncio.coroutine
    def ticker_gdax(self, quote="usd", base="btc"):
        try:
            url = "https://api.gdax.com/products/%s-%s/ticker" % (base.upper(), quote.upper())
            response = yield from asyncio.wait_for(self.session.get(url), 120)
            response = yield from response.read()
            result = json.loads(response.decode("utf-8-sig"))
            _ticker = {}
            _ticker["last"] = result["price"]
            _ticker["vol"] = result["volume"]
            _ticker["buy"] = result["bid"]
            _ticker["sell"] = result["ask"]
            for key in _ticker:
                _ticker[key] = float(_ticker[key])
            _ticker["low"] = None
            _ticker["high"] = None
            _ticker["time"] = int(datetime.datetime.strptime(result["time"][:19] + "+0000", "%Y-%m-%dT%H:%M:%S%z").timestamp())
            _ticker["name"] = "gdax"
            return _ticker
        except Exception as e:
            print("Error fetching ticker from gdax.com!", e)

    @asyncio.coroutine
    def ticker_bitstamp(self, quote="usd", base="btc"):
        try:
            url = "https://www.bitstamp.net/api/v2/ticker/%s%s" % (base, quote)
            response = yield from asyncio.wait_for(self.session.get(url), 120)
            response = yield from response.read()
            result = json.loads(response.decode("utf-8-sig"))
            _ticker = {}
            _ticker["last"] = result["last"]
            _ticker["vol"] = result["volume"]
            _ticker["buy"] = result["bid"]
            _ticker["sell"] = result["ask"]
            _ticker["low"] = result["low"]
            _ticker["high"] = result["high"]
            for key in _ticker:
                _ticker[key] = float(_ticker[key])
            _ticker["time"] = int(result['timestamp'])
            _ticker["name"] = "bitstamp"
            return _ticker
        except Exception as e:
            print("Error fetching ticker from bitstamp.net!", e)

    @asyncio.coroutine
    def ticker_btce(self, quote="usd", base="btc"):
        try:
            url = "https://btc-e.com/api/3/ticker/%s_%s" % (base, quote)
            response = yield from asyncio.wait_for(self.session.get(url), 120)
            response = yield from response.read()
            result = json.loads(response.decode("utf-8-sig"))
            result = result["%s_%s" % (base, quote)]
            _ticker = {}
            _ticker["last"] = result["last"]
            _ticker["vol"] = result["vol_cur"]
            _ticker["buy"] = result["buy"]
            _ticker["sell"] = result["sell"]
            _ticker["low"] = result["low"]
            _ticker["high"] = result["high"]
            for key in _ticker:
                _ticker[key] = float(_ticker[key])
            _ticker["time"] = int(result['updated'])
            _ticker["name"] = "btce"
            return _ticker
        except Exception as e:
            print("Error fetching ticker from btc-e.com!", e)

    @asyncio.coroutine
    def ticker_bitflyer(self, quote="usd", base="btc"):
        try:
            quote = quote.upper()
            base = base.upper()
            url = "https://api.bitflyer.com/v1/ticker?product_code=%s_%s" % (base, quote)
            response = yield from asyncio.wait_for(self.session.get(url), 120)
            response = yield from response.read()
            result = json.loads(response.decode("utf-8-sig"))
            _ticker = {}
            _ticker["last"] = result["ltp"]
            for key in _ticker:
                _ticker[key] = float(_ticker[key])
            _ticker["time"] = int(time.time())
            _ticker["name"] = "bitflyer_%s" % quote
            return _ticker
        except Exception as e:
            print("Error fetching ticker from bitflyer.com!", e)

    @asyncio.coroutine
    def ticker_bitfinex(self, quote="usd", base="btc"):
        try:
            quote = quote.upper()
            base = base.upper()
            url = "https://api.bitfinex.com/v2/ticker/t%s%s" % (base, quote)
            response = yield from asyncio.wait_for(self.session.get(url), 120)
            response = yield from response.read()
            result = json.loads(response.decode("utf-8-sig"))
            _ticker = {}
            _ticker["last"] = result[6]
            _ticker["vol"] = result[7]
            _ticker["buy"] = result[0]
            _ticker["sell"] = result[2]
            _ticker["low"] = result[9]
            _ticker["high"] = result[8]
            for key in _ticker:
                _ticker[key] = float(_ticker[key])
            _ticker["time"] = int(time.time())
            _ticker["name"] = "bitfinex"
            return _ticker
        except Exception as e:
            print("Error fetching ticker from bitfinex.com!", e)

    @asyncio.coroutine
    def ticker_kraken(self, quote="eur", base="btc"):
        try:
            quote = quote.upper()
            base = base.upper()
            url = "https://api.kraken.com/0/public/Ticker?pair=%s%s" % (base, quote)
            response = yield from asyncio.wait_for(self.session.get(url), 120)
            response = yield from response.read()
            result = json.loads(response.decode("utf-8-sig"))
            for key in result['result']:
                result = result['result'][key]
            _ticker = {}
            _ticker["last"] = result['c'][0]
            for key in _ticker:
                _ticker[key] = float(_ticker[key])
            _ticker["time"] = int(time.time())
            _ticker["name"] = "kraken"
            return _ticker
        except Exception as e:
            print("Error fetching ticker from kraken.com!", e)


if __name__ == "__main__":
    import json
    f = open("config.json", encoding='utf-8')
    config = json.load(f)
    loop = asyncio.get_event_loop()
    exchanges = Exchanges(config)

    @asyncio.coroutine
    def run_task(coro, *args):
        while True:
            result = yield from coro(*args)
            print(result)
            yield from asyncio.sleep(120)

    tasks = [
        # loop.create_task(run_task(exchanges.orderbook_btsbots)),
        # loop.create_task(run_task(exchanges.orderbook_btsbots, "OPEN.BTC", "BTS")),
        loop.create_task(run_task(exchanges.orderbook_aex)),
        # loop.create_task(run_task(exchanges.orderbook_lbank, "BTC", "BTS"))
        loop.create_task(run_task(exchanges.orderbook_binance)),
        #loop.create_task(run_task(exchanges.orderbook_fubt,"FBT","BTS"))
        #loop.create_task(run_task(exchanges.ticker_fubt))
        # loop.create_task(run_task(exchanges.orderbook_19800))
        # loop.create_task(run_task(exchanges.orderbook_yunbi)),
        # loop.create_task(run_task(exchanges.orderbook_poloniex))
        # loop.create_task(run_task(exchanges.ticker_btc38)),
        # loop.create_task(run_task(exchanges.ticker_gdax)),
        # loop.create_task(run_task(exchanges.ticker_btcchina)),
        # loop.create_task(run_task(exchanges.ticker_huobi)),
        # loop.create_task(run_task(exchanges.ticker_okcoin_cn)),
        loop.create_task(run_task(exchanges.ticker_okcoin_com)),
        loop.create_task(run_task(exchanges.ticker_binance,'USDT','BTC'))
        # loop.create_task(run_task(exchanges.ticker_bitfinex)),
        # loop.create_task(run_task(exchanges.ticker_bitflyer, 'jpy', 'btc')),
        # loop.create_task(run_task(exchanges.ticker_bitflyer, "usd", 'btc'))
    ]
    loop.run_until_complete(asyncio.wait(tasks))
    loop.run_forever()
