"""LLMPlayerManager — Phase 3 of the TUI interactivity redesign.

When a TUI client tags a player slot with an LLM (via the `assign-pN`
menu/choose round-trip), this manager spawns `.claude/skills/llm-vs/scripts/
game-loop.py` as a subprocess scoped to that side. On non-zero exit, the
manager advances a per-side randomized fallback chain — eventually reverting
to Human + publishing a `gwent/toast` notification when the chain is dry.

One subprocess per LLM side (so a P1-LLM / P2-LLM game has two subprocesses).
Reaped cleanly on game reset / swap / shutdown via SIGTERM.

Profuse logging per feedback_profuse_logging.
"""
from __future__ import annotations

import json
import os
import random
import signal
import subprocess
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import paho.mqtt.client as mqtt

import gwent.game
import gwent.messaging.ctrl
import gwent.messaging.factory
import gwent.messaging.menu
from gwent.game import (
    CH_CTRL,
    PubSubComponent,
    ch_menu_present,
)

if TYPE_CHECKING:
    from gwent.game.controller import Controller


# Repo root: software/gwent/gwent/game/llm_player.py -> ../../../../  is repo.
_REPO_ROOT = Path(__file__).resolve().parents[4]
_GAME_LOOP = _REPO_ROOT / ".claude" / "skills" / "llm-vs" / "scripts" / "game-loop.py"
_LLM_MODELS_JSON = _REPO_ROOT / "software" / "data" / "llm-models.json"
_LOG_DIR = _REPO_ROOT / "tmp" / "logs"

# How long to wait between fallback attempts on the same model before marking
# it broken for the rest of the game (skip on rotation).
_FAILURE_WINDOW_S = 60.0
_FAILURES_BEFORE_BLACKLIST = 2

# Topic for transient TUI notifications (Phase 3 toast banner).
_CH_TOAST = f"{gwent.game.MAIN_CHANNEL}/toast"


def load_curated_models() -> list[dict]:
    """Read software/data/llm-models.json and return the model list.

    Falls back to an empty list (logged) if the file is missing or malformed.
    """
    try:
        with _LLM_MODELS_JSON.open() as f:
            data = json.load(f)
        return [m for m in data.get("models", []) if isinstance(m, dict)]
    except Exception:
        # Logged by caller; return empty rather than crash.
        return []


class _Side:
    """Per-player state. Tracks the active subprocess + fallback chain."""

    def __init__(self, side: str):
        self.side = side  # "P1" or "P2"
        self.controller: str = "human"
        self.proc: Optional[subprocess.Popen] = None
        self.chain: list[str] = []          # remaining models to try
        self.tried: list[str] = []          # already-attempted (current chain run)
        self.blacklist: set[str] = set()    # models that failed twice (this game)
        self.failures: dict[str, list[float]] = {}  # model -> recent failure times


