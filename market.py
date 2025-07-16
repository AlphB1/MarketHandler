import math
import time

import requests
import json
import datetime

OFFICIAL_MARKET_API = 'https://www.milkywayidle.com/game_data/marketplace.json'
MOOKET_MARKET_API = 'https://mooket.qi-e.top/market/api.json'

with open('init_client_data.json', encoding='utf-8') as f:
    INIT_CLIENT_DATA = json.load(f)


class Market:
    def __init__(self):
        self.market_data = None
        self.market_data_time = None
        self.last_update_time = None
        self.market_cache = None
        self.self_make_items = set()
        self.refresh_market_data()

    def __str__(self):
        return (f"Last Update: {datetime.datetime.fromtimestamp(self.last_update_time).strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Market Data: {datetime.datetime.fromtimestamp(self.market_data_time).strftime('%Y-%m-%d %H:%M:%S')}")

    def refresh_market_data(self, url=MOOKET_MARKET_API):
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        self.market_data = data['marketData']
        self.market_data_time = data['timestamp']
        self.last_update_time = time.time()
        self.market_cache = {}

    def get_price(self, item_hrid: str, mode, enhance_level=0, hourly_rate=1_000_000, force_refresh=False, auto_refresh_time=600) -> int:
        assert item_hrid in self.market_data or item_hrid == '/items/coin'
        assert mode in ('a', 'b')
        assert enhance_level in range(0, 21) or enhance_level in map(str, range(0, 21))
        if item_hrid == '/items/coin':
            return 1
        enhance_level = str(enhance_level)
        item_detail = INIT_CLIENT_DATA['itemDetailMap'][item_hrid]
        assert hourly_rate is None or hourly_rate >= 0
        if force_refresh or time.time() - self.last_update_time > auto_refresh_time:
            self.refresh_market_data()
        if (item_hrid, mode, enhance_level, hourly_rate) in self.market_cache:
            return self.market_cache[(item_hrid, mode, enhance_level, hourly_rate)]
        market_price = self.market_data[item_hrid].get(enhance_level, {}).get(mode, -1)
        if market_price == -1:
            market_price = 1e11 if mode == 'a' else 0
        self_make_price = 1e11
        if mode == 'a' and item_detail['categoryHrid'] == '/item_categories/equipment':
            item_name = item_hrid[item_hrid.rfind('/') + 1:]
            for action, action_detail in INIT_CLIENT_DATA['actionDetailMap'].items():
                if action[action.rfind('/') + 1:] != item_name:
                    continue
                can_upgrade = 'upgradeItemHrid' in action_detail and action_detail['upgradeItemHrid'] != ''
                if math.ceil(int(enhance_level) / 0.7) > 20 or (math.ceil(int(enhance_level) / 0.7) > 0 and not can_upgrade):
                    break
                self_make_price = 0
                if can_upgrade:
                    self_make_price += self.get_price(action_detail['upgradeItemHrid'], 'a', enhance_level=math.ceil(int(enhance_level) / 0.7))
                self_make_price += 0.9 * sum(self.get_price(material['itemHrid'], 'a') * material['count']
                                             for material in action_detail['inputItems'])
                self_make_price += hourly_rate * action_detail['baseTimeCost'] / 3.6e12
                break
        if self_make_price < market_price:
            self.self_make_items.add((item_hrid, enhance_level, hourly_rate))
        self.market_cache[(item_hrid, mode, enhance_level, hourly_rate)] = int(min(market_price, self_make_price)) if mode == 'a' else market_price
        return self.market_cache[(item_hrid, mode, enhance_level, hourly_rate)]

    def find_self_make_items(self):
        for item_hrid, prices in self.market_data.items():
            if '_charm' in item_hrid or 'test_item' in item_hrid:
                continue
            for enhance_level, price in prices.items():
                if self.get_price(item_hrid, 'a', enhance_level) <= self.get_price(item_hrid, 'b', enhance_level) * 0.98:
                    print(f"{item_hrid}+{enhance_level} | "
                          f"{self.get_price(item_hrid, 'a', enhance_level)} <= 0.98 * {self.get_price(item_hrid, 'b', enhance_level)}")


if __name__ == '__main__':
    market = Market()
    print(market)
    print(market.get_price('/items/sundering_crossbow', mode='a'))
    print(market.get_price('/items/sundering_crossbow', mode='b'))
    print(market.get_price('/items/sundering_crossbow', mode='a', enhance_level=10))
    print(market.get_price('/items/sundering_crossbow', mode='b', enhance_level=10))
    print(market.get_price('/items/cheese_enhancer', mode='a', hourly_rate=99999999999))
    print(market.get_price('/items/cheese_enhancer', mode='a', hourly_rate=1_000_000))
    print(market.get_price('/items/cheese_enhancer', mode='a', hourly_rate=0))
    print(market.get_price('/items/cheese_enhancer', mode='a', hourly_rate=0, enhance_level=10))
    print(market.get_price('/items/cheese_enhancer', mode='a', hourly_rate=0, enhance_level=20))

    market.find_self_make_items()
