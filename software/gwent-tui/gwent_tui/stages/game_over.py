"""TUI stage: GameOver — rich consolidated game summary with Gwent flair."""

from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from textual.containers import Horizontal, Vertical
from textual.widgets import Static

from gwent_tui.emoji import (
    card_display, leader_display, gems_display, faction_emoji, card_display_short,
    FACTION_COLOR, FACTION_STYLE, CROWN, GEM, SKULL, ROW_EMOJI, WEATHER_EMOJI, ZAP,
    BOND, MORALE, COMMANDER, HERO,
)
from gwent_tui.game_state import P1, P2
from gwent_tui.widgets.header import _leader_nick

# Faction-themed victory quotes
VICTORY_QUOTES = {
    "Monsters": "The Wild Hunt claims another soul!",
    "Nilfgaardian": "The Empire's might is absolute.",
    "Northern Realms": "For Temeria! The North remembers!",
    "Scoia'tael": "The forest strikes swift and true!",
    "Skellige": "Skaal! The seas belong to the Isles!",
}

DEFEAT_QUIPS = {
    "Monsters": "Even monsters know when to retreat...",
    "Nilfgaardian": "The Emperor will not be pleased.",
    "Northern Realms": "Temeria has seen darker days.",
    "Scoia'tael": "The forest will grow back stronger.",
    "Skellige": "The sea gives, and the sea takes.",
}

ROUND_EMOJI = {1: "\u2776", 2: "\u2777", 3: "\u2778"}  # ❶ ❷ ❸


