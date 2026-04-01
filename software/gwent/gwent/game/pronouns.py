"""Pronoun helper for in-game narration.

Maps a base pronoun ('he', 'she', 'it') to all inflected forms suitable
for str.format() interpolation.  Unknown/missing values fall back to
gender-neutral 'they/their/them'.
"""


_FORMS = {
    "he": {
        "he": "he", "He": "He",
        "his": "his", "His": "His",
        "him": "him",
        "himself": "himself",
    },
    "she": {
        "he": "she", "He": "She",
        "his": "her", "His": "Her",
        "him": "her",
        "himself": "herself",
    },
    "it": {
        "he": "it", "He": "It",
        "his": "its", "His": "Its",
        "him": "it",
        "himself": "itself",
    },
}

_NEUTRAL = {
    "he": "they", "He": "They",
    "his": "their", "His": "Their",
    "him": "them",
    "himself": "themselves",
}


def pronoun_forms(pronoun: str) -> dict:
    """Return a dict of pronoun forms keyed for str.format().

    Keys: he, He, his, His, him, himself
    Values depend on *pronoun* ('he', 'she', 'it').
    Unknown values default to gender-neutral they/their/them.
    """
    return _FORMS.get(pronoun, _NEUTRAL)
