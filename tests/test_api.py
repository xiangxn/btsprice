import sys
sys.path.append('../btsprice')

import json
from btsprice.feedapi import FeedApi

class TestApi:
    
    def test_call_orders(self):
        # file = open("/Users/necklace/work/BTS/btsprice/config.json")
        with open('config.json','r',encoding='utf8')as file:
            config = json.load(file)
            feedapi = FeedApi(config)
            result=feedapi.fetch_back("CNY")
            print(result)