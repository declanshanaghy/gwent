"""TUI stage: DealCards — shows cards being dealt to each player in real-time."""

from rich.panel import Panel
from rich.table import Table
from rich import box
from textual.containers import Vertical
from textual.widgets import Static

from gwent_tui.emoji import card_display, leader_display, faction_emoji
from gwent_tui.game_state import P1, P2


class DealCardsWidget(Static):

    def render(self):
        state = self.app.state

        # Build P1 and P2 columns
        p1_lines = self._build_player_lines(P1, state)
        p2_lines = self._build_player_lines(P2, state)

        table = Table(
            box=box.SIMPLE_HEAVY,
            expand=True,
            padding=(0, 1),
            show_header=True,
        )

        p1_title = self._player_title(P1, state)
        p2_title = self._player_title(P2, state)
        table.add_column(p1_title, ratio=1)
        table.add_column(p2_title, ratio=1)

        max_len = max(len(p1_lines), len(p2_lines), 1)
        p1_lines.extend([""] * (max_len - len(p1_lines)))
        p2_lines.extend([""] * (max_len - len(p2_lines)))

        for p1, p2 in zip(p1_lines, p2_lines):
            table.add_row(p1, p2)

        # Announcement / prompt
        prompt = state.last_announcement or state.last_prompt or "Dealing cards..."
        p1_count = len(state.dealt_cards.get(P1, []))
        p2_count = len(state.dealt_cards.get(P2, []))
        subtitle = (
            f"\U0001f0cf [bold yellow]P1[/bold yellow]: {p1_count}"
            f"  [bold dodger_blue2]P2[/bold dodger_blue2]: {p2_count}"
        )

        return Panel(
            table,
            title=f"\U0001f0cf [bold]Dealing Cards[/bold]  {subtitle}",
            subtitle=f"\U0001f4df {prompt}",
        )

    def _player_title(self, player, state):
        leader = state.reg_leader1 if player == P1 else state.reg_leader2
        label = "P1" if player == P1 else "P2"
        if leader:
            faction = leader.get("faction", "")
            fe = faction_emoji(faction)
            return f"{fe[0]} {label} ({faction}) {fe[1]}"
        return f"{label}"

    def _build_player_lines(self, player, state):
        lines = []

        # Leader
        leader = state.reg_leader1 if player == P1 else state.reg_leader2
        if leader:
            lines.append(leader_display(leader, max_name=50))
        else:
            lines.append("[dim]No leader[/dim]")

        # Dealt cards (real-time from MQTT)
        dealt = state.dealt_cards.get(player, [])
        if dealt:
            lines.append(f"[dim]\u2500\u2500 Hand ({len(dealt)} cards) \u2500\u2500[/dim]")
            for i, card in enumerate(dealt, 1):
                lines.append(f"  {i}. {card_display(card, max_name=50)}")
        else:
            lines.append("[dim]Waiting for cards...[/dim]")

        return lines


class DealCardsStage(Vertical):
    DEFAULT_CSS = """
    DealCardsStage { height: 1fr; }
    """

    def compose(self):
        yield DealCardsWidget(id="deal-cards-content")
