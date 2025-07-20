import math
import time

import requests
import json
import datetime

import enhance
import item as item_module
from item import Item

OFFICIAL_MARKET_API = 'https://www.milkywayidle.com/game_data/marketplace.json'
MOOKET_MARKET_API = 'https://mooket.qi-e.top/market/api.json'

with open('init_client_data.json', encoding='utf-8') as f:
    INIT_CLIENT_DATA = json.load(f)


class Market:
    def __init__(self, default_price_a=100_000_000_000, default_price_b=0, enhance_item_mode='fallback', cowbell_price=False, back_slot_price=False):
        self.market_data = None
        self.market_data_time = None
        self.last_update_time = None
        self.market_cache = None
        self.refresh_market_data()
        self.default_price_a = default_price_a
        self.default_price_b = default_price_b
        self.enhance_item_mode = enhance_item_mode
        self.cowbell_price = cowbell_price
        self.back_slot_price = back_slot_price

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

    def get_loot_price(self, item: Item, mode, force_refresh=False, auto_refresh_time=600):
        assert mode in ('a', 'b')
        assert item.item_hrid in INIT_CLIENT_DATA['openableLootDropMap']
        loots = INIT_CLIENT_DATA['openableLootDropMap'][item.item_hrid]
        value = sum(self.get_price(Item(loot['itemHrid']), mode, force_refresh, auto_refresh_time) * loot['dropRate'] *
                    (loot['minCount'] + loot['maxCount']) / 2
                    for loot in loots if loot['itemHrid'] != '/items/purples_gift')
        if item.item_hrid == '/items/purples_gift':
            value *= 1 / 0.98
        if item.item_hrid == '/items/chimerical_chest':
            value -= self.get_price(Item('/items/chimerical_chest_key'), mode, force_refresh, auto_refresh_time)
        if item.item_hrid == '/items/sinister_chest':
            value -= self.get_price(Item('/items/sinister_chest_key'), mode, force_refresh, auto_refresh_time)
        if item.item_hrid == '/items/enchanted_chest':
            value -= self.get_price(Item('/items/enchanted_chest_key'), mode, force_refresh, auto_refresh_time)
        if item.item_hrid == '/items/pirate_chest':
            value -= self.get_price(Item('/items/pirate_chest_key'), mode, force_refresh, auto_refresh_time)
        return int(value)

    def get_dungeon_token_price(self, item: Item, mode, force_refresh=False, auto_refresh_time=600):
        assert mode in ('a', 'b')
        shop_item_detail_map = INIT_CLIENT_DATA['shopItemDetailMap']
        max_price = 0
        for shop_item, detail in shop_item_detail_map.items():
            if detail['costs'][0]['itemHrid'] != item.item_hrid:
                continue
            max_price = max(max_price,
                            self.get_price(Item(detail['itemHrid']), mode, force_refresh, auto_refresh_time) / detail['costs'][0]['count']
                            )
        return int(max_price)

    def get_task_token_price(self, mode, force_refresh=False, auto_refresh_time=600):
        assert mode in ('a', 'b')
        return min(
            self.get_price(Item('/items/large_meteorite_cache'), mode, force_refresh, auto_refresh_time),
            self.get_price(Item('/items/large_artisans_crate'), mode, force_refresh, auto_refresh_time),
            self.get_price(Item('/items/large_treasure_chest'), mode, force_refresh, auto_refresh_time),
        ) // 30

    def get_enhanced_price(self, item: Item, mode, force_refresh=False, auto_refresh_time=600):
        assert mode in ('a', 'b')
        enhancement_costs = item.item_detail['enhancementCosts']
        enhance_cost = sum(
            self.get_price(Item(cost['itemHrid']), mode, force_refresh, auto_refresh_time) * cost['count']
            for cost in enhancement_costs
        )
        protect_cost = min(
            self.get_price(Item(item.item_hrid), mode, force_refresh, auto_refresh_time),
            self.get_price(Item('/items/mirror_of_protection'), mode, force_refresh, auto_refresh_time),
            self.get_price(Item(item.item_detail.get('protectionItemHrids', ['/items/mirror_of_protection'])[0]), mode, force_refresh,
                           auto_refresh_time)
        )
        bonus_rate = 0.05418 + (135.32 - item.item_detail['itemLevel']) * 0.0005 + 0.003
        bonus_speed = 0.129 + 0.0532 + (135.32 - item.item_detail['itemLevel']) * 0.01 + 0.06 + 0.295 + 0.06774
        step_time = 12 / (1 + bonus_speed)
        min_cost = float('inf')
        for pl in range(min(2, item.enhance_level), item.enhance_level + 1):
            act = enhance.Action(item.enhance_level, pl, 0.0129, bonus_rate, enhance_cost, protect_cost)
            total_cost = act.expected_cost + act.expected_steps * step_time * (10_000_000 / 3600)
            min_cost = min(min_cost, total_cost)
        return int(min_cost) + self.get_price(Item(item.item_hrid), mode, force_refresh, auto_refresh_time)

    def get_price(self, item: Item, mode, force_refresh=False, auto_refresh_time=600):
        assert mode in ('a', 'b')
        if force_refresh or time.time() - self.last_update_time > auto_refresh_time:
            self.refresh_market_data()
        if (item, mode) in self.market_cache:
            return self.market_cache[(item, mode)]

        if item.item_hrid == '/items/coin':
            price = 1
        elif item.item_hrid in INIT_CLIENT_DATA['openableLootDropMap']:
            price = self.get_loot_price(item, mode, force_refresh, auto_refresh_time)
        elif item.item_hrid == '/items/cowbell':
            if self.cowbell_price:
                price = self.get_price(Item('/items/bag_of_10_cowbells'), mode, force_refresh, auto_refresh_time) / 10
            else:
                price = 0
        elif item.item_hrid in ('/items/chimerical_token', '/items/sinister_token', '/items/enchanted_token', '/items/pirate_token'):
            price = self.get_dungeon_token_price(item, mode, force_refresh, auto_refresh_time)
        elif item.item_hrid in ('/items/chimerical_quiver', '/items/sinister_cape', '/items/enchanted_cloak'):
            if self.back_slot_price:
                price = self.get_price(Item('/items/mirror_of_protection'), mode, force_refresh, auto_refresh_time)
            else:
                price = 0
        elif item.item_hrid in ('/items/basic_task_badge', '/items/advanced_task_badge', '/items/expert_task_badge'):
            price = 0
        elif item.item_hrid == '/items/task_crystal':
            price = 50 * self.get_task_token_price(mode, force_refresh, auto_refresh_time)
        elif item.item_hrid == '/items/task_token':
            price = self.get_task_token_price(mode, force_refresh, auto_refresh_time)
        else:
            if item.enhance_level > 0 and self.enhance_item_mode in ('force', 'fallback'):
                if self.enhance_item_mode == 'force':
                    price = self.get_enhanced_price(item, mode, force_refresh, auto_refresh_time)
                elif self.enhance_item_mode == 'fallback':
                    price = self.market_data[item.item_hrid].get(str(item.enhance_level), {}).get(mode, -1)
                    if price == -1:
                        price = self.get_enhanced_price(item, mode, force_refresh, auto_refresh_time)
                        print(f'Warning: {item} {mode} not found, use fallback value: {price}')
                else:
                    assert False
            else:
                price = self.market_data[item.item_hrid].get(str(item.enhance_level), {}).get(mode, -1)
                if price == -1:
                    price = self.default_price_a if mode == 'a' else self.default_price_b
                    print(f'Warning: {item} {mode} not found, use default value: {price}')
        # price = min(self.default_price_a, max(self.default_price_b, price))
        self.market_cache[(item, mode)] = int(price)
        return self.market_cache[(item, mode)]


if __name__ == '__main__':
    market = Market()
    print(market)