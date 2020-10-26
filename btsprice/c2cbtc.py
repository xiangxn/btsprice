import json
import asyncio
import aiohttp
import time

class C2CBTC():
    def __init__(self,config=None):
        header = {
            'Upgrade-Insecure-Requests':'1',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3'}
        #jar = aiohttp.DummyCookieJar()
        #jar = aiohttp.CookieJar(unsafe=True)
        #connector = SocksConnector.from_url('socks5://user:password@127.0.0.1:1086')
        self.session = aiohttp.ClientSession(headers=header)#,cookie_jar=jar)#,connector=connector)

    @asyncio.coroutine
    def get_btc_price(self):
        try:
            url = "https://www.okex.com/v3/c2c/tradingOrders/book?t=%s&side=all&baseCurrency=btc&quoteCurrency=cny&userType=certified&paymentMethod=all" % int(round(time.time() * 1000))
            # print(url)
            response = yield from asyncio.wait_for(self.session.get(url), 120)
            result = yield from response.json()
            buy = result["data"]["buy"][0]["price"]
            sell = result["data"]["sell"][-1]["price"]
            price = (float(buy)+float(sell))/2
            #print("get_btc_price", price)
            return price
        except Exception as e:
            print("Error fetching price from c2c okex!")
            print("err:", e)
            return None

    

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    c2c = C2CBTC() 
    loop.run_until_complete(c2c.get_btc_price())
    loop.run_forever()


    