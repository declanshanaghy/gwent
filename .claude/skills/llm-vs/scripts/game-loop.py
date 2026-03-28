#!/usr/bin/env python3
"""LLM vs LLM game loop — self-contained launcher and game manager.

Usage:
  python3 game-loop.py [--model MODEL] [--ollama-url URL] [--game-url URL]
                       [--fresh] [--max-turns N]

Models (prefix determines provider):
  anthropic/claude-haiku-4-5-20251001   (default)
  anthropic/claude-sonnet-4-6
  openai/gpt-4o-mini
  openai/gpt-4o
  openai/gpt-4.1-mini
  openai/gpt-4.1-nano
  llama3.2:3b                           (Ollama, no prefix)
  deepseek-r1:14b                       (Ollama)

Flags:
  --fresh       Restart the game server and trigger a random deal before playing.
  --model       Model name with provider prefix (default: anthropic/claude-haiku-4-5-20251001).
  --ollama-url  Ollama API base URL (default: http://hal-9005.lan:11434).
  --game-url    Game HTTP API base URL (default: http://localhost:8080).
  --max-turns   Max turns before auto-stopping (default: 60).
"""
import argparse
import json
import os
import re
import requests
import subprocess
import sys
import threading
import time

import paho.mqtt.client as mqtt

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(SKILL_DIR)))

MQ_BASE = ['mosquitto_pub', '-h', 'localhost', '-p', '1883',
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

GAME STRUCTURE:
- Best of 3 rounds. Each player starts with 2 gems (lives). Lose a gem each round you lose.
- Game ends when a player reaches 0 gems.
- Each turn you may: play a card from your hand, pass, or use your leader ability (once per game).
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
- spy: placed on OPPONENT's board (gives them the strength). You draw 2 cards from your deck. Play spies EARLY.
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
  "medic_target": "card name from your discard to resurrect (only if card has medic ability)",
  "decoy_target": "card name on your board to swap back to hand (only if playing a decoy card)",
  "reasoning": "brief explanation of your strategy"
}"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class AnnouncementSync:
    """Subscribe to MQTT and block until all announcements finish."""

    def __init__(self):
        self._count = 0
        self._lock = threading.Lock()
        self._event = threading.Event()
        self._client = mqtt.Client(client_id='llm-vs-sync',
                                   protocol=mqtt.MQTTv311)
        self._client.username_pw_set('geralt', 'gwent')
        self._client.on_message = self._on_message
        self._client.connect('localhost', 1883)
        self._client.subscribe('gwent/sfx/complete')
        self._client.loop_start()

    def _on_message(self, client, userdata, msg):
        try:
            d = json.loads(msg.payload)
            if d.get('subkind') == 'announcement_complete':
                with self._lock:
                    self._count += 1
                self._event.set()
        except Exception:
            pass

    def wait_all(self, timeout=60):
        """Block until all queued announcements finish playing.

        First waits for at least one announcement_complete (long timeout
        to allow TTS generation/download), then drains any remaining
        announcements using a shorter gap timer.
        """
        deadline = time.time() + timeout
        # Phase 1: wait for first announcement (TTS generation can be slow)
        self._event.clear()
        got = self._event.wait(timeout=min(30, timeout))
        if not got:
            return  # no announcement at all, move on
        # Phase 2: drain remaining — wait until no announcement for 5s
        while time.time() < deadline:
            self._event.clear()
            got = self._event.wait(timeout=5.0)
            if not got:
                return  # queue drained

    def drain(self):
        """Consume any stale events without blocking."""
        self._event.clear()
        with self._lock:
            self._count = 0

    def stop(self):
        self._client.loop_stop()
        self._client.disconnect()


def log(msg):
    print(msg, flush=True)


def mqpub(topic, payload):
    subprocess.run(MQ_BASE + ['-t', topic, '-m', payload],
                   check=True, capture_output=True)
    time.sleep(0.6)


