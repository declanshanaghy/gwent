from enum import Enum

class PLAYER(Enum):
    ONE = "player1"
    TWO = "player2"

    @property
    def display_name(self):
        return self.value.capitalize()

