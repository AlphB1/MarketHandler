import json
import pprint

import market
import item
from item import Item
from init_client_data import INIT_CLIENT_DATA


def get_house_price(market: market.Market, house_hrid, level, mode):
    house_room_detail = INIT_CLIENT_DATA['houseRoomDetailMap'][house_hrid]
    upgrade_cost = house_room_detail['upgradeCostsMap'][str(level)]
    return sum(
        market.get_price(Item(cost['itemHrid']), mode) * cost['count']
        for cost in upgrade_cost
    )


def get_player_networth(market: market.Market, data):
    ability_networth = {'a': 0, 'b': 0}
    for ability in data['characterAbilities']:
        ability_hrid = ability['abilityHrid']
        for item_hrid, item_detail in INIT_CLIENT_DATA['itemDetailMap'].items():
            if item_detail.get('abilityBookDetail', {}).get('abilityHrid', '') != ability_hrid:
                continue
            it = item.Item(item_hrid)
            price_a = market.get_price(it, mode='a')
            ability_networth['a'] += price_a * (ability['experience'] / item_detail['abilityBookDetail']['experienceGain'] + 1)

            price_b = market.get_price(it, mode='b')
            ability_networth['b'] += price_b * (ability['experience'] / item_detail['abilityBookDetail']['experienceGain'] + 1)
    ability_networth['a'] = int(ability_networth['a'])
    ability_networth['b'] = int(ability_networth['b'])

    inventory_networth = {'a': 0, 'b': 0}
    for inventory_item in data['characterItems']:
        inventory_networth['a'] += (market.get_price(item.Item(inventory_item['itemHrid'], inventory_item['enhancementLevel']), mode='a')
                                    * inventory_item['count'])
        inventory_networth['b'] += (market.get_price(item.Item(inventory_item['itemHrid'], inventory_item['enhancementLevel']), mode='b')
                                    * inventory_item['count'])

    market_networth = {'a': 0, 'b': 0}
    for listing in data['myMarketListings']:
        if listing['isSell']:
            market_networth['a'] += (market.get_price(Item(listing['itemHrid'], listing['enhancementLevel']), mode='a') *
                                     (listing['orderQuantity'] - listing['filledQuantity']))
            market_networth['b'] += (market.get_price(Item(listing['itemHrid'], listing['enhancementLevel']), mode='b') *
                                     (listing['orderQuantity'] - listing['filledQuantity']))
        else:
            market_networth['a'] += (listing['orderQuantity'] - listing['filledQuantity']) * listing['price']
            market_networth['b'] += (listing['orderQuantity'] - listing['filledQuantity']) * listing['price']

    house_networth = {'a': 0, 'b': 0}
    for house_hrid, detail in data['characterHouseRoomMap'].items():
        house_networth['a'] += sum(get_house_price(market, house_hrid, level, 'a') for level in range(1, detail['level'] + 1))
        house_networth['b'] += sum(get_house_price(market, house_hrid, level, 'b') for level in range(1, detail['level'] + 1))

    return {
        'ability_networth': ability_networth,
        'inventory_networth': inventory_networth,
        'market_networth': market_networth,
        'house_networth': house_networth,
    }


if __name__ == '__main__':
    market = market.Market(enhance_item_mode='force')
    with open('AlphB.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    res = get_player_networth(market, data)
    pprint.pprint(res)
    print(sum(v['b'] for v in res.values()))
