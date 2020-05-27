from gwent.game.cards import MONSTERS

FACTION = MONSTERS
CARDS_BY_FACTION = {
    MONSTERS: {
        "Eredin - King of the Wild Hunt": {
            "specialty": "leader",
            "leader": {
                "instructions": "Pick any weather card from your deck and play it instantly",
                "weather_ranges": ["close","ranged","siege"]
            },
            "starter": True,
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
        "Torrential Rain: 1": {
            "ranges": ["siege"],
            "specialty": "weather",
            "starter": True,
        },
        "Clear Weather: 1": {
            "specialty": "weather",
            "starter": True,
        },
        "Kayran": {
            "strength": 8,
            "ranges": ["close","ranged"],
            "starter": True,
            "specialty": "hero",
            "abilities": ["agile", "morale"]
        },
        "Imlerith": {
            "strength": 10,
            "ranges": ["close"],
            "specialty": "hero",
            "starter": True,
        },
        "Grave Hag": {
            "strength": 5,
            "ranges": ["ranged"],
            "starter": True,
        },
        "Ice Giant": {
            "strength": 5,
            "ranges": ["siege"],
            "starter": True,
        },
        "Werewolf": {
            "strength": 5,
            "ranges": ["close"],
            "starter": True,
        },
        "Griffin": {
            "strength": 5,
            "ranges": ["close"],
            "starter": True,
        },
        "Fire Elemental": {
            "strength": 6,
            "ranges": ["ranged"],
            "starter": True,
        },
        "Forktail": {
            "strength": 5,
            "ranges": ["close"],
            "starter": True,
        },
        "Wyvern": {
            "strength": 2,
            "ranges": ["ranged"],
            "starter": True,
        },
        "Gargoyle": {
            "strength": 2,
            "ranges": ["ranged"],
            "starter": True,
        },
        "Plague Maiden": {
            "strength": 5,
            "ranges": ["close"],
            "starter": True,
        },
        "Frightener": {
            "strength": 5,
            "ranges": ["close"],
            "starter": True,
        },
        "Endrega": {
            "strength": 2,
            "ranges": ["ranged"],
            "starter": True,
        },
        "Cockatrice": {
            "strength": 2,
            "ranges": ["ranged"],
            "starter": True,
        },
        "Celaeno Harpy": {
            "strength": 2,
            "ranges": ["close", "ranged"],
            "starter": True,
            "abilities": ["agile"]
        },
        "Arachas: Behemoth": {
            "strength": 6,
            "ranges": ["siege"],
            "starter": True,
            "abililties": ["muster"]
        },
        "Arachas: 1": {
            "strength": 4,
            "ranges": ["close"],
            "starter": True,
            "abililties": ["muster"]
        },
        "Arachas: 2": {
            "strength": 4,
            "ranges": ["close"],
            "starter": True,
            "abililties": ["muster"]
        },
        "Ghoul: 1": {
            "strength": 1,
            "ranges": ["close"],
            "starter": True,
            "abililties": ["muster"]
        },
        "Ghoul: 2": {
            "strength": 1,
            "ranges": ["close"],
            "starter": True,
            "abililties": ["muster"]
        },
        "Vampire: Garkhain": {
            "strength": 4,
            "ranges": ["close"],
            "starter": True,
            "abililties": ["muster"]
        },
        "Nekker: 1": {
            "strength": 2,
            "ranges": ["close"],
            "starter": True,
            "abililties": ["muster"]
        },
        "Crone: Brewess": {
            "strength": 6,
            "ranges": ["close"],
            "starter": True,
            "abililties": ["muster"]
        },
        "Fiend": {
            "strength": 6,
            "ranges": ["close"],
            "owner": "Declan Shanaghy"
        },
        "Foglet": {
            "strength": 2,
            "ranges": ["close"],
            "owner": "Declan Shanaghy"
        },
        "Botchling": {
            "strength": 4,
            "ranges": ["close"],
            "owner": "Declan Shanaghy"
        },
        "Bovine Defense Force": {
            "strength": 8,
            "ranges": ["close"],
            "owner": "Declan Shanaghy"
        },
        "Gaunter O'Dimm: Darkness 1": {
            "strength": 4,
            "ranges": ["ranged"],
            "abilities": ["muster"],
            "owner": "Declan Shanaghy"
        },
        "Gaunter O'Dimm: Darkness 2": {
            "strength": 4,
            "ranges": ["ranged"],
            "abilities": ["muster"],
            "owner": "Declan Shanaghy"
        },
        "Geralt of Rivia": {
            "strength": 15,
            "ranges": ["close"],
            "specialty": "hero",
            "owner": "Declan Shanaghy"
        },
        "Dandelion": {
            "strength": 2,
            "ranges": ["close"],
            "abilities": ["commander"],
            "owner": "Declan Shanaghy"
        },
        "Nekker: 2": {
            "strength": 2,
            "ranges": ["close"],
            "abilities": ["muster"],
            "owner": "Declan Shanaghy"
        },
        "Villentretenmerth": {
            "strength": 7,
            "ranges": ["close"],
            "abilities": ["scorch"],
            "owner": "Declan Shanaghy"
        },
    }
}
