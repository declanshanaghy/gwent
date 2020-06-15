import gwent.cards

FACTION = gwent.cards.NILFGAARDIAN
CARDS_BY_FACTION = {
    gwent.cards.NILFGAARDIAN: {
        "Emhyr var Emreis - His Imperial Majesty: 1": {
            "specialty": "leader",
            "leader": {
                "instructions": "Pick a torrential rain card from your deck and play it instantly",
                "weather_ranges": ["siege"]
            },
            "starter": True,
        },
        "Emhyr var Emreis - His Imperial Majesty: 2": {
            "specialty": "leader",
            "leader": {
                "instructions": "Draw a card from your opponents discard pile",
                "draw_opponent_discard": True,
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
        "Tibor Eggebracht": {
            "strength": 10,
            "ranges": ["ranged"],
            "starter": True,
            "specialty": "hero"
        },
        "Stefan Skellen": {
            "strength": 9,
            "ranges": ["close"],
            "starter": True,
            "abilities": ["spy"]
        },
        "Nausicaa Cavalry Rider: 1": {
            "strength": 2,
            "ranges": ["close"],
            "starter": True,
            "abilities": ["bond"]
        },
        "Nausicaa Cavalry Rider: 2": {
            "strength": 2,
            "ranges": ["close"],
            "starter": True,
            "abilities": ["bond"]
        },
        "Vanhemar": {
            "strength": 4,
            "ranges": ["ranged"],
            "starter": True,
        },
        "Siege Technician": {
            "strength": 0,
            "ranges": ["siege"],
            "starter": True,
            "abilities": ["medic"]
        },
        "Impera Brigade Guard: 1": {
            "strength": 3,
            "ranges": ["close"],
            "starter": True,
            "abilities": ["bond"]
        },
        "Impera Brigade Guard: 2": {
            "strength": 3,
            "ranges": ["close"],
            "starter": True,
            "abilities": ["bond"]
        },
        "Vattier de Rideaux": {
            "strength": 4,
            "ranges": ["close"],
            "starter": True,
            "abilities": ["spy"]
        },
        "Zerrikanian Fire Scorpion": {
            "strength": 5,
            "ranges": ["siege"],
            "starter": True,
        },
        "Etolian Auxillary Archers": {
            "strength": 1,
            "ranges": ["ranged"],
            "starter": True,
            "abilities": ["medic"]
        },
        "Shilard Fitz-Oesterlen": {
            "strength": 7,
            "ranges": ["close"],
            "starter": True,
            "abilities": ["spy"]
        },
        "Cahir Mawr Dyffryn aep Ceallach": {
            "strength": 6,
            "ranges": ["close"],
            "starter": True,
        },
        "Young Emissary: 1": {
            "strength": 5,
            "ranges": ["close"],
            "starter": True,
            "abilities": ["bond"]
        },
        "Cynthia": {
            "strength": 4,
            "ranges": ["ranged"],
            "starter": True,
        },
        "Assire var Anahid": {
            "strength": 6,
            "ranges": ["ranged"],
            "starter": True,
        },
        "Siege Engineer": {
            "strength": 6,
            "ranges": ["siege"],
            "starter": True,
        },
        "Rotten Mangonel": {
            "strength": 3,
            "ranges": ["siege"],
            "starter": True,
        },
        "Impera Brigade Guard": {
            "strength": 3,
            "ranges": ["close"],
            "starter": True,
            "abilities": ["bond"]
        },
        "Vreemde": {
            "strength": 2,
            "ranges": ["close"],
            "starter": True,
        },
        "Renauld aep Matsen": {
            "strength": 5,
            "ranges": ["ranged"],
            "starter": True,
        },
        "Rainfarn": {
            "strength": 4,
            "ranges": ["close"],
            "starter": True,
        },
        "Commander's Horn: 1": {
            "ranges": ["close","ranged","siege"],
            "specialty": "commander",
            "owner": "Declan Shanaghy"
        },
        "Emiel Regis Rohellec Terzieff: Vampire": {
            "strength": 5,
            "ranges": ["close"],
            "owner": "Declan Shanaghy"
        },
        "Fringilla Vigo": {
            "strength": 6,
            "ranges": ["ranged"],
            "owner": "Declan Shanaghy"
        },
        "Young Emissary: 2": {
            "strength": 5,
            "ranges": ["close"],
            "abilities": ["bond"],
            "owner": "Declan Shanaghy"
        },
        "Morvan Voorhis": {
            "strength": 10,
            "ranges": ["siege"],
            "specialty": "hero",
            "owner": "Declan Shanaghy"
        },
        "Menno Coehoorn": {
            "strength": 10,
            "ranges": ["close"],
            "abilities": "medic",
            "owner": "Declan Shanaghy"
        },
        "Dandelion": {
            "strength": 2,
            "ranges": ["close"],
            "abilities": ["commander"],
            "owner": "Declan Shanaghy"
        },
        "Emiel Regis Rohellec Terzieff: Human": {
            "strength": 5,
            "ranges": ["close"],
            "owner": "Declan Shanaghy"
        },
        "Decoy: 1": {
            "strength": 0,
            "specialty": "decoy",
            "owner": "Declan Shanaghy"
        },
    }
}
