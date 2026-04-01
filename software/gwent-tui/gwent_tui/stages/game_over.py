"""TUI stage: GameOver — organized 2x2 pane layout with game stats."""

from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from textual.containers import Horizontal, Vertical
from textual.widgets import Static

from gwent_tui.emoji import (
    card_display_short, gems_display, faction_emoji,
    FACTION_COLOR, FACTION_STYLE, CROWN, SKULL,
)
from gwent_tui.game_state import P1, P2
from gwent_tui.widgets.header import _leader_nick

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

ROUND_EMOJI = {1: "\u2776", 2: "\u2777", 3: "\u2778"}


def _info(state):
    """Common player info."""
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
        "p1_gems": state.gems.get(P1, 0),
        "p2_gems": state.gems.get(P2, 0),
        "p1e": faction_emoji(state.factions.get(P1, "")),
        "p2e": faction_emoji(state.factions.get(P2, "")),
    }


def _winner(state):
    p1g = state.gems.get(P1, 0)
    p2g = state.gems.get(P2, 0)
    if p1g > p2g:
        return P1
    elif p2g > p1g:
        return P2
    return None


class _Banner(Static):
    """Winner announcement banner."""

    def render(self):
        state = self.app.state
        i = _info(state)
        w = _winner(state)

        if w:
            wf = state.factions.get(w, "")
            wn = i["p1_name"] if w == P1 else i["p2_name"]
            wnick = i["p1_nick"] if w == P1 else i["p2_nick"]
            _, bg, fg = FACTION_STYLE.get(wf, ("white", "grey30", "white"))
            wfc = FACTION_COLOR.get(wf, "white")
            quote = VICTORY_QUOTES.get(wf, "Victory is sweet!")
            text = f"[bold {fg} on {bg}] {CROWN}{CROWN}{CROWN}  {wn} ({wnick}) WINS!  {CROWN}{CROWN}{CROWN} [/]\n[italic dim]{quote}[/]"
            return Panel(Text.from_markup(text, justify="center"),
                         title=f"{CROWN} GAME OVER {CROWN}", border_style=f"bold {wfc}")
        else:
            text = f"[bold yellow on grey23] {SKULL}{SKULL}{SKULL}  DRAW  {SKULL}{SKULL}{SKULL} [/]\n[italic dim]Neither player claims the day.[/]"
            return Panel(Text.from_markup(text, justify="center"),
                         title=f"{SKULL} GAME OVER {SKULL}", border_style="bold yellow")


class _MatchupAndGems(Static):
    """Top-left: Matchup with factions, leaders, gems."""

    def render(self):
        state = self.app.state
        i = _info(state)

        lines = [
            f"{i['p1e'][0]}{i['p1e'][1]} [{i['p1_fc']} bold]{i['p1_name']}[/]",
            f"  [dim]{i['p1_nick']} \u2022 {i['p1f']}[/]",
            f"  {gems_display(i['p1_gems'])}",
            "",
            f"{i['p2e'][0]}{i['p2e'][1]} [{i['p2_fc']} bold]{i['p2_name']}[/]",
            f"  [dim]{i['p2_nick']} \u2022 {i['p2f']}[/]",
            f"  {gems_display(i['p2_gems'])}",
        ]

        w = _winner(state)
        if w:
            lf = state.factions.get(P1 if w == P2 else P2, "")
            quip = DEFEAT_QUIPS.get(lf, "Better luck next time.")
            lines.extend(["", f"[dim italic]{quip}[/]"])

        return Panel(Text.from_markup("\n".join(lines)),
                     title="\u2694 Matchup", border_style="dim")


class _Rounds(Static):
    """Top-right: Round-by-round results table."""

    def render(self):
        state = self.app.state
        i = _info(state)

        t = Table(box=box.SIMPLE, expand=True, show_header=True, padding=(0, 1))
        t.add_column("Rnd", justify="center", width=4)
        t.add_column(i["p1_name"], justify="center", ratio=1, no_wrap=True)
        t.add_column(i["p2_name"], justify="center", ratio=1, no_wrap=True)
        t.add_column("Winner", justify="center", ratio=1, no_wrap=True)

        if state.round_results:
            for rr in state.round_results:
                rnum = rr["round"]
                p1s = rr["p1_score"]
                p2s = rr["p2_score"]
                rw = rr.get("winner")
                re = ROUND_EMOJI.get(rnum, str(rnum))

                if rw == P1:
                    r = (re, f"[bold green]{CROWN} {p1s}[/]", f"[dim]{p2s}[/]",
                         f"[{i['p1_fc']}]{i['p1_name']}[/]")
                elif rw == P2:
                    r = (re, f"[dim]{p1s}[/]", f"[bold green]{CROWN} {p2s}[/]",
                         f"[{i['p2_fc']}]{i['p2_name']}[/]")
                else:
                    r = (re, f"[yellow]{p1s}[/]", f"[yellow]{p2s}[/]", "[yellow]Draw[/]")
                t.add_row(*[Text.from_markup(c) for c in r])
        else:
            t.add_row("—", "—", "—", "[dim]No data[/]")

        return Panel(t, title="\u2694 Rounds", border_style="dim")


