"""TUI stage: RoundSummary — interstitial between rounds showing round stats."""

from collections import Counter

from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from textual.containers import Horizontal, Vertical
from textual.widgets import Static

from gwent_tui.emoji import FACTION_COLOR, FACTION_STYLE, CROWN, SKULL, faction_emoji
from gwent_tui.game_state import P1, P2
from gwent_tui.widgets.header import _leader_nick


def _info(state):
    p1l = state.leaders.get(P1) or {}
    p2l = state.leaders.get(P2) or {}
    return {
        "p1_name": state.player_names.get(P1, "Player 1"),
        "p2_name": state.player_names.get(P2, "Player 2"),
        "p1_nick": _leader_nick(p1l) if p1l else "P1",
        "p2_nick": _leader_nick(p2l) if p2l else "P2",
        "p1f": state.factions.get(P1, ""),
        "p2f": state.factions.get(P2, ""),
        "p1_fc": FACTION_COLOR.get(state.factions.get(P1, ""), "white"),
        "p2_fc": FACTION_COLOR.get(state.factions.get(P2, ""), "white"),
    }


def _round_result(state, round_num):
    """Find the round result for a given round number."""
    for rr in state.round_results:
        if rr["round"] == round_num:
            return rr
    return None


class _RoundBanner(Static):
    """Round winner/loser banner."""

    def render(self):
        state = self.app.state
        i = _info(state)
        rr = _round_result(state, state._summary_round)

        rnum = state._summary_round
        if rr:
            p1s = rr["p1_score"]
            p2s = rr["p2_score"]
            w = rr.get("winner")
            if w == P1:
                wn = i["p1_name"]
                wfc = i["p1_fc"]
            elif w == P2:
                wn = i["p2_name"]
                wfc = i["p2_fc"]
            else:
                wn = None
                wfc = "yellow"

            if wn:
                text = f"[bold {wfc}]{CROWN} {wn} wins Round {rnum}!  {p1s} — {p2s}[/]"
            else:
                text = f"[bold yellow]{SKULL} Round {rnum} is a draw!  {p1s} — {p2s}[/]"
        else:
            text = f"[dim]Round {rnum} Summary[/]"

        return Panel(Text.from_markup(text, justify="center"),
                     title=f"\u2694 Round {rnum} Summary",
                     border_style="bold bright_white")


class _CardsPlayed(Static):
    """Top-left: Cards played per player this round."""

    def render(self):
        state = self.app.state
        i = _info(state)
        events = state.events_for_round(state._summary_round)

        play_kinds = {"play_card", "place_card", "muster"}
        p1_cards = [e for e in events if e["player"] == P1 and e["subkind"] in play_kinds]
        p2_cards = [e for e in events if e["player"] == P2 and e["subkind"] in play_kinds]

        t = Table(box=box.SIMPLE, expand=True, show_header=True, padding=(0, 1))
        t.add_column(Text.from_markup(f"[{i['p1_fc']}]{i['p1_name']}[/]"), ratio=1, no_wrap=True)
        t.add_column(Text.from_markup(f"[{i['p2_fc']}]{i['p2_name']}[/]"), ratio=1, no_wrap=True)

        max_rows = max(len(p1_cards), len(p2_cards), 1)
        for idx in range(max_rows):
            p1 = ""
            p2 = ""
            if idx < len(p1_cards):
                e = p1_cards[idx]
                s = f" ({e['strength']})" if e.get("strength") else ""
                m = " [dim]M[/]" if e["subkind"] == "muster" else ""
                p1 = f"{e['name']}{s}{m}"
            if idx < len(p2_cards):
                e = p2_cards[idx]
                s = f" ({e['strength']})" if e.get("strength") else ""
                m = " [dim]M[/]" if e["subkind"] == "muster" else ""
                p2 = f"{e['name']}{s}{m}"
            t.add_row(Text.from_markup(p1), Text.from_markup(p2))

        subtitle = f"P1: {len(p1_cards)} cards | P2: {len(p2_cards)} cards"
        return Panel(t, title="\U0001f0cf Cards Played", subtitle=f"[dim]{subtitle}[/]",
                     border_style="dim")


class _Abilities(Static):
    """Top-right: Special events and abilities triggered."""

    def render(self):
        state = self.app.state
        events = state.events_for_round(state._summary_round)

        lines = []

        # Spies
        spies = [e for e in events if e["subkind"] == "spy_draw"]
        if spies:
            lines.append("[bold turquoise2]\U0001f575 Spy Activity[/]")
            for e in spies:
                lines.append(f"  {e['name']} \u2192 {e['player']}")

        # Medics
        medics = [e for e in events if e["subkind"] == "medic_resurrect"]
        if medics:
            lines.append("[bold green3]\U0001f48a Medic Resurrections[/]")
            for e in medics:
                lines.append(f"  {e['name']} resurrected ({e['player']})")

        # Scorches
        scorched = [e for e in events if e["subkind"] == "remove_card"]
        if scorched:
            lines.append("[bold bright_red]\U0001f525 Cards Destroyed[/]")
            for e in scorched:
                lines.append(f"  {e['name']} ({e.get('reason', 'scorch')})")

        # Musters
        musters = [e for e in events if e["subkind"] == "muster"]
        if musters:
            names = Counter(e["name"] for e in musters)
            lines.append("[bold orchid]\U0001f4e3 Muster Calls[/]")
            for name, count in names.items():
                lines.append(f"  {name} \u00d7{count}")

        # Commander horns
        horns = [e for e in events if e["subkind"] == "commander_horn"]
        if horns:
            lines.append("[bold gold1]\U0001f4ef Commander Horns[/]")
            for e in horns:
                lines.append(f"  {e.get('row', '?')} row ({e['player']})")

        # Transforms
        transforms = [e for e in events if e["subkind"] == "transform"]
        if transforms:
            lines.append("[bold bright_magenta]\U0001f500 Transformations[/]")
            for e in transforms:
                lines.append(f"  {e['name']} ({e['player']})")

        # Decoys
        decoys = [e for e in events if e["subkind"] == "decoy_swap"]
        if decoys:
            lines.append("[bold bright_cyan]\U0001f3ad Decoy Swaps[/]")
            for e in decoys:
                lines.append(f"  ({e['player']})")

        if not lines:
            lines.append("[dim]No special abilities triggered[/]")

        return Panel(Text.from_markup("\n".join(lines)),
                     title="\u2728 Abilities & Events", border_style="dim")


