import json
import math

SKELLIGE = "Skellige"
NAME = 'name'
FACTION = 'faction'

_template = {
    "image": None,
    "range": None,
    "specialty": None,
    "leader": {
        "instructions": ""
    },
    "strength": 0,
    "starter": True,
    "transforms_to": None,
    "ability": ""
}


class CardError(Exception):
    pass


class Card(object):
    id = 0
    details = {}

    def __init__(self, details, id=0, name=None, faction=None):
        if name is not None:
            details[NAME] = name
        if not NAME in details:
            raise CardError(f'No {NAME} specified for this card')

        if faction is not None:
            details[FACTION] = faction
        if not FACTION in details:
            raise CardError(f'No {FACTION} specified for this card')

        self.details = details
        self.id = id

    @property
    def bytes(self):
        return len(str(self))

    @property
    def name(self):
        return self.details['name']

    @property
    def faction(self):
        return self.details['faction']

    @property
    def blocks(self):
        return math.ceil(self.bytes / 16)

    @property
    def min_sector(self):
        return 1

    @property
    def max_sector(self):
        return math.ceil(math.ceil(self.bytes / 16) / 3)

    @property
    def sectors(self):
        return range(self.min_sector, self.max_sector + 1)

    def __str__(self):
        return json.dumps(self.details, sort_keys=True, indent=None,
                          separators=(',', ':')).strip()