class LLMPlayerManager(PubSubComponent):
    """Owns LLM-driver subprocesses for both players + the assign menus.

    Lifecycle:
        mgr = LLMPlayerManager(pubsub, controller)
        mgr.init()    # subscribes to nothing yet — MenuPublisher routes choose
        mgr.start()
        # Game runs; assign() called via MenuPublisher dispatch.
        mgr.shutdown()
    """

    # Class-level so MenuPublisher can also use these names.
    SIDE_P1 = "P1"
    SIDE_P2 = "P2"

    def __init__(self, pubsub: mqtt.Client, controller: "Controller"):
        super().__init__(pubsub)
        self._controller = controller
        self._sides: dict[str, _Side] = {
            self.SIDE_P1: _Side(self.SIDE_P1),
            self.SIDE_P2: _Side(self.SIDE_P2),
        }
        self._models: list[dict] = []
        self._lock = threading.Lock()
        # Track current backend stage so we only spawn game-loop.py when the
        # game is actually in PlayRound (the subprocess immediately exits
        # otherwise, exhausting the fallback chain pointlessly).
        self._current_stage: str = ""
        _LOG_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------------

    def init(self):
        super().init()
        self._models = load_curated_models()
        if not self._models:
            self._log.warning(
                f"No LLM models loaded from {_LLM_MODELS_JSON} — "
                "the controller picker will only offer Human")
        else:
            self._log.info(
                f"LLMPlayerManager loaded {len(self._models)} curated models")
        # Track stage transitions so we can defer subprocess spawn until the
        # game reaches PlayRound (game-loop.py errors out otherwise).
        self.subscribe(CH_CTRL, gwent.messaging.ctrl.KIND, self._on_ctrl)
        self._publish_assign_menus()

    def shutdown(self):
        self._log.info("LLMPlayerManager shutting down — terminating subprocesses")
        for side in self._sides.values():
            self._terminate(side)
        super().shutdown()

    # ------------------------------------------------------------------------
    # Public API (called by MenuPublisher choose dispatch)
    # ------------------------------------------------------------------------

    def assign(self, side: str, controller: str) -> None:
        """Reassign `side` (P1/P2) to a controller id ('human' or model id).

        Every change is published retained on gwent/players/controller/PLAYER.*
        — that topic is the live source of truth all clients (TUI, game-loop)
        read. Changes are legal at ANY time: before game start, mid-game,
        mid-round.

        - human  → terminate any running subprocess for that side
        - LLM id → if a driver (managed subprocess OR external game-loop) is
                   already running, it adopts the new model live from the
                   topic — no respawn. Otherwise spawn at PlayRound (now or
                   deferred via _on_ctrl).
        """
        side = side.upper()
        if side not in self._sides:
            self._log.warning(f"assign: unknown side {side!r}")
            return
        st = self._sides[side]
        controller = controller or "human"
        with self._lock:
            self._log.info(
                f"assign side={side} new_controller={controller!r} "
                f"prev_controller={st.controller!r} stage={self._current_stage!r}")
            st.controller = controller
            st.failures = {}
            # Don't reset blacklist — a model that failed earlier this game
            # remains skipped until reset_game().

        # Publish the new controller state (retained per-side) FIRST — the
        # TUI label and any running game-loop pick it up from here.
        self._publish_controller(side, controller)

        if controller == "human":
            # Tear down any LLM driver we own for that side.
            with self._lock:
                st.chain = []
                st.tried = []
                self._terminate(st)
            return

        if st.proc is not None and st.proc.poll() is None:
            # Our managed driver follows the retained topic live — keep it,
            # just refresh the fallback chain behind the new model.
            with self._lock:
                st.tried = [controller]
                st.chain = self._chain_others(st, controller)
            self._log.info(
                f"side={side} managed driver pid={st.proc.pid} adopts "
                f"{controller} live from topic (no respawn)")
            return

        ext = self._external_driver_pids()
        if ext:
            # A standalone game-loop (e.g. /llm-vs) is driving — it follows
            # the retained topic, so don't spawn a competing subprocess.
            self._log.info(
                f"side={side} external game-loop pids={sorted(ext)} will "
                f"adopt {controller} from the topic — not spawning")
            return

        if self._current_stage != "PlayRound":
            self._log.info(
                f"side={side} controller={controller} deferred — "
                f"stage is {self._current_stage!r}, spawn at PlayRound")
            if self._current_stage not in ("", "MainMenu", "Offline"):
                # In-game info; on the New Game screen this is just noise.
                self._publish_toast(
                    f"{side}: {controller} queued — will play when round begins",
                    level="info",
                )
            return

        # Build the fallback chain starting from the chosen model.
        self._start_chain(side, controller)

    def _on_ctrl(self, msg) -> None:
        """Track stage transitions so we can spawn deferred LLMs at PlayRound."""
        try:
            new_stage = msg._instance.get("stage", "")
            active = msg._instance.get("active", False)
        except Exception:
            return
        if not active:
            return
        if new_stage == self._current_stage:
            return
        prev = self._current_stage
        self._current_stage = new_stage
        self._log.info(f"stage transition {prev!r} -> {new_stage!r}")

        if new_stage == "PlayRound":
            with self._lock:
                deferred = [
                    (s, st.controller) for s, st in self._sides.items()
                    if st.controller not in ("", "human") and st.proc is None
                ]
            ext = self._external_driver_pids() if deferred else set()
            for side, controller in deferred:
                if ext:
                    self._log.info(
                        f"PlayRound reached — {side}: {controller} driven by "
                        f"external game-loop pids={sorted(ext)}, not spawning")
                    continue
                self._log.info(
                    f"PlayRound reached — spawning deferred LLM for {side}: {controller}")
                self._start_chain(side, controller)
        elif new_stage in ("MainMenu", "Offline", "GameOver", "DisplayWinner"):
            # Game ended / reset — tear down LLM subprocesses.
            with self._lock:
                for st in self._sides.values():
                    if st.proc is not None:
                        self._log.info(
                            f"side={st.side} stage->{new_stage}, terminating subprocess")
                        self._terminate(st)

    def reset_game(self) -> None:
        """Tear down all LLM subprocesses and clear per-game state.

        Called by MenuPublisher when the in-game `reset` choice fires.
        """
        with self._lock:
            for st in self._sides.values():
                self._terminate(st)
                st.controller = "human"
                st.chain = []
                st.tried = []
                st.failures = {}
                st.blacklist = set()
        for side in self._sides:
            self._publish_controller(side, "human")

    def current_controller(self, side: str) -> str:
        return self._sides.get(side.upper(), _Side(side)).controller

    @property
    def models(self) -> list[dict]:
        """The curated model list (id/label/icon/kind dicts)."""
        return self._models

    def pick_random_model(self) -> dict | None:
        """Pick a random LLM (non-human) model. Returns a model dict or None."""
        llms = [m for m in self._models if m.get("kind") == "llm"]
        if not llms:
            self._log.warning("pick_random_model: no llm-kind models available")
            return None
        choice = random.choice(llms)
        self._log.info(f"pick_random_model -> {choice.get('id')!r}")
        return choice

    # ------------------------------------------------------------------------
    # Menu publishing
    # ------------------------------------------------------------------------

    def _publish_assign_menus(self) -> None:
        """Publish (retained) `gwent/menu/present/assign-p1` and `-p2`."""
        for menu_id, side_label in (("assign-p1", "Player 1"),
                                    ("assign-p2", "Player 2")):
            choices = []
            for m in self._models:
                choices.append(gwent.messaging.menu.Choice(
                    id=m.get("id", ""),
                    text=m.get("label", m.get("id", "?")),
                    description=m.get("description"),
                    icon=m.get("icon", ""),
                ))
            if not choices:
                # At least offer Human so the menu isn't empty.
                choices.append(gwent.messaging.menu.Choice(
                    id="human", text="Human (RFID / touch)", icon="🃏"))
            msg = gwent.messaging.menu.Message.with_choices(
                menu_id=menu_id,
                choices=choices,
                prompt=f"{side_label} controller",
            )
            self.publish(ch_menu_present(menu_id), msg, retain=True)
            self._log.info(
                f"published assign menu {menu_id} ({len(choices)} choices)")

    def _publish_controller(self, side: str, controller: str) -> None:
        """Retained announce of which controller is on each side.

        The TUI subscribes to `gwent/players/controller/PLAYER.*` to show e.g.
        'P1 · Sonnet 4.6' next to scores.
        """
        player_str = f"PLAYER.{ 'ONE' if side == 'P1' else 'TWO' }"
        topic = f"{gwent.game.MAIN_CHANNEL}/players/controller/{player_str}"
        # Include the human-readable label so the TUI can display it directly.
        label = controller
        for m in self._models:
            if m.get("id") == controller:
                label = m.get("label", controller)
                break
        payload = json.dumps({
            "player": player_str,
            "controller": controller,
            "label": label,
        })
        self._pubsub.publish(topic, payload, qos=1, retain=True)
        self._log.info(f"published controller state {topic} -> {controller} ({label!r})")

    def _publish_toast(self, text: str, level: str = "warn") -> None:
        """Transient banner notification, picked up by the TUI's toast widget."""
        payload = json.dumps({
            "kind": "toast",
            "level": level,
            "text": text,
            "ts": time.time(),
        })
        self._pubsub.publish(_CH_TOAST, payload, qos=0, retain=False)
        self._log.info(f"toast ({level}): {text}")

    # ------------------------------------------------------------------------
    # Fallback chain + subprocess management
    # ------------------------------------------------------------------------

    def _chain_others(self, st: _Side, first_model: str) -> list[str]:
        """Randomized fallback models behind `first_model` (minus blacklisted)."""
        others = [m["id"] for m in self._models
                  if m.get("kind") == "llm" and m.get("id") != first_model
                  and m.get("id") not in st.blacklist]
        random.shuffle(others)
        return others

    def _external_driver_pids(self) -> set:
        """PIDs of game-loop.py processes NOT spawned by this manager.

        A standalone run (e.g. the /llm-vs skill) drives sides itself and
        follows the retained controller topic — when one is alive we only
        publish the topic and let it adopt, instead of spawning a competing
        subprocess."""
        own = {st.proc.pid for st in self._sides.values()
               if st.proc is not None and st.proc.poll() is None}
        try:
            out = subprocess.run(
                ["pgrep", "-f", r"game-loop\.py"],
                capture_output=True, text=True, timeout=5)
            pids = {int(p) for p in out.stdout.split() if p.strip().isdigit()}
        except Exception as e:
            self._log.warning(f"external game-loop scan failed: {e}")
            return set()
        ext = pids - own - {os.getpid()}
        if ext:
            self._log.debug(
                f"external game-loop pids={sorted(ext)} (own={sorted(own)})")
        return ext

    def _start_chain(self, side: str, first_model: str) -> None:
        st = self._sides[side]
        # Build chain: requested model first, then a randomized order of the
        # other LLM-kind models from the curated list (minus blacklisted).
        st.chain = [first_model] + self._chain_others(st, first_model)
        st.tried = []
        self._log.info(
            f"side={side} fallback chain (head): {st.chain[:5]}{'...' if len(st.chain) > 5 else ''}")
        self._spawn_next(side)

    def _spawn_next(self, side: str) -> None:
        st = self._sides[side]
        # Skip blacklisted models in chain.
        while st.chain:
            model = st.chain.pop(0)
            if model in st.blacklist:
                self._log.info(
                    f"side={side} skipping blacklisted model: {model}")
                continue
            st.tried.append(model)
            st.controller = model
            self._publish_controller(side, model)
            self._spawn(side, model)
            return

        # Chain exhausted — revert to Human and toast the user.
        self._log.warning(
            f"side={side} fallback chain exhausted (tried={st.tried}) — reverting to Human")
        st.controller = "human"
        self._publish_controller(side, "human")
        self._publish_toast(
            f"All LLM models failed for {side} — reverted to Human. Tap to reassign.",
            level="warn",
        )

    def _spawn(self, side: str, model: str) -> None:
        """Fork game-loop.py as a subprocess for this side."""
        st = self._sides[side]
        if not _GAME_LOOP.is_file():
            self._log.error(f"game-loop.py not found at {_GAME_LOOP}")
            self._publish_toast(
                f"LLM driver missing: {_GAME_LOOP.name}. Reverting {side} to Human.",
                level="error",
            )
            st.controller = "human"
            self._publish_controller(side, "human")
            return

        log_path = _LOG_DIR / f"llm-{side.lower()}.log"
        # game-loop.py uses --model-p1 / --model-p2 for both sides; we set the
        # one we're driving and leave the other as a placeholder. Since only
        # one subprocess per side runs at once, the "other" model arg is
        # irrelevant for this subprocess's behaviour — game-loop only acts on
        # turns whose `current_player` matches its own side per its loop.
        # However the script doesn't currently filter by side, so for v1 we
        # rely on the convention that only one side's model is "live" per
        # subprocess and the other side's player on the server is human or
        # served by a different subprocess.
        pflag = "--model-p1" if side == "P1" else "--model-p2"
        cmd = [
            "/home/dshanaghy/gwent-venv/bin/python",
            str(_GAME_LOOP),
            pflag, model,
            "--only-side", side,    # only act on this side's turns
            "--no-pause",
        ]
        self._log.info(f"spawning game-loop for side={side}: {' '.join(cmd)}")
        try:
            logf = log_path.open("a", buffering=1)
            logf.write(f"\n--- spawn at {time.strftime('%Y-%m-%dT%H:%M:%S%z')} "
                       f"side={side} model={model} ---\n")
            proc = subprocess.Popen(
                cmd,
                stdout=logf,
                stderr=subprocess.STDOUT,
                cwd=str(_REPO_ROOT),
                env=os.environ.copy(),
                start_new_session=True,  # own process group so SIGTERM is scoped
            )
        except Exception as e:
            self._log.exception(f"spawn failed for {side}/{model}: {e}")
            self._publish_toast(
                f"LLM spawn failed for {side} ({model}): {e}",
                level="error",
            )
            self._record_failure(side, model)
            self._spawn_next(side)
            return

        st.proc = proc
        # Reaper thread — when the subprocess exits, decide whether to advance
        # the fallback chain.
        t = threading.Thread(
            target=self._reap, args=(side, model, proc, log_path),
            daemon=True, name=f"llm-reaper-{side}",
        )
        t.start()

    def _reap(self, side: str, model: str, proc: subprocess.Popen,
              log_path: Path) -> None:
        """Wait for the subprocess to exit and advance the chain if it failed."""
        rc = proc.wait()
        self._log.info(
            f"side={side} model={model} subprocess exited rc={rc} (log: {log_path})")
        with self._lock:
            st = self._sides.get(side)
            # If user reassigned in the meantime, st.proc points to a NEW
            # subprocess; only react to the one we were reaping.
            if st is None or st.proc is not proc:
                self._log.debug(
                    f"reap: side={side} subprocess superseded — ignoring rc={rc}")
                return
            st.proc = None
            if rc == 0:
                # Clean exit — usually because game ended. Don't advance chain.
                self._log.info(
                    f"side={side} model={model} clean exit (rc=0) — chain idle")
                return
            self._record_failure(side, model)
            self._publish_toast(
                f"{side} model {model} failed (rc={rc}); trying next…",
                level="warn",
            )
            self._spawn_next(side)

    def _record_failure(self, side: str, model: str) -> None:
        st = self._sides[side]
        now = time.time()
        history = st.failures.setdefault(model, [])
        history.append(now)
        # Drop old entries outside the window.
        history[:] = [t for t in history if now - t <= _FAILURE_WINDOW_S]
        if len(history) >= _FAILURES_BEFORE_BLACKLIST:
            st.blacklist.add(model)
            self._log.warning(
                f"side={side} model={model} blacklisted "
                f"({len(history)} failures in {_FAILURE_WINDOW_S}s)")

    def _terminate(self, st: _Side) -> None:
        """SIGTERM the subprocess (per project rule — no SIGKILL)."""
        proc = st.proc
        st.proc = None
        if proc is None:
            return
        if proc.poll() is not None:
            return  # already exited
        self._log.info(
            f"side={st.side} terminating subprocess pid={proc.pid}")
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except Exception as e:
            self._log.warning(f"SIGTERM failed for pid={proc.pid}: {e}")
        # Give it a beat to exit cleanly.
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self._log.warning(
                f"subprocess pid={proc.pid} did not exit in 3s — leaving to OS reaper")
