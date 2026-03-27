"""Rich-based renderer that builds the TUI layout from GameState."""

from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from rich.console import Group

from gwent_tui.emoji import (
    faction_emoji, card_display, card_display_short,
    leader_display, ROW_EMOJI, WEATHER_EMOJI, ZAP, FLAG,
    WEATHER_NAME,
)

# Row colors for board display
ROW_COLOR = {
    "close":  "orange1",
    "ranged": "orchid",
    "siege":  "turquoise2",
}

# 3-line tall ASCII art digits for score display
_ASCII_DIGITS = {
    "0": [" ██ ", "█  █", "█  █", "█  █", " ██ "],
    "1": [" █  ", "██  ", " █  ", " █  ", "███ "],
    "2": [" ██ ", "█  █", "  █ ", " █  ", "████"],
    "3": ["███ ", "   █", " ██ ", "   █", "███ "],
    "4": ["█  █", "█  █", "████", "   █", "   █"],
    "5": ["████", "█   ", "███ ", "   █", "███ "],
    "6": [" ██ ", "█   ", "███ ", "█  █", " ██ "],
    "7": ["████", "   █", "  █ ", " █  ", " █  "],
    "8": [" ██ ", "█  █", " ██ ", "█  █", " ██ "],
    "9": [" ██ ", "█  █", " ███", "   █", " ██ "],
}


def _big_score_lines(n):
    """Render a number as 5-line ASCII art. Returns list of 5 strings."""
    digits = [_ASCII_DIGITS[c] for c in str(n)]
    lines = []
    for row in range(5):
        lines.append(" ".join(d[row] for d in digits))
    return lines
from rich.align import Align

from gwent_tui.game_state import P1, P2, GameState


