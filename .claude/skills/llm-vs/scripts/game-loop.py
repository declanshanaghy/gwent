#!/usr/bin/env python3
"""LLM vs LLM game loop — connects to a running game server and plays.

The game server must already be running and in PlayRound stage.

Usage:
  python3 game-loop.py [--model-p1 MODEL] [--model-p2 MODEL]
                       [--ollama-url URL] [--game-url URL] [--max-turns N]

Models (prefix determines provider):
  anthropic/claude-haiku-4-5-20251001   (default)
  anthropic/claude-sonnet-4-6
  openai/gpt-4o
  ollama/deepseek-r1:14b
  ollama/llama3.2:3b
"""
import argparse
import json
import logging
import os
import re
import requests
import signal
import subprocess
import sys
import threading
import time

import paho.mqtt.client as mqtt

# --- File logging setup ---
LOG_DIR = '/tmp/logs'
LOG_FILE = os.path.join(LOG_DIR, 'game-loop.log')
os.makedirs(LOG_DIR, exist_ok=True)

_file_logger = logging.getLogger('game-loop')
_file_logger.setLevel(logging.DEBUG)
_fh = logging.FileHandler(LOG_FILE)
_fh.setLevel(logging.DEBUG)
_fh.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'))
_file_logger.addHandler(_fh)

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(SKILL_DIR)))

_mqtt_host = 'localhost'

def _mq_base():
    return ['mosquitto_pub', '-h', _mqtt_host, '-p', '1883',
            '-u', 'geralt', '-P', 'gwent']

FACTION_PASSIVES = {
    "Skellige": "End of every round, resurrect 2 random non-hero cards from discard to hand.",
    "Northern Realms": "If you WIN the round, draw 1 extra card from deck.",
    "Monsters": "End of every round, keep the strongest non-hero card on board for next round.",
    "Nilfgaardian": "WIN ALL TIED ROUNDS. If scores are equal, Nilfgaardian wins.",
    "Scoia'tael": "Coin toss for first player in round 1.",
}

# ---------------------------------------------------------------------------
# System prompt template (sections 1-6, shared by both players)
# ---------------------------------------------------------------------------
SYSTEM_PROMPT_SHARED = """\
You are playing Gwent, a card game from The Witcher III. You are a skilled player.

CARD ZONES (understand these — they are different!):
- your_hand: cards you can PLAY on your turn. Play cards come from HERE.
- your_deck: draw pile. Cards move from deck to hand via spy draws or abilities. You CANNOT play directly from deck.
- your_discard: cards that were played and removed. Some leaders/medics can resurrect from here.
- opponent_discard: opponent's used cards. Some leaders can steal from here.

GAME STRUCTURE:
- Best of 3 rounds. Each player starts with 2 gems (lives). Lose a gem each round you lose.
- Game ends when a player reaches 0 gems.
- Each turn you may: play a card from your_hand, pass, or use your leader ability (once per game).
- IMPORTANT: You can ONLY play cards from your_hand. NOT from your_deck or your_discard.
- When playing a spy, you draw 2 cards from your_deck to your_hand. Specify spy_draws from your_deck.
- Playing a card removes it from your hand and places it on the board.
- Passing ends your turns for this round -- you cannot play more cards until next round.
- Round ends when both players pass. Higher total score wins.
- No cards are re-dealt between rounds. You keep whatever cards remain in your hand.

SCORING (per row, in this order):
1. Base strength. Weather reduces ALL non-hero cards in affected row to strength 1.
2. Tight Bond: same-name bond cards multiply their strength by the count of matching cards.
3. Morale: each morale card gives +1 to every OTHER non-hero card in the same row.
4. Commander Horn: doubles all non-hero strength in the row.
Hero cards are IMMUNE to all modifiers -- they always keep their base strength.

COMBAT ROWS:
- Close (melee): affected by Biting Frost
- Ranged (archers): affected by Impenetrable Fog
- Siege (war machines): affected by Torrential Rain

CARD SPECIALTIES (determines what the card IS):
- hero: immune to ALL effects (weather, scorch, decoy, horn). Always keeps base strength.
- weather: not a unit. Reduces non-heroes in affected row(s) to strength 1. Clear Weather removes all weather.
- scorch (SPECIALTY): not a unit. Destroys the highest-strength non-hero card(s) across the ENTIRE board (BOTH players, ALL rows).
- decoy: not a unit. Swap with a non-hero card on YOUR board -- that card returns to your hand.
- mardroeme: clears all weather effects.
- commander (SPECIALTY): standalone horn item. Doubles non-hero strength in chosen row(s).
- leader: one-time ability, played by scanning leader card. Not part of hand.

CARD ABILITIES (effects that unit cards HAVE):
- spy: placed on OPPONENT's board (gives them the strength). You then draw 2 cards from your DECK (not hand). You MUST include "spy_draws" listing exact card names from your_deck. Play spies EARLY.
- medic: after placing on board, resurrect 1 non-hero card from your discard to your hand. You must specify medic_target.
- bond (tight bond): same-name bond cards in a row multiply strength by count.
- morale: +1 to every OTHER non-hero in the same row. Stacks.
- commander (ABILITY): unit card that also doubles all non-hero strength in its row.
- agile: can be placed on multiple rows -- you MUST specify which row in your response.
- scorch (ABILITY): unit card that destroys strongest non-hero in OPPONENT's SAME ROW only.
- muster: auto-summons ALL cards with the same base name from hand AND deck.

SPECIALTY vs ABILITY SCORCH:
- Scorch SPECIALTY card: destroys strongest across ALL rows of BOTH players
- Scorch ABILITY on a unit: destroys strongest in opponent's SAME ROW only

FACTION PASSIVE ABILITIES (automatic):
- Monsters: end of every round, keep the strongest non-hero card on board for next round.
- Northern Realms: if you WIN the round, draw 1 extra card from deck.
- Skellige: end of every round, resurrect 2 random non-hero cards from discard to hand.
- Nilfgaardian: WIN ALL TIED ROUNDS. Ties are wins for you.
- Scoia'tael: coin toss for first player in round 1.

STRATEGY:
- Play spies EARLY in round 1 for card advantage.
- If you're Nilfgaardian, ties are WINS. You can pass at equal score and win.
- Consider deliberately losing round 1 to save cards if you have card advantage.
- Bond cards are devastating together -- save them for the same round.
- Weather counters rows with many non-hero units. Clear Weather counters weather.
- Heroes are your safest points -- immune to everything.
- When opponent passes, you only need to barely beat their score. Don't waste cards.
- Save your leader ability for when it matters most.

You MUST respond with ONLY a JSON object. No other text, no markdown, no explanation outside the JSON.

{
  "action": "play_card" or "pass" or "play_leader",
  "card_name": "exact card name from your hand (required for play_card)",
  "row": "close" or "ranged" or "siege" (required ONLY for agile cards with multiple rows)",
  "spy_draws": ["card name 1", "card name 2"] (REQUIRED when playing a spy — choose exactly from your_deck, NOT your_hand),
  "medic_target": "card name from your discard to resurrect (only if card has medic ability)",
  "decoy_target": "card name on your board to swap back to hand (only if playing a decoy card)",
  "reasoning": "brief explanation of your strategy"
}"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class AnnouncementSync:
    """Subscribe to MQTT and block until all TTS sources finish announcements.

    Tracks which TTS sources (gwent, gwent-tui) are expected to publish
    announcement_complete, and waits for all of them.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._event = threading.Event()
        self._last_announcement_time = 0.0
        self._expected_sources = {"gwent"}  # server always expected
        self._completed_sources = set()
        self._client = mqtt.Client(client_id='llm-vs-sync',
                                   protocol=mqtt.MQTTv311)
        self._client.username_pw_set('geralt', 'gwent')
        self._client.on_message = self._on_message
        self._client.connect(_mqtt_host, 1883)
        self._client.subscribe('gwent/sfx/complete')
        self._client.loop_start()

    def set_expected_sources(self, sources):
        """Set which TTS sources to wait for (e.g. {'gwent', 'gwent-tui'})."""
        with self._lock:
            self._expected_sources = set(sources)
        log_debug(f"AnnouncementSync: expecting sources={self._expected_sources}")

    def _on_message(self, client, userdata, msg):
        try:
            d = json.loads(msg.payload)
            if d.get('subkind') == 'announcement_complete':
                source = d.get('source', 'gwent')
                with self._lock:
                    self._completed_sources.add(source)
                    self._last_announcement_time = time.time()
                    # Only signal when all expected sources have completed
                    if self._expected_sources.issubset(self._completed_sources):
                        self._event.set()
        except Exception:
            pass

    def wait_all(self, timeout=60):
        """Block until all expected TTS sources finish playing.

        First waits for at least one announcement_complete (long timeout
        to allow TTS generation/download), then drains any remaining
        announcements using a shorter gap timer.

        If an announcement already arrived recently (within 10s), skip
        the long Phase 1 wait and go straight to draining.
        """
        deadline = time.time() + timeout
        with self._lock:
            recent = (time.time() - self._last_announcement_time) < 10.0
            self._completed_sources.clear()
        if not recent:
            self._event.clear()
            got = self._event.wait(timeout=min(30, timeout))
            if not got:
                return
        # Drain remaining
        while time.time() < deadline:
            with self._lock:
                self._completed_sources.clear()
            self._event.clear()
            got = self._event.wait(timeout=3.0)
            if not got:
                return

    def drain(self):
        """Consume any stale events without blocking."""
        self._event.clear()
        with self._lock:
            self._completed_sources.clear()

    def stop(self):
        self._client.loop_stop()
        self._client.disconnect()


