"""MenuPublisher — backend half of the TUI menu mirror protocol.

Publishes retained `gwent/menu/present/{menu_id}` messages so any client
(currently only the TUI; the MFD/rotary can mirror later) sees the current
menu without a request roundtrip. Subscribes to `gwent/menu/choose` and
dispatches selections to the right Controller action.

This is parallel to (not replacing) the existing `gwent/mfd/*` family which
the rotary/OLED still uses. Both channels can carry the same menus.

Menu inventory (Phase 2 ships the first; Phases 3-4 fill in the rest):

  main          server-idle main menu (recordings + random + fresh)
  assign-p1     P1 controller picker (Phase 3)
  assign-p2     P2 controller picker (Phase 3)
  in-game-menu  reset / step-mode / cancel (Phase 4)

Profuse logging — every publish, subscribe, dispatch, and error is logged
(per feedback_profuse_logging).
"""
from typing import TYPE_CHECKING

import paho.mqtt.client as mqtt

import gwent.game
import gwent.game.decks
import gwent.game.state
import gwent.messaging.factory
import gwent.messaging.menu
from gwent.game import (
    CH_MENU_CHOOSE,
    PubSubComponent,
    ch_menu_present,
)

if TYPE_CHECKING:
    from gwent.game.controller import Controller


class MenuPublisher(PubSubComponent):
    """Owns publishing the menu/* family and dispatching menu/choose events.

    Lifecycle:
        publisher = MenuPublisher(pubsub_client, controller)
        publisher.init()
        publisher.start()
        # ... game runs ...
        publisher.shutdown()
    """

    def __init__(self, pubsub: mqtt.Client, controller: "Controller"):
        super().__init__(pubsub)
        self._controller = controller
        # Track which menus we've published so we know which to clear on reset.
        self._published_menus: set[str] = set()
        # LLMPlayerManager handles assign-pN dispatch + game-loop subprocesses.
        # Wired by gwent.game.main.create_components() after construction.
        self.llm_player_manager = None
        # Startup-wizard pending selection (P1 human side + P2 AI side).
        # Rolled whenever we (re)enter the main menu; the TUI renders it as
        # the full-screen new-game screen and re-rolls/starts via menu/choose.
        self._wizard: dict | None = None

    # ------------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------------

    def init(self):
        super().init()
        self.subscribe(
            CH_MENU_CHOOSE,
            gwent.messaging.menu.KIND,
            self._on_choose,
        )
        self._log.info("MenuPublisher initialized")

    def shutdown(self):
        self._log.info("MenuPublisher shutting down — clearing retained menus")
        try:
            self.clear_all_menus()
        except Exception as e:
            self._log.warning(f"clear_all_menus during shutdown failed: {e}")
        try:
            self.unsubscribe(CH_MENU_CHOOSE)
        except Exception:
            pass
        super().shutdown()

    # ------------------------------------------------------------------------
    # Publish helpers
    # ------------------------------------------------------------------------

    def publish_main_menu(self):
        """Build + publish (retained) the main menu: recordings, random, fresh."""
        choices = []

        # Recordings — list from filesystem, newest-first by filename order
        # (the numeric prefix in the filenames naturally orders them).
        recordings = gwent.game.state.list_recordings()
        for rec in recordings:
            factions = " vs ".join(rec.get("factions") or []) or "?"
            choices.append(gwent.messaging.menu.Choice(
                id=f"rec:{rec['stem']}",
                text=rec["stem"],
                description=factions,
                icon="🎞",
            ))

        # Built-in options
        choices.append(gwent.messaging.menu.Choice(
            id="random", text="Two Random Decks", icon="🎲",
            description="Pick two random factions and start a fresh game",
        ))
        choices.append(gwent.messaging.menu.Choice(
            id="fresh", text="Fresh Game (RFID / touch)", icon="🃏",
            description="Register leaders & decks via scan or touch",
        ))

        msg = gwent.messaging.menu.Message.with_choices(
            menu_id=gwent.messaging.menu.MENU_MAIN,
            choices=choices,
            prompt="Choose a game",
        )
        topic = ch_menu_present(gwent.messaging.menu.MENU_MAIN)
        self.publish(topic, msg, retain=True)
        self._published_menus.add(gwent.messaging.menu.MENU_MAIN)
        self._log.info(
            f"published main menu: {len(recordings)} recordings + random + fresh"
        )

        # Entering the main menu = a fresh new-game suggestion. Roll a random
        # 1-player matchup + AI model and publish the wizard the TUI renders.
        try:
            self.roll_wizard(sides=True, model=True)
            self.publish_wizard()
        except Exception as e:
            self._log.error(f"publish_wizard failed: {e}", exc_info=True)

    # ------------------------------------------------------------------------
    # Startup wizard (1-player: P1 human, P2 AI)
    # ------------------------------------------------------------------------

    def roll_wizard(self, sides: bool = True, model: bool = True) -> None:
        """(Re)roll the wizard's pending matchup and/or P2 model."""
        if self._wizard is None:
            self._wizard = {"p1": {}, "p2": {}}
        self._wizard.setdefault("p1", {})
        self._wizard.setdefault("p2", {})
        if sides:
            self._roll_sides()
        if model:
            self._roll_model()

    def _roll_sides(self) -> None:
        owner_filter = getattr(self._controller, "_owner_filter", None)
        matchup = gwent.game.decks.pick_random_matchup(owner_filter=owner_filter)
        if matchup is None:
            self._log.error("wizard: not enough factions for a matchup")
            self._wizard["error"] = (
                "Need 2+ factions with chipped cards to start a game.")
            return
        self._wizard.pop("error", None)
        (f1, o1), (f2, o2) = matchup
        self._wizard["p1"].update({
            "faction": f1, "owner": o1,
            "controller": "human", "controller_label": "You (RFID / touch)",
        })
        self._wizard["p2"].update({"faction": f2, "owner": o2})
        self._log.info(f"wizard rolled sides: P1={f1}/{o1}  P2={f2}/{o2}")

    def _roll_model(self) -> None:
        self._wizard.setdefault("p2", {})
        if self.llm_player_manager is None:
            self._log.warning("wizard: llm_player_manager not wired; no model")
            return
        m = self.llm_player_manager.pick_random_model()
        if not m:
            self._wizard["p2"].update({
                "controller": "human", "controller_label": "Human", "icon": "🃏"})
            return
        self._wizard["p2"].update({
            "controller": m.get("id"),
            "controller_label": m.get("label", m.get("id")),
            "icon": m.get("icon", "🤖"),
        })
        self._log.info(f"wizard rolled model: P2={m.get('id')!r}")

    def publish_wizard(self) -> None:
        """Publish (retained) the wizard menu the TUI renders full-screen."""
        if self._wizard is None:
            self.roll_wizard()
        choices = [
            gwent.messaging.menu.Choice(
                id="reroll-sides", text="Re-select Sides", icon="🎲"),
            gwent.messaging.menu.Choice(
                id="reroll-model", text="Re-select Model", icon="🤖"),
            gwent.messaging.menu.Choice(id="start", text="START", icon="▶"),
        ]
        msg = gwent.messaging.menu.Message.with_choices(
            menu_id=gwent.messaging.menu.MENU_WIZARD,
            choices=choices,
            prompt="New Game",
            summary=self._wizard,
        )
        topic = ch_menu_present(gwent.messaging.menu.MENU_WIZARD)
        self.publish(topic, msg, retain=True)
        self._published_menus.add(gwent.messaging.menu.MENU_WIZARD)
        self._log.info(f"published wizard menu: {self._wizard}")

    def clear_menu(self, menu_id: str):
        """Publish an empty retained message to clear `menu_id`."""
        topic = ch_menu_present(menu_id)
        # Publish empty payload with retain=True to clear the retained slot.
        self._pubsub.publish(topic, payload="", qos=1, retain=True)
        self._published_menus.discard(menu_id)
        self._log.info(f"cleared menu: {menu_id}")

    def clear_all_menus(self):
        for menu_id in list(self._published_menus):
            self.clear_menu(menu_id)

    # ------------------------------------------------------------------------
    # Inbound — gwent/menu/choose dispatch
    # ------------------------------------------------------------------------

    def _on_choose(self, message: gwent.messaging.menu.Message):
        menu_id = message.menu_id
        choice_id = message.selected_id
        self._log.info(f"received choose menu_id={menu_id!r} id={choice_id!r}")

        if menu_id == gwent.messaging.menu.MENU_MAIN:
            self._handle_main_choose(choice_id)
        elif menu_id == gwent.messaging.menu.MENU_WIZARD:
            self._handle_wizard_choose(choice_id)
        elif menu_id == gwent.messaging.menu.MENU_IN_GAME:
            self._handle_in_game_choose(choice_id)
        elif menu_id in (gwent.messaging.menu.MENU_ASSIGN_P1,
                         gwent.messaging.menu.MENU_ASSIGN_P2):
            self._handle_assign_choose(menu_id, choice_id)
        else:
            self._log.warning(f"unknown menu_id {menu_id!r} — ignoring")

    def _handle_main_choose(self, choice_id: str):
        if not choice_id:
            self._log.warning("main choose with no id")
            return

        # Clear the main menu — we're about to start something.
        self.clear_menu(gwent.messaging.menu.MENU_MAIN)

        if choice_id == "random":
            self._log.info("main -> random decks")
            self._controller.start_game_from_decks()
            return

        if choice_id == "fresh":
            self._log.info("main -> fresh game (register leaders)")
            self._controller.start_register_leaders()
            return

        if choice_id.startswith("rec:"):
            stem = choice_id[4:]
            path = gwent.game.state.get_filepath(stem)
            self._log.info(f"main -> load recording {stem!r} ({path})")
            try:
                gwent.game.state.load(path, self._controller)
            except FileNotFoundError:
                self._log.error(f"recording not found: {path}")
                # Republish so the user can pick again.
                self.publish_main_menu()
            except Exception as e:
                self._log.exception(f"failed to load recording {path}: {e}")
                self.publish_main_menu()
            return

        self._log.warning(f"unknown main choice: {choice_id!r}")
        self.publish_main_menu()

    def _handle_wizard_choose(self, choice_id: str):
        """reroll-sides / reroll-model re-roll & republish; start launches."""
        if choice_id == "reroll-sides":
            self.roll_wizard(sides=True, model=False)
            self.publish_wizard()
        elif choice_id == "reroll-model":
            self.roll_wizard(sides=False, model=True)
            self.publish_wizard()
        elif choice_id == "start":
            self._wizard_start()
        else:
            self._log.warning(f"unknown wizard choice: {choice_id!r}")

    def _wizard_start(self):
        """Start a 1-player game from the wizard's pending selection.

        P1 = human (RFID / touch), P2 = the chosen AI model. The model
        assignment is deferred by LLMPlayerManager until PlayRound, where the
        game-loop subprocess spawns automatically.
        """
        w = self._wizard or {}
        p1 = w.get("p1") or {}
        p2 = w.get("p2") or {}
        if w.get("error") or not p1.get("faction") or not p2.get("faction"):
            self._log.error("wizard start with no valid selection — re-rolling")
            self.roll_wizard()
            self.publish_wizard()
            return

        f1, o1 = p1["faction"], p1["owner"]
        f2, o2 = p2["faction"], p2["owner"]
        model = p2.get("controller", "human")
        self._log.info(
            f"wizard START P1={f1}/{o1} (human)  P2={f2}/{o2} (model={model})")

        # Build the decks BEFORE assigning/clearing so we can bail cleanly.
        try:
            deck1 = gwent.game.decks.build_deck(f1, o1)
            deck2 = gwent.game.decks.build_deck(f2, o2)
        except Exception as e:
            self._log.exception(f"wizard build_deck failed: {e}")
            self.roll_wizard()
            self.publish_wizard()
            return
        if not deck1 or not deck2:
            self._log.error("wizard: empty deck(s) — re-rolling")
            self.roll_wizard()
            self.publish_wizard()
            return

        # Assign controllers (P1 human, P2 the model). Deferred spawn @PlayRound.
        if self.llm_player_manager is not None:
            try:
                self.llm_player_manager.assign("P1", "human")
                self.llm_player_manager.assign("P2", model)
            except Exception as e:
                self._log.exception(f"wizard assign failed: {e}")

        # Clear the menus and kick off the game.
        self.clear_menu(gwent.messaging.menu.MENU_WIZARD)
        self.clear_menu(gwent.messaging.menu.MENU_MAIN)
        self._controller.start_deal_cards(deck1, deck2)

    def _handle_in_game_choose(self, choice_id: str):
        """Phase 4 fills in step-mode toggle; Phase 2 only handles reset."""
        if choice_id == "reset":
            self._log.info("in-game-menu -> reset; returning to main")
            # Tear down any active LLM subprocesses before reset.
            if self.llm_player_manager is not None:
                try:
                    self.llm_player_manager.reset_game()
                except Exception as e:
                    self._log.error(f"reset_game failed: {e}", exc_info=True)
            self.clear_menu(gwent.messaging.menu.MENU_IN_GAME)
            self._controller.start_main_menu()
            self.publish_main_menu()
        else:
            self._log.info(f"in-game-menu choice deferred to Phase 4: {choice_id}")

    def _handle_assign_choose(self, menu_id: str, choice_id: str) -> None:
        """assign-p1 / assign-p2 → tell LLMPlayerManager to reassign that side."""
        side = "P1" if menu_id == gwent.messaging.menu.MENU_ASSIGN_P1 else "P2"
        if self.llm_player_manager is None:
            self._log.error(
                f"assign-{side.lower()} choose received but LLMPlayerManager not wired")
            return
        try:
            self.llm_player_manager.assign(side, choice_id)
        except Exception as e:
            self._log.exception(f"assign({side}, {choice_id}) failed: {e}")
