"""TUI stage views — one module per game stage, mirroring gwent/game/stages/."""

from gwent_tui.stages.main_menu import MainMenuStage
from gwent_tui.stages.register_leaders import RegisterLeadersStage
from gwent_tui.stages.register_decks import RegisterDecksStage
from gwent_tui.stages.deal_cards import DealCardsStage
from gwent_tui.stages.play_round import PlayRoundStage
from gwent_tui.stages.round_end import RoundEndStage
from gwent_tui.stages.game_over import GameOverStage
from gwent_tui.stages.unknown import UnknownStage
from gwent_tui.stages.offline import OfflineStage

# Map server stage names to TUI stage widgets
STAGE_WIDGETS = {
    "MainMenu": MainMenuStage,
    "RegisterLeaders": RegisterLeadersStage,
    "RegisterDecks": RegisterDecksStage,
    "DealCards": DealCardsStage,
    "PlayRound": PlayRoundStage,
    "RoundEnd": RoundEndStage,
    "GameOver": GameOverStage,
    "DisplayWinner": GameOverStage,
}
