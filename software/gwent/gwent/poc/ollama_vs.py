"""ollama-vs — Two LLM models play Gwent against each other.

Connects to a running gwent game via its HTTP API for state and MQTT for
injecting card scans and choices. Each model gets its own conversation thread,
makes moves via JSON responses, and the engine publishes them into the live game.

Supports multiple providers via model name prefix:
  ollama/deepseek-r1:14b   — Ollama (default if no prefix)
  openai/gpt-4o            — OpenAI API (requires OPENAI_API_KEY)
"""

import argparse
import json
import logging
import os
import random
import re
import sys
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
import requests
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

import gwent.messaging.card
from gwent.game.board import Board, ROWS
from gwent.game.constants import PLAYER

load_dotenv()

console = Console()

MQTT_HOST = "localhost"
MQTT_PORT = 1883
MQTT_USER = "geralt"
MQTT_PASS = "gwent"
TOPIC_CARD = "gwent/cards/raw/read"
TOPIC_CHOICE = "gwent/mfd/choose"

_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))
LOG_DIR = os.path.join(_REPO_ROOT, "tmp", "logs")

log = logging.getLogger("ollama-vs")


LOG_FILE = os.path.join(LOG_DIR, "ollama-vs.log")


def _setup_logging():
    """Configure plain-text file logging."""
    os.makedirs(LOG_DIR, exist_ok=True)
    handler = logging.FileHandler(LOG_FILE)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S"))
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)

# ── LLM system prompt ──────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are playing Gwent, a card game from The Witcher III. You are a skilled player.

RULES:
- Each turn you may: play a card from your hand, pass, or use your leader ability (once per game).
- Playing a card removes it from your hand and places it on the board.
- Passing ends your turns for this round — you cannot play again until next round.
- Round ends when both players pass. Higher total score wins. Loser loses 1 gem.
- If scores are tied, Nilfgaardian faction wins. Otherwise both lose a gem.
- Game ends when a player reaches 0 gems. You start with 2 gems.
- There are 3 rows: close, ranged, siege. Cards have a default row.

CARD ABILITIES (resolved automatically unless noted):
- spy: placed on OPPONENT's board (gives them strength), but you draw 2 cards from your deck.
- medic: after playing, you may resurrect 1 non-hero card from your discard pile. You must specify medic_target.
- muster: auto-summons all cards with the same base name from your hand and deck.
- scorch (ability on a unit): destroys the strongest non-hero card in the opponent's same row.
- bond (tight bond): each copy of the same-named card multiplies its strength by the number of copies.
- morale: gives +1 strength to every OTHER non-hero card in the same row.
- agile: card can be placed on multiple rows — you MUST specify which row.
- weather: reduces all non-hero cards in affected row(s) to strength 1. Heroes are immune.
- decoy: swap with a non-hero card already on your board, returning that card to your hand. You must specify decoy_target.
- commander horn: doubles all non-hero strength in its row.

CARD SPECIALTIES:
- hero: immune to all effects (weather, scorch, decoy, horn). Very powerful.
- weather: a weather effect card.
- scorch: destroys the strongest non-hero cards across ALL rows of BOTH players.
- decoy: swaps with a card on your board.
- mardroeme: clears all active weather effects.
- commander: applies commander horn to its row(s).

STRATEGY TIPS:
- Spies are powerful: you lose points short-term but gain 2 card draws. Play them early.
- Save strong cards for later rounds if you're likely to lose the current one.
- Passing early when behind can save cards for the next round.
- Weather cards can devastate rows with many non-hero units.
- Bond cards are strongest when played together.
- Consider passing if you're ahead and your opponent has passed.
- Heroes are immune to everything — they're your most reliable points.

You MUST respond with ONLY a JSON object. No other text.
"""

ACTION_SCHEMA = """\
Respond with exactly this JSON structure:
{
  "action": "play_card" or "pass" or "play_leader",
  "card_name": "exact card name from your hand (required for play_card). For play_leader with available_targets, specify the target card name here.",
  "row": "close" or "ranged" or "siege" (required ONLY for agile cards with multiple rows)",
  "medic_target": "card name from your discard to resurrect (only if card has medic ability)",
  "decoy_target": "card name on your board to swap back to hand (only if playing a decoy card)",
  "reasoning": "brief explanation of your strategy"
}
"""

# ── Transcript / conversation loggers ───────────────────────────────────────

class ConversationLog:
    """JSONL logger for a single agent's conversation (one per model)."""

    def __init__(self, filepath):
        self._filepath = filepath
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        log.info("Conversation log: %s", filepath)

    @property
    def filepath(self):
        return self._filepath

    def append(self, role, content, **meta):
        entry = {"ts": time.time(), "role": role, "content": content, **meta}
        with open(self._filepath, "a") as f:
            f.write(json.dumps(entry) + "\n")


