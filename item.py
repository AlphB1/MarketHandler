import json
import weakref
from init_client_data import INIT_CLIENT_DATA

with open('e2c.json', 'r', encoding='utf-8') as f:
    E2C = json.load(f)


class Item:
    _pool = weakref.WeakValueDictionary()

    def __new__(cls, item_hrid, enhance_level=0, *args, **kwargs):
        assert enhance_level in range(0, 21)
        if (item_hrid, enhance_level) in cls._pool:
            return cls._pool[(item_hrid, enhance_level)]
        else:
            obj = super().__new__(cls)
            cls._pool[(item_hrid, enhance_level)] = obj
            return obj

    def __init__(self, item_hrid, enhance_level=0):
        self.item_hrid = item_hrid
        self.enhance_level = enhance_level
        self.item_detail = INIT_CLIENT_DATA["itemDetailMap"][item_hrid]
        self.name_en = f"{self.item_detail['name']}+{self.enhance_level}"
        self.name_zh = f"{E2C.get(self.item_hrid, self.name_en)}+{self.enhance_level}"

    def __repr__(self):
        return f"Item({self.item_hrid})"

    def __str__(self, lang='zh'):
        if lang == 'zh':
            return self.name_zh
        if lang == 'en':
            return self.name_en
        return repr(self)


COIN = Item("/items/coin")
