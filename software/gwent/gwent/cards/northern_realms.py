import gwent.cards

FACTION = gwent.cards.NORTHERN_REALMS
CARDS_BY_FACTION = {
    gwent.cards.NORTHERN_REALMS: {
        "Foltest - King of Temeria": {
            "specialty": "leader",
            "leader": {
                "instructions": "Pick an impenetrable fog card from your deck and play it instantly",
                "weather_ranges": ["ranged"]
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
        "Impenetrable Fog: 3": {
            "ranges": ["ranged"],
            "specialty": "weather",
            "owner": "Declan Shanaghy"
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
        "Clear Weather: 2": {
            "specialty": "weather",
            "owner": "Declan Shanaghy"
        },
        "Dethmold": {
            "strength": 6,
            "ranges": ["ranged"],
            "starter": True,
        },
        "Trebuchet: 1": {
            "strength": 6,
            "ranges": ["siege"],
            "starter": True,
        },
        "Trebuchet: 2": {
            "strength": 6,
            "ranges": ["siege"],
            "starter": True,
        },
        "Prince Stennis": {
            "strength": 5,
            "ranges": ["close"],
            "starter": True,
            "abilities": ["spy"]
        },
        "Siege Tower: 1": {
            "strength": 6,
            "ranges": ["siege"],
            "starter": True,
        },
        "Ballista: 1": {
            "strength": 6,
            "ranges": ["ranged"],
            "starter": True,
        },
        "Ballista: 2": {
            "strength": 6,
            "ranges": ["ranged"],
            "starter": True,
        },
        "Ves": {
            "strength": 5,
            "ranges": ["close"],
            "starter": True,
        },
        "Kiera Metz": {
            "strength": 5,
            "ranges": ["ranged"],
            "starter": True,
        },
        "Dun Banner Medic": {
            "strength": 5,
            "ranges": ["siege"],
            "starter": True,
            "abilities": ["medic"]
        },
        "Siegfried of Denesle": {
            "strength": 5,
            "ranges": ["close"],
            "starter": True,
        },
        "Sheldon Skaggs": {
            "strength": 4,
            "ranges": ["ranged"],
            "starter": True,
        },
        "Síle de Tansarville": {
            "strength": 5,
            "ranges": ["ranged"],
            "starter": True,
        },
        "Sabrina Glevissig": {
            "strength": 4,
            "ranges": ["ranged"],
            "starter": True,
        },
        "Redanian Foot Soldier: 1": {
            "strength": 1,
            "ranges": ["close"],
            "starter": True,
        },
        "Redanian Foot Soldier: 2": {
            "strength": 1,
            "ranges": ["close"],
            "starter": True,
        },
        "Poor Fucking Infantry: 1": {
            "strength": 1,
            "ranges": ["close"],
            "starter": True,
            "abilities": ["bond"]
        },
        "Poor Fucking Infantry: 2": {
            "strength": 1,
            "ranges": ["close"],
            "starter": True,
            "abilities": ["bond"]
        },
        "Yarpen Zigrin": {
            "strength": 2,
            "ranges": ["close"],
            "starter": True,
        },
        "Kaedweni Siege Expert: 1": {
            "strength": 1,
            "ranges": ["siege"],
            "starter": True,
            "abilities": ["morale"]
        },
        "Kaedweni Siege Expert: 2": {
            "strength": 1,
            "ranges": ["siege"],
            "starter": True,
            "abilities": ["morale"]
        },
        "Kaedweni Siege Expert: 3": {
            "strength": 1,
            "ranges": ["siege"],
            "starter": True,
            "abilities": ["morale"]
        },
        "Sigismund Dijkstra": {
            "strength": 4,
            "ranges": ["close"],
            "abilities": ["spy"],
            "owner": "Declan Shanaghy"
        },
        "Siege Tower: 2": {
            "strength": 6,
            "ranges": ["siege"],
            "owner": "Declan Shanaghy"
        },
        "Triss Merigold": {
            "strength": 7,
            "ranges": ["close"],
            "specialty": "hero",
            "owner": "Declan Shanaghy"
        },
        "Catapult": {
            "strength": 8,
            "ranges": ["ranged"],
            "abilities": ["bond"],
            "owner": "Declan Shanaghy"
        },
        "Zoltan Chivay": {
            "strength": 5,
            "ranges": ["close"],
            "owner": "Declan Shanaghy"
        },
        "Gaunter O'Dimm: Darkness 1": {
            "strength": 4,
            "ranges": ["ranged"],
            "abilities": ["muster"],
            "owner": "Declan Shanaghy"
        },
        "Villentretenmerth": {
            "strength": 7,
            "ranges": ["close"],
            "abilities": ["scorch"],
            "owner": "Declan Shanaghy"
        },
        "Yennefer of Vengerberg": {
            "strength": 7,
            "ranges": ["ranged"],
            "specialty": "hero",
            "abilities": ["medic"],
            "owner": "Declan Shanaghy"
        },
        "Commander's Horn: 1": {
            "ranges": ["close", "ranged", "siege"],
            "specialty": "commander",
            "owner": "Declan Shanaghy"
        },
        "Scorch": {
            "ranges": ["close", "ranged", "siege"],
            "specialty": "scorch",
            "owner": "Declan Shanaghy"
        },
        "Philippa Eilhart": {
            "strength": 10,
            "ranges": ["ranged"],
            "specialty": "hero",
            "owner": "Declan Shanaghy"
        },
    }
}
