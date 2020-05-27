from gwent.game.cards import SKELLIGE

FACTION = SKELLIGE
CARDS_BY_FACTION = {
    SKELLIGE: {
        "Crach an Craite": {
            "specialty": "leader",
            "leader": {
                "instructions": "Shuffle all cards from each player's graveyard back into their decks",
                "reshuffle_graveyards": True
            },
            "starter": True,
        },
        "Torrential Rain: 1": {
            "ranges": ["siege"],
            "specialty": "weather",
            "starter": True,
        },
        "Torrential Rain: 2": {
            "ranges": ["siege"],
            "specialty": "weather",
            "owner": "Declan Shanaghy",
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
        "Clear Weather: 1": {
            "specialty": "weather",
            "starter": True,
        },
        "Clear Weather: 2": {
            "specialty": "weather",
            "owner": "Declan Shanaghy",
        },
        "Hjalmar": {
            "ranges": ["ranged"],
            "specialty": "hero",
            "strength": 10,
            "starter": True,
        },
        "Mardroeme: 1": {
            "specialty": "mardroeme",
            "starter": True,
        },
        "Berserker": {
            "ranges": ["close"],
            "strength": 4,
            "starter": True,
            "transforms_to": "Transformed Vildkaarl",
            "abilities": ["berserker"]
        },
        "Young Berserker": {
            "ranges": ["ranged"],
            "strength": 2,
            "starter": True,
            "transforms_to": "Transformed Young Vildkaarl",
            "abilities": ["berserker"]
        },
        "Transformed Vildkaarl": {
            "ranges": ["close"],
            "strength": 14,
            "starter": True,
            "abilities": ["morale"]
        },
        "Transformed Young Vildkaarl: 1": {
            "ranges": ["ranged"],
            "strength": 8,
            "starter": True,
            "abilities": ["bond"]
        },
        "Udalyrk": {
            "strength": 4,
            "ranges": ["close"],
            "starter": True,
        },
        "Clan Heymaey Skals": {
            "strength": 4,
            "ranges": ["close"],
            "starter": True,
        },
        "Light Longship: 1": {
            "strength": 4,
            "ranges": ["ranged"],
            "starter": True,
            "abilities": ["muster"]
        },
        "Light Longship: 2": {
            "strength": 4,
            "ranges": ["ranged"],
            "starter": True,
            "abilities": ["muster"]
        },
        "Clan Brokvar Archer: 1": {
            "strength": 6,
            "ranges": ["ranged"],
            "starter": True,
        },
        "Clan Brokvar Archer: 2": {
            "strength": 6,
            "ranges": ["ranged"],
            "starter": True,
        },
        "Holger Blackhand": {
            "strength": 4,
            "ranges": ["siege"],
            "starter": True,
        },
        "Birna Bran": {
            "strength": 2,
            "ranges": ["close"],
            "starter": True,
            "abilities": ["medic"]
        },
        "Donar an Hindar": {
            "strength": 4,
            "ranges": ["close"],
            "starter": True,
        },
        "Svanrige": {
            "strength": 4,
            "ranges": ["close"],
            "starter": True,
        },
        "War Longship: 1": {
            "strength": 6,
            "ranges": ["siege"],
            "starter": True,
            "abilities": ["bond"]
        },
        "War Longship: 2": {
            "strength": 6,
            "ranges": ["siege"],
            "starter": True,
            "abilities": ["bond"]
        },
        "Clan an Craite Warrior: 1": {
            "strength": 6,
            "ranges": ["close"],
            "starter": True,
            "abilities": ["bond"]
        },
        "Clan an Craite Warrior: 2": {
            "strength": 6,
            "ranges": ["close"],
            "starter": True,
            "abilities": ["bond"]
        },
        "Clan an Craite Warrior: 3": {
            "strength": 6,
            "ranges": ["close"],
            "starter": True,
            "abilities": ["bond"]
        },
        "Blueboy Lugos": {
            "strength": 6,
            "ranges": ["close"],
            "starter": True,
        },
        "Madman Lugos": {
            "strength": 6,
            "ranges": ["close"],
            "starter": True,
        },
        "Clan Drummond Shield Maiden: 1": {
            "strength": 4,
            "ranges": ["close"],
            "starter": True,
            "abilities": ["bond"]
        },
        "Clan Tordarroch Armorsmith": {
            "strength": 4,
            "ranges": ["close"],
            "starter": True,
        },
        "Triss Merigold": {
            "strength": 7,
            "ranges": ["close"],
            "specialty": "hero",
            "owner": "Declan Shanaghy"
        },
        "Avallac'h": {
            "strength": 0,
            "ranges": ["close"],
            "abilities": ["spy"],
            "owner": "Declan Shanaghy"
        },
        "Scorch: 1": {
            "ranges": ["close", "ranged", "siege"],
            "specialty": "scorch",
            "owner": "Declan Shanaghy"
        },
        "Transformed Young Vildkaarl: 2": {
            "strength": 8,
            "ranges": ["ranged"],
            "abilities": ["bond"],
            "owner": "Declan Shanaghy"
        },
        "Clan Drummond Shield Maiden: 2": {
            "strength": 4,
            "ranges": ["close"],
            "abilities": ["bond"],
            "owner": "Declan Shanaghy"
        },
        "Olaf": {
            "strength": 12,
            "ranges": ["close", "ranged"],
            "abilities": ["agile", "morale"],
            "owner": "Declan Shanaghy"
        },
        "Dandelion": {
            "strength": 2,
            "ranges": ["close"],
            "abilities": ["commander"],
            "owner": "Declan Shanaghy"
        },
        "Draig Bon-Dhu": {
            "strength": 2,
            "ranges": ["siege"],
            "abilities": ["commander"],
            "owner": "Declan Shanaghy"
        },
        "Commander's Horn": {
            "ranges": ["close", "ranged", "siege"],
            "specialty": "commander",
            "owner": "Declan Shanaghy"
        },
        "Zoltan Chivay": {
            "strength": 5,
            "ranges": ["close"],
            "owner": "Declan Shanaghy"
        },
        "Decoy: 1": {
            "specialty": "decoy",
            "owner": "Declan Shanaghy"
        },
        "Gaunter O'Dimm: Darkness 1": {
            "strength": 4,
            "ranges": ["ranged"],
            "abilities": ["muster"],
            "owner": "Declan Shanaghy"
        },
        "Scorch: 2": {
            "ranges": ["close","ranged","siege"],
            "specialty": "scorch",
            "owner": "Declan Shanaghy"
        },
    }
}
