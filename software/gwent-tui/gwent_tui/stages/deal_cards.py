"""TUI stage: DealCards — shows cards being dealt to each player in real-time."""

from rich.panel import Panel
from rich.table import Table
from rich import box
from textual.containers import VerticalScroll
from textual.widgets import Static

from gwent_tui.emoji import card_display, leader_display, faction_emoji
from gwent_tui.game_state import P1, P2


class DealCardsWidget(Static):

    def _get_leader(self, player, state):
        """Get leader from registration data, board leaders, or deck."""
        if player == P1:
            leader = state.reg_leader1 or state.leaders.get(P1)
            deck = state.reg_deck1
        else:
            leader = state.reg_leader2 or state.leaders.get(P2)
            deck = state.reg_deck2
        if not leader and deck:
            leader = next((c for c in deck if c.get("leader")), None)
        return leader

    def _get_deck(self, player, state):
        """Get the full deck from registration data."""
        return state.reg_deck1 if player == P1 else state.reg_deck2

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
        leader = self._get_leader(player, state)
        label = "P1" if player == P1 else "P2"
        if leader:
            faction = leader.get("faction", "")
            fe = faction_emoji(faction)
            return f"{fe[0]} {label} ({faction}) {fe[1]}"
        return f"{label}"

    def _build_player_lines(self, player, state):
        lines = []

        # Leader
        leader = self._get_leader(player, state)
        if leader:
            lines.append(leader_display(leader, max_name=50))
        else:
            lines.append("[dim]Waiting for leader...[/dim]")

        # Dealt cards (real-time from MQTT)
        dealt = state.dealt_cards.get(player, [])
        if dealt:
            lines.append(f"[dim]\u2500\u2500 Hand ({len(dealt)} cards) \u2500\u2500[/dim]")
            for i, card in enumerate(dealt, 1):
                lines.append(f"  {i}. {card_display(card, max_name=50)}")
        else:
            lines.append("[dim]Waiting for cards...[/dim]")

        # Remaining deck cards (from HTTP snapshot)
        deck = self._get_deck(player, state)
        if deck:
            dealt_names = {c.get("name") for c in dealt}
            remaining = [c for c in deck
                         if not c.get("leader")
                         and c.get("name") not in dealt_names]
            if remaining:
                lines.append("")
                lines.append(
                    f"[dim]\u2500\u2500 Deck ({len(remaining)} remaining) \u2500\u2500[/dim]")
                for i, card in enumerate(remaining, 1):
                    lines.append(f"  {i}. [dim]{card_display(card, max_name=50)}[/dim]")

        return lines


class DealCardsStage(VerticalScroll):
    DEFAULT_CSS = """
    DealCardsStage { height: 1fr; }
    DealCardsStage #deal-cards-content { height: 1fr; min-height: 100%; }
    """

    def compose(self):
        yield DealCardsWidget(id="deal-cards-content")
