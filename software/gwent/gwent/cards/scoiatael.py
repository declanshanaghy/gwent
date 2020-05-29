from gwent.cards import SCOIATAEL

FACTION = SCOIATAEL
CARDS_BY_FACTION = {
    SCOIATAEL: {
        "Francesca Findabair - Pureblood Elf": {
            "specialty": "leader",
            "leader": {
                "instructions": "Pick a biting frost card from your deck and play it instantly",
                "weather_ranges": ["close"]
            },
            "starter": True,
        },
        "Francesca Findabair - The Beautiful": {
            "specialty": "leader",
            "leader": {
                "instructions": "Doubles the strength of all your ranged combat units (unless commanders horn is present in that row)",
                "commander_ranges": ["ranged"]
            },
            "starter": True,
            "owner": "Declan Shanaghy"
        },
        "Impenetrable Fog: 1": {
            "ranges": ["ranged"],
            "specialty": "weather",
            "starter": True,
        },
        "Impenetrable Fog: 2": {
            "ranges": ["ranged"],
            "specialty": "weather",
            "starter": True,
        },
        "Biting Frost: 1": {
            "ranges": ["close"],
            "specialty": "weather",
            "starter": True,
        },
        "Biting Frost: 2": {
            "ranges": ["close"],
            "specialty": "weather",
            "starter": True,
        },
        "Biting Frost: 3": {
            "ranges": ["close"],
            "specialty": "weather",
            "owner": "Declan Shanaghy"
        },
        "Torrential Rain: 1": {
            "ranges": ["siege"],
            "specialty": "weather",
            "starter": True,
        },
        "Clear Weather: 1": {
            "specialty": "weather",
            "starter": True,
        },
        "Iorveth": {
            "strength": 10,
            "ranges": ["ranged"],
            "starter": True,
            "specialty": "hero"
        },
        "Dol Blathanna Archer: 1": {
            "strength": 4,
            "ranges": ["ranged"],
            "starter": True,
        },
        "Riordan": {
            "strength": 1,
            "ranges": ["ranged"],
            "starter": True,
        },
        "Toruviel": {
            "strength": 2,
            "ranges": ["ranged"],
            "starter": True,
        },
        "Dwarven Skirmisher: 1": {
            "strength": 3,
            "ranges": ["close"],
            "starter": True,
            "abilities": ["muster"]
        },
        "Dwarven Skirmisher: 2": {
            "strength": 3,
            "ranges": ["close"],
            "starter": True,
            "abilities": ["muster"]
        },
        "Dwarven Skirmisher: 3": {
            "strength": 3,
            "ranges": ["close"],
            "starter": True,
            "abilities": ["muster"]
        },
        "Dennis Cranmer": {
            "strength": 6,
            "ranges": ["close"],
            "starter": True,
        },
        "Dol Blathanna Scout: 1": {
            "strength": 6,
            "ranges": ["close", "ranged"],
            "starter": True,
            "abilities": ["agile"]
        },
        "Dol Blathanna Scout: 2": {
            "strength": 6,
            "ranges": ["close", "ranged"],
            "starter": True,
            "abilities": ["agile"]
        },
        "Elven Skirmisher: 1": {
            "strength": 2,
            "ranges": ["ranged"],
            "starter": True,
            "abilities": ["muster"]
        },
        "Elven Skirmisher: 2": {
            "strength": 2,
            "ranges": ["ranged"],
            "starter": True,
            "abilities": ["muster"]
        },
        "Filavandrel aen Fidhail": {
            "strength": 6,
            "ranges": ["close", "ranged"],
            "starter": True,
            "abilities": ["agile"]
        },
        "Vrihedd Brigade Veteran: 1": {
            "strength": 5,
            "ranges": ["close", "ranged"],
            "starter": True,
            "abilities": ["agile"]
        },
        "Vrihedd Brigade Veteran: 2": {
            "strength": 5,
            "ranges": ["close", "ranged"],
            "starter": True,
            "abilities": ["agile"]
        },
        "Vrihedd Brigade Recruit": {
            "strength": 4,
            "ranges": ["ranged"],
            "starter": True,
        },
        "Ida Emean aep Sivney": {
            "strength": 6,
            "ranges": ["ranged"],
            "starter": True,
        },
        "Mahakaman Defender: 1": {
            "strength": 5,
            "ranges": ["close"],
            "starter": True,
        },
        "Mahakaman Defender: 2": {
            "strength": 5,
            "ranges": ["close"],
            "starter": True,
        },
        "Mahakaman Defender: 3": {
            "strength": 5,
            "ranges": ["close"],
            "starter": True,
        },
        "Havekar Smuggler": {
            "strength": 5,
            "ranges": ["close"],
            "starter": True,
            "abilities": ["muster"]
        },
        "Havekar Healer": {
            "strength": 0,
            "ranges": ["ranged"],
            "starter": True,
            "abilities": ["medic"]
        },
        "Ciaran aep Easnilie": {
            "strength": 3,
            "ranges": ["close", "ranged"],
            "starter": True,
            "abilities": ["agile"]
        },
        "Decoy: 1": {
            "specialty": "decoy",
            "owner": "Declan Shanaghy"
        },
        "Decoy: 2": {
            "specialty": "decoy",
            "owner": "Declan Shanaghy"
        },
        "Gaunter O'Dimm: Darkness 1": {
            "strength": 4,
            "ranges": ["ranged"],
            "ability": "muster",
            "owner": "Declan Shanaghy"
        },
        "Mahakaman Defender: 4": {
            "strength": 5,
            "ranges": ["close"],
            "owner": "Declan Shanaghy"
        },
        "Scorch": {
            "ranges": ["close", "ranged", "siege"],
            "specialty": "scorch",
            "owner": "Declan Shanaghy"
        },
        "Cirilla Fiona Elen Riannon": {
            "strength": 15,
            "ranges": ["close"],
            "specialty": "hero",
            "owner": "Declan Shanaghy"
        },
        "Mahakaman Defender: 5": {
            "strength": 5,
            "ranges": ["close"],
            "owner": "Declan Shanaghy"
        },
    }
}