class _ScoreProgression(Static):
    """Bottom-left: Score after each play."""

    def render(self):
        state = self.app.state
        i = _info(state)
        events = state.events_for_round(state._summary_round)

        play_kinds = {"play_card", "place_card", "muster"}
        plays = [e for e in events if e["subkind"] in play_kinds]

        t = Table(box=box.SIMPLE, expand=True, show_header=True, padding=(0, 0))
        t.add_column("#", width=3, justify="center")
        t.add_column("Card", ratio=2, no_wrap=True)
        t.add_column("P1", width=4, justify="right")
        t.add_column("P2", width=4, justify="right")
        t.add_column("\u0394", width=5, justify="center")

        prev_diff = 0
        for idx, e in enumerate(plays[:12], 1):  # Cap at 12 rows
            p1s = e.get("p1_score", 0)
            p2s = e.get("p2_score", 0)
            diff = p1s - p2s
            delta = diff - prev_diff
            prev_diff = diff

            delta_str = ""
            if abs(delta) >= 5:
                color = "green" if (delta > 0 and e["player"] == P1) or (delta < 0 and e["player"] == P2) else "red"
                delta_str = f"[{color}]{'+' if delta > 0 else ''}{delta}[/]"

            name = e["name"][:15]
            t.add_row(
                str(idx),
                Text.from_markup(name),
                str(p1s),
                str(p2s),
                Text.from_markup(delta_str),
            )

        return Panel(t, title="\U0001f4c8 Score Progression", border_style="dim")


class _WeatherAndSwings(Static):
    """Bottom-right: Weather effects and big score swings."""

    def render(self):
        state = self.app.state
        events = state.events_for_round(state._summary_round)

        lines = []

        # Weather
        weather = [e for e in events if e["subkind"] == "weather_change"]
        if weather:
            lines.append("[bold grey70]\u2601 Weather Effects[/]")
            for e in weather:
                rows = e.get("weather_rows", [])
                if rows:
                    lines.append(f"  Active: {', '.join(rows)}")
                else:
                    lines.append("  \u2600 Weather cleared")
            lines.append("")

        # Big swings (score changed by 10+)
        play_kinds = {"play_card", "place_card", "muster"}
        plays = [e for e in events if e["subkind"] in play_kinds]
        prev_diff = 0
        swings = []
        for e in plays:
            diff = e.get("p1_score", 0) - e.get("p2_score", 0)
            delta = abs(diff - prev_diff)
            if delta >= 10:
                swings.append((e["name"], e["player"], delta))
            prev_diff = diff

        if swings:
            lines.append("[bold bright_yellow]\U0001f4a5 Big Swings[/]")
            for name, player, delta in swings:
                lines.append(f"  {name} ({player}) \u2014 {delta} pt swing")
            lines.append("")

        # Hero cards played
        heroes = [e for e in events if e.get("specialty") == "hero"
                  and e["subkind"] in play_kinds]
        if heroes:
            lines.append(f"[bold]\U0001f9b8 Heroes Deployed[/]")
            for e in heroes:
                s = e.get("strength", "?")
                lines.append(f"  {e['name']} ({s} str) \u2014 {e['player']}")

        if not lines:
            lines.append("[dim]A quiet round — no weather or big swings[/]")

        return Panel(Text.from_markup("\n".join(lines)),
                     title="\U0001f4a8 Weather & Highlights", border_style="dim")


class _ContinueHint(Static):
    """Bottom hint to proceed."""

    def render(self):
        return Text.from_markup(
            "[dim]Press any key to continue to the next round...[/]",
            justify="center")


class RoundSummaryStage(Vertical):
    DEFAULT_CSS = """
    RoundSummaryStage { height: 1fr; }
    RoundSummaryStage #rs-banner { height: auto; max-height: 4; }
    RoundSummaryStage #rs-top { height: 1fr; }
    RoundSummaryStage #rs-bottom { height: 1fr; }
    RoundSummaryStage .rs-pane { width: 1fr; height: 100%; }
    RoundSummaryStage #rs-hint { height: 1; }
    """

    def compose(self):
        yield _RoundBanner(id="rs-banner")
        with Horizontal(id="rs-top"):
            yield _CardsPlayed(id="rs-cards", classes="rs-pane")
            yield _Abilities(id="rs-abilities", classes="rs-pane")
        with Horizontal(id="rs-bottom"):
            yield _ScoreProgression(id="rs-scores", classes="rs-pane")
            yield _WeatherAndSwings(id="rs-weather", classes="rs-pane")
        yield _ContinueHint(id="rs-hint")

    def on_key(self, event):
        """Any key dismisses the summary and proceeds to next round."""
        self.app.state.dismiss_round_summary()
        self.app._current_stage_name = None  # force re-switch on next tick
