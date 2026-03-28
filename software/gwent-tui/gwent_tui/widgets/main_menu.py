"""Main menu / registration widget: 2-pane P1|P2 display with leaders and deck cards."""

from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from textual.widgets import Static

from gwent_tui.emoji import card_display, leader_display, faction_emoji
from gwent_tui.widgets.header import _STATUS_COLOR


class MainMenuWidget(Static):

    def render(self):
        state = self.app.state
        mc = _STATUS_COLOR.get(state.mqtt_status, "grey50")
        hc = _STATUS_COLOR.get(state.http_status, "grey50")

        # Build P1 and P2 columns
        p1_lines = self._build_player_lines(
            state.reg_leader1, state.reg_deck1, "P1")
        p2_lines = self._build_player_lines(
            state.reg_leader2, state.reg_deck2, "P2")

        # Create 2-column table
        table = Table(
            box=box.SIMPLE_HEAVY,
            expand=True,
            padding=(0, 1),
            show_header=True,
        )

        p1_title = self._player_title(state.reg_leader1, "P1")
        p2_title = self._player_title(state.reg_leader2, "P2")
        table.add_column(p1_title, ratio=1)
        table.add_column(p2_title, ratio=1)

        max_len = max(len(p1_lines), len(p2_lines), 1)
        p1_lines.extend([""] * (max_len - len(p1_lines)))
        p2_lines.extend([""] * (max_len - len(p2_lines)))

        for p1, p2 in zip(p1_lines, p2_lines):
            table.add_row(p1, p2)

        # Prompt / status bar
        prompt = state.last_prompt or "Waiting..."
        status_line = Text.from_markup(
            f"\U0001f4df {prompt}   "
            f"[{mc}]MQTT[/{mc}] [{hc}]HTTP[/{hc}]"
        )

        # Card count summary for registration stages
        p1_count = len([c for c in state.reg_deck1 if c.get("specialty") != "leader"])
        p2_count = len([c for c in state.reg_deck2 if c.get("specialty") != "leader"])
        p1_leader = "\u2713" if state.reg_leader1 else "\u2717"
        p2_leader = "\u2713" if state.reg_leader2 else "\u2717"
        count_summary = (
            f"  [bold yellow]P1[/bold yellow] {p1_leader} {p1_count}/20"
            f"  [bold dodger_blue2]P2[/bold dodger_blue2] {p2_leader} {p2_count}/20"
        )

        return Panel(
            table,
            title=f"\u2694 [bold]{state.stage}[/bold]{count_summary}",
            subtitle=status_line,
        )

    def _player_title(self, leader, label):
        if leader:
            faction = leader.get("faction", "")
            fe = faction_emoji(faction)
            return f"{fe[0]} {label} ({faction}) {fe[1]}"
        return f"{label} — waiting"

    def _build_player_lines(self, leader, deck, label):
        lines = []

        # Leader
        if leader:
            lines.append(leader_display(leader, max_name=50))
        else:
            lines.append("[dim]No leader registered[/dim]")

        # Deck cards (skip leader in deck list)
        cards = [c for c in deck if c.get("specialty") != "leader"]
        if cards:
            lines.append(f"[dim]── Deck ({len(cards)} cards) ──[/dim]")
            for c in cards:
                lines.append(card_display(c, max_name=50))
        else:
            lines.append("[dim]No deck cards[/dim]")

        return lines