class GameTranscript:
    """Coordinates game-level event logging and per-agent conversation logs."""

    def __init__(self, model1, model2):
        os.makedirs(LOG_DIR, exist_ok=True)
        m1 = _safe(model1)
        m2 = _safe(model2)
        # Disambiguate when both models are the same
        if m1 == m2:
            m1 = f"{m1}-p1"
            m2 = f"{m2}-p2"
        self._conv_logs = {
            PLAYER.ONE: ConversationLog(
                os.path.join(LOG_DIR, f"ollama-vs-{m1}.jsonl")),
            PLAYER.TWO: ConversationLog(
                os.path.join(LOG_DIR, f"ollama-vs-{m2}.jsonl")),
        }

    def conv(self, player):
        """Get the ConversationLog for a player."""
        return self._conv_logs[player]

    def log_event(self, event_type, **kwargs):
        log.info("event=%s %s", event_type,
                 " ".join(f"{k}={v}" for k, v in kwargs.items()
                          if k != "board"))

    def log_turn(self, *, round_num, turn, player, model, prompt_tokens,
                 completion_tokens, latency_ms, action, valid, error,
                 board_dict):
        log.info(
            "turn=%d round=%d player=%s model=%s tokens=%d+%d latency=%dms "
            "valid=%s action=%s%s",
            turn, round_num, str(player), model, prompt_tokens,
            completion_tokens, latency_ms, valid,
            _action_summary(action),
            f" error={error}" if error else "")


def _safe(model_name):
    """Sanitize a model name for use in filenames."""
    return re.sub(r'[^a-zA-Z0-9._-]', '_', model_name)


def _action_summary(action):
    """One-line summary of an action dict for the plain-text log."""
    if isinstance(action, dict):
        act = action.get("action", "?")
        name = action.get("card_name", "")
        return f"{act}({name})" if name else act
    return str(action)[:80] if action else "None"


# ── Provider parsing ───────────────────────────────────────────────────────

def parse_model(model_spec):
    """Parse 'provider/model' string. Default provider is 'ollama'.

    Examples:
        'openai/gpt-4o'       -> ('openai', 'gpt-4o')
        'ollama/deepseek-r1'  -> ('ollama', 'deepseek-r1')
        'deepseek-r1:14b'     -> ('ollama', 'deepseek-r1:14b')
    """
    if "/" in model_spec:
        provider, model = model_spec.split("/", 1)
        return provider.lower(), model
    return "ollama", model_spec


# ── LLM API callers ───────────────────────────────────────────────────────

MAX_LLM_RETRIES = 5
LLM_TIMEOUT = 300


def _call_openai_compatible(url, model, messages, temperature, timeout,
                            headers=None, provider_label="API"):
    """Shared OpenAI-compatible chat completion caller with retry + backoff.

    Returns (content_str, prompt_tokens, completion_tokens, latency_ms).
    """
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }

    for attempt in range(MAX_LLM_RETRIES):
        backoff = min(2 ** attempt * 5, 60)
        try:
            t0 = time.time()
            resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
            latency_ms = int((time.time() - t0) * 1000)
            resp.raise_for_status()

            data = resp.json()
            choice = data["choices"][0]
            content = choice["message"]["content"]
            usage = data.get("usage", {})

            return (
                content,
                usage.get("prompt_tokens", 0),
                usage.get("completion_tokens", 0),
                latency_ms,
            )
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            log.warning("%s attempt %d/%d failed: %s — retrying in %ds",
                        provider_label, attempt + 1, MAX_LLM_RETRIES, e, backoff)
            console.print(f"  [yellow]{provider_label} timeout (attempt {attempt + 1}/{MAX_LLM_RETRIES}), "
                          f"retrying in {backoff}s...[/yellow]")
            time.sleep(backoff)
        except requests.exceptions.HTTPError as e:
            log.error("%s HTTP error (attempt %d/%d): %s", provider_label, attempt + 1, MAX_LLM_RETRIES, e)
            console.print(f"  [red]{provider_label} HTTP error: {e}[/red]")
            time.sleep(backoff)

    raise RuntimeError(f"{provider_label} failed after {MAX_LLM_RETRIES} retries")