_json_output = False

# Pause/resume via SIGUSR1, auto-pause toggle via SIGUSR2
_pause_event = threading.Event()
_pause_event.set()  # starts unpaused
_auto_pause = True  # default: pause after every turn

ORDERS_FILE_P1 = '/tmp/llm-vs-orders-p1.json'
ORDERS_FILE_P2 = '/tmp/llm-vs-orders-p2.json'
STATUS_FILE = '/tmp/llm-vs-status.json'
PID_FILE = '/tmp/pids/game-loop.pid'

# Faction-themed commander order preambles
COMMANDER_PREAMBLE = {
    "Monsters":        "The Crone whispers from the shadows",
    "Nilfgaardian":    "By Imperial decree of the Emperor",
    "Northern Realms": "A royal edict from the throne of Temeria",
    "Scoia'tael":      "The elder of the Scoia'tael commands",
    "Scoiatael":       "The elder of the Scoia'tael commands",
    "Skellige":        "The Jarl's war council demands",
}


def _toggle_pause(signum, frame):
    """SIGUSR1: resume one turn (or pause if running)."""
    log_debug(f"SIGUSR1 received, _pause_event.is_set()={_pause_event.is_set()}")
    if _pause_event.is_set():
        _pause_event.clear()
        log("\u23f8  PAUSED (SIGUSR1 to resume)")
    else:
        _pause_event.set()
        log("\u25b6  RESUMED")


def _toggle_auto_pause(signum, frame):
    """SIGUSR2: toggle auto-pause mode on/off."""
    global _auto_pause
    _auto_pause = not _auto_pause
    log_debug(f"SIGUSR2 received, _auto_pause={_auto_pause}")
    if _auto_pause:
        log("\u23f8  AUTO-PAUSE ON — will pause after each turn")
    else:
        log("\u25b6  AUTO-PAUSE OFF — running uninterrupted")
        _pause_event.set()  # unpause immediately when switching to continuous


signal.signal(signal.SIGUSR1, _toggle_pause)
signal.signal(signal.SIGUSR2, _toggle_auto_pause)


def _read_orders(pnum):
    """Read and consume the orders file for a specific player. Returns order text or None."""
    orders_file = ORDERS_FILE_P1 if pnum == '1' else ORDERS_FILE_P2
    try:
        if os.path.exists(orders_file):
            with open(orders_file) as f:
                data = json.load(f)
            os.remove(orders_file)
            return data.get('order', '')
    except Exception:
        pass
    return None


def _write_status(board, cur, turn):
    """Write current status for external tools to read."""
    try:
        status = {
            'turn': turn,
            'current_player': cur,
            'round': board.get('round_number', 1),
            'scores': board.get('scores', {}),
            'pid': os.getpid(),
        }
        with open(STATUS_FILE, 'w') as f:
            json.dump(status, f)
    except Exception:
        pass


def log(msg):
    print(msg, flush=True)
    _file_logger.info(msg)


def log_debug(msg):
    """Log to file only (not stdout)."""
    _file_logger.debug(msg)


def log_json(event_type, data):
    """Log a structured JSON event to stdout."""
    if _json_output:
        print(json.dumps({"event": event_type, **data}), flush=True)
    _file_logger.debug("JSON event: %s %s", event_type, json.dumps(data)[:200])