class _GameSummary(Static):
    """Full-screen consolidated game summary."""

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

        # Player info
        p1_leader = state.leaders.get(P1) or {}
        p2_leader = state.leaders.get(P2) or {}
        p1_nick = _leader_nick(p1_leader) if p1_leader else "P1"
        p2_nick = _leader_nick(p2_leader) if p2_leader else "P2"
        p1_name = state.player_names.get(P1, "Player 1")
        p2_name = state.player_names.get(P2, "Player 2")
        p1f = state.factions.get(P1, "")
        p2f = state.factions.get(P2, "")
        p1e = faction_emoji(p1f)
        p2e = faction_emoji(p2f)
        p1_fc = FACTION_COLOR.get(p1f, "white")
        p2_fc = FACTION_COLOR.get(p2f, "white")

        lines = []

        # === WINNER BANNER ===
        if winner:
            w_faction = state.factions.get(winner, "")
            w_name = state.player_names.get(winner, "???")
            w_nick = _leader_nick(state.leaders.get(winner) or {})
            w_fe = faction_emoji(w_faction)
            _, w_bg, w_fg = FACTION_STYLE.get(w_faction, ("white", "grey30", "white"))
            quote = VICTORY_QUOTES.get(w_faction, "Victory is sweet!")

            lines.append(f"[bold {w_fg} on {w_bg}]  {CROWN} {CROWN} {CROWN}  {w_name} ({w_nick}) WINS!  {CROWN} {CROWN} {CROWN}  [/bold {w_fg} on {w_bg}]")
            lines.append(f"[italic dim]{quote}[/italic dim]")
        else:
            lines.append(f"[bold yellow on grey23]  {SKULL} {SKULL} {SKULL}  DRAW — NO VICTOR  {SKULL} {SKULL} {SKULL}  [/bold yellow on grey23]")
            lines.append("[italic dim]The cards fall silent... neither player claims the day.[/italic dim]")
        lines.append("")

        # === MATCHUP ===
        lines.append(f"{p1e[0]}{p1e[1]} [{p1_fc} bold]{p1_name}[/{p1_fc} bold] ([dim]{p1_nick}[/dim], {p1f})")
        lines.append(f"    [dim]vs[/dim]")
        lines.append(f"{p2e[0]}{p2e[1]} [{p2_fc} bold]{p2_name}[/{p2_fc} bold] ([dim]{p2_nick}[/dim], {p2f})")
        lines.append("")

        # === ROUND-BY-ROUND ===
        lines.append("[bold underline]\u2694 Round-by-Round[/bold underline]")
        lines.append("")

        if state.round_results:
            for rr in state.round_results:
                rnum = rr["round"]
                p1s = rr["p1_score"]
                p2s = rr["p2_score"]
                rw = rr.get("winner")
                remoji = ROUND_EMOJI.get(rnum, f"R{rnum}")

                if rw == P1:
                    p1_tag = f"[bold green]{CROWN} {p1s}[/bold green]"
                    p2_tag = f"[dim]{p2s}[/dim]"
                    result = f"[{p1_fc}]{p1_name}[/{p1_fc}]"
                elif rw == P2:
                    p1_tag = f"[dim]{p1s}[/dim]"
                    p2_tag = f"[bold green]{CROWN} {p2s}[/bold green]"
                    result = f"[{p2_fc}]{p2_name}[/{p2_fc}]"
                else:
                    p1_tag = f"[yellow]{p1s}[/yellow]"
                    p2_tag = f"[yellow]{p2s}[/yellow]"
                    result = "[yellow]Draw[/yellow]"

                lines.append(f"  {remoji} Round {rnum}:  {p1_tag}  —  {p2_tag}    {CROWN} {result}")
        else:
            lines.append("  [dim]No round data recorded[/dim]")
        lines.append("")

        # === FINAL GEMS ===
        lines.append("[bold underline]\U0001f48e Final Standing[/bold underline]")
        lines.append("")
        lines.append(f"  {p1e[0]}{p1e[1]} [{p1_fc}]{p1_name}[/{p1_fc}]  {gems_display(p1_gems)}")
        lines.append(f"  {p2e[0]}{p2e[1]} [{p2_fc}]{p2_name}[/{p2_fc}]  {gems_display(p2_gems)}")
        lines.append("")

        # === MOVE TIMING ===
        p1_times = state.move_times.get(P1, [])
        p2_times = state.move_times.get(P2, [])
        if p1_times or p2_times:
            lines.append("[bold underline]\u23f1 Timing[/bold underline]")
            lines.append("")
            for p, times, name, fc in [
                (P1, p1_times, p1_name, p1_fc),
                (P2, p2_times, p2_name, p2_fc),
            ]:
                if times:
                    avg = sum(times) / len(times)
                    total = sum(times)
                    lines.append(
                        f"  [{fc}]{name}[/{fc}]:  "
                        f"{len(times)} moves, {avg:.1f}s avg, {total:.0f}s total"
                    )
            lines.append("")

        # === REMAINING HANDS ===
        p1_hand = state.hands.get(P1, [])
        p2_hand = state.hands.get(P2, [])
        if p1_hand or p2_hand:
            lines.append("[bold underline]\U0001f0cf Cards Left in Hand[/bold underline]")
            lines.append("")
            for p, hand, name, fc in [
                (P1, p1_hand, p1_name, p1_fc),
                (P2, p2_hand, p2_name, p2_fc),
            ]:
                if hand:
                    total_str = sum(c.get("strength", 0) for c in hand)
                    lines.append(f"  [{fc}]{name}[/{fc}] ({len(hand)} cards, {total_str} str):")
                    for c in hand:
                        lines.append(f"    {card_display_short(c)}")
            lines.append("")

        # === LOSER QUIP ===
        if loser:
            l_faction = state.factions.get(loser, "")
            quip = DEFEAT_QUIPS.get(l_faction, "Better luck next time.")
            lines.append(f"[dim italic]{quip}[/dim italic]")

        # Build the panel
        if winner:
            w_faction = state.factions.get(winner, "")
            w_fc = FACTION_COLOR.get(w_faction, "white")
            w_fe = faction_emoji(w_faction)
            title = f"{w_fe[0]} {CROWN} GAME OVER {CROWN} {w_fe[1]}"
            border = f"bold {w_fc}"
        else:
            title = f"{SKULL} GAME OVER {SKULL}"
            border = "bold yellow"

        return Panel(
            Text.from_markup("\n".join(lines), justify="center"),
            title=title,
            border_style=border,
        )


class GameOverStage(Vertical):
    DEFAULT_CSS = """
    GameOverStage { height: 1fr; }
    GameOverStage #game-summary { height: 1fr; }
    """

    def compose(self):
        yield _GameSummary(id="game-summary")
