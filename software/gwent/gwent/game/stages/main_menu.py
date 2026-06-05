from gwent.game.stages.base import GameStage


class MainMenu(GameStage):
    """Idle waiting stage — holds the server in 'MainMenu' so the TUI renders
    the full-screen wizard. All wizard interaction is client-side; the game
    starts when the TUI sends gwent/game/start, handled by MenuPublisher."""

    @property
    def stage(self):
        return "MainMenu"