def board_summary(board):
    """Return a compact board state summary string."""
    if not board:
        return ""
    scores = board.get('scores', {})
    p1s = scores.get('PLAYER.ONE', {})
    p2s = scores.get('PLAYER.TWO', {})
    players = board.get('players', {})
    p1b = players.get('PLAYER.ONE', {})
    p2b = players.get('PLAYER.TWO', {})

    def row_cards(pb, row):
        cards = pb.get('rows', {}).get(row, [])
        return [c.get('name', '?') for c in cards]

    def row_str(pb, sc, label):
        parts = []
        for row in ('close', 'ranged', 'siege'):
            names = row_cards(pb, row)
            rs = sc.get(row, 0)
            if names:
                parts.append(f"  {row}: {rs} [{', '.join(names)}]")
            elif rs:
                parts.append(f"  {row}: {rs}")
        gems = pb.get('gems', '?')
        passed = " PASSED" if pb.get('passed') else ""
        header = f"{label}: {sc.get('total', 0)} pts, {gems} gems{passed}"
        return header + ("\n" + "\n".join(parts) if parts else "")

    weather = board.get('weather_rows', [])
    w_str = f"  Weather: {', '.join(weather)}" if weather else ""
    p1_hands = len(board.get('hands', {}).get('PLAYER.ONE', []))
    p2_hands = len(board.get('hands', {}).get('PLAYER.TWO', []))

    lines = [
        row_str(p1b, p1s, "P1"),
        row_str(p2b, p2s, "P2"),
    ]
    if weather:
        lines.append(w_str)
    lines.append(f"  Hands: P1={p1_hands} P2={p2_hands}")
    return "\n".join(lines)


_commentary_enabled = True


def mqpub(topic, payload):
    subprocess.run(_mq_base() + ['-t', topic, '-m', payload],
                   check=True, capture_output=True)
    time.sleep(0.6)


def announce(text, faction=None):
    """Publish a TTS announcement to MQTT (if commentary enabled)."""
    if not _commentary_enabled:
        return
    msg = {"kind": "sfx", "subkind": "announcement", "announcement": text}
    if faction:
        msg["faction"] = faction
    mqpub('gwent/sfx', json.dumps(msg))


def fetch(game_url):
    """Fetch fresh game state — no ETag caching."""
    r = requests.get(f'{game_url}/state', timeout=10)
    d = r.json()
    return d.get('active_stage', '?'), d.get('state', {}).get('board', {})


def poll_until_change(game_url, prev_stage, prev_player, timeout=10):
    """Poll the game server until state changes or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(0.5)
        try:
            stage, board = fetch(game_url)
            if stage != prev_stage or board.get('current_player') != prev_player:
                return stage, board
        except Exception:
            pass
    return None, None


def wait_for_turn_advance(game_url, cur_player, timeout=30):
    """Poll until current_player changes or stage transitions away from PlayRound."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(0.5)
        try:
            stage, board = fetch(game_url)
            if stage != 'PlayRound' or board.get('current_player') != cur_player:
                return stage, board
        except Exception:
            pass
    return fetch(game_url)


# ---------------------------------------------------------------------------
# Conversation initialisation: build per-player system prompts
# ---------------------------------------------------------------------------

def card_line(c):
    parts = [c['name']]
    if c.get('strength'):
        parts.append(f"str:{c['strength']}")
    rng = c.get('ranges', [])
    if rng:
        parts.append(f"row:{rng[0]}")
    if len(rng) > 1:
        parts.append(f"rows:{rng}")
    if c.get('abilities'):
        parts.append(f"abilities:{c['abilities']}")
    if c.get('specialty'):
        parts.append(f"specialty:{c['specialty']}")
    return " | ".join(parts)


def build_system_prompt(board, player):
    """Build the full system prompt for one player."""
    opp = 'PLAYER.TWO' if player == 'PLAYER.ONE' else 'PLAYER.ONE'
    faction = board['factions'][player]
    opp_faction = board['factions'][opp]
    leader = board['leaders'][player]
    opp_leader = board['leaders'][opp]
    hand_cards = board['hands'][player]
    deck_cards = board['decks'][player]

    hand_text = "\n".join(f"  - {card_line(c)}" for c in hand_cards) or "  (empty)"
    deck_text = "\n".join(f"  - {card_line(c)}" for c in deck_cards) or "  (empty)"

    section7 = f"""
YOUR FACTION: {faction}
YOUR FACTION PASSIVE: {FACTION_PASSIVES.get(faction, 'Unknown')}

YOUR LEADER: {leader['name']}
LEADER ABILITY: {leader.get('leader', {}).get('instructions', '?')} (one-time use)

YOUR HAND (cards you can play):
{hand_text}

YOUR DECK (draw pile — spy_draws MUST come from here, NOT from your hand):
{deck_text}

OPPONENT FACTION: {opp_faction}
OPPONENT PASSIVE: {FACTION_PASSIVES.get(opp_faction, 'Unknown')}
OPPONENT LEADER: {opp_leader['name']}
OPPONENT LEADER ABILITY: {opp_leader.get('leader', {}).get('instructions', '?')}"""

    return SYSTEM_PROMPT_SHARED + "\n" + section7


def init_conversations(board, round_history=None):
    """Create /tmp/logs/llm-vs-p{1,2}.jsonl with system prompts.

    If round_history is provided, appends a round summary as the first
    user message so the LLM has context about past rounds.
    """
    os.makedirs('/tmp/logs', exist_ok=True)
    for pnum, player in [('1', 'PLAYER.ONE'), ('2', 'PLAYER.TWO')]:
        prompt = build_system_prompt(board, player)
        fp = f'/tmp/logs/llm-vs-p{pnum}.jsonl'
        with open(fp, 'w') as f:
            f.write(json.dumps({"role": "system", "content": prompt}) + '\n')
            if round_history:
                summary = _build_round_summary(board, player, round_history)
                f.write(json.dumps({"role": "user", "content": summary}) + '\n')
                f.write(json.dumps({"role": "assistant", "content":
                    json.dumps({"action": "acknowledge",
                                "reasoning": "Understood. New round, fresh strategy."})
                }) + '\n')

    f1 = board['factions']['PLAYER.ONE']
    f2 = board['factions']['PLAYER.TWO']
    l1 = board['leaders']['PLAYER.ONE']['name']
    l2 = board['leaders']['PLAYER.TWO']['name']
    h1 = len(board['hands']['PLAYER.ONE'])
    d1 = len(board['decks']['PLAYER.ONE'])
    h2 = len(board['hands']['PLAYER.TWO'])
    d2 = len(board['decks']['PLAYER.TWO'])
    rnd = board.get('round_number', 1)
    log(f"Round {rnd}: P1 {f1} ({l1}) {h1}h+{d1}d | "
        f"P2 {f2} ({l2}) {h2}h+{d2}d")


