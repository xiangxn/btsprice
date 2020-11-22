#!/usr/bin/env python3
###############################################################################
#
# The MIT License (MIT)
#
# Copyright (c) Tavendo GmbH
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
###############################################################################

from bts import HTTPRPC
from datetime import datetime
import fractions


class FeedApi(object):
    def __init__(self, config=None):
        self.witnessID = None
        self.blackswan = []
        self.feeds = {}
        self.my_feeds = {}
        self.asset_info = {}
        self.init_feed_temple()
        self.init_default()
        if config:
            self.init_config(config)
        self.init_chain_info()

    def init_feed_temple(self):
        self.feed_temple = {
            "settlement_price": {
                "quote": {
                    "asset_id": "1.3.0",
                    "amount": None
                },
                "base": {
                    "asset_id": None,
                    "amount": None,
                }
            },
            "maintenance_collateral_ratio": 1750,
            "maximum_short_squeeze_ratio": 1020,
            "core_exchange_rate": {
                "quote": {
                    "asset_id": "1.3.0",
                    "amount": None
                },
                "base": {
                    "asset_id": None,
                    "amount": None,
                }
            }
        }
        self.core_exchange_factor = 1.01

    def init_default(self):
        self.asset_list = ["BTC", "SILVER", "GOLD", "TRY", "SGD", "HKD", "NZD", "CNY", "MXN", "CAD", "CHF", "AUD", "GBP", "JPY", "EUR", "USD", "KRW", "ARS"]
        self.alias = {}
        self.witness = None
        self.password = ""
        self.rpc = HTTPRPC("http://localhost:8092")

    def init_config(self, config):
        self.asset_list = config["asset_list"]
        if "alias" in config:
            self.alias = config["alias"]
        self.witness = config["witness"]
        cli_wallet = config["cli_wallet"]
        self.password = cli_wallet["unlock"]
        if 'uri' in cli_wallet:
            uri = cli_wallet["uri"]
        else:
            uri = "http://%s:%s" % (cli_wallet["host"], cli_wallet["port"])
        self.rpc = HTTPRPC(uri)
        self.feed_temple["maintenance_collateral_ratio"] = config["asset_config"]["default"]["maintenance_collateral_ratio"]
        self.feed_temple["maximum_short_squeeze_ratio"] = config["asset_config"]["default"]["maximum_short_squeeze_ratio"]
        self.quote_asset_id = config["asset_config"]["default"]["quote_asset_id"]
        self.feed_temple["settlement_price"]["quote"]["asset_id"] = self.quote_asset_id
        self.feed_temple["core_exchange_rate"]["quote"]["asset_id"] = self.quote_asset_id
        self.core_exchange_factor = config["asset_config"]["default"]["core_exchange_factor"]
        self.quote_asset = config["asset_config"]["default"]["quote_asset"]
        self.custom = config["asset_config"]

    def init_chain_info(self):
        if self.witness:
            self.witnessID = self.rpc.get_witness(self.witness)["witness_account"]
        self.fetch_asset_info()
        self.fetch_feed()

    def encode_feed(self, asset, price, bts_price, custom={}):
        feed_info = self.feed_temple.copy()
        feed_info["settlement_price"]["base"]["asset_id"] = self.asset_info[asset]["id"]
        feed_info["core_exchange_rate"]["base"]["asset_id"] = self.asset_info[asset]["id"]
        if "maintenance_collateral_ratio" in custom:
            feed_info["maintenance_collateral_ratio"] = custom["maintenance_collateral_ratio"]
        if "maximum_short_squeeze_ratio" in custom:
            feed_info["maximum_short_squeeze_ratio"] = custom["maximum_short_squeeze_ratio"]

        if 'min_price' in custom:
            pmin = float(custom["min_price"])
            if price < pmin:
                price = pmin

        bts_quote_precision = self.asset_info[self.quote_asset]["precision"]
        if "quote_asset" in custom:
            quote_precision = self.asset_info[custom["quote_asset"]]["precision"]
            feed_info["settlement_price"]["quote"]["asset_id"] = custom["quote_asset_id"]
            #feed_info["core_exchange_rate"]["quote"]["asset_id"] = custom["quote_asset_id"]
        else:
            quote_precision = self.asset_info[self.quote_asset]["precision"]
            feed_info["settlement_price"]["quote"]["asset_id"] = self.quote_asset_id
            #feed_info["core_exchange_rate"]["quote"]["asset_id"] = self.quote_asset_id
        base_precision = self.asset_info[asset]["precision"]
        if "core_exchange_factor" in custom:
            core_exchange_factor = custom["core_exchange_factor"]
        else:
            core_exchange_factor = self.core_exchange_factor

        price_settle = price * 10**(base_precision - quote_precision)
        if feed_info["settlement_price"]["quote"]["asset_id"] == feed_info["core_exchange_rate"]["quote"]["asset_id"]:
            price_rate = price_settle * core_exchange_factor
        else:
            price_rate = (bts_price * 10**(base_precision - bts_quote_precision)) * core_exchange_factor
        price_settle = fractions.Fraction.from_float(price_settle).limit_denominator(100000)
        price_rate = fractions.Fraction.from_float(price_rate).limit_denominator(100000)

        # print("encode_feed:",price_rate,price_settle,core_exchange_factor)

        feed_info["settlement_price"]["base"]["amount"] = price_settle.numerator
        feed_info["settlement_price"]["quote"]["amount"] = price_settle.denominator
        feed_info["core_exchange_rate"]["base"]["amount"] = price_rate.numerator
        feed_info["core_exchange_rate"]["quote"]["amount"] = price_rate.denominator

        return feed_info

    def get_my_feed(self):
        return self.my_feeds

    def get_quote_assets(self):
        result = []
        c_names = list(self.custom)
        for name in c_names:
            if "quote_asset" in self.custom[name]:
                result.append(self.custom[name]["quote_asset"])
        return result

    def fetch_asset_info(self):
        for asset in self.asset_list + list(self.alias) + self.get_quote_assets():
            a = self.rpc.get_asset(asset)
            # print("{}: {}".format(asset,a))
            self.asset_info[asset] = a  # resolve SYMBOL
            self.asset_info[a["id"]] = a  # resolve id

    def is_blackswan(self, asset):
        return asset in self.blackswan

    def decode_feed(self, price_info):
        base = price_info["base"]
        quote = price_info["quote"]
        base_precision = self.asset_info[base["asset_id"]]["precision"]
        quote_precision = self.asset_info[quote["asset_id"]]["precision"]
        base_amount = (float(base["amount"]) / 10**base_precision)
        quote_amount = (float(quote["amount"]) / 10**quote_precision)
        if quote_amount == 0:
            return 0
        return float(base_amount / quote_amount)

    def is_com_wit_feed(self, asset,f=0x80):
        obj = self.asset_info[asset]
        flags = obj['options']['flags']
        return (flags & f) == f

    def fetch_feed(self):
        for asset in self.asset_list + list(self.alias):
            result = self.rpc.get_bitasset_data(asset)
            self.feeds[asset] = self.decode_feed(result["current_feed"]["settlement_price"])
            self.asset_info[asset]["feed_lifetime_sec"] = result["options"]["feed_lifetime_sec"]
            if int(result['settlement_fund']) != 0:
                self.blackswan.append(asset)
            if not self.witnessID:
                continue
            for feed in result["feeds"]:
                if feed[0] == self.witnessID:
                    ptimestamp = datetime.strptime(feed[1][0] + "+0000", "%Y-%m-%dT%H:%M:%S%z").timestamp()
                    if ptimestamp == 0:
                        continue
                    self.my_feeds[asset] = {}
                    self.my_feeds[asset]["timestamp"] = ptimestamp
                    self.my_feeds[asset]["price"] = self.decode_feed(feed[1][1]["settlement_price"])

    def fetch_black_price(self, symbol, count=1):
        order = self.rpc.get_call_orders(symbol, count)
        feed_data = self.rpc.get_bitasset_data(symbol)
        mssr = feed_data['current_feed']['maximum_short_squeeze_ratio']
        debt = int(order[0]['debt'])
        collateral = int(order[0]['collateral'])
        black_price = mssr * debt / collateral
        # print("mssr: ",mssr,black_price)
        return 1 / black_price

    def publish_feed(self, feeds, bts_price):
        print("publish_feed:", feeds)
        wallet_was_unlocked = False

        if self.rpc.is_locked():
            wallet_was_unlocked = True
            self.rpc.unlock(self.password)
        print("begin feeds......")
        handle = self.rpc.begin_builder_transaction()
        for asset in feeds:
            custom = {}
            if asset in self.custom:
                custom = self.custom[asset]
            feed_info = self.encode_feed(asset, feeds[asset], bts_price, custom)
            # print("publish_feed:",asset,feed_info)
            self.rpc.add_operation_to_builder_transaction(handle,
                                                          [19, {
                                                              "asset_id": self.asset_info[asset]["id"],
                                                              "feed": feed_info,
                                                              "publisher": self.witnessID,
                                                          }])

        # Set fee
        self.rpc.set_fees_on_builder_transaction(handle, "1.3.0")

        # Signing and Broadcast
        try:
            self.rpc.sign_builder_transaction(handle, True)
        except Exception as e:
            print(e)

        if wallet_was_unlocked:
            self.rpc.lock()


if __name__ == '__main__':
    feedapi = FeedApi()
    print(feedapi.feeds)
    print(feedapi.encode_feed("CNY", feedapi.feeds["CNY"]))
