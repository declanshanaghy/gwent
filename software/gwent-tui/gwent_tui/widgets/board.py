"""Board widget: 3 combat rows x 2 players, plus top-level scoreboard.

Each combat-row section (close/ranged/siege for P1 and P2) is tappable: a tap
opens a view-only CardListModal listing that section's cards. We record the
y-band of each combat row during render() so on_click can map a tap to the
right (player, row). See feedback_left_anchored_menus / project_pi_display.
"""

import logging

from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from textual import events
from textual.containers import Vertical
from textual.widgets import Static

log = logging.getLogger("gwent_tui.board")

from gwent_tui.emoji import (
    card_display_short, gems_display, ROW_EMOJI, WEATHER_EMOJI, WEATHER_NAME, FLAG, ZAP,
    FACTION_STYLE, faction_emoji,
    BOND, MORALE, COMMANDER, HERO,
)
from gwent_tui.game_state import P1, P2

ROW_COLOR = {
    "close": "orange1",
    "ranged": "orchid",
    "siege": "turquoise2",
}

# Two-column box with solid vertical divider and horizontal row separators
SPLIT_BOX = box.Box(
    "    \n"
    "  \u2502 \n"
    "\u2500\u2500\u253c\u2500\n"
    "  \u2502 \n"
    "\u2500\u2500\u253c\u2500\n"
    "  \u2502 \n"
    "  \u2502 \n"
    "    \n"
)


class ScoreboardWidget(Static):
    """Top-level scoreboard: P1 status | scores | P2 status."""

    def render(self):
        state = self.app.state
        p1s = state.scores[P1]
        p2s = state.scores[P2]

        # Weather
        if state.weather_rows:
            weather_items = []
            for row in sorted(state.weather_rows):
                emoji = WEATHER_EMOJI.get(row, "")
                name = WEATHER_NAME.get(row, row)
                weather_items.append(f"{emoji} {name}")
            weather = " | ".join(weather_items)
        else:
            weather = ""

        # Passed status
        p1_passed = state.passed.get(P1, False)
        p2_passed = state.passed.get(P2, False)
        p1_pass = f"{FLAG}" if p1_passed else ""
        p2_pass = f"{FLAG}" if p2_passed else ""

        # Gems (highlight on change)
        p1_gems_str = gems_display(state.gems.get(P1, 0))
        p2_gems_str = gems_display(state.gems.get(P2, 0))
        if state.is_highlighted(f"gems:{P1}"):
            p1_gems_str = f"[on dark_red]{p1_gems_str}[/on dark_red]"
        if state.is_highlighted(f"gems:{P2}"):
            p2_gems_str = f"[on dark_red]{p2_gems_str}[/on dark_red]"

        # Score highlights
        p1s_style = "on dark_green" if state.is_highlighted(f"score:{P1}") else ""
        p2s_style = "on dark_green" if state.is_highlighted(f"score:{P2}") else ""
        p1s_open = f"[{p1s_style}]" if p1s_style else ""
        p1s_close = f"[/{p1s_style}]" if p1s_style else ""
        p2s_open = f"[{p2s_style}]" if p2s_style else ""
        p2s_close = f"[/{p2s_style}]" if p2s_style else ""

        # Leader names with faction emoji — chop middle if too long
        from gwent_tui.widgets.header import _leader_nick
        max_name = 14
        p1_leader = state.leaders.get(P1)
        p2_leader = state.leaders.get(P2)
        p1_nick = _leader_nick(p1_leader) if p1_leader else ""
        p2_nick = _leader_nick(p2_leader) if p2_leader else ""

        def _mid_truncate(name, limit):
            if len(name) <= limit:
                return name
            keep = limit - 1  # room for ellipsis char
            left = (keep + 1) // 2
            right = keep // 2
            return name[:left] + "\u2026" + name[-right:]

        p1_nick = _mid_truncate(p1_nick, max_name)
        p2_nick = _mid_truncate(p2_nick, max_name)
        p1e = faction_emoji(state.factions.get(P1, ""))
        p2e = faction_emoji(state.factions.get(P2, ""))
        p1f = state.factions.get(P1, "")
        p2f = state.factions.get(P2, "")
        p1_fc = FACTION_STYLE.get(p1f, ("white", "grey30", "white"))[0]
        p2_fc = FACTION_STYLE.get(p2f, ("white", "grey30", "white"))[0]

        # Row 1: LEADER1 vs LEADER2, each leader flanked by its faction
        # emoji pair, faction-colored, centered.
        def _leader_cell(nick, emoji_pair, fc):
            if not nick:
                return "[dim]-[/dim]"
            return f"[{fc}]{emoji_pair[0]} {nick} {emoji_pair[1]}[/{fc}]"
        p1_pass_tag = f"{p1_pass} " if p1_pass else ""
        p2_pass_tag = f" {p2_pass}" if p2_pass else ""
        row1 = (f"{p1_pass_tag}{_leader_cell(p1_nick, p1e, p1_fc)}"
                f"  [bold]vs[/bold]  "
                f"{_leader_cell(p2_nick, p2e, p2_fc)}{p2_pass_tag}")

        # Turn indicator: an arrow in the middle pointing at the active side —
        # ◀ for P1 (left), ▶ for P2 (right), in that side's faction color.
        cur = getattr(state, "current_player", None)
        if cur == P1:
            turn_arrow = f"[bold {p1_fc}]◀◀◀[/]"
        elif cur == P2:
            turn_arrow = f"[bold {p2_fc}]▶▶▶[/]"
        else:
            turn_arrow = "[dim]—[/dim]"

        # Row 2: scores with the turn arrow between them (no "vs"), centered.
        row2 = (
            f"{p1_gems_str} "
            f"{p1s_open}[bold yellow]{p1s}[/bold yellow]{p1s_close}"
            f"   {turn_arrow}   "
            f"{p2s_open}[bold dodger_blue2]{p2s}[/bold dodger_blue2]{p2s_close}"
            f" {p2_gems_str}"
        )

        table = Table(box=None, expand=True, show_header=False, padding=(0, 0))
        table.add_column(justify="center", no_wrap=True)
        table.add_row(Text.from_markup(row1))
        table.add_row(Text.from_markup(row2))

        return Panel(table, title="\U0001f3c6 Scoreboard")