class Renderer:
    def render(self, state, save_dialog=None, show_help=False, poller=None):
        """Build complete Layout from current GameState."""
        self._poller = poller
        if show_help:
            return self._render_help()

        with state.lock:
            in_game = state.stage in GameState._GAME_STAGES

            if not in_game:
                return self._render_lobby(state, save_dialog)

            return self._render_game(state, save_dialog)

    def _render_help(self):
        """Render the help screen showing all keyboard shortcuts."""
        table = Table(
            box=box.ROUNDED,
            expand=False,
            show_header=True,
            padding=(0, 2),
            title="\U0001f3ae Gwent TUI — Keyboard Shortcuts",
            title_style="bold bright_cyan",
        )
        table.add_column("Key", style="bold yellow", justify="right")
        table.add_column("Action", style="white")

        shortcuts = [
            ("?", "Show this help screen"),
            ("\u2191", "Increase poll rate (-1s)"),
            ("\u2193", "Decrease poll rate (+1s)"),
            ("Ctrl+S", "Open save state dialog"),
            ("Ctrl+C", "Quit gwent-tui"),
            ("", ""),
            ("[bold dim]Save Dialog[/bold dim]", ""),
            ("Tab", "Cycle focus: Input \u2192 OK \u2192 Cancel"),
            ("Enter", "Save file / activate focused button"),
            ("Esc", "Close dialog"),
            ("Backspace", "Delete last character"),
            ("", ""),
            ("[bold dim]During Card Write[/bold dim]", ""),
            ("Any key", "Skip current card"),
        ]

        for key, action in shortcuts:
            table.add_row(key, action)

        help_text = Text.from_markup(
            "\n[dim]Press any key to dismiss[/dim]"
        )
        help_text.justify = "center"

        layout = Layout()
        layout.split_column(
            Layout(name="body"),
        )
        layout["body"].update(
            Align.center(
                Group(table, help_text),
                vertical="middle",
            )
        )
        return layout

    def _render_lobby(self, state, save_dialog=None):
        """Simple screen for non-game stages (MainMenu, BuildDeck, etc.)."""
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=5),
        )

        mqtt_color = "green" if state.connected else "red"
        http_color = "green" if state.http_ok else "red"
        poll_rate = ""
        if self._poller:
            poll_rate = f" [dim]{self._poller.interval:.0f}s[/dim]"
        header = Text.from_markup(
            f" Gwent Companion "
            f"[{mqtt_color}]MQTT[/{mqtt_color}] [{http_color}]HTTP[/{http_color}]{poll_rate}"
        )
        header.justify = "center"
        layout["header"].update(Panel(header, style="bold"))

        stage_text = Text.from_markup(
            f"\n\n\u2694\ufe0f  Server Stage: [bold cyan]{state.stage}[/bold cyan]\n\n"
            f"[dim]Waiting for game to start...[/dim]\n\n"
            f"[dim]Ctrl+S to save state[/dim]"
        )
        stage_text.justify = "center"

        if save_dialog and save_dialog.active:
            layout["body"].update(save_dialog.render())
        else:
            layout["body"].update(Align.center(stage_text, vertical="middle"))

        layout["footer"].update(self._render_footer(state))
        return layout

    def _render_game(self, state, save_dialog=None):
        """Full game board layout for active game stages."""
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=5),
        )
        layout["body"].split_row(
            Layout(name="left", ratio=1),
            Layout(name="right", ratio=1),
        )
        layout["left"].split_column(
            Layout(name="board", minimum_size=12),
            Layout(name="weather", size=5),
        )
        layout["right"].split_column(
            Layout(name="hands", ratio=2),
            Layout(name="decks", ratio=1),
            Layout(name="discard", ratio=1),
        )

        layout["header"].update(self._render_header(state, None, None))
        layout["weather"].update(self._render_weather_passed(state))
        layout["hands"].update(self._render_hands(state))
        layout["decks"].update(self._render_decks(state))
        layout["discard"].update(self._render_discard(state))
        layout["footer"].update(self._render_footer(state))

        if save_dialog and save_dialog.active:
            layout["board"].update(save_dialog.render())
        else:
            layout["board"].update(self._render_board(state))

        return layout

    def _gems_header(self, gems, max_gems=2):
        """Render gems as 💎 and skull emojis, fixed-width for stability."""
        alive = min(gems, max_gems)
        dead = max_gems - alive
        return "\U0001f48e" * alive + "\U0001f480" * dead

    def _render_header(self, state, p1h, p2h):
        turn = "P1" if state.current_player == P1 else "P2"

        p1_gems = self._gems_header(state.gems[P1])
        p2_gems = self._gems_header(state.gems[P2])

        p1f = state.factions.get(P1, "")
        p2f = state.factions.get(P2, "")
        p1e = faction_emoji(p1f)
        p2e = faction_emoji(p2f)

        p1_label = f"{p1e[0]} [bold yellow]P1 ({p1f})[/bold yellow] {p1e[1]}" if p1f else "[bold yellow]P1[/bold yellow]"
        p2_label = f"{p2e[0]} [bold blue]P2 ({p2f})[/bold blue] {p2e[1]}" if p2f else "[bold blue]P2[/bold blue]"

        center = Text.from_markup(
            f" {p1_label} {p1_gems}    "
            f"\u2694\ufe0f Round {state.round_number} "
            f"\U0001f3af {turn}"
            f"    {p2_gems} {p2_label} "
        )
        center.justify = "center"

        mqtt_color = "green" if state.connected else "red"
        http_color = "green" if state.http_ok else "red"
        poll_rate = ""
        if self._poller:
            poll_rate = f" [dim]{self._poller.interval:.0f}s[/dim]"
        status = Text.from_markup(
            f"[{mqtt_color}]MQTT[/{mqtt_color}] [{http_color}]HTTP[/{http_color}]{poll_rate} "
        )
        status.justify = "right"

        table = Table(box=None, expand=True, show_header=False, padding=0)
        table.add_column(ratio=1)
        table.add_column(width=14, justify="right")
        table.add_row(center, status)

        return Panel(table, style="bold")

    def _render_board(self, state):
        p1s = state.scores[P1]
        p2s = state.scores[P2]
        p1_style = "bold yellow"
        p2_style = "bold blue"
        title = Text.from_markup(
            f"\u2694\ufe0f [{p1_style}]{p1s}[/{p1_style}]"
            f" [dim]vs[/dim] "
            f"[{p2_style}]{p2s}[/{p2_style}]"
        )

        table = Table(
            title=title,
            box=box.SIMPLE_HEAVY,
            expand=True,
            padding=(0, 1),
            show_header=False,
            show_lines=True,
        )
        table.add_column(ratio=1)
        table.add_column(ratio=1)

        for row_name in ("close", "ranged", "siege"):
            re = ROW_EMOJI.get(row_name, "")
            weather_active = row_name in state.weather_rows
            weather_tag = f" {WEATHER_EMOJI.get(row_name, '')}" if weather_active else ""

            p1_cards = state.board_rows[P1].get(row_name, [])
            p2_cards = state.board_rows[P2].get(row_name, [])

            p1_horn = row_name in state.commander_horn_rows.get(P1, set())
            p2_horn = row_name in state.commander_horn_rows.get(P2, set())

            p1_row_score = state._calculate_row_score(P1, row_name)
            p2_row_score = state._calculate_row_score(P2, row_name)

            p1_text = self._format_row(p1_cards, row_name, re, weather_tag, p1_horn,
                                       p1_row_score, weather_active=weather_active)
            p2_text = self._format_row(p2_cards, row_name, re, weather_tag, p2_horn,
                                       p2_row_score, weather_active=weather_active)

            table.add_row(p1_text, p2_text)

        return Panel(table)

    def _format_row(self, cards, row_name, row_emoji, weather_tag, has_horn,
                    row_score=0, weather_active=False):
        """Format a single board row."""
        rc = ROW_COLOR.get(row_name, "white")
        horn_tag = " \U0001f4ef\U0001f50a" if has_horn else ""
        header = f"[bold {rc}]{row_emoji} {row_name.title()}:{weather_tag}{horn_tag} {ZAP}{row_score}[/bold {rc}]"

        if not cards:
            return header

        lines = [header]
        for c in cards:
            lines.append(f"  {card_display_short(c, weather_active=weather_active)}")
        return "\n".join(lines)

    def _render_hands(self, state):
        p1_count = len(state.hands[P1])
        p2_count = len(state.hands[P2])
        table = Table(
            box=box.SIMPLE_HEAVY,
            expand=True,
            padding=(0, 1),
            show_header=False,
        )
        table.add_column(ratio=1)
        table.add_column(ratio=1)

        # Leaders first
        p1_rows = [leader_display(state.leaders[P1])]
        p2_rows = [leader_display(state.leaders[P2])]

        for c in state.hands[P1]:
            p1_rows.append(card_display(c))
        for c in state.hands[P2]:
            p2_rows.append(card_display(c))

        max_len = max(len(p1_rows), len(p2_rows))
        p1_rows.extend([""] * (max_len - len(p1_rows)))
        p2_rows.extend([""] * (max_len - len(p2_rows)))

        for p1, p2 in zip(p1_rows, p2_rows):
            table.add_row(p1, p2)

        return Panel(table, title=f"\U0001f0cf Hands ({p1_count} | {p2_count})")

    def _render_decks(self, state):
        p1_count = len(state.decks[P1])
        p2_count = len(state.decks[P2])
        table = Table(
            box=box.SIMPLE_HEAVY,
            expand=True,
            padding=(0, 1),
            show_header=False,
        )
        table.add_column(ratio=1)
        table.add_column(ratio=1)

        p1_cards = [card_display(c) for c in state.decks[P1]]
        p2_cards = [card_display(c) for c in state.decks[P2]]

        max_len = max(len(p1_cards), len(p2_cards), 1)
        p1_cards.extend([""] * (max_len - len(p1_cards)))
        p2_cards.extend([""] * (max_len - len(p2_cards)))

        for p1, p2 in zip(p1_cards, p2_cards):
            table.add_row(p1, p2)

        return Panel(table, title=f"\U0001f4e6 Deck ({p1_count} | {p2_count})")

    def _render_discard(self, state):
        p1_disc = state.discard[P1]
        p2_disc = state.discard[P2]

        if not p1_disc and not p2_disc:
            return Panel(
                Text("No discards", justify="center", style="dim"),
                title="\U0001f5d1\ufe0f Discard",
            )

        table = Table(
            box=box.SIMPLE_HEAVY,
            expand=True,
            padding=(0, 1),
            show_header=False,
        )
        table.add_column(ratio=1)
        table.add_column(ratio=1)

        p1_cards = [card_display(c) for c in p1_disc]
        p2_cards = [card_display(c) for c in p2_disc]

        max_len = max(len(p1_cards), len(p2_cards), 1)
        p1_cards.extend([""] * (max_len - len(p1_cards)))
        p2_cards.extend([""] * (max_len - len(p2_cards)))

        for p1, p2 in zip(p1_cards, p2_cards):
            table.add_row(p1, p2)

        return Panel(table, title=f"\U0001f5d1\ufe0f Discard ({len(p1_disc)} | {len(p2_disc)})")

    def _render_weather_passed(self, state):
        parts = []

        if state.weather_rows:
            weather_items = []
            for row in sorted(state.weather_rows):
                emoji = WEATHER_EMOJI.get(row, "")
                name = WEATHER_NAME.get(row, row)
                weather_items.append(f"{emoji} {name} ({row})")
            parts.append("\U0001f326\ufe0f Weather: " + ", ".join(weather_items))
        else:
            parts.append("\U0001f326\ufe0f No active weather")

        p1_passed = state.passed.get(P1, False)
        p2_passed = state.passed.get(P2, False)
        if p1_passed and p2_passed:
            parts.append(f"{FLAG} Both players passed")
        elif p1_passed:
            parts.append(f"{FLAG} P1 passed")
        elif p2_passed:
            parts.append(f"{FLAG} P2 passed")
        else:
            parts.append("\u270b Neither player has passed")

        return Panel(Text("\n".join(parts)), style="dim")

    def _render_footer(self, state):
        parts = []

        if state.last_prompt:
            parts.append(f"\U0001f4df {state.last_prompt}")
        if state.last_announcement and state.last_announcement != state.last_prompt:
            parts.append(f"\U0001f4e2 {state.last_announcement}")
        if state.last_card_read:
            name = state.last_card_read.get("name", "???")
            faction = state.last_card_read.get("faction", "")
            fe = faction_emoji(faction)
            parts.append(f"\U0001f4f1 Scanned: {fe[0]}{fe[1]} {name}")
        if state.last_error:
            parts.append(f"\u274c {state.last_error}")

        if state.event_log:
            recent = list(state.event_log)[-3:]
            parts.append(
                "\u2502 ".join(f"[dim]{e}[/dim]" for e in recent)
            )

        if not parts:
            parts.append("[dim]Waiting for events...[/dim]")

        content = "\n".join(parts)
        return Panel(Text.from_markup(content), title="Events", style="dim")
