"""TUI stage: GameOver — showcase winning leader, remaining hands, and discards."""

from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from textual.containers import Horizontal, Vertical
from textual.widgets import Static

from gwent_tui.emoji import (
    card_display, leader_display, gems_display, faction_emoji, card_display_short,
    FACTION_COLOR, FACTION_STYLE, CROWN, GEM, SKULL, ROW_EMOJI, WEATHER_EMOJI, ZAP,
)
from gwent_tui.game_state import P1, P2
from gwent_tui.widgets.board import ScoreboardWidget
from gwent_tui.widgets.header import _leader_nick


class _WinnerBanner(Static):
    """Large banner announcing the winner with leader and faction info."""

    def render(self):
        state = self.app.state
        p1_gems = state.gems.get(P1, 0)
        p2_gems = state.gems.get(P2, 0)

        if p1_gems > p2_gems:
            winner = P1
        elif p2_gems > p1_gems:
            winner = P2
        else:
            winner = None

        # Always show P1 on left, P2 on right
        p1_leader = state.leaders.get(P1) or {}
        p2_leader = state.leaders.get(P2) or {}
        p1_nick = _leader_nick(p1_leader) if p1_leader else "P1"
        p2_nick = _leader_nick(p2_leader) if p2_leader else "P2"
        p1f = state.factions.get(P1, "")
        p2f = state.factions.get(P2, "")
        p1e = faction_emoji(p1f)
        p2e = faction_emoji(p2f)
        p1_fc = FACTION_COLOR.get(p1f, "white")
        p2_fc = FACTION_COLOR.get(p2f, "white")

        if winner:
            w_leader = state.leaders.get(winner) or {}
            w_faction = state.factions.get(winner, "")
            w_name = _leader_nick(w_leader) if w_leader else "Unknown"
            w_fe = faction_emoji(w_faction)
            _, w_bg, w_fg = FACTION_STYLE.get(w_faction, ("white", "grey30", "white"))
            w_fc = FACTION_COLOR.get(w_faction, "white")

            banner = (
                f"{w_fe[0]} {CROWN} [bold {w_fg} on {w_bg}] {w_name} WINS! [/bold {w_fg} on {w_bg}] {CROWN} {w_fe[1]}\n"
                f"[bold green]VICTORY![/bold green] {w_name} ({w_faction})\n"
                f"{p1e[0]} [{p1_fc}]{p1_nick}[/{p1_fc}] {gems_display(p1_gems)}"
                f"  vs  "
                f"{gems_display(p2_gems)} [{p2_fc}]{p2_nick}[/{p2_fc}] {p2e[1]}"
            )
            title = f"{w_fe[0]} GAME OVER {w_fe[1]}"
            border = f"bold {w_fc}"
        else:
            banner = (
                f"{SKULL} [bold yellow]DRAW![/bold yellow] {SKULL}\n"
                f"Both leaders fall — no victor emerges\n"
                f"{p1e[0]} [{p1_fc}]{p1_nick}[/{p1_fc}] {gems_display(p1_gems)}"
                f"  vs  "
                f"{gems_display(p2_gems)} [{p2_fc}]{p2_nick}[/{p2_fc}] {p2e[1]}"
            )
            title = f"{SKULL} GAME OVER {SKULL}"
            border = "bold yellow"

        return Panel(
            Text.from_markup(banner, justify="center"),
            title=title,
            border_style=border,
        )


class _FinalBoard(Static):
    """Final board state showing all rows with scores."""
    DEFAULT_CSS = "_FinalBoard { width: 1fr; min-height: 100%; }"

    def _format_row(self, cards, row_name, row_score, weather_active, has_horn):
        from gwent_tui.widgets.board import ROW_COLOR
        rc = ROW_COLOR.get(row_name, "white")
        re = ROW_EMOJI.get(row_name, "")
        weather_tag = f" {WEATHER_EMOJI.get(row_name, '')}" if weather_active else ""
        horn_tag = " \U0001f4ef\U0001f50a" if has_horn else ""
        header = f"[bold {rc}]{re} {row_name.title()}:{weather_tag}{horn_tag}  {ZAP} {row_score}[/bold {rc}]"

        if not cards:
            return header

        lines = [header]
        for c in cards:
            lines.append(f"  {card_display_short(c, weather_active=weather_active)}")
        return "\n".join(lines)

    def render(self):
        state = self.app.state

        table = Table(
            box=box.SIMPLE_HEAVY, expand=True, padding=(0, 1),
            show_header=False, show_lines=True,
        )
        table.add_column(ratio=1)
        table.add_column(ratio=1)

        for row_name in ("close", "ranged", "siege"):
            weather_active = row_name in state.weather_rows
            for side in (P1, P2):
                cards = state.board_rows[side].get(row_name, [])
                horn = row_name in state.commander_horn_rows.get(side, set())
                row_score = state.row_scores[side].get(row_name, 0)

            p1_text = self._format_row(
                state.board_rows[P1].get(row_name, []), row_name,
                state.row_scores[P1].get(row_name, 0), weather_active,
                row_name in state.commander_horn_rows.get(P1, set()))
            p2_text = self._format_row(
                state.board_rows[P2].get(row_name, []), row_name,
                state.row_scores[P2].get(row_name, 0), weather_active,
                row_name in state.commander_horn_rows.get(P2, set()))
            table.add_row(p1_text, p2_text)

        return Panel(table, title="\u2694 Final Board")