def _build_round_summary(board, player, round_history):
    """Build a concise summary of past rounds for a player."""
    opp = 'PLAYER.TWO' if player == 'PLAYER.ONE' else 'PLAYER.ONE'
    pnum = '1' if player == 'PLAYER.ONE' else '2'
    opp_num = '2' if player == 'PLAYER.ONE' else '1'
    my_gems = board['players'][player]['gems']
    opp_gems = board['players'][opp]['gems']
    my_hand = len(board['hands'][player])
    opp_hand = len(board['hands'][opp])
    my_deck = len(board['decks'][player])
    rnd = board.get('round_number', 1)

    lines = ["ROUND SUMMARY — NEW ROUND STARTING"]
    lines.append("")

    # Past rounds
    for rh in round_history:
        my_score = rh['scores'].get(player, 0)
        opp_score = rh['scores'].get(opp, 0)
        if rh['winner'] == player:
            result = "YOU WON"
        elif rh['winner'] == opp:
            result = "YOU LOST"
        else:
            result = "DRAW"
        lines.append(f"Round {rh['round']}: {result} ({my_score} vs {opp_score})")

    # Current standings
    lines.append("")
    lines.append(f"CURRENT STANDINGS: You have {my_gems} gem(s), opponent has {opp_gems} gem(s).")
    lines.append(f"You have {my_hand} cards in hand, {my_deck} in deck. Opponent has {opp_hand} cards in hand.")

    # Stakes
    if my_gems == 1 and opp_gems == 1:
        lines.append("STAKES: FINAL ROUND — whoever loses this round loses the match!")
    elif my_gems == 1:
        lines.append("STAKES: You are on your LAST GEM. You MUST win this round to survive!")
    elif opp_gems == 1:
        lines.append("STAKES: Opponent is on their last gem. Win this round to claim victory!")
    else:
        lines.append(f"STAKES: Round {rnd} of best-of-3. Play smart, conserve cards when possible.")

    lines.append("")
    lines.append("No cards are re-dealt between rounds. You keep your remaining hand.")
    lines.append("The game state below shows your current hand and board for this new round.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# State building for LLM turns
# ---------------------------------------------------------------------------

def card_summary(c):
    r = {'name': c['name'], 'strength': c.get('strength', 0)}
    rng = c.get('ranges', [])
    if rng:
        r['row'] = rng[0]
    if len(rng) > 1:
        r['rows'] = rng
    if c.get('abilities'):
        r['abilities'] = c['abilities']
    if c.get('specialty'):
        r['specialty'] = c['specialty']
    return r


def rows_summary(board, p):
    return {
        rn: [{'name': c['name'], 'strength': c.get('strength', 0)}
             for c in cards]
        for rn, cards in board['players'][p]['rows'].items()
    }


def build_state(board, cur):
    opp = 'PLAYER.TWO' if cur == 'PLAYER.ONE' else 'PLAYER.ONE'
    li = {'name': board['leaders'][cur]['name'],
          'used': board['players'][cur]['leader_used']}
    if not li['used']:
        ld = board['leaders'][cur].get('leader', {})
        li['instructions'] = ld.get('instructions', '')
        if ld.get('draw_opponent_discard'):
            li['choose_from'] = 'opponent_discard'
            li['available_targets'] = [
                {'name': c['name'], 'strength': c.get('strength', 0)}
                for c in board['players'][opp]['discard']]
        elif ld.get('draw_own_discard'):
            li['choose_from'] = 'your_discard'
            li['available_targets'] = [
                {'name': c['name'], 'strength': c.get('strength', 0)}
                for c in board['players'][cur]['discard']
                if c.get('specialty') != 'hero']
        elif ld.get('weather_ranges'):
            allowed = set(ld['weather_ranges'])
            li['choose_from'] = 'weather_in_deck'
            li['available_targets'] = [
                {'name': c['name'], 'row': c.get('ranges', ['?'])[0]}
                for c in board['decks'][cur]
                if c.get('specialty') == 'weather'
                and any(r in allowed for r in c.get('ranges', []))]
    result = {
        'round': board['round_number'],
        'your_gems': board['players'][cur]['gems'],
        'opponent_gems': board['players'][opp]['gems'],
        'your_score': board['scores'][cur]['total'],
        'opponent_score': board['scores'][opp]['total'],
        'your_hand': [card_summary(c) for c in board['hands'][cur]],
        'your_deck': [card_summary(c) for c in board['decks'][cur]],
        'your_discard': [card_summary(c) for c in board['players'][cur]['discard']],
        'opponent_discard': [card_summary(c) for c in board['players'][opp]['discard']],
        'your_board': rows_summary(board, cur),
        'opponent_board': rows_summary(board, opp),
        'weather_active': board['weather_rows'],
        'your_leader': li,
        'opponent_hand_size': len(board['hands'][opp]),
        'opponent_passed': board['players'][opp]['passed'],
    }
    return result


# ---------------------------------------------------------------------------
# LLM providers
# ---------------------------------------------------------------------------

def _provider(model):
    """Return (provider, model_id) from a model string.

    Prefixes: 'openai/' -> OpenAI, 'anthropic/' -> Anthropic,
    'ollama/' -> Ollama (explicit), else Ollama (implicit).
    """
    if model.startswith('openai/'):
        return 'openai', model[len('openai/'):]
    if model.startswith('anthropic/'):
        return 'anthropic', model[len('anthropic/'):]
    if model.startswith('ollama/'):
        return 'ollama', model[len('ollama/'):]
    return 'ollama', model


def _short_model_name(model):
    """Shorten a model string for display.

    'anthropic/claude-haiku-4-5-20251001' → 'claude-haiku'
    'openai/gpt-4o' → 'gpt-4o'
    'deepseek-r1:14b' → 'deepseek-r1:14b'
    """
    name = model.split("/")[-1]  # drop provider prefix
    # Trim long version suffixes (segments of 3+ digits)
    parts = name.split("-")
    short = []
    for p in parts:
        if p.isdigit() and len(p) > 2:
            break
        short.append(p)
    return "-".join(short) or name


def _load_env():
    """Load .env file from repo root into os.environ (simple key=value)."""
    env_path = os.path.join(REPO_ROOT, '.env')
    if not os.path.exists(env_path):
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k not in os.environ:
                os.environ[k] = v


def _call_openai(model_id, messages):
    """Call OpenAI chat completions API."""
    log_debug(f"Calling OpenAI: model={model_id}, messages={len(messages)}")
    api_key = os.environ.get('OPENAI_API_KEY', '')
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    resp = requests.post(
        'https://api.openai.com/v1/chat/completions',
        headers={'Authorization': f'Bearer {api_key}',
                 'Content-Type': 'application/json'},
        json={'model': model_id, 'messages': messages,
              'temperature': 0.7,
              'response_format': {'type': 'json_object'}},
        timeout=120)
    resp.raise_for_status()
    return resp.json()['choices'][0]['message']['content']


def _call_anthropic(model_id, messages):
    """Call Anthropic messages API."""
    log_debug(f"Calling Anthropic: model={model_id}, messages={len(messages)}")
    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    # Anthropic uses a separate system param, not a system message
    system_text = ''
    api_messages = []
    for m in messages:
        if m['role'] == 'system':
            system_text = m['content']
        else:
            api_messages.append(m)
    resp = requests.post(
        'https://api.anthropic.com/v1/messages',
        headers={'x-api-key': api_key,
                 'anthropic-version': '2023-06-01',
                 'Content-Type': 'application/json'},
        json={'model': model_id, 'max_tokens': 1024,
              'system': system_text,
              'messages': api_messages,
              'temperature': 0.7},
        timeout=120)
    resp.raise_for_status()
    return resp.json()['content'][0]['text']


def _call_ollama(ollama_url, model_id, messages):
    """Call Ollama OpenAI-compatible API."""
    resp = requests.post(
        f'{ollama_url}/v1/chat/completions',
        json={'model': model_id, 'messages': messages,
              'temperature': 0.7,
              'response_format': {'type': 'json_object'}},
        timeout=300)
    resp.raise_for_status()
    return resp.json()['choices'][0]['message']['content']


def call_llm(ollama_url, model, pnum, state_json):
    fp = f'/tmp/logs/llm-vs-p{pnum}.jsonl'
    with open(fp) as f:
        lines = f.readlines()
    msgs = [json.loads(lines[0])]
    for ln in lines[1:]:
        msgs.append(json.loads(ln))
    # Keep system + last 6 exchanges
    if len(msgs) > 7:
        msgs = msgs[:1] + msgs[-6:]
    msgs.append({"role": "user", "content": state_json})

    provider, model_id = _provider(model)

    t0 = time.time()
    if provider == 'openai':
        content = _call_openai(model_id, msgs)
    elif provider == 'anthropic':
        content = _call_anthropic(model_id, msgs)
    else:
        content = _call_ollama(ollama_url, model_id, msgs)
    lat = int((time.time() - t0) * 1000)

    with open(fp, 'a') as f:
        f.write(json.dumps({"role": "user", "content": state_json}) + '\n')
        f.write(json.dumps({"role": "assistant", "content": content}) + '\n')
    return content, lat


# ---------------------------------------------------------------------------
# Move validation and execution
# ---------------------------------------------------------------------------

def find_card(hand, name):
    if not name:
        return None
    n = re.sub(r'\s*:\s*', ': ', name.lower().strip())
    for c in hand:
        if re.sub(r'\s*:\s*', ': ', c['name'].lower()) == n:
            return c
    for c in hand:
        if n in c['name'].lower():
            return c
    return None


def execute(board, cur, action, sync=None, game_url=None):
    opp = 'PLAYER.TWO' if cur == 'PLAYER.ONE' else 'PLAYER.ONE'
    act = action.get('action', '').lower()

    if act == 'pass':
        mqpub('gwent/mfd/choose',
              json.dumps({"kind": "choice", "id": "p", "text": "Pass"}))
        return True, 'passed'

    if act == 'play_leader':
        if board['players'][cur]['leader_used']:
            return False, 'Leader already used.'
        mqpub('gwent/cards/raw/read', json.dumps(board['leaders'][cur]))
        ld = board['leaders'][cur].get('leader', {})
        if ld.get('draw_own_discard'):
            nh = [c for c in board['players'][cur]['discard']
                  if c.get('specialty') != 'hero']
            if nh:
                tgt = find_card(nh, action.get('card_name', ''))
                if not tgt:
                    tgt = max(nh, key=lambda c: c.get('strength', 0))
                mqpub('gwent/cards/raw/read', json.dumps(tgt))
        elif ld.get('draw_opponent_discard'):
            od = board['players'][opp]['discard']
            if od:
                tgt = find_card(od, action.get('card_name', ''))
                if not tgt:
                    tgt = max(od, key=lambda c: c.get('strength', 0))
                mqpub('gwent/cards/raw/read', json.dumps(tgt))
        elif ld.get('weather_ranges'):
            allowed = set(ld['weather_ranges'])
            wc = [c for c in board['decks'][cur]
                  if c.get('specialty') == 'weather'
                  and any(r in allowed for r in c.get('ranges', []))]
            if wc:
                mqpub('gwent/cards/raw/read', json.dumps(wc[0]))
        elif ld.get('discard_and_draw'):
            cfg = ld['discard_and_draw']
            sh = sorted(board['hands'][cur],
                        key=lambda c: c.get('strength', 0))
            for i in range(min(cfg.get('discard', 2), len(sh))):
                mqpub('gwent/cards/raw/read', json.dumps(sh[i]))
            for i in range(min(cfg.get('draw', 1),
                               len(board['decks'][cur]))):
                mqpub('gwent/cards/raw/read',
                      json.dumps(board['decks'][cur][i]))
        return True, f'leader: {board["leaders"][cur]["name"]}'

    if act == 'play_card':
        name = action.get('card_name', '')
        hand = board['hands'][cur]
        card = find_card(hand, name)
        if not card:
            return False, (f"Card '{name}' not in hand. "
                           f"Your hand: {[c['name'] for c in hand]}")

        is_agile = ('agile' in card.get('abilities', [])
                    and len(card.get('ranges', [])) > 1)
        if is_agile:
            row = action.get('row', '').lower()
            if row not in card['ranges']:
                return False, (f"Agile card needs valid row. "
                               f"Ranges: {card['ranges']}")

        is_decoy = card.get('specialty') == 'decoy'
        if is_decoy and not action.get('decoy_target'):
            return False, "Decoy needs decoy_target."

        mqpub('gwent/cards/raw/read', json.dumps(card))

        if is_agile:
            row = action.get('row', '').lower()
            idx = card['ranges'].index(row)
            mqpub('gwent/mfd/choose',
                  json.dumps({"kind": "choice", "id": str(idx),
                              "text": row}))

        if is_decoy:
            tname = action['decoy_target']
            for rn in ['close', 'ranged', 'siege']:
                for c in board['players'][cur]['rows'][rn]:
                    if (tname.lower() in c['name'].lower()
                            and c.get('specialty') != 'hero'):
                        mqpub('gwent/cards/raw/read', json.dumps(c))
                        break

        if 'spy' in card.get('abilities', []) and board['decks'][cur]:
            # Spy draws: wait for server to transition, then re-fetch
            # fresh deck state for each draw to avoid RFID mismatches.
            num_draws = min(2, len(board['decks'][cur]))
            for draw_idx in range(num_draws):
                if sync:
                    sync.wait_all()
                    sync.drain()
                time.sleep(2.0)
                # Re-fetch fresh state so we have current deck contents
                if game_url:
                    _, fresh_board = fetch(game_url)
                    if fresh_board:
                        fresh_deck = fresh_board['decks'][cur]
                    else:
                        break
                else:
                    break
                if not fresh_deck:
                    break
                # Pick from LLM's spy_draws (must be deck cards), fallback to top
                spy_draws = action.get('spy_draws', [])
                tgt = None
                if draw_idx < len(spy_draws):
                    tgt = find_card(fresh_deck, spy_draws[draw_idx])
                if not tgt:
                    tgt = fresh_deck[0]
                if not tgt:
                    break
                mqpub('gwent/cards/raw/read', json.dumps(tgt))
                # Wait for server to process the draw
                prev_size = len(fresh_deck)
                for _ in range(30):
                    time.sleep(0.5)
                    _, poll_board = fetch(game_url)
                    if poll_board and len(poll_board['decks'][cur]) < prev_size:
                        break

        if 'medic' in card.get('abilities', []):
            nh = [c for c in board['players'][cur]['discard']
                  if c.get('specialty') != 'hero']
            if nh:
                tgt = find_card(nh, action.get('medic_target', ''))
                if not tgt:
                    tgt = max(nh, key=lambda c: c.get('strength', 0))
                mqpub('gwent/cards/raw/read', json.dumps(tgt))

        return True, f"played {card['name']}"

    return False, f"Unknown action: {act}"


# ---------------------------------------------------------------------------
# Main game loop
# ---------------------------------------------------------------------------

def game_loop(args, board, sync):
    """Run the turn-by-turn game loop until game over or max turns."""
    turn = 0
    current_round = board.get('round_number', 1)
    round_history = []  # [{round, scores, winner}, ...]

    log_debug(f"Entering game_loop, max_turns={args.max_turns}")
    while turn < args.max_turns:
        stage, board = fetch(args.game_url)
        log_debug(f"Loop iteration: turn={turn}, stage={stage}")

        if stage in ('GameOver', 'DisplayWinner'):
            g1 = board['players']['PLAYER.ONE']['gems']
            g2 = board['players']['PLAYER.TWO']['gems']
            w = 'P1' if g1 > g2 else 'P2' if g2 > g1 else 'Draw'
            log(f"\n=== GAME OVER === {w} wins! "
                f"P1={g1} gems, P2={g2} gems")
            break

        if stage == 'RoundEnd':
            s1 = board['scores']['PLAYER.ONE']['total']
            s2 = board['scores']['PLAYER.TWO']['total']
            g1 = board['players']['PLAYER.ONE']['gems']
            g2 = board['players']['PLAYER.TWO']['gems']
            log(f"--- Round End --- scores P1={s1} P2={s2} | "
                f"gems P1={g1} P2={g2}")

            # Record round result
            if s1 > s2:
                winner = 'PLAYER.ONE'
            elif s2 > s1:
                winner = 'PLAYER.TWO'
            else:
                winner = None
            round_history.append({
                'round': current_round,
                'scores': {'PLAYER.ONE': s1, 'PLAYER.TWO': s2},
                'winner': winner,
            })

            # Wait for server to leave RoundEnd
            for _ in range(30):
                s, b = poll_until_change(
                    args.game_url, stage, board.get('current_player', ''), timeout=5)
                if s is not None and s != 'RoundEnd':
                    break
            # Wait for round-end announcements to finish
            sync.wait_all()

            # Fresh fetch to get definitive post-round state
            stage, board = fetch(args.game_url)

            # If new round started, reset conversations with round summary
            if stage == 'PlayRound':
                new_round = board.get('round_number', current_round)
                if new_round != current_round:
                    current_round = new_round
                    log(f"--- New Round {current_round} — resetting conversations ---")
                    init_conversations(board, round_history=round_history)
            continue

        if stage != 'PlayRound':
            time.sleep(2)
            continue

        if (board['players']['PLAYER.ONE']['passed']
                and board['players']['PLAYER.TWO']['passed']):
            time.sleep(2)
            continue

        cur = board['current_player']
        if board['players'][cur]['passed']:
            time.sleep(2)
            continue

        pnum = '1' if cur == 'PLAYER.ONE' else '2'
        faction = board['factions'][cur]
        plab = f"P{pnum} ({faction})"

        # --- Pause checkpoint ---
        log_debug(f"Pause checkpoint: turn={turn}, player={cur}, auto_pause={_auto_pause}")
        _write_status(board, cur, turn)
        if _auto_pause:
            log_debug("Auto-pausing, waiting for SIGUSR1...")
            _pause_event.clear()  # re-pause after each turn
        _pause_event.wait()  # blocks until unpaused
        log_debug(f"Unpaused, proceeding with turn {turn}")

        # --- Check for commander orders ---
        order_text = _read_orders(pnum)
        orders_for_cur = None
        if order_text:
            preamble = COMMANDER_PREAMBLE.get(faction, "Your commander orders")
            orders_for_cur = (
                f"[COMMANDER'S ORDERS] {preamble}: {order_text}\n"
                f"You MUST follow these orders. They override your own strategy.\n\n"
            )
            log(f"\u2694 Commander orders for {plab}: {order_text}")

        state = build_state(board, cur)
        state_json = json.dumps(state)
        if orders_for_cur:
            state_json = orders_for_cur + state_json

        # --- Pre-turn input summary ---
        hand_size = len(board['hands'][cur])
        ps1 = board['scores']['PLAYER.ONE']['total']
        ps2 = board['scores']['PLAYER.TWO']['total']
        weather = board.get('weather_rows', [])
        leader_used = board['players'][cur]['leader_used']
        log(f"--- {plab} turn {turn} ---")
        log(f"  Hand: {hand_size} cards | Scores: P1={ps1} P2={ps2}")
        log(f"  Weather: {', '.join(weather) if weather else 'clear'} | "
            f"Leader: {'spent' if leader_used else 'available'}")
        if orders_for_cur:
            log(f"  ORDERS: {order_text}")

        # Announce turn start with varied phrasing
        player_model = args.model_p1 if pnum == '1' else args.model_p2
        short_model = _short_model_name(player_model)
        if ps1 == ps2:
            score_desc = f"Scores are tied at {ps1}"
        elif (pnum == '1' and ps1 > ps2) or (pnum == '2' and ps2 > ps1):
            score_desc = f"Leading {max(ps1,ps2)} to {min(ps1,ps2)}"
        else:
            score_desc = f"Trailing {min(ps1,ps2)} to {max(ps1,ps2)}"
        import random
        thinking_phrases = [
            f"{short_model} considers their next move.",
            f"{short_model} studies the board carefully.",
            f"{short_model} weighs their options.",
            f"{short_model} plots their strategy.",
            f"{short_model} surveys the battlefield.",
            f"{short_model} takes a moment to think.",
            f"{short_model} deliberates.",
            f"{short_model} eyes the cards intently.",
            f"{short_model} calculates the odds.",
            f"The crowd watches as {short_model} decides.",
            f"All eyes on {short_model}.",
            f"{short_model} reaches for a card.",
            f"{short_model} strokes their chin thoughtfully.",
            f"{short_model} narrows their eyes at the board.",
            f"A hush falls as {short_model} contemplates.",
            f"{short_model} taps the table, deep in thought.",
            f"{short_model} scans the opponent's side of the board.",
            f"{short_model} leans forward, studying their hand.",
            f"The tension builds as {short_model} decides.",
            f"{short_model} glances at their remaining cards.",
            f"{short_model} pauses before making their move.",
            f"What will {short_model} do next?",
            f"{short_model} takes a deep breath.",
            f"{short_model} mulls over the possibilities.",
        ]
        thinking = random.choice(thinking_phrases)
        announce(
            f"{thinking} {score_desc}, with {hand_size} cards remaining.",
            faction=faction)

        # Wait for "thinking" announcement to finish before LLM call
        if _commentary_enabled:
            sync.wait_all()

        ok = False
        for attempt in range(3):
            log_debug(f"LLM call attempt {attempt+1}/3 for {plab}")
            content, lat = call_llm(
                args.ollama_url, player_model, pnum,
                state_json if attempt == 0 else json.dumps(state))
            log_debug(f"LLM response received: latency={lat:.1f}s, len={len(content) if content else 0}")
            try:
                cleaned = content.strip()
                if cleaned.startswith('```'):
                    cleaned = re.sub(r'^```\w*\n?', '', cleaned)
                    cleaned = re.sub(r'\n?```$', '', cleaned)
                action = json.loads(cleaned)
            except json.JSONDecodeError:
                err = (f"ERROR: Invalid JSON. "
                       f"Your hand: {[c['name'] for c in board['hands'][cur]]}")
                with open(f'/tmp/logs/llm-vs-p{pnum}.jsonl', 'a') as f:
                    f.write(json.dumps({"role": "user", "content": err})
                            + '\n')
                log(f"  {plab}: bad JSON (attempt {attempt + 1})")
                continue

            # Announce the LLM's decision before executing
            act = action.get('action', '?')
            card_name = action.get('card_name', '')
            reasoning = action.get('reasoning', '')
            if act == 'pass':
                summary = f"{short_model} passes! {reasoning}"
            elif act == 'play_leader':
                summary = f"{short_model} uses their leader ability! {reasoning}"
            else:
                summary = f"{short_model} plays {card_name}! {reasoning}"
            announce(summary, faction=faction)

            # Wait for commentary announcement to finish before executing
            if _commentary_enabled:
                sync.wait_all()

            # Drain stale announcements, then execute
            log_debug(f"Parsed action: {act} {card_name}")
            sync.drain()
            log_debug("Executing action...")
            valid, msg = execute(board, cur, action, sync=sync,
                                             game_url=args.game_url)
            log_debug(f"Execute result: valid={valid}, msg={msg}")

            if valid:
                ok = True
                turn += 1
                # 1. Confirm state changed (turn advanced or stage changed)
                log_debug("Waiting for turn advance...")
                stage, board = wait_for_turn_advance(
                    args.game_url, cur)
                log_debug(f"Turn advanced: stage={stage}")
                # 2. Wait for ALL queued announcements to finish playing
                log_debug("Waiting for announcements...")
                sync.wait_all()
                log_debug("Announcements done")
                # 3. Fetch final state for accurate scores
                stage, board = fetch(args.game_url)
                if board and 'scores' in board:
                    ps1 = board['scores']['PLAYER.ONE']['total']
                    ps2 = board['scores']['PLAYER.TWO']['total']
                else:
                    ps1, ps2 = '?', '?'
                turn_label = f"R{board.get('round_number','?')}T{turn-1}"
                log(f"{turn_label} {plab}: "
                    f"{act} {card_name} ({lat}ms) | {msg} | "
                    f"P1={ps1} P2={ps2}")
                if reasoning:
                    log(f'  "{reasoning}"')
                log(board_summary(board))
                log_json("turn", {
                    "turn": turn_label,
                    "player": plab,
                    "action": act,
                    "card": card_name,
                    "reasoning": reasoning,
                    "latency_ms": lat,
                    "scores": {"P1": ps1, "P2": ps2},
                    "board": board,
                })
                break
            else:
                err = f"ERROR: {msg}"
                with open(f'/tmp/logs/llm-vs-p{pnum}.jsonl', 'a') as f:
                    f.write(json.dumps({"role": "user", "content": err})
                            + '\n')
                log(f"  {plab}: INVALID {act} {card_name} -> "
                    f"{msg} (attempt {attempt + 1})")

        if not ok:
            log(f"  {plab}: FORCED PASS after 3 retries")
            announce(f"{short_model} is confused and forced to pass!", faction=faction)
            sync.drain()
            mqpub('gwent/mfd/choose',
                  json.dumps({"kind": "choice", "id": "p",
                              "text": "Pass"}))
            wait_for_turn_advance(args.game_url, cur)
            sync.wait_all()

    log(f"\n{turn} turns played.")
    log(f"Logs: /tmp/logs/llm-vs-p1.jsonl, /tmp/logs/llm-vs-p2.jsonl")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='LLM vs LLM Gwent game manager')
    parser.add_argument('--model-p1', default='anthropic/claude-haiku-4-5-20251001',
                        help='Model for P1')
    parser.add_argument('--model-p2', default=None,
                        help='Model for P2 (defaults to --model-p1)')
    parser.add_argument('--ollama-url', default='http://hal-9005.lan:11434')
    parser.add_argument('--host', default='localhost',
                        help='Gwent server hostname (used for both HTTP and MQTT)')
    parser.add_argument('--game-url', default=None,
                        help='Override HTTP game URL (default: http://<host>:8080)')
    parser.add_argument('--max-turns', type=int, default=60)
    parser.add_argument('--no-commentary', action='store_true',
                        help='Disable MQTT announcements for LLM turn commentary')
    parser.add_argument('--json', action='store_true',
                        help='Also emit structured JSON events to stdout')
    parser.add_argument('--no-pause', action='store_true',
                        help='Run continuously without pausing between turns')
    args = parser.parse_args()

    # Derive game_url and mqtt host from --host
    global _mqtt_host
    _mqtt_host = args.host
    if not args.game_url:
        args.game_url = f'http://{args.host}:8080'

    log_debug(f"=== game-loop.py starting === PID={os.getpid()}")

    # Write PID file
    os.makedirs(os.path.dirname(PID_FILE), exist_ok=True)
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))
    import atexit
    atexit.register(lambda: os.remove(PID_FILE) if os.path.exists(PID_FILE) else None)

    # Default P2 model to P1 model if not specified
    if not args.model_p2:
        args.model_p2 = args.model_p1
    log_debug(f"Args: model_p1={args.model_p1}, model_p2={args.model_p2}, no_pause={args.no_pause}, game_url={args.game_url}")

    global _json_output
    _json_output = args.json

    global _commentary_enabled
    if args.no_commentary:
        _commentary_enabled = False
        log_debug("Commentary disabled (--no-commentary)")

    global _auto_pause
    if args.no_pause:
        _auto_pause = False
        log_debug("Auto-pause disabled (--no-pause)")
    else:
        _pause_event.clear()  # default: start paused
        log_debug("Starting PAUSED — waiting for SIGUSR1 to begin first turn")

    # Load .env for API keys
    _load_env()
    log_debug(f"ANTHROPIC_API_KEY set: {'yes' if os.environ.get('ANTHROPIC_API_KEY') else 'NO'}")
    log_debug(f"OPENAI_API_KEY set: {'yes' if os.environ.get('OPENAI_API_KEY') else 'NO'}")

    # 1. Check model availability (both P1 and P2)
    for label, model_str in [("P1", args.model_p1), ("P2", args.model_p2)]:
        provider, model_id = _provider(model_str)
        log(f"{label} provider: {provider}, model: {model_id}")

        if provider == 'openai':
            if not os.environ.get('OPENAI_API_KEY'):
                log("ERROR: OPENAI_API_KEY not set (check .env)")
                return 1
        elif provider == 'anthropic':
            if not os.environ.get('ANTHROPIC_API_KEY'):
                log("ERROR: ANTHROPIC_API_KEY not set (check .env)")
                return 1
        else:
            log(f"Checking Ollama model {model_id} on {args.ollama_url}...")
            try:
                r = requests.get(f'{args.ollama_url}/api/tags', timeout=10)
                models = [m['name'] for m in r.json().get('models', [])]
                if model_id not in models:
                    log(f"ERROR: Model '{model_id}' not found. "
                        f"Available: {models}")
                    return 1
            except Exception as e:
                log(f"ERROR: Cannot reach Ollama at {args.ollama_url}: {e}")
                return 1

    # 2. Check MQTT
    log("Checking MQTT broker...")
    try:
        subprocess.run(_mq_base() + ['-t', 'test/ping', '-m', '{"kind":"test"}'],
                       check=True, capture_output=True, timeout=5)
    except Exception as e:
        log(f"ERROR: MQTT broker not reachable: {e}")
        return 1

    # 3. Check game is in PlayRound
    try:
        stage, board = fetch(args.game_url)
    except Exception as e:
        log(f"ERROR: Cannot reach game server at {args.game_url}: {e}")
        return 1

    if stage != 'PlayRound':
        log(f"ERROR: Game not in PlayRound (stage={stage}). "
            f"Start the server and deal cards first.")
        return 1

    log(f"Game ready: stage={stage}")

    # 3b. Set player display names on the server
    short_p1 = _short_model_name(args.model_p1)
    short_p2 = _short_model_name(args.model_p2)
    try:
        requests.put(f'{args.game_url}/players',
                     json={"PLAYER.ONE": short_p1,
                           "PLAYER.TWO": short_p2},
                     timeout=5)
        log(f"Player names set: {short_p1} vs {short_p2}")
    except Exception as e:
        log_debug(f"Failed to set player names: {e}")

    # 4. Initialize conversation logs
    init_conversations(board)

    # 5. Start MQTT announcement sync
    sync = AnnouncementSync()
    # Drain any announcements from the deal stage
    sync.drain()

    # 5b. Determine active TTS sources from /state
    try:
        full_state = requests.get(f'{args.game_url}/state', timeout=10).json()
        server_tts = full_state.get('tts_provider', 'none')
        client_tts = full_state.get('client_tts', {})
        expected = set()
        if server_tts and server_tts != 'none':
            expected.add('gwent')
        for cid, cprov in client_tts.items():
            if cprov and cprov not in ('none', 'off', 'auto'):
                expected.add(cid)
        if expected:
            sync.set_expected_sources(expected)
            log(f"Waiting for TTS sources: {expected}")
        else:
            log("No active TTS — announcements complete instantly")
    except Exception as e:
        log_debug(f"Failed to read TTS sources: {e}")

    # 6. Announce player takeover
    p1_faction = board.get('factions', {}).get('PLAYER.ONE', '')
    p2_faction = board.get('factions', {}).get('PLAYER.TWO', '')
    announce(f"{short_p1} takes command of {p1_faction}!", faction=p1_faction)
    announce(f"{short_p2} takes command of {p2_faction}!", faction=p2_faction)

    # 7. Run the game loop
    log(f"\nStarting game: {args.model_p1} vs {args.model_p2}")
    log("=" * 60)
    try:
        game_loop(args, board, sync)
    finally:
        sync.stop()
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main() or 0)
    except Exception as e:
        _file_logger.exception("game-loop.py crashed: %s", e)
        raise
