#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import asyncio
from btsprice.task_exchanges import TaskExchanges
from btsprice.task_pusher import TaskPusher
from btsprice.bts_price_after_match import BTSPriceAfterMatch
from btsprice.feedapi import FeedApi
import time
import logging
import logging.handlers
import os
from prettytable import PrettyTable
from math import fabs
import locale
import json
from pathlib import Path
locale.setlocale(locale.LC_ALL, 'C')


class FeedPrice(object):
    def __init__(self, config=None):
        self.exchange_data = {}
        self.init_config(config)
        self.bts_price = BTSPriceAfterMatch(self.exchange_data)
        self.bts_price.callback = self.change_weight
        self.bts_price.set_weight(self.config["market_weight"])
        self.init_tasks()

        self.setup_log()
        self.init_mpa_info()
        self.magicrate = None
        self.sample = self.config["price_limit"]["filter_minute"] / \
            self.config["timer_minute"]
        if self.sample < 1:
            self.sample = 1
        # don't need feedapi if not witness
        if self.config["witness"]:
            self.feedapi = FeedApi(config)
        else:
            self.feedapi = None
        self.filter_price = None
        if 'alias' in self.config:
            self.alias = self.config['alias']
        else:
            self.alias = {}
        self.lastrate = self.config["negative_feedback_rate"]

    def init_config(self, config):
        if config:
            self.config = config
            return
        config = {}
        config["witness"] = None
        config["pusher"] = {"enable": 0, "user": "", "password": ""}
        config["timer_minute"] = 3
        config["price_limit"] = {"change_min": 0.5, "change_max": 50, "spread": 0.01, "filter_minute": 30}
        config["market_weight"] = {
            "btsbots_cny": 0.5,
            "btsbots_usd": 0.5,
            "btsbots_open.btc": 1,
            "poloniex_btc": 1,
            "yunbi_cny": 1,
            "btc38_cny": 1,
            "chbtc_cny": 1
        }

        self.config = config

    def init_tasks(self):
        loop = asyncio.get_event_loop()
        # init task_exchanges
        task_exchanges = TaskExchanges(self.exchange_data, self.config)
        task_exchanges.set_period(int(self.config["timer_minute"]) * 60)

        # init task_pusher
        if self.config["pusher"]["enable"]:
            topic = "bts.exchanges"
            login_info = None
            if self.config["pusher"]["user"]:
                login_info = self.config["pusher"]
            task_pusher = TaskPusher(self.exchange_data)
            task_pusher.topic = topic
            task_pusher.set_expired(self.config["timer_minute"] * 60 + 30)
            if "publish" in self.config["pusher"]:

                def publish_data(_type, _name, _data):
                    # print("publish: %s %s" % (_type, _name))
                    task_pusher.pusher.publish(topic, _type, _name, _data)

                task_exchanges.handler = publish_data
            task_pusher.run_tasks(loop, login_info)

        task_exchanges.run_tasks(loop)

    def setup_log(self):
        # Setting up Logger
        self.logger = logging.getLogger('bts')
        self.logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s[%(levelname)s]: %(message)s')
        fh = logging.handlers.RotatingFileHandler("/tmp/bts_delegate_task.log")
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)

    def init_mpa_info(self):
        peg_asset_list = [
            "KRW", "BTC", "SILVER", "GOLD", "HKD", "RUB", "CNY", "CAD", "AUD", "GBP", "JPY", "EUR", "USD", "SHENZHEN", "NASDAQC", "NIKKEI", "HANGSENG",
            "SHANGHAI", "TCNY", "TUSD"
        ]
        self.price_queue = {}
        for asset in peg_asset_list:
            self.price_queue[asset] = []
        self.time_publish_feed = 0
        self.adjust_scale = 1.00

    def change_weight(self, orderbook):
        for order_type in self.bts_price.order_types:
            for market in orderbook:
                if market not in self.config["market_weight"]:
                    _weight = 0.0
                else:
                    _weight = self.config["market_weight"][market]
                for _order in orderbook[market][order_type]:
                    _order[1] *= _weight

    def get_bts_price(self):
        # calculate real price
        volume, volume_sum, real_price = self.bts_price.compute_price(spread=self.config["price_limit"]["spread"])
        if real_price is None:
            return real_price, volume
        self.valid_depth = self.bts_price.get_valid_depth(price=real_price, spread=self.config["price_limit"]["spread"])
        self.logger.info("fetch price is %.5f CNY/BTS, volume is %.3f", real_price, volume)
        self.logger.info("efficent depth : %s" % self.valid_depth)
        return real_price, volume

    # these MPA's precision is 100, it's too small,
    # have to change the price
    # but we should fixed these at BTS2.0
    def patch_nasdaqc(self, price):
        if "SHENZHEN" in price:
            price["SHENZHEN"] /= price["CNY"]
        if "SHANGHAI" in price:
            price["SHANGHAI"] /= price["CNY"]
        if "NASDAQC" in price:
            price["NASDAQC"] /= price["USD"]
        if "NIKKEI" in price:
            price["NIKKEI"] /= price["JPY"]
        if "HANGSENG" in price:
            price["HANGSENG"] /= price["HKD"]

    def price_filter(self, bts_price_in_cny):
        price_mode = self.config["price_mode"]
        if price_mode == 1:
            self.filter_price = self.get_average_price(bts_price_in_cny)
        elif price_mode == 2:
            self.filter_price = self.get_median_price(bts_price_in_cny)
        else:
            self.filter_price = self.get_max_price(bts_price_in_cny)
        self.filter_price = self.proc_asset_tag(self.filter_price)
        print("self.filter_price: ",self.filter_price)

    def get_median_price(self, bts_price_in_cny):
        median_price = {}
        for asset in self.price_queue:
            if asset not in self.bts_price.rate_cny or self.bts_price.rate_cny[asset] is None:
                continue
            self.price_queue[asset].append(bts_price_in_cny / self.bts_price.rate_cny[asset])
            if len(self.price_queue[asset]) > self.sample:
                self.price_queue[asset].pop(0)
            median_price[asset] = sorted(self.price_queue[asset])[int(len(self.price_queue[asset]) / 2)]
        for asset in list(self.alias):
            alias = self.alias[asset]
            if alias in median_price:
                median_price[asset] = median_price[alias]
        self.patch_nasdaqc(median_price)
        return median_price

    def get_max_price(self, bts_price_in_cny):
        max_price = {}
        for asset in self.price_queue:
            if asset not in self.bts_price.rate_cny or \
                    self.bts_price.rate_cny[asset] is None:
                continue
            self.price_queue[asset].append(bts_price_in_cny / self.bts_price.rate_cny[asset])
            if len(self.price_queue[asset]) > self.sample:
                self.price_queue[asset].pop(0)
            max_price[asset] = sorted(self.price_queue[asset])[int(len(self.price_queue[asset]) - 1)]
        for asset in list(self.alias):
            alias = self.alias[asset]
            if alias in max_price:
                max_price[asset] = max_price[alias]
        self.patch_nasdaqc(max_price)
        return max_price

    def get_average_price(self, bts_price_in_cny):
        average_price = {}
        for asset in self.price_queue:
            if asset not in self.bts_price.rate_cny or \
                    self.bts_price.rate_cny[asset] is None:
                continue
            self.price_queue[asset].append(bts_price_in_cny / self.bts_price.rate_cny[asset])
            if len(self.price_queue[asset]) > self.sample:
                self.price_queue[asset].pop(0)
            average_price[asset] = sum(self.price_queue[asset]) / len(self.price_queue[asset])
        for asset in list(self.alias):
            alias = self.alias[asset]
            if alias in average_price:
                average_price[asset] = average_price[alias]
        self.patch_nasdaqc(average_price)
        return average_price

    def display_depth(self, volume):
        t = PrettyTable(["market", "bid price", "bid_volume", "ask price", "ask_volume"])
        t.align = 'r'
        t.border = True
        for market in sorted(self.valid_depth):
            _bid_price = "%.8f" % self.valid_depth[market]["bid_price"]
            _bid_volume = "{:,.0f}".format(self.valid_depth[market]["bid_volume"])
            _ask_price = "%.8f" % self.valid_depth[market]["ask_price"]
            _ask_volume = "{:,.0f}".format(self.valid_depth[market]["ask_volume"])
            t.add_row([market, _bid_price, _bid_volume, _ask_price, _ask_volume])
        print(t.get_string())

    def display_price(self):
        price_mode = self.config["price_mode"]
        t = PrettyTable(["asset", "rate(CNY/)", "current(/BTS)", "current(BTS/)", "max(/BTS)", "max(BTS/)", "my feed"])
        if price_mode == 1:
            t = PrettyTable(["asset", "rate(CNY/)", "current(/BTS)", "current(BTS/)", "average(/BTS)", "average(BTS/)", "my feed"])
        elif price_mode == 2:
            t = PrettyTable(["asset", "rate(CNY/)", "current(/BTS)", "current(BTS/)", "median(/BTS)", "median(BTS/)", "my feed"])
        t.align = 'r'
        t.border = True
        for asset in sorted(self.filter_price):
            if asset in self.alias:
                _alias = self.alias[asset]
            else:
                _alias = asset
            if _alias in self.bts_price.rate_cny:
                _rate_cny = "%.3f" % (self.bts_price.rate_cny[_alias])
            else:
                _rate_cny = "%.3f" % (self.bts_price.rate_cny[_alias.replace("1.0","")])
            if _alias in self.price_queue:
                _price_bts1 = "%.8f" % self.price_queue[_alias][-1]
                _price_bts2 = "%.3f" % (1 / self.price_queue[_alias][-1])
            else:
                _alias_source = _alias.replace("1.0","")
                _price_bts1 = "%.8f" % self.price_queue[_alias_source][-1]
                _price_bts2 = "%.3f" % (1 / self.price_queue[_alias_source][-1])
            _median_bts1 = "%.8f" % self.filter_price[_alias]
            _median_bts2 = "%.3f" % (1 / self.filter_price[_alias])
            if self.feedapi and self.feedapi.my_feeds and asset in self.feedapi.my_feeds:
                _my_feed = "%.8f" % self.feedapi.my_feeds[asset]["price"]
            else:
                _my_feed = 'x'
            t.add_row([asset, _rate_cny, _price_bts1, _price_bts2, _median_bts1, _median_bts2, _my_feed])
        print(t.get_string())
        #print("display_price:",sorted(self.filter_price))

    def task_get_price(self):
        bts_price, volume = self.get_bts_price()
        #btc_price = self.bts_price.get_okexc2c_btc_price()
        # print("btc_price:",bts_price)
        if bts_price is None or volume <= 0.0:
            # print("task_get_price:return")
            return

        self.price_filter(bts_price)
        #if "GCNY" in self.feedapi.asset_list:
        #    self.filter_price["GCNY"] = btc_price
        #    self.price_queue["GCNY"][0] = btc_price
        os.system("clear")
        cur_t = time.strftime("%Y/%m/%d %H:%M:%S", time.localtime(time.time()))
        print("[%s] efficent price: %.5f CNY/BTS, depth: %s BTS" % (cur_t, bts_price, "{:,.0f}".format(volume)))
        self.display_depth(volume)
        print()
        self.display_price()

    def check_publish(self, asset_list, my_feeds, real_price):
        need_publish = {}
        #print("check_publish:",asset_list)
        for asset in asset_list:
            if asset not in real_price:
                continue
            if self.config["price_limit"]["check_blackswan"] == 1 and self.feedapi.is_blackswan(asset):
                continue
            if asset not in my_feeds:
                need_publish[asset] = real_price[asset]
                continue
            change = fabs(my_feeds[asset]["price"] - real_price[asset]) * 100.0 / my_feeds[asset]["price"]
            if change >= self.config["price_limit"]["change_max"]:
                continue
            if asset not in my_feeds:
                need_publish[asset] = real_price[asset]
                continue
            if time.time() - my_feeds[asset]["timestamp"] > self.feedapi.asset_info[asset]["feed_lifetime_sec"] - 600:
                need_publish[asset] = real_price[asset]
                continue
            if change > self.config["price_limit"]["change_min"]:
                need_publish[asset] = real_price[asset]
                continue
        #print("check_publish:",need_publish)
        return need_publish

    def price_add_by_magicwallet(self, real_price):
        ready_publish = {}
        self.magicrate = self.bts_price.get_magic_rate()
        mrate = self.config["maigcwalletrate"]
        minr = self.config["maigcwallet_min"]
        print("计算公式为 原有价格*(1+(%s-1)*%s))" % (self.magicrate, mrate))
        for oneprice in real_price:
            ready_publish[oneprice] = real_price[oneprice] * \
                (1 + (self.magicrate - 1) * mrate) * minr
        print(real_price)
        if ready_publish:
            return ready_publish
        else:
            return real_price

    def price_add_by_black(self, real_price):
        ready_publish = {}
        for oneprice in real_price:
            custom = None
            if oneprice in self.config['asset_config']:
                custom = self.config['asset_config'][oneprice]
            # print("real_price[oneprice]: ",oneprice, real_price[oneprice])
            if custom and "black_min" in custom:
                minr = custom["black_min"]
                if minr != 0:
                    b_price = self.feedapi.fetch_black_price(oneprice)
                    if real_price[oneprice] <= b_price:
                        ready_publish[oneprice] = b_price * minr
                    else:
                        ready_publish[oneprice] = real_price[oneprice]
                else:
                    ready_publish[oneprice] = real_price[oneprice]
            else:
                ready_publish[oneprice] = real_price[oneprice]
        btc_price = self.bts_price.get_okexc2c_btc_price()
        if btc_price and "GCNY" in self.feedapi.asset_list:
            ready_publish["GCNY"] = btc_price
            #self.price_queue["GCNY_____"].= btc_price

        #print("price_add_by_black:",ready_publish)
        if ready_publish:
            return ready_publish
        else:
            return real_price

    def price_negative_feedback(self, price):
        ready_publish = {}
        self.magicrate = self.bts_price.get_magic_rate()
        print("magicrate:%.8f" % (self.magicrate))
        print("premium:%.8f" % (1 - self.magicrate))
        print("lastrate:%.8f" % (self.lastrate))
        fmax = self.config["negative_feedback_max"]
        fmin = self.config["negative_feedback_min"]
        # frate = self.config["negative_feedback_rate"]
        rate = (1 - self.magicrate) * self.config["price_coefficient"]
        rate = self.lastrate - rate
        rate = max(rate, fmin)
        rate = min(rate, fmax)
        self.lastrate = rate
        print("newrate:%.8f" % (self.lastrate))
        if rate == 0:
            self.lastrate = self.config["negative_feedback_rate"]
            rate = 1
        else:
            rate = 1 + rate
        for oneprice in price:
            if oneprice == "CNY":
                ready_publish[oneprice] = price[oneprice] * rate
            else:
                ready_publish[oneprice] = price[oneprice]
        #print(price)
        if ready_publish:
            return ready_publish
        else:
            return price

    def get_asset_config(self, symbol):
        cnf = self.config['asset_config']['default']
        if symbol in self.config['asset_config']:
            tmp = self.config['asset_config'][symbol]
            for k in tmp.keys():
                cnf[k] = tmp[k]
        return cnf

    def proc_baip2(self, ):
        d_path = "./baip2.data.json"
        price_data = {}
        if Path(d_path).is_file():
            datafile = open(d_path, "r")
            price_data = json.load(datafile)
        max_item = int(60 / self.config['timer_minute'] * 48)
        # print(max_item)
        for symbol in self.filter_price:
            if symbol in price_data:
                p = 0
                c = len(price_data[symbol])
                for price in price_data[symbol]:
                    p += price
                po = p / c
                last_p = self.filter_price[symbol]
                if self.get_asset_config(symbol)['use_baip2'] > 0:
                    self.filter_price[symbol] = max(last_p, po)
                if c >= max_item:
                    tmp = price_data[symbol][1:]
                    tmp.append(last_p)
                    price_data[symbol] = tmp
                else:
                    price_data[symbol].append(last_p)
            else:
                price_data[symbol] = [self.filter_price[symbol]]
        with open(d_path, "w") as f:
            json.dump(price_data, f)
            
    def proc_asset_tag(self, prices, tag="1.0"):
        ready_publish = {}
        for oneprice in prices:
            ready_publish[oneprice] = prices[oneprice]
            if oneprice in self.config["ver_assets"]:
                ver_asset = "{}{}".format(oneprice,tag)
                if ver_asset in self.config['asset_list']:
                    ready_publish[ver_asset] = prices[oneprice]
                
        if ready_publish:
            return ready_publish
        return prices

    def task_publish_price(self):
        nf = self.config["negative_feedback"]
        if nf == 1:
            self.filter_price = self.price_negative_feedback(self.filter_price)
        elif nf == 2:
            self.filter_price = self.price_add_by_black(self.filter_price)

        #print("task_publish_price:",self.filter_price)
        if not self.config["witness"]:
            return
        self.feedapi.fetch_feed()
        self.proc_baip2()
        btscny = self.filter_price["CNY"]
        # print("task_publish_price",self.filter_price)
        feed_need_publish = self.check_publish(self.feedapi.asset_list + list(self.alias), self.feedapi.my_feeds, self.filter_price)
        if feed_need_publish:
            feed_list = {}
            for asset in feed_need_publish:
                if asset in self.feedapi.my_feeds:
                    feed_list[asset] = feed_need_publish[asset]
            self.logger.info("publish feeds: %s" % feed_list)
            self.feedapi.publish_feed(feed_need_publish, btscny)

    @asyncio.coroutine
    def run_task(self):
        config_timer = int(self.config["timer_minute"]) * 60
        try:
            while True:
                self.task_get_price()
                #print("run_task:",self.filter_price)
                if self.filter_price:
                    self.task_publish_price()
                if self.filter_price:
                    timer = config_timer
                else:
                    timer = 3
                yield from asyncio.sleep(timer)
        except Exception as e:
            print("Error: ",e)

    def execute(self):
        loop = asyncio.get_event_loop()
        loop.create_task(self.run_task())
        loop.run_forever()
        loop.close()


if __name__ == '__main__':
    feedprice = FeedPrice()
    feedprice.execute()