def fetch(game_url):
    r = requests.get(f'{game_url}/state', timeout=10)
    etag = r.headers.get('ETag', '')
    d = r.json()
    return d.get('active_stage', '?'), d.get('state', {}).get('board', {}), etag


def poll_until_change(game_url, etag, timeout=10):
    """Long-poll the game server, blocking until state changes or timeout."""
    try:
        r = requests.get(
            f'{game_url}/state?timeout={timeout}',
            headers={'If-None-Match': etag} if etag else {},
            timeout=timeout + 5)
        if r.status_code == 304:
            return None, None, etag
        d = r.json()
        new_etag = r.headers.get('ETag', '')
        return (d.get('active_stage', '?'),
                d.get('state', {}).get('board', {}), new_etag)
    except requests.Timeout:
        return None, None, etag


def wait_for_turn_advance(game_url, etag, cur_player, timeout=30):
    """Poll until current_player changes or stage transitions away from PlayRound."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        remaining = max(1, int(deadline - time.time()))
        stage, board, etag = poll_until_change(
            game_url, etag, timeout=min(remaining, 10))
        if stage is None:
            stage, board, etag = fetch(game_url)
        if stage != 'PlayRound' or board.get('current_player') != cur_player:
            return stage, board, etag
    return fetch(game_url)


# ---------------------------------------------------------------------------
# Game setup: restart server, trigger random deal, wait for PlayRound
# ---------------------------------------------------------------------------

def ensure_game_ready(game_url, fresh=False, tts='gtts'):
    """Ensure the game server is running and in PlayRound.

    If --fresh, restart the server and trigger a random deal.
    Returns (stage, board, etag) when ready, or raises on failure.
    """
    dev_script = os.path.join(REPO_ROOT, 'scripts', 'dev-server.sh')

    if fresh:
        log(f"Restarting game server (tts={tts})...")
        cmd = ['bash', dev_script, 'gwent', 'restart', '--tts', tts]
        subprocess.run(cmd, check=True, capture_output=True)
        # Wait for server to come up
        for _ in range(10):
            time.sleep(1)
            try:
                stage, board, etag = fetch(game_url)
                break
            except Exception:
                continue
        else:
            raise RuntimeError("Game server did not start")

        log(f"Server ready (stage={stage})")

        if stage == 'MainMenu':
            log("Triggering random deal...")
            mqpub('gwent/mfd/choose',
                  json.dumps({"kind": "choice", "id": "1",
                              "text": "Random Deal"}))
            # Wait for PlayRound
            for _ in range(30):
                time.sleep(1)
                stage, board, etag = fetch(game_url)
                if stage == 'PlayRound':
                    break
            if stage != 'PlayRound':
                raise RuntimeError(
                    f"Expected PlayRound after deal, got {stage}")
    else:
        stage, board, etag = fetch(game_url)
        if stage != 'PlayRound':
            raise RuntimeError(
                f"Game not in PlayRound (stage={stage}). "
                f"Use --fresh to start a new game.")

    return stage, board, etag


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
    all_cards = board['hands'][player] + board['decks'][player]

    cards_text = "\n".join(f"  - {card_line(c)}" for c in all_cards)

    section7 = f"""
YOUR FACTION: {faction}
YOUR FACTION PASSIVE: {FACTION_PASSIVES.get(faction, 'Unknown')}

YOUR LEADER: {leader['name']}
LEADER ABILITY: {leader.get('leader', {}).get('instructions', '?')} (one-time use)

YOUR DECK CARDS (hand + deck combined):
{cards_text}

