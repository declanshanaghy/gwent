import json
import jsonschema
import math

import gwent.messaging.base

KIND = 'card'

CONTENT_ID = 'content_id'
RFID = 'rfid'

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


class Message(gwent.messaging.base.Message):
    @staticmethod
    def from_properties(details=None, rfid=None, name=None, faction=None):
        if details is None:
            details = {}

        if name is not None:
            details[NAME] = name

        if faction is not None:
            details[FACTION] = faction

        if rfid is not None:
            details[RFID] = rfid

        # Create a blank card message if only RFID is provided
        is_blank_card = rfid is not None and name is None and faction is None and not details.get(NAME) and not details.get(FACTION)
        
        return BlankCardMessage(details) if is_blank_card else Message(details)

    @property
    def kind(self):
        return KIND

    @property
    def announcement(self):
        return self.name if hasattr(self, 'name') and NAME in self.instance else f"Card {self.rfid}"

    # content_id is only used during MQTT communications and not stored in the card files
    @property
    def content_id(self):
        return self.instance.get(CONTENT_ID)

    @content_id.setter
    def content_id(self, content_id):
        self.instance[CONTENT_ID] = content_id

    @property
    def rfid(self):
        return self.instance.get(RFID)

    @rfid.setter
    def rfid(self, rfid):
        self.instance[RFID] = rfid


    def validate_extra(self):
        super().validate_extra()

        # Skip validation for blank cards
        if not hasattr(self, 'name') or NAME not in self.instance or not hasattr(self, 'faction') or FACTION not in self.instance:
            return
            
        self._validate_starter()
        self._validate_leader()
        self._validate_agile()
        self._validate_strength()
        self._validate_ranges()

    def _validate_starter(self):
        if self.is_starter and self.has_owner:
            if LEADER not in self.instance:
                raise jsonschema.ValidationError(
                    message=f"{self.name} of {self.faction} is a starter so "
                            f"cannot be owned by {self.owner}",
                    path=(SPECIALTY, LEADER))

    def _validate_leader(self):
        if self.is_leader:
            if LEADER not in self.instance:
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

    def _validate_strength(self):
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
                path=RANGES)

    def _validate_ranges(self):
        if (not self.is_leader and
                not self.is_decoy and
                not self.is_weather and
                not self.is_mardroeme and
                not self.has_ranges):
            raise jsonschema.ValidationError(
                message=f"{self.name} of {self.faction} has no {RANGES}",
                path=RANGES)

    def _validate_agile(self):
        if self.has_ranges and self.has_abilities:
            if self.num_ranges > 1 and not self.is_agile:
                raise jsonschema.ValidationError(
                    message=f"{self.name} of {self.faction} must have {AGILE} "
                            f"ability because they have multiple "
                            f"ranges: {self.ranges}",
                    path=(ABILITIES, RANGES))
            if self.is_agile and self.num_ranges <= 1:
                raise jsonschema.ValidationError(
                    message=f"{self.name} of {self.faction} must have more "
                            f"ranges than {self.ranges} because they have the "
                            f"{AGILE} ability",
                    path=(ABILITIES, RANGES))

    @property
    def full_name(self):
        return self.instance.get(NAME, f"Blank Card {self.rfid}")

    @property
    def name(self):
        if NAME not in self.instance:
            return f"Blank Card {self.rfid}"
        parts = self.instance[NAME].split(':')
        return parts[0]

    @property
    def faction(self):
        return self.instance.get(FACTION, "Unknown")

    @property
    def strength(self):
        return self.instance.get(STRENGTH, 0)

    @property
    def has_specialty(self):
        return SPECIALTY in self.instance

    @property
    def is_medic(self):
        return self.has_abilities and MEDIC in self.abilities

    @property
    def is_spy(self):
        return self.has_abilities and SPY in self.abilities

    @property
    def is_starter(self):
        return STARTER in self.instance and self.instance[STARTER] == True

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
        return self.instance[LEADER]

    @property
    def has_ranges(self):
        return RANGES in self.instance

    @property
    def is_agile(self):
        return AGILE in self.instance[ABILITIES]

    @property
    def abilities(self):
        return self.instance[ABILITIES]

    @property
    def specialty(self):
        return self.instance[SPECIALTY]

    @property
    def num_ranges(self):
        return len(self.ranges)

    @property
    def ranges(self):
        return self.instance.get(RANGES)

    @property
    def has_abilities(self):
        return ABILITIES in self.instance

    @property
    def has_owner(self):
        return OWNER in self.instance

    @property
    def owner(self):
        return self.instance[OWNER]

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
        return Message.header_sector_start(),

    @property
    def header(self):
        return json.dumps({"bytes": self.bytes}).strip()

    @staticmethod
    def body_sector_start():
        return Message.header_sector_start() + 1

    @staticmethod
    def num_sectors_required(n_bytes: int):
        return math.ceil(math.ceil(n_bytes / 16) / 3)

    @staticmethod
    def sector_range(start, n_bytes):
        num_sectors = Message.num_sectors_required(n_bytes)
        return range(start, start + num_sectors)

    @property
    def body_sectors(self):
        return Message.sector_range(Message.body_sector_start(), self.bytes)


# Special class for blank cards that skips validation
class BlankCardMessage(Message):
    def should_validate(self):
        return False
        
    @property
    def announcement(self):
        return f"Blank Card {self.rfid}"
