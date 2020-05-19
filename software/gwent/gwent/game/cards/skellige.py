from gwent.game.cards import SKELLIGE

FACTION = SKELLIGE
CARDS_BY_FACTION = {
    SKELLIGE: {
        "Crach an Craite": {
            "specialty": "leader",
            "leader": {
                "instructions": "Shuffle all cards from each player's graveyard back into their decks"
            },
            "starter": True,
        },
        "Torrential Rain 1": {
            "range": ["siege"],
            "specialty": "weather",
            "starter": True,
        },
        "Hjalmar": {
            "range": ["ranged"],
            "specialty": "hero",
            "strength": 10,
            "starter": True,
        },
        "Mardroeme 1": {
            "specialty": "mardreome",
            "starter": True,
        },
        "Berserker": {
            "range": ["close"],
            "strength": 4,
            "starter": True,
            "transforms_to": "Transformed Vildkaarl",
            "ability": "berserker"
        },
        "Transformed Vildkaarl": {
            "range": ["close"],
            "strength": 14,
            "starter": True,
            "ability": "morale boost"
        },
    }
}