OPPONENT FACTION: {opp_faction}
OPPONENT PASSIVE: {FACTION_PASSIVES.get(opp_faction, 'Unknown')}
OPPONENT LEADER: {opp_leader['name']}
OPPONENT LEADER ABILITY: {opp_leader.get('leader', {}).get('instructions', '?')}"""

    return SYSTEM_PROMPT_SHARED + "\n" + section7


def init_conversations(board):
    """Create /tmp/logs/llm-vs-p{1,2}.jsonl with system prompts."""
    os.makedirs('/tmp/logs', exist_ok=True)
    for pnum, player in [('1', 'PLAYER.ONE'), ('2', 'PLAYER.TWO')]:
        prompt = build_system_prompt(board, player)
        fp = f'/tmp/logs/llm-vs-p{pnum}.jsonl'
        with open(fp, 'w') as f:
            f.write(json.dumps({"role": "system", "content": prompt}) + '\n')

    f1 = board['factions']['PLAYER.ONE']
    f2 = board['factions']['PLAYER.TWO']
    l1 = board['leaders']['PLAYER.ONE']['name']
    l2 = board['leaders']['PLAYER.TWO']['name']
    h1 = len(board['hands']['PLAYER.ONE'])
    d1 = len(board['decks']['PLAYER.ONE'])
    h2 = len(board['hands']['PLAYER.TWO'])
    d2 = len(board['decks']['PLAYER.TWO'])
    log(f"P1: {f1} ({l1}) -- {h1} hand + {d1} deck")
    log(f"P2: {f2} ({l2}) -- {h2} hand + {d2} deck")


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
    return {
        'round': board['round_number'],
        'your_gems': board['players'][cur]['gems'],
        'opponent_gems': board['players'][opp]['gems'],
        'your_score': board['scores'][cur]['total'],
        'opponent_score': board['scores'][opp]['total'],
        'your_hand': [card_summary(c) for c in board['hands'][cur]],
        'your_board': rows_summary(board, cur),
        'opponent_board': rows_summary(board, opp),
        'your_discard': [
            {'name': c['name'], 'strength': c.get('strength', 0)}
            for c in board['players'][cur]['discard']],
        'weather_active': board['weather_rows'],
        'your_leader': li,
        'your_deck_size': len(board['decks'][cur]),
        'opponent_hand_size': len(board['hands'][opp]),
        'opponent_passed': board['players'][opp]['passed'],
    }


# ---------------------------------------------------------------------------
# LLM providers
# ---------------------------------------------------------------------------

def _provider(model):
    """Return (provider, model_id) from a model string.

    Prefixes: 'openai/' -> OpenAI, 'anthropic/' -> Anthropic, else Ollama.
    """
    if model.startswith('openai/'):
        return 'openai', model[len('openai/'):]
    if model.startswith('anthropic/'):
        return 'anthropic', model[len('anthropic/'):]
    return 'ollama', model


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


def execute(board, cur, action):
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

        if 'spy' in card.get('abilities', []):
            deck = board['decks'][cur]
            for i in range(min(2, len(deck))):
                mqpub('gwent/cards/raw/read', json.dumps(deck[i]))

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

def game_loop(args, board, etag, sync):
    """Run the turn-by-turn game loop until game over or max turns."""
    turn = 0
    while turn < args.max_turns:
        stage, board, etag = fetch(args.game_url)

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
            for _ in range(30):
                s, b, etag = poll_until_change(
                    args.game_url, etag, timeout=5)
                if s is not None and s != 'RoundEnd':
                    break
            continue

        if stage != 'PlayRound':
            poll_until_change(args.game_url, etag, timeout=5)
            continue

        if (board['players']['PLAYER.ONE']['gems'] <= 0
                or board['players']['PLAYER.TWO']['gems'] <= 0):
            break

        if (board['players']['PLAYER.ONE']['passed']
                and board['players']['PLAYER.TWO']['passed']):
            poll_until_change(args.game_url, etag, timeout=5)
            continue

        cur = board['current_player']
        if board['players'][cur]['passed']:
            poll_until_change(args.game_url, etag, timeout=5)
            continue

        pnum = '1' if cur == 'PLAYER.ONE' else '2'
        plab = f"P{pnum} ({board['factions'][cur]})"

        state = build_state(board, cur)
        state_json = json.dumps(state)

        ok = False
        for attempt in range(3):
            content, lat = call_llm(
                args.ollama_url, args.model, pnum,
                state_json if attempt == 0 else json.dumps(state))
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

            # Drain stale announcements, then execute
            sync.drain()
            valid, msg = execute(board, cur, action)
            reasoning = action.get('reasoning', '')
            card_name = action.get('card_name', '')
            act = action.get('action', '?')

            if valid:
                ok = True
                turn += 1
                # 1. Confirm state changed (turn advanced or stage changed)
                stage, board, etag = wait_for_turn_advance(
                    args.game_url, etag, cur)
                # 2. Wait for ALL queued announcements to finish playing
                sync.wait_all()
                # 3. Fetch final state for accurate scores
                stage, board, etag = fetch(args.game_url)
                if board and 'scores' in board:
                    ps1 = board['scores']['PLAYER.ONE']['total']
                    ps2 = board['scores']['PLAYER.TWO']['total']
                else:
                    ps1, ps2 = '?', '?'
                log(f"R{board.get('round_number','?')}T{turn-1} {plab}: "
                    f"{act} {card_name} ({lat}ms) | {msg} | "
                    f"P1={ps1} P2={ps2}")
                if reasoning:
                    log(f'  "{reasoning}"')
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
            sync.drain()
            mqpub('gwent/mfd/choose',
                  json.dumps({"kind": "choice", "id": "p",
                              "text": "Pass"}))
            wait_for_turn_advance(args.game_url, etag, cur)
            sync.wait_all()

    log(f"\n{turn} turns played.")
    log(f"Logs: /tmp/logs/llm-vs-p1.jsonl, /tmp/logs/llm-vs-p2.jsonl")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='LLM vs LLM Gwent game manager')
    parser.add_argument('--model', default='anthropic/claude-haiku-4-5-20251001')
    parser.add_argument('--ollama-url', default='http://hal-9005.lan:11434')
    parser.add_argument('--game-url', default='http://localhost:8080')
    parser.add_argument('--max-turns', type=int, default=60)
    parser.add_argument('--tts', default='gtts',
                        help='TTS provider: gtts (default, free), openai, elevenlabs')
    parser.add_argument('--fresh', action='store_true',
                        help='Restart server and trigger random deal')
    args = parser.parse_args()

    # Load .env for API keys
    _load_env()

    # 1. Check model availability
    provider, model_id = _provider(args.model)
    log(f"Provider: {provider}, model: {model_id}")

    if provider == 'openai':
        if not os.environ.get('OPENAI_API_KEY'):
            log("ERROR: OPENAI_API_KEY not set (check .env)")
            return 1
        log(f"OpenAI model: {model_id}")
    elif provider == 'anthropic':
        if not os.environ.get('ANTHROPIC_API_KEY'):
            log("ERROR: ANTHROPIC_API_KEY not set (check .env)")
            return 1
        log(f"Anthropic model: {model_id}")
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
        subprocess.run(MQ_BASE + ['-t', 'test/ping', '-m', '{"kind":"test"}'],
                       check=True, capture_output=True, timeout=5)
    except Exception as e:
        log(f"ERROR: MQTT broker not reachable: {e}")
        return 1

    # 3. Ensure game is ready
    try:
        stage, board, etag = ensure_game_ready(args.game_url, fresh=args.fresh,
                                                   tts=args.tts)
    except RuntimeError as e:
        log(f"ERROR: {e}")
        return 1

    log(f"Game ready: stage={stage}")

    # 4. Initialize conversation logs
    init_conversations(board)

    # 5. Start MQTT announcement sync
    sync = AnnouncementSync()
    # Drain any announcements from the deal stage
    sync.drain()

    # 6. Run the game loop
    log(f"\nStarting game: {args.model} vs {args.model}")
    log("=" * 60)
    try:
        game_loop(args, board, etag, sync)
    finally:
        sync.stop()
    return 0


if __name__ == '__main__':
    sys.exit(main() or 0)