class _HandsAndDiscards(Static):
    """Combined view: leader + remaining hand + all discards for both players."""
    DEFAULT_CSS = "_HandsAndDiscards { width: 1fr; min-height: 100%; }"

    def render(self):
        state = self.app.state
        p1_gems = state.gems.get(P1, 0)
        p2_gems = state.gems.get(P2, 0)

        if p1_gems > p2_gems:
            winner, loser = P1, P2
        elif p2_gems > p1_gems:
            winner, loser = P2, P1
        else:
            winner, loser = P1, P2  # arbitrary for draw

        table = Table(
            box=box.SIMPLE_HEAVY, expand=True, padding=(0, 1),
            show_header=False,
        )
        table.add_column(ratio=1)
        table.add_column(ratio=1)

        for player in (P1, P2):
            pass  # build below

        # Build rows for each player
        p1_rows = self._build_player_rows(state, P1, P1 == winner)
        p2_rows = self._build_player_rows(state, P2, P2 == winner)

        max_len = max(len(p1_rows), len(p2_rows))
        p1_rows.extend([""] * (max_len - len(p1_rows)))
        p2_rows.extend([""] * (max_len - len(p2_rows)))

        for p1, p2 in zip(p1_rows, p2_rows):
            table.add_row(p1, p2)

        p1_hand_n = len(state.hands[P1])
        p2_hand_n = len(state.hands[P2])
        p1_disc_n = len(state.discard[P1])
        p2_disc_n = len(state.discard[P2])

        return Panel(
            table,
            title=(f"\U0001f451 Leaders, Hands ({p1_hand_n}|{p2_hand_n})"
                   f" & Discards ({p1_disc_n}|{p2_disc_n})"),
        )

    def _build_player_rows(self, state, player, is_winner):
        rows = []
        gems = state.gems.get(player, 0)
        faction = state.factions.get(player, "")
        fe = faction_emoji(faction)
        fc = FACTION_COLOR.get(faction, "white")
        leader = state.leaders.get(player)
        nick = _leader_nick(leader) if leader else ("P1" if player == P1 else "P2")

        # Header with gems — winner gets highlight
        if is_winner:
            _, bg, fg = FACTION_STYLE.get(faction, ("white", "grey30", "white"))
            tag = f"[bold {fg} on {bg}] WINNER [/bold {fg} on {bg}] "
        else:
            tag = ""
        rows.append(f"{tag}{fe[0]} [bold {fc}]{nick}[/bold {fc}] {gems_display(gems)} {fe[1]}")

        # Leader
        leader = state.leaders.get(player)
        if leader:
            rows.append(leader_display(leader, used=state.leader_used.get(player, False)))

        rows.append("[dim]" + "\u2500" * 30 + "[/dim]")

        # Remaining hand
        hand = state.hands.get(player, [])
        if hand:
            rows.append(f"[bold]\U0001f0cf Hand ({len(hand)}):[/bold]")
            for c in hand:
                rows.append(f"  {card_display(c)}")
        else:
            rows.append("[dim]Hand: empty[/dim]")

        rows.append("[dim]" + "\u2500" * 30 + "[/dim]")

        # Discards
        disc = state.discard.get(player, [])
        if disc:
            rows.append(f"[bold]\U0001f5d1 Discard ({len(disc)}):[/bold]")
            for c in disc:
                rows.append(f"  {card_display(c)}")
        else:
            rows.append("[dim]Discard: empty[/dim]")

        return rows


class GameOverStage(Vertical):
    DEFAULT_CSS = """
    GameOverStage { height: 1fr; }
    GameOverStage #winner-banner { height: auto; max-height: 7; }
    GameOverStage #game-over-columns { height: 1fr; }
    GameOverStage #final-board { width: 2fr; }
    GameOverStage #hands-discards { width: 3fr; }
    """

    def compose(self):
        yield _WinnerBanner(id="winner-banner")
        with Horizontal(id="game-over-columns"):
            yield _FinalBoard(id="final-board")
            yield _HandsAndDiscards(id="hands-discards")
