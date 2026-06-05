"""MenuPublisher — backend half of the TUI menu mirror protocol.

Publishes retained `gwent/menu/present/{menu_id}` messages so any client
(currently only the TUI; the MFD/rotary can mirror later) sees the current
menu without a request roundtrip. Subscribes to `gwent/menu/choose` and
dispatches selections to the right Controller action.

This is parallel to (not replacing) the existing `gwent/mfd/*` family which
the rotary/OLED still uses. Both channels can carry the same menus.

Menu inventory (Phase 2 ships the first; Phases 3-4 fill in the rest):

  main          server-idle main menu (random + fresh)
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
import gwent.messaging.factory
import gwent.messaging.menu
import gwent.messaging.game_start
from gwent.game import (
    CH_MENU_CHOOSE,
    CH_GAME_START,
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
        # CameraClient — used by the in-game-menu reset path to stop+discard
        # an in-flight recording. Wired by gwent.game.main.create_components().
        self.camera_client = None
        # Startup-wizard pending selection (P1 human side + P2 AI side).
        # Rolled whenever we (re)enter the main menu; the TUI renders it as
        # the full-screen new-game screen and re-rolls/starts via menu/choose.
        self._wizard: dict | None = None
        # Full per-side decks (raw card dicts incl. leader) backing the wizard
        # summary. Built independently per side on re-roll; START uses them
        # directly (no re-derivation from ownership / a file).
        self._wizard_decks: dict = {"p1": [], "p2": []}

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
        # Client-initiated game start (New Game wizard sends both decks here).
        self.subscribe(
            CH_GAME_START,
            gwent.messaging.game_start.KIND,
            self._on_game_start,
        )
        self._log.info("MenuPublisher initialized")

    def _on_game_start(self, message: "gwent.messaging.game_start.Message"):
        """Deal a game from two client-proposed decks (faction/leader/cards
        chosen on the TUI's New Game screen).

        Controllers are NOT part of this message anymore — they live on the
        retained `gwent/players/controller/PLAYER.*` topics and are assigned
        via the assign-pN menus, so whatever the player picked on the New
        Game screen (or mid-game) stays in effect. A `controller` field is
        still honoured when explicitly present (back-compat).
        """
        p1 = message.p1 or {}
        p2 = message.p2 or {}
        deck1 = gwent.game.decks.messages_from_dicts(p1.get("deck") or [])
        deck2 = gwent.game.decks.messages_from_dicts(p2.get("deck") or [])
        c1 = p1.get("controller")
        c2 = p2.get("controller")
        self._log.info(
            f"game_start: P1 ctrl={c1!r} deck={len(deck1)}  "
            f"P2 ctrl={c2!r} deck={len(deck2)}")
        if not deck1 or not deck2:
            self._log.error("game_start with empty deck(s) — ignoring")
            return
        # Assign controllers ONLY when explicitly carried in the message;
        # otherwise the retained controller topic assignments stand.
        if self.llm_player_manager is not None:
            try:
                if c1 is not None:
                    self.llm_player_manager.assign("P1", c1)
                if c2 is not None:
                    self.llm_player_manager.assign("P2", c2)
            except Exception as e:
                self._log.exception(f"game_start assign failed: {e}")
        # Clear menus and deal.
        self.clear_menu(gwent.messaging.menu.MENU_MAIN)
        self.clear_menu(gwent.messaging.menu.MENU_WIZARD)
        try:
            self._controller.start_deal_cards(deck1, deck2)
        except Exception as e:
            self._log.exception(f"game_start start_deal_cards failed: {e}")

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
        """Roll a fresh matchup and publish the New Game wizard to retained
        gwent/menu/present/wizard so the TUI shows it immediately."""
        self.clear_menu(gwent.messaging.menu.MENU_MAIN)
        self.roll_wizard()
        self.publish_wizard()
        self._log.info("publish_main_menu: wizard rolled and published")

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
        # Build each side dynamically: random faction → random image leader →
        # 20 random image units from the card DB. Two distinct factions.
        sides = gwent.game.decks.pick_random_matchup_sides(deck_size=20)
        if sides is None:
            self._log.error("wizard: not enough factions with card art")
            self._wizard["error"] = (
                "Need 2+ factions with card images to start a game.")
            return
        self._wizard.pop("error", None)
        s1, s2 = sides
        self._wizard_decks = {"p1": s1["deck"], "p2": s2["deck"]}
        self._wizard["p1"].update({
            "faction": s1["faction"],
            "controller": "human", "controller_label": "You (RFID / touch)",
            "leader": s1["leader"], "leader_card": s1["leader_card"],
            "strength": s1["strength"], "count": s1["count"],
        })
        self._wizard["p2"].update({
            "faction": s2["faction"],
            "leader": s2["leader"], "leader_card": s2["leader_card"],
            "strength": s2["strength"], "count": s2["count"],
        })
        self._log.info(
            f"wizard rolled sides: P1={s1['faction']} "
            f"(leader={s1['leader']!r} cards={s1['count']} str={s1['strength']})  "
            f"P2={s2['faction']} (leader={s2['leader']!r} cards={s2['count']} "
            f"str={s2['strength']})")

    def _roll_model(self) -> None:
        self._wizard.setdefault("p2", {})
        if self.llm_player_manager is None:
            self._log.warning("wizard: llm_player_manager not wired; no model")
            return
        m = self.llm_player_manager.pick_random_model()
        if not m:
            self._wizard["p2"].update(self._model_fields("human"))
            return
        self._wizard["p2"].update(self._model_fields(m.get("id")))
        self._log.info(f"wizard rolled model: P2={m.get('id')!r}")

    def _model_fields(self, model_id: str) -> dict:
        """Wizard summary fields (controller/label/icon) for a model id."""
        if not model_id or model_id == "human":
            return {"controller": "human",
                    "controller_label": "You (RFID / touch)", "icon": "🃏"}
        models = self.llm_player_manager.models if self.llm_player_manager else []
        for m in models:
            if m.get("id") == model_id:
                return {"controller": model_id,
                        "controller_label": m.get("label", model_id),
                        "icon": m.get("icon", "🤖")}
        return {"controller": model_id, "controller_label": model_id,
                "icon": "🤖"}

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

        if menu_id == gwent.messaging.menu.MENU_IN_GAME:
            self._handle_in_game_choose(choice_id)
        elif menu_id in (gwent.messaging.menu.MENU_ASSIGN_P1,
                         gwent.messaging.menu.MENU_ASSIGN_P2):
            self._handle_assign_choose(menu_id, choice_id)
        else:
            self._log.warning(f"unknown menu_id {menu_id!r} — ignoring")

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
        # Use whatever controllers the wizard currently holds — these reflect
        # both the rolled model AND any change made via the Assign menu.
        c1 = p1.get("controller", "human")
        c2 = p2.get("controller", "human")
        self._log.info(
            f"wizard START P1={f1}/{o1} (ctrl={c1})  P2={f2}/{o2} (ctrl={c2})")

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

        # Assign the chosen controllers. Deferred spawn happens at PlayRound.
        if self.llm_player_manager is not None:
            try:
                self.llm_player_manager.assign("P1", c1)
                self.llm_player_manager.assign("P2", c2)
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
            # A reset game never reaches GameOver's save prompt — stop any
            # in-flight recording and leave it unconfirmed (evictable).
            if self.camera_client is not None:
                rec_id = self.camera_client.finish_recording()
                if rec_id:
                    self.camera_client.discard_recording(rec_id)
            self.clear_menu(gwent.messaging.menu.MENU_IN_GAME)
            self._controller.start_main_menu()
        else:
            self._log.info(f"in-game-menu choice deferred to Phase 4: {choice_id}")

    def _handle_assign_choose(self, menu_id: str, choice_id: str) -> None:
        """assign-p1 / assign-p2 → reassign that side.

        While the New Game wizard is up (game not started), fold the choice into
        the wizard selection and re-render it — START then applies it. Otherwise
        (mid-game) reassign live via the LLMPlayerManager.
        """
        side = "P1" if menu_id == gwent.messaging.menu.MENU_ASSIGN_P1 else "P2"

        if gwent.messaging.menu.MENU_WIZARD in self._published_menus and self._wizard:
            key = "p1" if side == "P1" else "p2"
            self._wizard.setdefault(key, {}).update(self._model_fields(choice_id))
            self._log.info(
                f"wizard {key} controller set via assign menu -> {choice_id!r}")
            self.publish_wizard()
            return

        if self.llm_player_manager is None:
            self._log.error(
                f"assign-{side.lower()} choose received but LLMPlayerManager not wired")
            return
        try:
            self.llm_player_manager.assign(side, choice_id)
        except Exception as e:
            self._log.exception(f"assign({side}, {choice_id}) failed: {e}")