def call_ollama(base_url, model, messages, temperature=0.7):
    """Call Ollama's OpenAI-compatible chat endpoint."""
    url = f"{base_url}/v1/chat/completions"
    return _call_openai_compatible(url, model, messages, temperature,
                                   LLM_TIMEOUT, provider_label="Ollama")


def call_openai(model, messages, temperature=0.7):
    """Call the OpenAI API. Requires OPENAI_API_KEY env var."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable is not set")
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}"}
    return _call_openai_compatible(url, model, messages, temperature,
                                   LLM_TIMEOUT, headers=headers,
                                   provider_label="OpenAI")


def call_llm(provider, model, messages, ollama_base_url, temperature=0.7):
    """Dispatch to the appropriate provider.

    Returns (content_str, prompt_tokens, completion_tokens, latency_ms).
    """
    if provider == "ollama":
        return call_ollama(ollama_base_url, model, messages, temperature)
    elif provider == "openai":
        return call_openai(model, messages, temperature)
    else:
        raise RuntimeError(f"Unknown provider: {provider}. Use ollama/ or openai/ prefix.")


# ── Game state formatting ───────────────────────────────────────────────────

def _card_summary(card):
    """Compact card dict for the LLM."""
    d = {"name": card.name, "strength": card.strength or 0}
    if card.ranges:
        d["row"] = card.ranges[0]
        if len(card.ranges) > 1:
            d["rows"] = list(card.ranges)
    if card.has_abilities and card.abilities:
        d["abilities"] = list(card.abilities)
    if card.has_specialty and card.specialty:
        d["specialty"] = card.specialty
    return d


def _board_rows_summary(board, player):
    """Summarize a player's board rows."""
    result = {}
    for row in ROWS:
        cards = board.players[player].rows[row]
        if cards:
            result[row] = [{"name": c.name, "strength": c.strength or 0} for c in cards]
        else:
            result[row] = []
    return result


def _leader_summary(board, player, leader, leader_data):
    """Build leader info dict with available targets for choice-based abilities."""
    opp = board.opponent(player)
    info = {
        "name": leader.name,
        "instructions": leader_data.get("instructions", ""),
        "used": board.players[player].leader_used,
    }
    if board.players[player].leader_used:
        return info

    # Enrich with choosable targets so the LLM can specify card_name
    if leader_data.get("draw_opponent_discard"):
        opp_discard = board.players[opp].discard
        info["choose_from"] = "opponent_discard"
        info["available_targets"] = [
            {"name": c.name, "strength": c.strength or 0} for c in opp_discard
        ]
    elif leader_data.get("draw_own_discard"):
        own_discard = board.players[player].discard
        non_hero = [c for c in own_discard
                    if not (c.has_specialty and c.specialty == "hero")]
        info["choose_from"] = "your_discard"
        info["available_targets"] = [
            {"name": c.name, "strength": c.strength or 0} for c in non_hero
        ]
    elif leader_data.get("weather_ranges"):
        allowed = set(leader_data["weather_ranges"])
        weather = [c for c in board.decks[player]
                   if c.is_weather and any(r in allowed for r in (c.ranges or []))]
        info["choose_from"] = "weather_in_deck"
        info["available_targets"] = [
            {"name": c.name, "row": c.ranges[0] if c.ranges else "?"} for c in weather
        ]
    elif leader_data.get("discard_and_draw"):
        cfg = leader_data["discard_and_draw"]
        info["discard_count"] = cfg.get("discard", 2)
        info["draw_count"] = cfg.get("draw", 1)

    return info


def format_game_state(board, player):
    """Build the game state dict sent to the LLM each turn."""
    opp = board.opponent(player)
    leader = board.leaders[player]
    leader_data = leader.leader if leader.leader else {}

    return {
        "round": board.round_number,
        "your_gems": board.players[player].gems,
        "opponent_gems": board.players[opp].gems,
        "your_score": board.calculate_player_score(player),
        "opponent_score": board.calculate_player_score(opp),
        "your_hand": [_card_summary(c) for c in board.hands[player]],
        "your_board": _board_rows_summary(board, player),
        "opponent_board": _board_rows_summary(board, opp),
        "your_discard": [{"name": c.name, "strength": c.strength or 0}
                         for c in board.players[player].discard],
        "weather_active": list(board.weather_rows),
        "your_leader": _leader_summary(board, player, leader, leader_data),
        "your_deck_size": len(board.decks[player]),
        "opponent_hand_size": len(board.hands[opp]),
        "opponent_passed": board.players[opp].passed,
    }