class _CardsPlayed(Static):
    """Bottom-left: Cards played summary across the whole game."""

    def render(self):
        state = self.app.state
        i = _info(state)
        events = state.card_events
        play_kinds = {"play_card", "place_card", "muster"}

        t = Table(box=box.SIMPLE, expand=True, show_header=True, padding=(0, 1))
        t.add_column("Stat", ratio=2, no_wrap=True)
        t.add_column(Text.from_markup(f"[{i['p1_fc']}]{i['p1_name']}[/]"),
                     justify="center", ratio=1)
        t.add_column(Text.from_markup(f"[{i['p2_fc']}]{i['p2_name']}[/]"),
                     justify="center", ratio=1)

        def _c(player, **filt):
            return sum(1 for e in events if e["player"] == player
                       and all(e.get(k) == v for k, v in filt.items()))

        p1p = sum(1 for e in events if e["player"] == P1 and e["subkind"] in play_kinds)
        p2p = sum(1 for e in events if e["player"] == P2 and e["subkind"] in play_kinds)
        t.add_row("\U0001f0cf Cards Played", str(p1p), str(p2p))
        t.add_row("\U0001f9b8 Heroes", str(_c(P1, specialty="hero")), str(_c(P2, specialty="hero")))
        t.add_row("\U0001f575 Spy Draws", str(_c(P1, subkind="spy_draw")), str(_c(P2, subkind="spy_draw")))
        t.add_row("\U0001f4e3 Musters", str(_c(P1, subkind="muster")), str(_c(P2, subkind="muster")))
        t.add_row("\U0001f48a Resurrections", str(_c(P1, subkind="medic_resurrect")), str(_c(P2, subkind="medic_resurrect")))
        t.add_row("\U0001f525 Destroyed", str(_c(P1, subkind="remove_card")), str(_c(P2, subkind="remove_card")))
        t.add_row("\u2601 Weather", str(_c(P1, subkind="weather_change")), str(_c(P2, subkind="weather_change")))

        return Panel(t, title="\U0001f4ca Game Stats", border_style="dim")


