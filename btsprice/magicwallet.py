import json
import asyncio
import aiohttp
import datetime
import time
import traceback

class Magicwallet():
    def __init__(self,config): 
        header = {
            'User-Agent': 'curl/7.35.0',
            'Accept': '*/*',
            'apikey':config}
        self.session = aiohttp.ClientSession(headers=header)

    
    @asyncio.coroutine
    def get_changerate(self):
        try:
            url = "https://redemption.icowallet.net/api_v2/RechargeAndWithdrawTables/GetListForRechargeAndWithdrawtable" 
            response = yield from asyncio.wait_for(self.session.post(url), 120)
            response = yield from response.read()
            result = json.loads(response.decode("utf-8-sig"))
            wantpricerate = 0
            for pricelist in result:
                if pricelist['datatype'] == '1h':
                    rbitcny = float(pricelist['depositBitCNY'])
                    wbitcny = float(pricelist['withdrawBitCNY'])
                    rfiatcny = float(pricelist['depositFiatCNY'])
                    wfiatcny = float(pricelist['withdrawFiatCNY'])
                    if (rfiatcny + wfiatcny) == 0:
                        for pricelist24 in result:
                            if pricelist24['datatype'] == '24h':
                                rbitcny = float(pricelist24['depositBitCNY'])
                                wbitcny = float(pricelist24['withdrawBitCNY'])
                                rfiatcny = float(pricelist24['depositFiatCNY'])
                                wfiatcny = float(pricelist24['withdrawFiatCNY'])
                                if (rfiatcny + wfiatcny) == 0:
                                    wantpricerate = 1 
                                else:
                                    wantpricerate = round(float((rfiatcny + wfiatcny) / (rbitcny + wbitcny)),2)
                    else:
                        wantpricerate = float((rfiatcny + wfiatcny) / (rbitcny + wbitcny))
            print("premium:%.8f" %(wantpricerate))
            return wantpricerate
        except Exception as e:
            print("Error fetching book from icowallet!")
            print(e)
            return 1


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    magicwallet = Magicwallet() 
    loop.run_until_complete(magicwallet.get_changerate())
    loop.run_forever()