# ── Card name matching ──────────────────────────────────────────────────────

def _norm(name):
    """Normalize for matching: lowercase, collapse whitespace around colons."""
    return re.sub(r'\s*:\s*', ': ', name.lower().strip())


def find_card_by_name(cards, name):
    """Find a card in a list by name (exact, normalized, prefix, substring)."""
    if not name:
        return None
    for c in cards:
        if c.name == name:
            return c
    n = _norm(name)
    for c in cards:
        if _norm(c.name) == n:
            return c
    for c in cards:
        if _norm(c.name).startswith(n):
            return c
    for c in cards:
        if n in _norm(c.name):
            return c
    return None


# ── MQTT client ─────────────────────────────────────────────────────────────

def connect_mqtt():
    """Connect to the gwent MQTT broker."""
    client = mqtt.Client()
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.connect(MQTT_HOST, MQTT_PORT)
    client.loop_start()
    log.info("MQTT connected to %s:%d", MQTT_HOST, MQTT_PORT)
    return client


def publish_card(mq, card):
    """Publish a card scan to the live game."""
    payload = json.dumps(card._instance)
    log.debug("MQTT publish card: %s (rfid=%s)", card.name, card.rfid)
    mq.publish(TOPIC_CARD, payload, qos=1).wait_for_publish(timeout=5)


def publish_choice(mq, choice_id, text=""):
    """Publish a choice (pass, row selection, etc.) to the live game."""
    payload = json.dumps({"kind": "choice", "id": choice_id, "text": text})
    log.debug("MQTT publish choice: id=%s text=%s", choice_id, text)
    mq.publish(TOPIC_CHOICE, payload, qos=1).wait_for_publish(timeout=5)


# ── State polling ───────────────────────────────────────────────────────────

def fetch_board(game_url):
    """Fetch current board from the live game HTTP API. Returns Board or None."""
    resp = requests.get(f"{game_url}/state", timeout=10)
    resp.raise_for_status()
    snapshot = resp.json()
    stage = snapshot.get("active_stage")
    state = snapshot.get("state", {})
    board_data = state.get("board")
    if not board_data:
        return None, stage
    return Board.from_dict(board_data), stage