class _Awards(Static):
    """Bottom-right: Game awards, hero callouts, and special stats."""

    def render(self):
        state = self.app.state
        i = _info(state)
        awards = []

        best_round_score = 0
        best_round_player = None
        best_round_num = 0
        biggest_margin = 0
        margin_player = None
        closest_round = 999
        closest_round_num = 0
        total_pts = {P1: 0, P2: 0}

        if state.round_results:
            for rr in state.round_results:
                p1s = rr["p1_score"]
                p2s = rr["p2_score"]
                total_pts[P1] += p1s
                total_pts[P2] += p2s
                diff = abs(p1s - p2s)
                if diff < closest_round:
                    closest_round = diff
                    closest_round_num = rr["round"]
                for p, s, opp_s in [(P1, p1s, p2s), (P2, p2s, p1s)]:
                    if s > best_round_score:
                        best_round_score = s
                        best_round_player = p
                        best_round_num = rr["round"]
                    margin = s - opp_s
                    if margin > biggest_margin:
                        biggest_margin = margin
                        margin_player = p

        def _pname(p):
            return i["p1_name"] if p == P1 else i["p2_name"]
        def _pfc(p):
            return i["p1_fc"] if p == P1 else i["p2_fc"]

        # Hero of the Game — highest single round score
        if best_round_player:
            awards.append(
                f"{CROWN} [bold]Hero of the Game[/]  "
                f"[{_pfc(best_round_player)}]{_pname(best_round_player)}[/] "
                f"— {best_round_score} pts (R{best_round_num})")

        # Biggest Margin
        if margin_player and biggest_margin > 0:
            awards.append(
                f"\U0001f4aa [bold]Crushing Victory[/]  "
                f"[{_pfc(margin_player)}]{_pname(margin_player)}[/] "
                f"— won a round by {biggest_margin}")

        # Closest Round
        if closest_round < 999 and closest_round_num > 0:
            awards.append(
                f"\u2694 [bold]Closest Battle[/]  "
                f"Round {closest_round_num} — only {closest_round} pts apart")

        # Fastest Player
        p1_times = state.move_times.get(P1, [])
        p2_times = state.move_times.get(P2, [])
        if p1_times and p2_times:
            p1_avg = sum(p1_times) / len(p1_times)
            p2_avg = sum(p2_times) / len(p2_times)
            fast = P1 if p1_avg < p2_avg else P2
            awards.append(
                f"\u26a1 [bold]Speed Demon[/]  "
                f"[{_pfc(fast)}]{_pname(fast)}[/] "
                f"— {min(p1_avg, p2_avg):.1f}s avg per move")

        # Slowest Player (the thinker)
        if p1_times and p2_times:
            slow = P2 if p1_avg < p2_avg else P1
            awards.append(
                f"\U0001f914 [bold]The Thinker[/]  "
                f"[{_pfc(slow)}]{_pname(slow)}[/] "
                f"— {max(p1_avg, p2_avg):.1f}s avg per move")

        # Most Total Points across all rounds
        if total_pts[P1] != total_pts[P2]:
            pts_leader = P1 if total_pts[P1] > total_pts[P2] else P2
            awards.append(
                f"\U0001f4ca [bold]Point Machine[/]  "
                f"[{_pfc(pts_leader)}]{_pname(pts_leader)}[/] "
                f"— {total_pts[pts_leader]} total pts across all rounds")

        # Card Hoarder — most cards left in hand
        p1_hand = len(state.hands.get(P1, []))
        p2_hand = len(state.hands.get(P2, []))
        if p1_hand > 0 or p2_hand > 0:
            hoarder = P1 if p1_hand >= p2_hand else P2
            awards.append(
                f"\U0001f0cf [bold]Card Hoarder[/]  "
                f"[{_pfc(hoarder)}]{_pname(hoarder)}[/] "
                f"— {max(p1_hand, p2_hand)} cards unplayed")

        # Most Moves
        if p1_times and p2_times:
            busy = P1 if len(p1_times) > len(p2_times) else P2
            if len(p1_times) != len(p2_times):
                awards.append(
                    f"\U0001f3af [bold]Busiest Commander[/]  "
                    f"[{_pfc(busy)}]{_pname(busy)}[/] "
                    f"— {max(len(p1_times), len(p2_times))} moves played")

        # Event-driven awards from card_events
        events = state.card_events
        if events:
            # Spymaster — most spy cards played
            p1_spies = sum(1 for e in events if e["player"] == P1 and e["subkind"] == "spy_draw")
            p2_spies = sum(1 for e in events if e["player"] == P2 and e["subkind"] == "spy_draw")
            if p1_spies > 0 or p2_spies > 0:
                spy_master = P1 if p1_spies >= p2_spies else P2
                awards.append(
                    f"\U0001f575 [bold]Spymaster[/]  "
                    f"[{_pfc(spy_master)}]{_pname(spy_master)}[/] "
                    f"— {max(p1_spies, p2_spies)} spy draws")

            # Scorch Master — most cards destroyed
            p1_scorch = sum(1 for e in events if e["player"] == P1 and e["subkind"] == "remove_card")
            p2_scorch = sum(1 for e in events if e["player"] == P2 and e["subkind"] == "remove_card")
            if p1_scorch > 0 or p2_scorch > 0:
                scorch_master = P1 if p1_scorch >= p2_scorch else P2
                awards.append(
                    f"\U0001f525 [bold]Scorch Master[/]  "
                    f"[{_pfc(scorch_master)}]{_pname(scorch_master)}[/] "
                    f"— {max(p1_scorch, p2_scorch)} cards destroyed")

            # Master Medic — most resurrections
            p1_medic = sum(1 for e in events if e["player"] == P1 and e["subkind"] == "medic_resurrect")
            p2_medic = sum(1 for e in events if e["player"] == P2 and e["subkind"] == "medic_resurrect")
            if p1_medic > 0 or p2_medic > 0:
                medic_master = P1 if p1_medic >= p2_medic else P2
                awards.append(
                    f"\U0001f48a [bold]Master Medic[/]  "
                    f"[{_pfc(medic_master)}]{_pname(medic_master)}[/] "
                    f"— {max(p1_medic, p2_medic)} resurrections")

            # Weather Wizard — most weather cards
            p1_w = sum(1 for e in events if e["player"] == P1 and e["subkind"] == "weather_change")
            p2_w = sum(1 for e in events if e["player"] == P2 and e["subkind"] == "weather_change")
            if p1_w > 0 or p2_w > 0:
                weather_wiz = P1 if p1_w >= p2_w else P2
                awards.append(
                    f"\u2601 [bold]Weather Wizard[/]  "
                    f"[{_pfc(weather_wiz)}]{_pname(weather_wiz)}[/] "
                    f"— {max(p1_w, p2_w)} weather cards played")

        if not awards:
            awards.append("[dim]No special stats to report[/]")

        return Panel(Text.from_markup("\n".join(awards)),
                     title="\U0001f3c6 Awards & Heroes", border_style="dim")


class GameOverStage(Vertical):
    DEFAULT_CSS = """
    GameOverStage { height: 1fr; }
    GameOverStage #go-banner { height: auto; max-height: 5; }
    GameOverStage #go-top { height: 1fr; }
    GameOverStage #go-bottom { height: 1fr; }
    GameOverStage .go-pane { width: 1fr; height: 100%; }
    """

    def compose(self):
        yield _Banner(id="go-banner")
        with Horizontal(id="go-top"):
            yield _MatchupAndGems(id="go-matchup", classes="go-pane")
            yield _Rounds(id="go-rounds", classes="go-pane")
        with Horizontal(id="go-bottom"):
            yield _CardsPlayed(id="go-cards-played", classes="go-pane")
            yield _Awards(id="go-awards", classes="go-pane")