class _BoardRows(Static):
    """The 3 combat rows (close, ranged, siege) for both players."""
    DEFAULT_CSS = """
    _BoardRows { width: 1fr; height: 1fr; }
    """

    # Filled during render(): list of (row_name, y_start, y_end) in widget
    # coords. on_click uses it (plus x < width/2 → P1) to open a section view.
    _bands: list

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._bands = []

    def _max_name(self):
        """Compute max card name length based on pane width."""
        col_width = max(10, (self.size.width - 4) // 2)
        return max(8, col_width - 10)

    def _format_row(self, cards, row_name, row_emoji, weather_tag, has_horn,
                    row_score=0, weather_active=False, player=None,
                    min_lines=0, max_lines=0):
        rc = ROW_COLOR.get(row_name, "white")

        # Detect active abilities from cards on this row
        abilities = []
        has_bond = False
        has_morale = False
        has_hero = False
        for c in cards:
            card_abs = c.get("abilities", [])
            card_ab = c.get("ability", "")
            if "bond" in card_abs or card_ab == "bond":
                has_bond = True
            if "morale" in card_abs or card_ab == "morale":
                has_morale = True
            if c.get("specialty") == "hero":
                has_hero = True
        if has_bond:
            abilities.append(f"{BOND}Bond")
        if has_morale:
            abilities.append(f"{MORALE}Morale")
        if has_horn:
            abilities.append(f"{COMMANDER}Horn\u00d72")
        if weather_active:
            abilities.append(f"{WEATHER_EMOJI.get(row_name, '')}{WEATHER_NAME.get(row_name, 'Weather')}")

        ability_str = " ".join(abilities)
        if ability_str:
            header = f"[bold {rc}]{row_emoji} {row_name.title()}: {row_score}[/bold {rc}]  {ability_str}"
        else:
            header = f"[bold {rc}]{row_emoji} {row_name.title()}: {row_score}[/bold {rc}]"

        state = self.app.state

        # Flash highlight when a card has just landed on this row
        flash_key = f"flash:{player}:{row_name}" if player else ""
        if flash_key and state.is_highlighted(flash_key):
            header = f"[on dark_green]{header}[/on dark_green]"

        mn = self._max_name()
        half_weather = state.half_weather_penalty.get(player, False) if player else False
        lines = [header]
        # Show ghost (removed) cards first with red strikethrough
        if player:
            for c in state.get_ghosts("board", player, row_name):
                text = card_display_short(c, max_name=mn, weather_active=weather_active,
                                          half_weather=half_weather)
                lines.append(f"  [on dark_red strike]{text}[/on dark_red strike]")
        for c in cards:
            name = c.get("name", "")
            hl_key = f"board:{player}:{row_name}:{name}" if player else ""
            text = card_display_short(c, max_name=mn, weather_active=weather_active,
                                      half_weather=half_weather)
            if player and state.is_highlighted(hl_key):
                lines.append(f"  [on dark_green]{text}[/on dark_green]")
            else:
                lines.append(f"  {text}")
        # Truncate to max_lines so rows don't push others off screen
        if max_lines and len(lines) > max_lines:
            hidden = len(lines) - max_lines + 1
            lines = lines[:max_lines - 1]
            lines.append(f"  [dim]… +{hidden} more[/dim]")
        # Pad to min_lines so rows fill evenly
        while len(lines) < min_lines:
            lines.append("")
        return "\n".join(lines)

    def render(self):
        state = self.app.state

        # Minimum lines per row: header + 1 empty slot
        min_row_lines = 2

        table = Table(
            box=SPLIT_BOX,
            expand=True,
            padding=(0, 1),
            show_header=False,
            show_lines=True,
            show_edge=False,
        )
        table.add_column(ratio=1)
        table.add_column(ratio=1)

        # Track y-bands for click mapping. y=0 is the Panel's top border line;
        # interior content starts at y=1. show_lines adds one separator line
        # between adjacent table rows.
        self._bands = []
        y = 1

        for row_name in ("close", "ranged", "siege"):
            re = ROW_EMOJI.get(row_name, "")
            weather_active = row_name in state.weather_rows
            weather_tag = f" {WEATHER_EMOJI.get(row_name, '')}" if weather_active else ""

            p1_cards = state.board_rows[P1].get(row_name, [])
            p2_cards = state.board_rows[P2].get(row_name, [])

            p1_horn = row_name in state.commander_horn_rows.get(P1, set())
            p2_horn = row_name in state.commander_horn_rows.get(P2, set())

            p1_row_score = state.row_scores[P1].get(row_name, 0)
            p2_row_score = state.row_scores[P2].get(row_name, 0)

            p1_text = self._format_row(p1_cards, row_name, re, weather_tag, p1_horn,
                                       p1_row_score, weather_active=weather_active,
                                       player=P1, min_lines=min_row_lines)
            p2_text = self._format_row(p2_cards, row_name, re, weather_tag, p2_horn,
                                       p2_row_score, weather_active=weather_active,
                                       player=P2, min_lines=min_row_lines)

            table.add_row(p1_text, p2_text)

            # Band = this row's content + its trailing separator line (tapping
            # the divider maps to the row above — forgiving on touch).
            h = max(p1_text.count("\n") + 1, p2_text.count("\n") + 1)
            self._bands.append((row_name, y, y + h + 1))
            y += h + 1  # content + separator

            # Horn indicator between rows — only when active
            if p1_horn or p2_horn:
                HORN = "\U0001f4ef"
                p1_horn_str = f"[bold yellow]{HORN} HORN \u00d72 {HORN}[/bold yellow]" if p1_horn else ""
                p2_horn_str = f"[bold yellow]{HORN} HORN \u00d72 {HORN}[/bold yellow]" if p2_horn else ""
                table.add_row(p1_horn_str, p2_horn_str)
                y += 2  # horn row + its separator

        # Leader ability footer row — short nickname, faction colored
        from gwent_tui.widgets.header import _leader_nick
        p1_ability = ""
        p2_ability = ""
        p1_leader = state.leaders.get(P1)
        p2_leader = state.leaders.get(P2)
        for p, leader in ((P1, p1_leader), (P2, p2_leader)):
            if not leader:
                continue
            nick = _leader_nick(leader)
            instr = leader.get("leader", {}).get("instructions", "")
            used = state.leader_used.get(p, False)
            faction = leader.get("faction", "")
            fg = FACTION_STYLE.get(faction, ("white", "grey30", "white"))[0]
            if used:
                style = f"strike dim {fg}"
            else:
                style = f"italic {fg}"
            text = f"\U0001f451 [{style}]{nick}: {instr}[/{style}]"
            if p == P1:
                p1_ability = text
            else:
                p2_ability = text
        table.add_row(p1_ability, p2_ability)

        # Weather summary at bottom
        if state.weather_rows:
            weather_items = []
            for row in sorted(state.weather_rows):
                emoji = WEATHER_EMOJI.get(row, "")
                name = WEATHER_NAME.get(row, row)
                weather_items.append(f"{emoji} {name}")
            weather_str = "  ".join(weather_items)
            table.add_row(
                f"[bold red]{weather_str}[/bold red]",
                f"[bold red]{weather_str}[/bold red]",
            )

        return Panel(table, title="\u2694 Board")

    def on_click(self, event: events.Click) -> None:
        """Tap a combat-row section \u2192 view-only list of that section's cards."""
        y = event.y
        row_name = None
        for rn, y_start, y_end in (self._bands or []):
            if y_start <= y < y_end:
                row_name = rn
                break
        if row_name is None:
            log.debug("Board tap y=%d hit no row band (%s)", y, self._bands)
            return
        width = self.size.width or 1
        player = P1 if event.x < width / 2 else P2
        state = self.app.state
        cards = list(state.board_rows[player].get(row_name, []))
        tag = "P1" if player == P1 else "P2"
        title = f"\u2694 {tag} \u2014 {row_name.title()} ({len(cards)})"
        log.info("Board section tapped x=%d y=%d -> %s %s (%d cards)",
                 event.x, y, player, row_name, len(cards))
        try:
            from gwent_tui.hand_detail_modal import CardListModal
            self.app.push_screen(
                CardListModal(title, cards, player_key=player))
        except Exception as e:
            log.error("failed to open board section view: %s", e, exc_info=True)


class BoardWidget(Vertical):

    DEFAULT_CSS = """
    BoardWidget {
        height: 1fr;
    }
    """

    def compose(self):
        yield _BoardRows()