def wait_for_turn_advance(game_url, prev_player, timeout=30):
    """Poll HTTP API until current_player changes or stage changes.

    Returns (new_board, new_stage) or (None, None) on timeout.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(0.8)
        board, stage = fetch_board(game_url)
        if stage != "PlayRound":
            return board, stage
        if board and board.current_player != prev_player:
            return board, stage
        # Also detect both-passed (round will transition to RoundEnd)
        if board and board.players[PLAYER.ONE].passed and board.players[PLAYER.TWO].passed:
            return board, stage
    return None, None


# ── Action execution via MQTT ───────────────────────────────────────────────

SETTLE_DELAY = 0.6  # seconds between MQTT publishes for multi-step actions


def execute_action(mq, game_url, board, player, action):
    """Validate an LLM action and publish it to the live game via MQTT.

    Returns (success: bool, message: str).
    """
    act = action.get("action", "").lower().strip()

    if act == "pass":
        publish_choice(mq, "p", "Pass")
        return True, "passed"

    if act == "play_leader":
        return _execute_leader(mq, board, player, action)

    if act == "play_card":
        return _execute_play_card(mq, game_url, board, player, action)

    return False, f"Unknown action: {act}. Must be play_card, pass, or play_leader."


def _execute_play_card(mq, game_url, board, player, action):
    """Validate and publish a play_card action."""
    card_name = action.get("card_name", "")
    hand = board.hands[player]
    card = find_card_by_name(hand, card_name)

    if not card:
        hand_names = [c.name for c in hand]
        return False, f"Card '{card_name}' not found in hand. Your hand: {hand_names}"

    # Agile: validate row choice upfront (before publishing)
    is_agile = (card.has_abilities and "agile" in card.abilities
                and len(card.ranges or []) > 1)
    if is_agile:
        row = action.get("row", "").lower().strip()
        if row not in (card.ranges or []):
            return False, (f"Agile card '{card.name}' needs a row. "
                           f"Valid rows: {list(card.ranges)}. Specify 'row' in your response.")

    # Decoy: validate target exists upfront
    is_decoy = card.has_specialty and card.specialty == "decoy"
    decoy_target = None
    if is_decoy:
        target_name = action.get("decoy_target", "")
        if not target_name:
            return False, "Decoy requires decoy_target: name of a non-hero card on your board."
        for rn in ROWS:
            for c in board.players[player].rows[rn]:
                if c.name.lower() == target_name.lower() or target_name.lower() in c.name.lower():
                    if c.has_specialty and c.specialty == "hero":
                        return False, "Cannot swap a hero card with Decoy."
                    decoy_target = c
                    break
            if decoy_target:
                break
        if not decoy_target:
            board_cards = [c.name for rn in ROWS for c in board.players[player].rows[rn]]
            return False, f"Decoy target '{target_name}' not on your board. Cards: {board_cards}"

    # ── Publish the card scan ──
    publish_card(mq, card)
    time.sleep(SETTLE_DELAY)

    # ── Handle multi-step follow-ups ──

    if is_agile:
        row = action.get("row", card.ranges[0]).lower().strip()
        idx = card.ranges.index(row) if row in card.ranges else 0
        publish_choice(mq, str(idx), row)
        time.sleep(SETTLE_DELAY)

    if is_decoy and decoy_target:
        publish_card(mq, decoy_target)
        time.sleep(SETTLE_DELAY)

    # Spy: auto-draw top 2 cards from player's deck
    if card.has_abilities and "spy" in card.abilities:
        for i in range(min(2, len(board.decks[player]))):
            publish_card(mq, board.decks[player][i])
            time.sleep(SETTLE_DELAY)

    # Medic: publish chosen discard card for resurrection
    if card.has_abilities and "medic" in card.abilities:
        discard = board.players[player].discard
        non_hero = [c for c in discard if not (c.has_specialty and c.specialty == "hero")]
        if non_hero:
            target_name = action.get("medic_target", "")
            target = find_card_by_name(non_hero, target_name)
            if not target:
                target = max(non_hero, key=lambda c: c.strength or 0)
            publish_card(mq, target)
            time.sleep(SETTLE_DELAY)

    return True, f"played {card.name}"


def _execute_leader(mq, board, player, action):
    """Validate and publish a leader ability."""
    pb = board.players[player]
    if pb.leader_used:
        return False, "Leader ability already used this game.", None

    leader = board.leaders[player]
    leader_data = leader.leader if leader.leader else {}

    # Publish the leader card scan
    publish_card(mq, leader)
    time.sleep(SETTLE_DELAY)

    # Handle leader abilities that require follow-up scans
    if leader_data.get("draw_own_discard"):
        discard = board.players[player].discard
        non_hero = [c for c in discard if not (c.has_specialty and c.specialty == "hero")]
        if non_hero:
            card_name = action.get("card_name", "")
            target = find_card_by_name(non_hero, card_name)
            if not target:
                target = max(non_hero, key=lambda c: c.strength or 0)
            publish_card(mq, target)
            time.sleep(SETTLE_DELAY)

    elif leader_data.get("draw_opponent_discard"):
        opp = board.opponent(player)
        opp_discard = board.players[opp].discard
        if opp_discard:
            card_name = action.get("card_name", "")
            target = find_card_by_name(opp_discard, card_name)
            if not target:
                target = max(opp_discard, key=lambda c: c.strength or 0)
            publish_card(mq, target)
            time.sleep(SETTLE_DELAY)

    elif leader_data.get("weather_ranges"):
        allowed = set(leader_data["weather_ranges"])
        weather = [c for c in board.decks[player]
                   if c.is_weather and any(r in allowed for r in (c.ranges or []))]
        if weather:
            publish_card(mq, weather[0])
            time.sleep(SETTLE_DELAY)

    elif leader_data.get("discard_and_draw"):
        cfg = leader_data["discard_and_draw"]
        n_discard = cfg.get("discard", 2)
        n_draw = cfg.get("draw", 1)
        hand = board.hands[player]
        if len(hand) >= n_discard and len(board.decks[player]) >= n_draw:
            sorted_hand = sorted(hand, key=lambda c: c.strength or 0)
            for i in range(n_discard):
                publish_card(mq, sorted_hand[i])
                time.sleep(SETTLE_DELAY)
            for i in range(n_draw):
                publish_card(mq, board.decks[player][i])
                time.sleep(SETTLE_DELAY)

    elif leader_data.get("view_opponent_hand"):
        # Reveal happens server-side; mirror it client-side so we can tell the LLM
        count = leader_data["view_opponent_hand"]
        opp = board.opponent(player)
        opp_hand = board.hands[opp]
        sample = min(count, len(opp_hand))
        if sample > 0:
            revealed = random.sample(opp_hand, sample)
            names = [_card_summary(c) for c in revealed]
            return True, f"leader: revealed {len(names)} opponent cards", names

    # Other leader abilities (commander_ranges, clear_weather, etc.) auto-resolve
    # from the initial leader card scan — no follow-up needed.

    return True, f"leader: {leader.name}", None


# ── Console commentary ──────────────────────────────────────────────────────

def print_status(board):
    """Print a one-line board status summary."""
    p1s = board.calculate_player_score(PLAYER.ONE)
    p2s = board.calculate_player_score(PLAYER.TWO)
    p1g = board.players[PLAYER.ONE].gems
    p2g = board.players[PLAYER.TWO].gems
    f1 = board.factions[PLAYER.ONE]
    f2 = board.factions[PLAYER.TWO]
    cur = "P1" if board.current_player == PLAYER.ONE else "P2"
    console.print(
        f"  [dim]R{board.round_number} | {f1} {p1s}pts {'*'*p1g} vs "
        f"{f2} {p2s}pts {'*'*p2g} | turn: {cur} | "
        f"hands: {len(board.hands[PLAYER.ONE])}/{len(board.hands[PLAYER.TWO])}[/dim]")


# ── Main game loop ──────────────────────────────────────────────────────────

def game_loop(mq, game_url, ollama_base_url, model1, model2, transcript, max_retries=3):
    """Run the full game loop, publishing moves via MQTT and polling state via HTTP."""
    system_content = SYSTEM_PROMPT + ACTION_SCHEMA
    histories = {
        PLAYER.ONE: [{"role": "system", "content": system_content}],
        PLAYER.TWO: [{"role": "system", "content": system_content}],
    }
    provider1, model_name1 = parse_model(model1)
    provider2, model_name2 = parse_model(model2)
    providers = {PLAYER.ONE: provider1, PLAYER.TWO: provider2}
    models = {PLAYER.ONE: model_name1, PLAYER.TWO: model_name2}
    display_names = {PLAYER.ONE: model1, PLAYER.TWO: model2}
    turn_count = 0

    for p in (PLAYER.ONE, PLAYER.TWO):
        transcript.conv(p).append("system", system_content)

    while True:
        # Fetch fresh state from the live game each iteration
        board, stage = fetch_board(game_url)
        if not board:
            log.error("Could not fetch board (stage=%s)", stage)
            console.print(f"[red]Lost game connection (stage={stage})[/red]")
            break

        if stage in ("GameOver", "DisplayWinner"):
            p1g = board.players[PLAYER.ONE].gems
            p2g = board.players[PLAYER.TWO].gems
            winner = "P1" if p1g > p2g else "P2" if p2g > p1g else "Draw"
            console.print(f"\n[bold green]GAME OVER! {winner} wins! "
                          f"(P1={p1g} gems, P2={p2g} gems)[/bold green]")
            log.info("GAME OVER: %s | P1=%d gems, P2=%d gems", winner, p1g, p2g)
            break

        if stage == "RoundEnd":
            console.print("[yellow]Round ended. Waiting for next round...[/yellow]")
            log.info("Round end, waiting for server")
            for _ in range(60):
                time.sleep(1)
                _, s = fetch_board(game_url)
                if s != "RoundEnd":
                    break
            continue

        if stage != "PlayRound":
            log.debug("Waiting for PlayRound (stage=%s)", stage)
            time.sleep(2)
            continue

        if board.players[PLAYER.ONE].gems <= 0 or board.players[PLAYER.TWO].gems <= 0:
            break

        # Both passed — server handles round end
        if board.players[PLAYER.ONE].passed and board.players[PLAYER.TWO].passed:
            time.sleep(1)
            continue

        cur = board.current_player
        if board.players[cur].passed:
            time.sleep(0.5)
            continue

        player_num = "P1" if cur == PLAYER.ONE else "P2"
        model = models[cur]
        history = histories[cur]
        conv = transcript.conv(cur)

        print_status(board)

        # Build state for LLM
        state = format_game_state(board, cur)
        state_content = json.dumps(state)
        history.append({"role": "user", "content": state_content})
        conv.append("user", state_content, turn=turn_count, round=board.round_number)
        log.debug("%s state: score=%d opp=%d hand=%d deck=%d",
                  player_num, state["your_score"], state["opponent_score"],
                  len(state["your_hand"]), state["your_deck_size"])

        if len(history) > 13:
            history[:] = history[:1] + history[-12:]

        display = display_names[cur]
        console.print(f"[bold {'cyan' if cur == PLAYER.ONE else 'magenta'}]"
                      f"{player_num} ({board.factions[cur]}) thinking... "
                      f"[model: {display}][/bold {'cyan' if cur == PLAYER.ONE else 'magenta'}]")

        # Call LLM with retries
        provider = providers[cur]
        success = False
        for attempt in range(max_retries):
            try:
                content, pt, ct, latency = call_llm(provider, model, history, ollama_base_url)
            except Exception as e:
                log.error("%s LLM error: %s", player_num, e)
                console.print(f"  [red]LLM error: {e}[/red]")
                conv.append("error", str(e), attempt=attempt)
                transcript.log_turn(
                    round_num=board.round_number, turn=turn_count,
                    player=cur, model=model, prompt_tokens=0,
                    completion_tokens=0, latency_ms=0,
                    action=None, valid=False, error=str(e),
                    board_dict=board.to_dict())
                continue

            console.print(f"  [dim]({latency}ms, {pt}+{ct} tokens)[/dim]")
            log.debug("%s response: %dms %d+%d tokens", player_num, latency, pt, ct)
            conv.append("assistant", content, prompt_tokens=pt,
                        completion_tokens=ct, latency_ms=latency, attempt=attempt)

            # Parse JSON
            try:
                cleaned = content.strip()
                if cleaned.startswith("```"):
                    cleaned = re.sub(r"^```\w*\n?", "", cleaned)
                    cleaned = re.sub(r"\n?```$", "", cleaned)
                action = json.loads(cleaned)
            except json.JSONDecodeError as e:
                error_msg = f"Invalid JSON: {e}. Raw: {content[:200]}"
                log.warning("%s bad JSON (attempt %d): %s", player_num, attempt + 1, error_msg)
                console.print(f"  [red]Retry {attempt+1}: {error_msg}[/red]")
                history.append({"role": "assistant", "content": content})
                error_content = f"ERROR: Your response was not valid JSON. Respond with ONLY a JSON object. {ACTION_SCHEMA}"
                history.append({"role": "user", "content": error_content})
                conv.append("user", error_content, error_type="json_parse", attempt=attempt)
                transcript.log_turn(
                    round_num=board.round_number, turn=turn_count,
                    player=cur, model=model, prompt_tokens=pt,
                    completion_tokens=ct, latency_ms=latency,
                    action=content[:500], valid=False, error=error_msg,
                    board_dict=board.to_dict())
                continue

            # Execute action via MQTT
            ok, msg = execute_action(mq, game_url, board, cur, action)
            reasoning = action.get("reasoning", "")

            if ok:
                act = action.get("action", "?")
                card_name = action.get("card_name", "")
                console.print(f"  [green]{player_num} -> {act}"
                              f"{f': {card_name}' if card_name else ''}[/green]"
                              f"  [dim]{msg}[/dim]")
            else:
                console.print(f"  [red]INVALID: {msg}[/red]")
            if reasoning:
                console.print(f"  [dim italic]{reasoning}[/dim italic]")

            log.info("%s turn=%d: %s -> %s%s", player_num, turn_count,
                     _action_summary(action), "OK" if ok else f"FAIL: {msg}",
                     f" | {reasoning}" if reasoning else "")

            history.append({"role": "assistant", "content": json.dumps(action)})
            transcript.log_turn(
                round_num=board.round_number, turn=turn_count,
                player=cur, model=model, prompt_tokens=pt,
                completion_tokens=ct, latency_ms=latency,
                action=action, valid=ok, error=None if ok else msg,
                board_dict=board.to_dict())

            if ok:
                turn_count += 1
                success = True
                console.print("  [dim]Waiting for game server...[/dim]")
                wait_for_turn_advance(game_url, cur, timeout=15)
                break
            else:
                error_content = f"ERROR: {msg}\nTry again. Current state: {json.dumps(state)}\n{ACTION_SCHEMA}"
                history.append({"role": "user", "content": error_content})
                conv.append("user", error_content, error_type="invalid_move", attempt=attempt)

        if not success:
            log.warning("%s forced pass after %d retries", player_num, max_retries)
            console.print(f"  [bold red]{player_num} forced to pass[/bold red]")
            publish_choice(mq, "p", "Pass")
            transcript.log_event("forced_pass", player=str(cur), model=model)
            wait_for_turn_advance(game_url, cur, timeout=10)


# ── CLI entry point ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Two LLM models play Gwent against each other. "
                    "Prefix model names with provider: openai/gpt-4o, ollama/deepseek-r1:14b. "
                    "Default provider is ollama.")
    parser.add_argument("--model1", default="ollama/deepseek-r1:14b",
                        help="Model for Player 1 (default: ollama/deepseek-r1:14b)")
    parser.add_argument("--model2", default="ollama/deepseek-r1:14b",
                        help="Model for Player 2 (default: ollama/deepseek-r1:14b)")
    parser.add_argument("--base-url", default="http://hal-9005.lan:11434",
                        help="Ollama API base URL (default: http://hal-9005.lan:11434)")
    parser.add_argument("--game-url", default="http://localhost:8080",
                        help="Gwent game server URL (default: http://localhost:8080)")
    parser.add_argument("--max-retries", type=int, default=3,
                        help="Max invalid-move retries per turn (default: 3)")

    args = parser.parse_args()

    _setup_logging()
    transcript = GameTranscript(args.model1, args.model2)

    log.info("=" * 60)
    log.info("NEW GAME model1=%s model2=%s ollama=%s game=%s",
             args.model1, args.model2, args.base_url, args.game_url)

    # Connect to MQTT
    mq = connect_mqtt()

    # Fetch initial state
    board, stage = fetch_board(args.game_url)
    if not board or stage != "PlayRound":
        console.print(f"[red]Game not in PlayRound (stage={stage}). "
                      f"Start a game first.[/red]")
        return 1

    console.print(Panel(
        f"[bold]LLM vs LLM — Gwent[/bold]\n"
        f"P1: {args.model1} ({board.factions[PLAYER.ONE]}) | "
        f"P2: {args.model2} ({board.factions[PLAYER.TWO]})\n"
        f"Leaders: {board.leaders[PLAYER.ONE].name} vs {board.leaders[PLAYER.TWO].name}\n"
        f"Ollama: {args.base_url} | Game: {args.game_url}\n"
        f"Logs: {LOG_FILE}\n"
        f"  P1 conv: {transcript.conv(PLAYER.ONE).filepath}\n"
        f"  P2 conv: {transcript.conv(PLAYER.TWO).filepath}",
        title="GWENT"))

    log.info("Live game: %s vs %s | round=%d gems=%d/%d hands=%d/%d",
             board.factions[PLAYER.ONE], board.factions[PLAYER.TWO],
             board.round_number,
             board.players[PLAYER.ONE].gems, board.players[PLAYER.TWO].gems,
             len(board.hands[PLAYER.ONE]), len(board.hands[PLAYER.TWO]))

    transcript.log_event("game_start",
                         model1=args.model1, model2=args.model2,
                         base_url=args.base_url, game_url=args.game_url)

    try:
        game_loop(mq, args.game_url, args.base_url,
                  args.model1, args.model2,
                  transcript, max_retries=args.max_retries)
    except KeyboardInterrupt:
        console.print("\n[yellow]Game interrupted.[/yellow]")
        log.info("Game interrupted by user")
    finally:
        mq.loop_stop()
        mq.disconnect()

    console.print(f"\n[dim]Logs: {LOG_FILE}[/dim]")
    console.print(f"[dim]P1 conv: {transcript.conv(PLAYER.ONE).filepath}[/dim]")
    console.print(f"[dim]P2 conv: {transcript.conv(PLAYER.TWO).filepath}[/dim]")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
