"""TUI stage: GameOver — showcase winning leader, remaining hands, and discards."""

from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from textual.containers import Horizontal, Vertical
from textual.widgets import Static

from gwent_tui.emoji import (
    card_display, leader_display, gems_display, faction_emoji, card_display_short,
    FACTION_COLOR, CROWN, GEM, SKULL, ROW_EMOJI, WEATHER_EMOJI, ZAP,
)
from gwent_tui.game_state import P1, P2
from gwent_tui.widgets.board import ScoreboardWidget


class _WinnerBanner(Static):
    """Large banner announcing the winner with leader and faction info."""

    def render(self):
        state = self.app.state
        p1_gems = state.gems.get(P1, 0)
        p2_gems = state.gems.get(P2, 0)

        if p1_gems > p2_gems:
            winner, loser = P1, P2
        elif p2_gems > p1_gems:
            winner, loser = P2, P1
        else:
            winner, loser = None, None

        if winner:
            w_leader = state.leaders.get(winner) or {}
            w_faction = state.factions.get(winner, "")
            w_name = w_leader.get("name", "Unknown")
            w_num = "1" if winner == P1 else "2"
            l_num = "1" if loser == P1 else "2"
            fe = faction_emoji(w_faction)
            fc = FACTION_COLOR.get(w_faction, "white")

            banner = (
                f"{fe[0]} {CROWN} [{fc} bold]{w_name}[/{fc} bold] {CROWN} {fe[1]}\n"
                f"[bold green]VICTORY![/bold green] "
                f"Player {w_num} ({w_faction}) defeats Player {l_num}\n"
                f"{gems_display(state.gems.get(winner, 0))} vs {gems_display(state.gems.get(loser, 0))}"
            )
            title = f"{fe[0]} GAME OVER {fe[1]}"
        else:
            banner = (
                f"{SKULL} [bold yellow]DRAW![/bold yellow] {SKULL}\n"
                f"Both leaders fall — no victor emerges\n"
                f"{gems_display(0)} vs {gems_display(0)}"
            )
            title = f"{SKULL} GAME OVER {SKULL}"

        return Panel(
            Text.from_markup(banner, justify="center"),
            title=title,
            border_style="bold yellow",
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

        return Panel(table, title="\u2694\ufe0f Final Board")


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
        pnum = "1" if player == P1 else "2"
        gems = state.gems.get(player, 0)
        faction = state.factions.get(player, "")
        fe = faction_emoji(faction)

        # Header with gems
        tag = "[bold green]WINNER[/bold green] " if is_winner else ""
        rows.append(f"{tag}{fe[0]} [bold]Player {pnum}[/bold] {gems_display(gems)} {fe[1]}")

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
            rows.append(f"[bold]\U0001f5d1\ufe0f Discard ({len(disc)}):[/bold]")
            for c in disc:
                rows.append(f"  {card_display(c)}")
        else:
            rows.append("[dim]Discard: empty[/dim]")

        return rows


class GameOverStage(Vertical):
    DEFAULT_CSS = """
    GameOverStage { height: 1fr; }
    GameOverStage #winner-banner { height: auto; max-height: 7; }
    GameOverStage #final-board { height: 2fr; }
    GameOverStage #hands-discards { height: 3fr; }
    """

    def compose(self):
        yield _WinnerBanner(id="winner-banner")
        with Horizontal(id="game-over-columns"):
            yield _FinalBoard(id="final-board")
            yield _HandsAndDiscards(id="hands-discards")
