import os
import json
import jsonschema
import logging
import math


SKELLIGE = "Skellige"
SCOIATAEL = "Scoia'tael"
MONSTERS = "Monsters"
NILFGAARDIAN = "Nilfgaardian"
NORTHERN_REALMS = "Northern Realms"

ID = 'id'
NAME = 'name'
FACTION = 'faction'
RANGES = 'ranges'
STRENGTH = 'strength'
ABILITIES = 'abilities'
SPECIALTY = "specialty"
OWNER = "owner"
STARTER = 'starter'

# SPECIALTIES
LEADER = "leader"
MARDROEME = "mardroeme"
SCORCH = "scorch"

# ABILITIES
AGILE = 'agile'
COMMANDER = 'commander'
DECOY = 'decoy'
MEDIC = "medic"
SPY = "spy"
WEATHER = "weather"

# LEADER properties
DRAW_DISCARD = "draw_opponent_discard"
WEATHER_RANGES = "weather_ranges"
COMMANDER_RANGES = "commander_ranges"


class CardError(Exception):
    pass


class Card(object):
    _log = logging.getLogger(__name__)
    _schema = None

    id = 0
    details = {}

    @staticmethod
    def get_schema():
        if Card._schema is None:
            dir = os.path.abspath(os.path.dirname(__file__))
            abs_schema = os.path.join(dir, "schema.json")
            with open(abs_schema) as fd:
                Card._schema = json.load(fd)
        return Card._schema

    def __init__(self, details, id=None, name=None, faction=None):
        if name is not None:
            details[NAME] = name

        if faction is not None:
            details[FACTION] = faction

        self.details = details

        if id is not None:
            self.id = id
            self.details[ID] = id
        elif ID in self.details:
            self.id = self.details[ID]

        self._log.info({
            'action': 'validate card',
            'name': name,
            'faction': faction,
        })

        jsonschema.validate(instance=details, schema=Card.get_schema())
        self._validate_xtra()

    def _validate_xtra(self):
        self._vaildate_starter()
        self._vaildate_leader()
        self._vaildate_agile()
        self._vaildate_strength()
        self._vaildate_ranges()

    def _vaildate_starter(self):
        if self.is_starter and self.has_owner:
            if not LEADER in self.details:
                raise jsonschema.ValidationError(
                    message=f"{self.name} of {self.faction} is a starter so "
                            f"cannot be owned by {self.owner}",
                    path=(SPECIALTY, LEADER))

    def _vaildate_leader(self):
        if self.is_leader:
            if not LEADER in self.details:
                raise jsonschema.ValidationError(
                    message=f"{self.name} of {self.faction} must have {LEADER} "
                            f"property",
                    path=(SPECIALTY, LEADER))

            max_leader_props = 2
            n_leader_props = len(self.leader.keys())
            if n_leader_props != max_leader_props:
                # Leader should have instructions and 1 other property
                raise jsonschema.ValidationError(
                    message=f"{self.name} of {self.faction} should have "
                            f"exactly {max_leader_props} leader properties, "
                            f"but they have {n_leader_props}: "
                            f"{self.leader.keys()}",
                    path=(SPECIALTY, LEADER))

    def _vaildate_strength(self):
        if (not self.is_leader and
                not self.is_scorch_specialty and
                not self.is_commander_specialty and
                not self.is_decoy and
                not self.is_weather and
                not self.is_mardroeme and
                not self.is_medic and
                not self.is_spy and
                self.strength == 0):
            raise jsonschema.ValidationError(
                message=f"{self.name} of {self.faction} has "
                        f"{self.strength} strength",
                path=(RANGES))

    def _vaildate_ranges(self):
        if (not self.is_leader and
                not self.is_decoy and
                not self.is_weather and
                not self.is_mardroeme and
                not self.has_ranges):
            raise jsonschema.ValidationError(
                message=f"{self.name} of {self.faction} has no {RANGES}",
                path=(RANGES))

    def _vaildate_agile(self):
        if self.has_ranges and self.has_abilities:
            if (self.num_ranges > 1 and not self.is_agile):
                raise jsonschema.ValidationError(
                    message=f"{self.name} of {self.faction} must have {AGILE} "
                            f"ability because they have multiple "
                            f"ranges: {self.ranges}",
                    path=(ABILITIES, RANGES))
            if (self.is_agile and self.num_ranges <= 1):
                raise jsonschema.ValidationError(
                    message=f"{self.name} of {self.faction} must have more "
                            f"ranges than {self.ranges} because they have the "
                            f"{AGILE} ability",
                    path=(ABILITIES, RANGES))

    @property
    def full_name(self):
        return self.details[NAME]

    @property
    def name(self):
        parts = self.details[NAME].split(':')
        return parts[0]

    @property
    def faction(self):
        return self.details[FACTION]

    @property
    def strength(self):
        return self.details.get(STRENGTH, 0)

    @property
    def has_specialty(self):
        return SPECIALTY in self.details

    @property
    def is_medic(self):
        return self.has_abilities and MEDIC in self.abilities

    @property
    def is_spy(self):
        return self.has_abilities and SPY in self.abilities

    @property
    def is_starter(self):
        return STARTER in self.details and self.details[STARTER] == True

    @property
    def is_weather(self):
        return self.has_specialty and self.specialty == WEATHER

    @property
    def is_commander_specialty(self):
        return self.has_specialty and self.specialty == COMMANDER

    @property
    def is_scorch_specialty(self):
        return self.has_specialty and self.specialty == SCORCH

    @property
    def is_decoy(self):
        return self.has_specialty and self.specialty == DECOY

    @property
    def is_mardroeme(self):
        return self.has_specialty and self.specialty == MARDROEME

    @property
    def is_leader(self):
        return self.has_specialty and self.specialty == LEADER

    @property
    def leader(self):
        return self.details[LEADER]

    @property
    def has_ranges(self):
        return RANGES in self.details

    @property
    def is_agile(self):
        return AGILE in self.details[ABILITIES]

    @property
    def abilities(self):
        return self.details[ABILITIES]

    @property
    def specialty(self):
        return self.details[SPECIALTY]

    @property
    def num_ranges(self):
        return len(self.ranges)

    @property
    def ranges(self):
        return self.details.get(RANGES)

    @property
    def has_abilities(self):
        return ABILITIES in self.details

    @property
    def has_owner(self):
        return OWNER in self.details

    @property
    def owner(self):
        return self.details[OWNER]

    @property
    def bytes(self):
        return len(self.body)

    @property
    def blocks(self):
        return math.ceil(self.bytes / 16)

    @staticmethod
    def header_sector_start():
        return 1

    @staticmethod
    def header_sectors():
        return (Card.header_sector_start(),)

    @property
    def header(self):
        return json.dumps({"bytes": self.bytes})

    @staticmethod
    def body_sector_start():
        return Card.header_sector_start() + 1

    @staticmethod
    def num_sectors_required(bytes: int):
        return math.ceil(math.ceil(bytes / 16) / 3)

    @staticmethod
    def sector_range(start, bytes):
        num_sectors = Card.num_sectors_required(bytes)
        return range(start, start + num_sectors)

    @property
    def body_sectors(self):
        return Card.sector_range(Card.body_sector_start(), self.bytes)

    @property
    def body(self):
        return json.dumps(self.details, sort_keys=True, indent=None,
                          separators=(',', ':')).strip()


def __str__(self):
    return self.body
