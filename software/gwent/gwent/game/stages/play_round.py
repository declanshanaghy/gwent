"""PlayRound stage — the core game loop.

Players alternate scanning cards from their hand to place on the board,
or pressing OK to pass. When both players have passed, the round ends.
"""

import random
from typing import Callable, List

import gwent.game
import gwent.game.stages.base
import gwent.game.board
import gwent.messaging.card
import gwent.messaging.ctrl
import gwent.messaging.choice
import gwent.messaging.card_play
import gwent.messaging.mfd

from gwent.game.constants import PLAYER
from gwent.game.board import Board, ROWS


class PlayRound(gwent.game.stages.base.GameStage):
    """Turn-based card play stage."""

    # Internal state machine
    AWAITING_CARD = 'card'
    AWAITING_ROW_CHOICE = 'row_choice'
    AWAITING_MEDIC_CHOICE = 'medic_choice'
    AWAITING_DECOY_CHOICE = 'decoy_choice'
    AWAITING_LEADER_DISCARD = 'leader_discard'
    AWAITING_LEADER_OWN_DISCARD = 'leader_own_discard'
    AWAITING_SPY_DRAW = 'spy_draw'
    AWAITING_LEADER_DISCARD_HAND = 'leader_discard_hand'
    AWAITING_LEADER_DRAW_DECK = 'leader_draw_deck'

    # --- Simple-mode variations (short messages for --simple flag) ---

    _SIMPLE_TURN = [
        "{player}'s turn.",
        "{player}, you're up.",
        "{player} steps forward.",
        "Your move, {player}.",
        "{player}, make your play.",
        "The board awaits {player}.",
    ]

    _SIMPLE_PASS = [
        "{player} passed.",
        "{player} stands down.",
        "{player} yields the field.",
        "{player} holds back.",
        "{player} bides {his} time.",
        "{player} folds {his} arms.",
    ]

    _SIMPLE_PLACEMENT = [
        "{player}: {name} on {row}, strength {strength}.",
        "{player} plays {name}. {row} row, {strength} strength.",
        "{name} enters the {row}. {strength} strength for {player}.",
        "{player} deploys {name} to {row}. {strength} power.",
        "{name} to the {row} for {player}. {strength} strong.",
        "{player} sends {name} into the {row}. Strength {strength}.",
    ]

    _SIMPLE_SPY = [
        "{player}: {name}, spy. Draw 2.",
        "{player} plants {name} as a spy! Drawing 2.",
        "A spy for {player}! {name} infiltrates. {He} draws 2.",
        "{player} sends {name} behind enemy lines. 2 cards drawn.",
        "{name} the double agent! {player} draws 2.",
        "Espionage! {player}'s {name} switches sides. {He} draws 2.",
    ]

    _SIMPLE_CHOOSE_ROW = [
        "Choose row for {name}.",
        "Where does {name} fight? Pick a row.",
        "{name} is agile. Choose a row.",
        "Place {name} — which row?",
        "{name} awaits orders. Select a row.",
        "Assign {name} to a row.",
    ]

    _SIMPLE_SPY_DRAW = [
        "{msg} Scan 2 cards from your deck to draw.",
        "{msg} Pick 2 from your deck.",
        "{msg} Choose 2 deck cards to claim.",
        "{msg} Select 2 cards from your draw pile.",
        "{msg} Your deck awaits. Scan 2 cards.",
        "{msg} Raid your deck for 2 cards.",
    ]

    _SIMPLE_DECOY_PROMPT = [
        "{player}: Decoy! Scan a card on {his} board to return to hand.",
        "{player}: Decoy deployed! Pick a card from {his} board to retrieve.",
        "{player} plays Decoy. Which card comes back to hand?",
        "{player}: Decoy swap! Scan a board card to reclaim.",
        "Decoy in play! {player}, choose a card to pull back.",
        "{player}: tactical retreat! Scan a card to return to {his} hand.",
    ]

    _SIMPLE_NO_DECOY_TARGET = [
        "No non-hero cards on your board to swap with Decoy.",
        "Nothing to swap — no valid targets for Decoy.",
        "Decoy finds no one to replace. No non-hero cards on board.",
        "Your board has no swappable cards for Decoy.",
        "Decoy looks around — no non-hero targets available.",
        "Can't play Decoy. No eligible cards on your board.",
    ]

    _SIMPLE_HERO_DECOY = [
        "Cannot swap a hero card with Decoy.",
        "Heroes refuse the Decoy's call.",
        "A hero cannot be recalled by Decoy.",
        "That's a hero — Decoy won't work on them.",
        "Heroes stand firm. Choose a non-hero card.",
        "Decoy can't touch heroes. Try another card.",
    ]

    _SIMPLE_LEADER_USED = [
        "Leader ability already used this game.",
        "Your leader has already spoken.",
        "That ability was already spent.",
        "The leader's power is exhausted.",
        "Once per game — already used.",
        "Your leader already played {his} part.",
    ]

    _SIMPLE_CHOOSE_ROW_FIRST = [
        "Choose a row from the menu first.",
        "Pick a row before playing.",
        "Select a row from the choices first.",
        "Row selection needed first.",
        "Choose where to place before scanning.",
        "A row must be chosen first.",
    ]

    _SIMPLE_LEADER_WEATHER = [
        "{player}: leader ability. Scan a weather card from {his} deck.",
        "{player}'s leader commands the skies. Scan a weather card.",
        "{player}: invoke the elements! Scan a weather card from deck.",
        "By the leader's will! {player}, scan a weather card.",
        "{player}'s leader stirs the heavens. Choose a weather card.",
        "The leader commands weather! {player}, scan from {his} deck.",
    ]

    _SIMPLE_LEADER_OPP_DISCARD = [
        "{player}: leader ability. Scan a card from opponent's discard to take. {count} available.",
        "{player}'s leader raids the enemy graveyard! {count} cards to plunder. Scan one.",
        "{player}: claim a fallen foe! {count} in opponent's discard. Scan to take.",
        "The leader picks through enemy remains. {count} cards, {player}. Scan one.",
        "{player}'s leader loots the battlefield! {count} enemy cards await. {He} scans to claim.",
        "Enemy discard lies open! {player}, scan one of {count} cards to seize.",
    ]

    _SIMPLE_LEADER_OWN_DISCARD = [
        "{player}: leader ability. Scan a card from {his} discard to restore. {count} available.",
        "{player}'s leader reaches into the grave! {count} cards to resurrect. Scan one.",
        "{player}: reclaim a fallen ally! {count} in {his} discard. Scan to restore.",
        "The leader calls to the dead. {count} cards, {player}. Scan one to revive.",
        "{player}'s leader defies death! {count} cards in discard. {He} scans one.",
        "From the ashes! {player}, scan one of {count} discarded cards to reclaim.",
    ]

    _SIMPLE_LEADER_DISCARD_HAND = [
        "{player}: leader ability. Scan {count} card(s) from {his} hand to discard.",
        "{player}'s leader demands sacrifice! Scan {count} card(s) to discard.",
        "The leader requires tribute. {player}, discard {count} from hand.",
        "{player}: surrender {count} card(s) from {his} hand to the leader's will.",
        "A price must be paid! {player}, scan {count} hand card(s) to discard.",
        "{player}'s leader calls for offerings. Scan {count} from {his} hand.",
    ]

    _SIMPLE_MEDIC_PROMPT = [
        "{player}: {name}, medic. Scan discard. {count} available.",
        "{player}'s {name} arrives as medic! {count} in discard. Scan one.",
        "Medic {name} for {player}! Choose from {count} fallen cards.",
        "{name} the healer! {player}, scan 1 of {count} discarded cards.",
        "{player}: {name} medic deployed. {count} cards to resurrect.",
        "The medic cometh! {player}'s {name} eyes {count} fallen warriors.",
    ]

    _SIMPLE_MEDIC_RESURRECT = [
        "{player}: {resurrected} resurrected.",
        "{resurrected} rises again for {player}!",
        "{player} brings back {resurrected} from the grave!",
        "From death to glory! {resurrected} returns for {player}.",
        "{player}'s medic saves {resurrected}!",
        "{resurrected} cheats death! Back in {player}'s hand.",
    ]
    # NOTE: _SIMPLE_MEDIC_PROMPT, _SIMPLE_MEDIC_EMPTY, _SIMPLE_MUSTER, _SIMPLE_SCORCH,
    # _SIMPLE_DECOY, _SIMPLE_MARDROEME, _SIMPLE_SCORCH_SPECIALTY, _SIMPLE_COMMANDER
    # all accept **pn via their _msg_* callers. Pronoun placeholders are added
    # where natural English calls for gendered language.

    _SIMPLE_MEDIC_EMPTY = [
        "{player}: {name}, medic. No targets.",
        "{player}'s {name} finds no one to save.",
        "The graveyard is bare. {name} finds no targets for {player}.",
        "{name} looks for the fallen — nothing there for {player}.",
        "Empty discard! {player}'s {name} heals the air.",
        "No corpses to revive. {player}'s {name} stands idle.",
    ]

    _SIMPLE_MUSTER = [
        "{player}: {name}, muster. {mustered}.",
        "Muster! {player}'s {name} calls {mustered} to battle!",
        "{name} rallies the troops! {mustered} join {player}'s ranks.",
        "To arms! {player}'s {name} summons {mustered}.",
        "{player} musters {mustered} with {name}!",
        "The horde assembles! {name} brings {mustered} for {player}.",
    ]

    _SIMPLE_SCORCH = [
        "{player}: {name}, scorch. {scorched}.",
        "Flames! {player}'s {name} scorches {scorched}!",
        "{name} burns {scorched} for {player}!",
        "Fire and fury! {player}'s {name} incinerates {scorched}.",
        "{player}'s {name} unleashes scorch on {scorched}!",
        "Burn! {scorched} falls to {player}'s {name}.",
    ]

    _SIMPLE_SCORCH_NO_TARGETS = [
        "{name}, scorch. No targets.",
        "{name} scorches thin air. No targets!",
        "The flames of {name} find nothing to burn.",
        "{name}'s fire fizzles. No valid targets.",
        "Wasted scorch! {name} hits nothing.",
        "{name} breathes fire at an empty field.",
    ]

    _SIMPLE_DECOY = [
        "{player}: Decoy on {row}. {target} returned to hand.",
        "{player} swaps {target} with a Decoy! Back to hand.",
        "Decoy deployed! {player} retrieves {target} from {row}.",
        "{target} recalled by Decoy! {player} gets it back.",
        "Tactical swap! {player}'s Decoy replaces {target} on {row}.",
        "{player} pulls {target} off the {row}. Decoy takes its place.",
    ]

    _SIMPLE_MARDROEME = [
        "{player}: {name}. Weather cleared.",
        "{name} clears the skies for {player}!",
        "Mardroeme! {player}'s {name} banishes the weather.",
        "{player} plays {name}. All weather effects gone!",
        "The storm passes! {player}'s {name} clears the field.",
        "{name} restores clear skies. {player}'s board breathes easy.",
    ]

    _SIMPLE_SCORCH_SPECIALTY = [
        "{player}: {name}, scorch. {scorched}.",
        "{player} unleashes {name}! Scorch destroys {scorched}!",
        "Total annihilation! {name} incinerates {scorched} for {player}.",
        "{name} rains fire! {scorched} consumed for {player}.",
        "Scorch card! {player}'s {name} burns {scorched} to ash.",
        "{player} drops {name}. {scorched} scorched from existence!",
    ]

    _SIMPLE_SCORCH_SPECIALTY_EMPTY = [
        "{player}: {name}, scorch. No targets.",
        "{player}'s {name} scorch fizzles. Nothing to burn!",
        "Wasted card! {player}'s {name} finds no worthy targets.",
        "{name} lands for {player}, but the field is bare.",
        "The great scorch of {name}... burns nothing. {player} shrugs.",
        "No targets for {player}'s {name}. The flames die out.",
    ]

    _SIMPLE_COMMANDER = [
        "{player}: {name}, horn on {row}.",
        "{name} sounds the horn! {row} row doubles for {player}.",
        "Commander's Horn! {player}'s {name} boosts the {row}.",
        "{player} blasts {name} on {row}. Double power!",
        "The horn roars! {player}'s {row} row surges with {name}.",
        "{name} rallies the {row} for {player}! Strength doubled.",
    ]

    @property
    def stage(self):
        return gwent.messaging.ctrl.STAGE_PLAY_ROUND

    def activate(self, complete: Callable, cancel: Callable,
                 deck1, hand1, deck2, hand2, board=None):
        super().activate(complete, cancel)

        self._pending_card = None
        self._pending_weather_cards = None
        self._last_action_summary = None
        self._spy_draws_remaining = 0
        self._leader_discards_remaining = 0
        self._leader_draws_remaining = 0

        if board is None:
            # New game — generate fresh game_id
            from gwent.game.state import new_game_id
            gid = new_game_id()
            self._log.info("New game started, game_id=%s", gid)

            # First round — extract leaders from decks
            leader1 = next((c for c in deck1 if c.is_leader), None)
            leader2 = next((c for c in deck2 if c.is_leader), None)
            self._board = Board(leader1, leader2)

            # Populate hands/decks (exclude leaders from both)
            self._board.hands[PLAYER.ONE] = [c for c in hand1 if not c.is_leader]
            self._board.hands[PLAYER.TWO] = [c for c in hand2 if not c.is_leader]
            self._board.decks[PLAYER.ONE] = [c for c in deck1 if c not in hand1 and not c.is_leader]
            self._board.decks[PLAYER.TWO] = [c for c in deck2 if c not in hand2 and not c.is_leader]

            # Scoai'tel faction check — coin toss for first player
            scoaitel_p1 = self._board.factions[PLAYER.ONE] == "Scoia'tael"
            scoaitel_p2 = self._board.factions[PLAYER.TWO] == "Scoia'tael"
            if scoaitel_p1 or scoaitel_p2:
                self._board.current_player = random.choice([PLAYER.ONE, PLAYER.TWO])
                first_reason = f"Scoia'tael coin toss: {self._player_label(self._board.current_player)} goes first."
            else:
                self._board.current_player = PLAYER.ONE
                first_reason = "Player 1 goes first."
        else:
            self._board = board
            cur = self._board.current_player
            label = self._player_label(cur)
            if self._board.round_number == 1:
                first_reason = None  # Restored game, skip redundant announcement
            else:
                first_reason = f"Round {self._board.round_number}. {label} goes first as round loser."

        # Log cards in each player's hand
        for card in self._board.hands[PLAYER.ONE]:
            self._log.info(f"Player 1 hand: {card.name} (strength={card.strength}, faction={card.faction})")
        for card in self._board.hands[PLAYER.TWO]:
            self._log.info(f"Player 2 hand: {card.name} (strength={card.strength}, faction={card.faction})")

        self._log.info({
            'action': 'play_round_activated',
            'round': self._board.round_number,
            'current_player': str(self._board.current_player),
            'p1_hand': len(self._board.hands[PLAYER.ONE]),
            'p2_hand': len(self._board.hands[PLAYER.TWO]),
            'p1_gems': self._board.players[PLAYER.ONE].gems,
            'p2_gems': self._board.players[PLAYER.TWO].gems,
        })

        if first_reason:
            self._publish_prompt_then(first_reason, self._prompt_turn,
                                      faction=self._current_faction())
        else:
            self._prompt_turn()

    # --- Turn management ---

    def _current_faction(self):
        """Return the current player's faction name, or None."""
        try:
            return self._board.factions[self._board.current_player]
        except (AttributeError, KeyError):
            return None

    # Short nicknames for leader names used in announcements
    _LEADER_NICKNAMES = {
        "Eredin Bréacc Glas: the Treacherous": "Eredin the Treacherous",
        "Eredin: Bringer of Death": "Eredin",
        "Eredin: Commander of the Red Riders": "Eredin",
        "Eredin: Destroyer of Worlds": "Eredin Destroyer",
        "Eredin - King of the Wild Hunt": "Eredin",
        "Emhyr var Emreis: Emperor of Nilfgaard": "Emperor Emhyr",
        "Emhyr var Emreis: Invader of the North": "Emhyr the Invader",
        "Emhyr var Emreis: The White Flame": "The White Flame",
        "Emhyr var Emreis - His Imperial Majesty": "Emhyr",
        "Emhyr var Emreis - The Relentless": "Emhyr the Relentless",
        "Foltest - King of Temeria": "King Foltest",
        "Foltest: Lord Commander of the North": "Lord Commander Foltest",
        "Foltest: Son of Medell": "Foltest",
        "Foltest: the Siegemaster": "Foltest the Siegemaster",
        "Foltest: The Steel-Forged": "Foltest Steel-Forged",
        "Francesca Findabair: Daisy of the Valley": "Francesca Daisy",
        "Francesca Findabair: Hope of the aen Seidhe": "Francesca",
        "Francesca Findabair - Pureblood Elf": "Francesca Pureblood",
        "Francesca Findabair: Queen of Dol Blathanna": "Queen Francesca",
        "Francesca Findabair - The Beautiful": "Francesca the Beautiful",
        "Crach an Craite": "Crach",
    }

    def _player_label(self, player):
        leader = self._board.leaders.get(player)
        if leader:
            name = leader.name if hasattr(leader, 'name') else leader.get('name', '')
            return self._LEADER_NICKNAMES.get(name, name)
        return "Player 1" if player == PLAYER.ONE else "Player 2"

    def _player_pronouns(self, player):
        """Return pronoun format dict for the player's leader."""
        from gwent.game.pronouns import pronoun_forms
        leader = self._board.leaders.get(player)
        if leader:
            p = leader.pronoun if hasattr(leader, 'pronoun') else (
                leader.get('pronoun', '') if hasattr(leader, 'get') else '')
            return pronoun_forms(p)
        return pronoun_forms("")

    def _announce_and_advance(self, prompt):
        """Announce a card play, save as last action summary, then advance turn."""
        self._last_action_summary = prompt
        self._publish_prompt_then(prompt, self._advance_turn,
                                  faction=self._current_faction())

    @property
    def _simple(self):
        return gwent.game.BaseComponent.simple_mode

    # --- Announcement helpers (SRP: one method per announcement type) ---

    def _msg_turn_prompt(self, label, score, opp_score, margin, opp_passed, **pn):
        if self._simple:
            return random.choice(self._SIMPLE_TURN).format(player=label, **pn)
        if opp_passed:
            quips = self._TURN_OPP_PASSED_AHEAD if margin > 0 else self._TURN_OPP_PASSED_BEHIND
        elif margin > 15:
            quips = self._TURN_CRUSHING
        elif margin > 5:
            quips = self._TURN_AHEAD
        elif margin > -5:
            quips = self._TURN_EVEN
        elif margin > -15:
            quips = self._TURN_BEHIND
        else:
            quips = self._TURN_DESPERATE
        return random.choice(quips).format(
            player=label, score=score, opp_score=opp_score, margin=abs(margin), **pn)

    def _msg_pass(self, label, score, opp_score, margin, **pn):
        if self._simple:
            return random.choice(self._SIMPLE_PASS).format(player=label, **pn)
        if margin > 10:
            quips = self._PASS_DOMINATING
        elif margin > 0:
            quips = self._PASS_AHEAD
        elif margin == 0:
            quips = self._PASS_TIED
        elif margin > -10:
            quips = self._PASS_BEHIND
        else:
            quips = self._PASS_DESPERATE
        return random.choice(quips).format(
            player=label, score=score, opp_score=opp_score, margin=abs(margin), **pn)

    def _msg_placement(self, label, name, strength, row, **pn):
        if self._simple:
            return random.choice(self._SIMPLE_PLACEMENT).format(
                player=label, name=name, strength=strength, row=row, **pn)
        row_phrases = self._ROW_PHRASES.get(row, self._CLOSE_PHRASES)
        return random.choice(row_phrases).format(
            player=label, name=name, strength=strength, **pn)

    def _msg_spy(self, label, name, strength, **pn):
        if self._simple:
            return random.choice(self._SIMPLE_SPY).format(
                player=label, name=name, strength=strength, **pn)
        return random.choice(self._SPY_PHRASES).format(
            player=label, name=name, strength=strength, **pn)

    _MEDIC_PROMPT_PHRASES = [
        "{player} deploys {name} the battlefield medic! Scan a card from discard to resurrect. {count} available.",
        "{name} kneels over the fallen! {player}'s medic can save one soul. {count} in the graveyard. Scan to resurrect!",
        "The battlefield surgeon arrives! {player}'s {name} surveys {count} fallen warriors. Scan one to bring back!",
        "Death is not the end! {player}'s {name} reaches into the grave. {He} finds {count} souls awaiting resurrection!",
        "{name} channels forbidden magic! {count} cards in {player}'s discard. {He} must scan one to cheat death!",
        "By blood and sorcery! {player}'s {name} can raise the dead! {count} candidates. {He} must choose wisely!",
    ]

    def _msg_medic_prompt(self, label, name, count, **pn):
        if self._simple:
            return random.choice(self._SIMPLE_MEDIC_PROMPT).format(
                player=label, name=name, count=count, **pn)
        return random.choice(self._MEDIC_PROMPT_PHRASES).format(
            player=label, name=name, count=count, **pn)

    def _msg_medic_resurrect(self, label, resurrected, **pn):
        if self._simple:
            return random.choice(self._SIMPLE_MEDIC_RESURRECT).format(
                player=label, resurrected=resurrected, **pn)
        return random.choice(self._MEDIC_PHRASES).format(
            player=label, name="the medic", resurrected=resurrected, **pn)

    _MEDIC_EMPTY_PHRASES = [
        "{player} deploys {name}, but the graveyard offers no one to save.",
        "{name} searches the fallen for {player}, but death holds tight. No one to resurrect!",
        "The graveyard is empty! {player}'s {name} finds no souls to reclaim.",
        "{name} reaches into the void for {player}, but the dead stay dead. {His} power is wasted this time.",
        "Not a single corpse worth saving! {player}'s {name} stands over an empty graveyard. {He} shakes {his} head.",
        "{player}'s {name} looks for the fallen, but {he} finds the crows have already picked the bones clean.",
    ]

    def _msg_medic_empty(self, label, name, **pn):
        if self._simple:
            return random.choice(self._SIMPLE_MEDIC_EMPTY).format(
                player=label, name=name, **pn)
        return random.choice(self._MEDIC_EMPTY_PHRASES).format(
            player=label, name=name, **pn)

    def _msg_muster(self, label, name, count, mustered, **pn):
        if self._simple:
            return random.choice(self._SIMPLE_MUSTER).format(
                player=label, name=name, count=count, mustered=mustered, **pn)
        return random.choice(self._MUSTER_PHRASES).format(
            player=label, name=name, count=count, mustered=mustered, **pn)

    def _msg_scorch(self, label, name, scorched, **pn):
        if self._simple:
            return random.choice(self._SIMPLE_SCORCH).format(
                player=label, name=name, scorched=scorched, **pn)
        return random.choice(self._SCORCH_ABILITY_PHRASES).format(
            player=label, name=name, scorched=scorched, **pn)

    _SCORCH_NO_TARGET_PHRASES = [
        "{name} breathes fire, but finds no worthy targets!",
        "{name} unleashes flames across an empty field! {His} fire rages, but nothing burns.",
        "The inferno of {name} roars, but the battlefield is barren. Not even a drowner to scorch!",
        "{name} spews dragon fire into the void! {His} display is impressive, but pointless.",
        "Flames erupt from {name}, but {he} finds only empty ground. The Continent shrugs.",
        "{name} scorches nothing but pride! No targets on the field.",
    ]

    def _msg_scorch_no_targets(self, name, **pn):
        if self._simple:
            return random.choice(self._SIMPLE_SCORCH_NO_TARGETS).format(name=name, **pn)
        return random.choice(self._SCORCH_NO_TARGET_PHRASES).format(name=name, **pn)

    def _msg_decoy(self, label, target_name, row, **pn):
        if self._simple:
            return random.choice(self._SIMPLE_DECOY).format(
                player=label, target=target_name, row=row, **pn)
        return random.choice(self._DECOY_PHRASES).format(
            player=label, target=target_name, row=row, **pn)

    def _msg_mardroeme(self, label, name, **pn):
        if self._simple:
            return random.choice(self._SIMPLE_MARDROEME).format(
                player=label, name=name, **pn)
        return random.choice(self._MARDROEME_PHRASES).format(
            player=label, name=name, **pn)

    def _msg_scorch_specialty(self, label, card_name, scorched_names, **pn):
        if self._simple:
            return random.choice(self._SIMPLE_SCORCH_SPECIALTY).format(
                player=label, name=card_name, scorched=scorched_names, **pn)
        return random.choice(self._SCORCH_SPECIALTY_PHRASES).format(
            player=label, name=card_name, scorched=scorched_names, **pn)

    def _msg_scorch_specialty_empty(self, label, card_name, **pn):
        if self._simple:
            return random.choice(self._SIMPLE_SCORCH_SPECIALTY_EMPTY).format(
                player=label, name=card_name, **pn)
        return random.choice(self._SCORCH_SPECIALTY_NO_TARGETS).format(
            player=label, name=card_name, **pn)

    def _msg_commander(self, label, name, faction, row, **pn):
        if self._simple:
            return random.choice(self._SIMPLE_COMMANDER).format(
                player=label, name=name, row=row, **pn)
        return random.choice(self._COMMANDER_PHRASES).format(
            name=name, faction=faction, row=row, **pn)

    def _prompt_turn(self):
        """Prompt the current player to play a card or pass."""
        p1_passed = self._board.players[PLAYER.ONE].passed
        p2_passed = self._board.players[PLAYER.TWO].passed

        if p1_passed and p2_passed:
            self._log.info("Both players passed, completing round")
            self.complete(self._board)
            return

        cur = self._board.current_player
        # Skip if current player already passed
        if self._board.players[cur].passed:
            self._board.current_player = self._board.opponent(cur)
            cur = self._board.current_player

        self._publish_scores()

        label = self._player_label(cur)
        opp = self._board.opponent(cur)
        player_num = "1" if cur == PLAYER.ONE else "2"

        cur_score = self._board.calculate_player_score(cur)
        opp_score = self._board.calculate_player_score(opp)
        margin = cur_score - opp_score
        opp_passed = self._board.players[opp].passed

        pn = self._player_pronouns(cur)
        prompt = self._msg_turn_prompt(label, cur_score, opp_score, margin, opp_passed, **pn)

        self._awaiting = self.AWAITING_CARD
        self.publish_prompt(
            prompt,
            ok=False, cancel=False, clear_choices=True,
            faction=self._current_faction())

        choices = []
        if self._last_action_summary:
            choices.append(
                gwent.messaging.choice.Message.from_properties('h', 'Repeat'))
        choices.append(
            gwent.messaging.choice.Message.from_properties(
                'p', f'Player {player_num} Pass'))
        mfd = gwent.messaging.mfd.Message.with_choices(
            choices, clear_prompt=False)
        self.publish(gwent.game.CH_MFD_PRESENT, mfd)

    def _advance_turn(self):
        """Advance to the next player's turn."""
        cur = self._board.current_player
        self._board.current_player = self._board.opponent(cur)
        self._prompt_turn()

    def _publish_scores(self):
        """Publish updated scores to Player components."""
        cur = self._board.current_player
        for player in (PLAYER.ONE, PLAYER.TWO):
            score = self._board.calculate_player_score(player)
            active = (player == cur)
            msg = gwent.messaging.card_play.Message.with_update_score(str(player), score, active_turn=active)
            topic = gwent.game.make_channel(gwent.game.CH_CARDS_PLAY, str(player))
            self.publish(topic, msg)

    # --- Card processing ---

    def process_card(self, card: gwent.messaging.card.Message):
        super().process_card(card)

        if self._awaiting == self.AWAITING_ROW_CHOICE:
            self.publish_error(random.choice(self._SIMPLE_CHOOSE_ROW_FIRST))
            return
        if self._awaiting == self.AWAITING_MEDIC_CHOICE:
            self._process_medic_scan(card)
            return
        if self._awaiting == self.AWAITING_DECOY_CHOICE:
            self._process_decoy_scan(card)
            return
        if self._awaiting == self.AWAITING_LEADER_DISCARD:
            self._process_leader_discard_scan(card)
            return
        if self._awaiting == self.AWAITING_LEADER_OWN_DISCARD:
            self._process_leader_own_discard_scan(card)
            return
        if self._awaiting == self.AWAITING_SPY_DRAW:
            self._process_spy_draw_scan(card)
            return
        if self._awaiting == self.AWAITING_LEADER_DISCARD_HAND:
            self._process_leader_discard_hand_scan(card)
            return
        if self._awaiting == self.AWAITING_LEADER_DRAW_DECK:
            self._process_leader_draw_deck_scan(card)
            return
        if self._awaiting == 'leader_weather_choice':
            self._process_leader_weather_scan(card)
            return
        if self._awaiting != self.AWAITING_CARD:
            return

        cur = self._board.current_player
        label = self._player_label(cur)

        # Check if it's the player's leader card
        leader = self._board.leaders.get(cur)
        if leader and leader.rfid == card.rfid:
            self._play_leader(leader)
            return

        # Validate card is in current player's hand
        hand_card = self._board.find_in_hand(cur, card.rfid)
        if not hand_card:
            self.publish_error(f"{card.name} is not in {label}'s hand")
            return

        # Route by card type
        if hand_card.is_weather:
            self._play_weather(hand_card)
        elif hand_card.has_specialty and hand_card.specialty == "scorch":
            self._play_scorch_specialty(hand_card)
        elif hand_card.has_specialty and hand_card.specialty == "decoy":
            self._play_decoy(hand_card)
        elif hand_card.has_specialty and hand_card.specialty == "mardroeme":
            self._play_mardroeme(hand_card)
        elif hand_card.has_specialty and hand_card.specialty == "commander":
            self._play_commander_card(hand_card)
        else:
            self._play_unit_card(hand_card)

    _FROST_COMMENTARY = [
        "A bitter frost descends! {affected} cards frozen, {damage} strength lost!",
        "Ice grips the battlefield! {affected} warriors shiver, losing {damage} strength!",
        "The cold bites deep! {affected} units reduced, {damage} strength sapped!",
        "The White Frost reaches out from beyond the Conjunction! {affected} frozen solid, {damage} strength shattered!",
        "Skellige winters have nothing on this! {affected} units encased in ice, {damage} strength lost to the cold!",
        "Even Vesemir's campfire couldn't warm this! {affected} cards frost-bitten, {damage} strength crumbles!",
        "The Wild Hunt rides and winter follows! {affected} warriors feel the chill, {damage} strength drained!",
        "The White Frost spreads across the melee! {affected} warriors frozen solid, {damage} strength shattered like Kaer Morhen's walls!",
        "Biting cold from the Skellige seas! {affected} soldiers lose {damage} strength as ice claims the front line!",
        "Even Witchers shiver! The frost bites {affected} units for {damage} strength. The melee is a frozen wasteland!",
    ]
    _FOG_COMMENTARY = [
        "An impenetrable fog rolls in! {affected} archers blinded, {damage} strength lost!",
        "Visibility drops to nothing! {affected} ranged units lose {damage} strength!",
        "The mist swallows the field! {affected} cards lose their aim, {damage} strength gone!",
        "A fog thick as Velen's swamps! {affected} archers can't see past their bowstrings, {damage} strength wasted!",
        "Even a Witcher's cat eyes couldn't pierce this murk! {affected} ranged units blinded, {damage} strength lost!",
        "The fog rolls in from Oxenfurt way! {affected} units lost in the haze, {damage} strength vanished!",
        "Drowner weather! {affected} cards swallowed by mist, {damage} strength dissolved into nothing!",
        "A fog thick as Velen's swamps! {affected} archers lose their mark, {damage} strength vanished into the mist!",
        "The sorceresses' illusion descends! {affected} ranged units blinded, {damage} strength lost in the haze!",
        "Like the mists of Thanedd Isle! {affected} units can't see a ploughing thing, {damage} strength gone!",
    ]
    _RAIN_COMMENTARY = [
        "Torrential rain pounds the siege! {affected} engines flooded, {damage} strength lost!",
        "The downpour is relentless! {affected} siege units lose {damage} strength!",
        "Rain hammers the war machines! {affected} cards drenched, {damage} strength washed away!",
        "A storm fit for Skellige! {affected} siege engines waterlogged, {damage} strength ruined!",
        "The heavens weep for the fallen! {affected} war machines drenched, {damage} strength washed into the mud!",
        "Not even Dijkstra's coin could buy dry weather! {affected} siege units soaked, {damage} strength lost!",
        "Rain like the Pontar in flood! {affected} cards battered, {damage} strength swept away!",
        "A storm worthy of Skellige! {affected} siege engines drown in the deluge, {damage} strength washed into the mud!",
        "The heavens weep for the losing side! {affected} war machines flooded, {damage} strength lost to the downpour!",
        "Torrents from the mountains! {affected} siege units battered by rain, {damage} strength swept away like drowners in a current!",
    ]
    _CLEAR_COMMENTARY = [
        "The skies clear! Soldiers rally, regaining {recovered} strength!",
        "Sunshine breaks through! {recovered} strength restored across the field!",
        "The storm passes! Forces recover {recovered} total strength!",
        "Triss Merigold smiles from afar! The weather breaks and {recovered} strength returns to the field!",
        "The Lodge of Sorceresses would approve! Skies clear, {recovered} strength surges back!",
        "Like dawn over Kaer Morhen! The clouds part and {recovered} strength is restored!",
        "Toussaint sunshine graces the battlefield! {recovered} total strength recovered!",
        "The mages dispel the storm! Warriors shake off the cold, {recovered} strength surges back!",
        "Clear skies over the battlefield! Like dawn at Kaer Morhen, {recovered} strength returns to the fray!",
        "The weather breaks! Soldiers roar with renewed vigor, {recovered} total strength restored!",
    ]
    _WEATHER_COMMENTARY = {
        "close": _FROST_COMMENTARY,
        "ranged": _FOG_COMMENTARY,
        "siege": _RAIN_COMMENTARY,
    }
    _COMMANDER_PHRASES = [
        "{faction}'s fearless commander {name} sounds the horn! All {row} units double their strength!",
        "The horn of {name} echoes across the {row} line! {faction} warriors fight with renewed fury under {his} command!",
        "{name} rallies the troops! {He} drives {faction}'s {row} combat forces to surge with power!",
        "A mighty blast from {name}'s horn! {faction}'s {row} warriors are inspired to fight harder!",
        "Commander {name} takes the field! The {row} line roars with doubled strength for {faction}!",
        "{name} raises the banner of {faction}! Every {row} soldier fights with the strength of two!",
        "Like Foltest at the siege of Vizima! {name} doubles {faction}'s {row} line!",
        "The horn blast shakes the walls of Novigrad! {name} empowers every {row} warrior for {faction}!",
        "Vesemir taught {him} well! {name} inspires {faction}'s {row} forces to fight like two armies!",
        "A commander worthy of Kaer Morhen! {name} doubles {row} strength for {faction}!",
        "The bards of Oxenfurt will sing of this! {name} rallies {faction}'s {row} line to twice their power!",
        "By the Great Sun! {name} blasts the horn and {faction}'s {row} forces surge with doubled might!",
        "Dandelion strums a war chord! {name} fires up {faction}'s {row} warriors to legendary strength!",
        "The horn of war! {name} inspires {faction}'s {row} forces to fight with the fury of a hundred Witchers!",
        "Like Foltest rallying at Brenna! {name} doubles {faction}'s {row} combat strength with a mighty war cry!",
        "{name} channels the spirit of Kaer Morhen! {His} call drives {faction}'s {row} warriors to surge with doubled might!",
        "A blast that echoes from Novigrad to Nilfgaard! {name} empowers {faction}'s entire {row} line!",
        "The {row} troops roar as {name} raises the banner! {faction}'s forces fight with the strength of the Wild Hunt!",
        "Dandelion would compose a ballad! {name} inspires {faction}'s {row} line to legendary feats of strength!",
    ]
    _NO_IMPACT = [
        "The weather shifts, but no one is affected.",
        "The elements rage, but the battlefield is empty.",
        "Nature's fury finds no targets.",
        "The Continent's weather changes, but the soldiers barely notice.",
        "Geralt would say: medallion's not humming. No effect.",
        "The winds howl across an empty field. Nothing stirs.",
        "Even the Wild Hunt would find nothing to freeze here.",
        "The elements howl, but the battlefield stands empty. Not even a drowner to freeze.",
        "Nature rages against an empty field. Geralt would shrug.",
        "Weather shifts across barren ground. The Continent doesn't care.",
    ]

    # --- Placement commentary by row ---
    # All templates accept: {player}, {name}, {strength}
    _CLOSE_PHRASES = [
        "{player} sends {name} charging into the fray! Strength {strength}.",
        "{name} draws steel and joins the melee for {player}! Strength {strength}.",
        "{name} storms the front line! {strength} points of raw fury for {player}.",
        "Swords clash as {name} enters close combat! Strength {strength} for {player}.",
        "{player} deploys {name} to the vanguard. {strength} strength holds the line!",
        "Blood and steel! {name} wades into the thick of battle for {player}! Strength {strength}.",
        "{name} roars a challenge and charges! {strength} points of close combat carnage for {player}!",
        "The enemy flinches as {name} joins {player}'s front line. {strength} strength, blade raised!",
        "Into the breach! {player} throws {name} at the enemy! {His} warrior brings strength {strength}.",
        "{name} shoulders past the shield wall! {strength} points of melee might for {player}!",
        "School of the Wolf style! {name} cuts through the front line at {strength} for {player}!",
        "Geralt would be proud! {name} enters the melee with {strength} points for {player}!",
        "{name} fights like a cornered fiend! {strength} strength added to {player}'s close combat!",
        "Lambert would call this reckless. {name} charges in at {strength} for {player}!",
        "Like a leshen emerging from the woods! {name} brings {strength} points of terror to {player}'s front line!",
        "{player} plays {name} like a Novigrad fistfight! {strength} points of brutal close combat!",
        "The stench of blood draws {name} to the vanguard! {strength} for {player}, blade singing!",
        "Eskel nods in approval. {name} takes position at {strength} strength for {player}!",
        "Zoltan would buy this fighter a drink! {name} at {strength} strength, brawling for {player}!",
        "A duel worthy of Toussaint's knights! {name} joins {player}'s melee at {strength}!",
        "{name} wields {his} blade like Ciri in a fury! {strength} points of close combat for {player}!",
        "Steel for humans! {name} unsheathes and charges for {player}! Strength {strength}.",
        "Like a wolf among sheep! {name} tears into the melee for {player}! {strength} points of savage fury!",
        "The White Wolf would approve! {name} joins {player}'s vanguard with {strength} points of cold steel!",
        "Medallion's humming! {name} senses blood and joins {player}'s front line! Strength {strength}!",
        "{player} plays {name} like a master! {He} sends {strength} points of close combat expertise onto the field!",
        "The School of the Wolf teaches: strike fast! {name} does exactly that for {player}! {He} brings strength {strength}.",
        "Throats will be cut! {name} storms into the fray with {strength} points of pure aggression for {player}!",
        "By Melitele's grace! {name} wades into battle for {player}, bringing {strength} points of righteous fury!",
        "{name} bellows a challenge across the field! {strength} points of melee devastation for {player}!",
        "The tavern brawl spills onto the battlefield! {name} brings {strength} points of bar-fight fury for {player}!",
    ]
    _RANGED_PHRASES = [
        "{name} takes aim from the ridge! {strength} points of ranged power for {player}.",
        "{player} positions {name} among the archers. Strength {strength}, arrows nocked!",
        "From beyond the treeline, {name} rains down fire! Strength {strength} for {player}.",
        "{name} joins {player}'s ranged line. {strength} strength, eyes on the enemy.",
        "{player} sends {name} to high ground! {strength} points of deadly precision.",
        "A volley of death! {name} draws back and lets fly for {player}! Strength {strength}.",
        "{name} picks {his} target from afar. {strength} points of cold, calculated fury for {player}.",
        "The arrows of {name} darken the sky! {strength} ranged strength for {player}!",
        "{player} stations {name} on the hill. {strength} points of eagle-eyed destruction!",
        "No one is safe from {name}'s reach! {strength} ranged power rains down for {player}!",
        "Trained at Oxenfurt Academy! {name} calculates the perfect shot at {strength} for {player}!",
        "{name} perches like a griffin on the clifftop! {strength} ranged strength for {player}!",
        "Yennefer herself couldn't deflect this! {name} rains {strength} points of ranged fury for {player}!",
        "From the towers of Vizima! {name} takes deadly aim at {strength} strength for {player}!",
        "{player} deploys {name} with the precision of a Scoia'tael ambush! {His} archer brings {strength} ranged power!",
        "The archers of Skellige have nothing on {name}! {strength} points of ranged devastation for {player}!",
        "{name} fires from beyond the fog like a ghost! {strength} strength rains down for {player}!",
        "Steady as a crossbow on a wall! {name} at {strength} ranged strength for {player}!",
        "A shot worthy of the Blue Stripes! {name} brings {strength} points of ranged havoc to {player}'s line!",
        "Triss would call that aim magical! {name} at {strength} ranged power for {player}!",
        "{player} sets {name} on the ridgeline. {He} aims {strength} points, every one at a throat!",
        "Silver for monsters! {name} takes aim for {player}! {strength} points of deadly precision!",
        "From the towers of Oxenfurt! {name} rains judgment for {player}! Strength {strength}!",
        "Like Milva from the treetops! {name} lets fly for {player}! {strength} points of lethal accuracy!",
        "The elves taught precision. {name} proves it for {player}! {strength} ranged strength on target!",
        "{player} positions {name} on the ridge. {His} {strength} points of hawk-eyed destruction await!",
        "Not even a leshen could hide from {name}! {strength} points of ranged fury for {player}!",
        "{name} draws, steadies, fires! {strength} points of ranged power streak across the field for {player}!",
        "The archers of Dol Blathanna would be proud! {name} joins {player}'s ranged line at strength {strength}!",
        "Wind's howling, but {name}'s aim is true! {strength} ranged power for {player}!",
        "{player} unleashes {name} from beyond the treeline! {strength} points rain down like a Skellige hailstorm!",
    ]
    _SIEGE_PHRASES = [
        "{name} rolls onto the battlefield! {strength} siege power for {player}.",
        "{player} deploys {name} behind the walls. Strength {strength}, ready to bombard!",
        "The ground shakes as {name} takes position! {strength} points of siege for {player}.",
        "{name} locks onto enemy fortifications! Strength {strength} for {player}.",
        "{player} unleashes {name}! {strength} points of devastating siege force.",
        "Walls crumble as {name} opens fire! {strength} siege power for {player}!",
        "{name} hurls destruction from afar! {strength} points of earth-shattering siege for {player}!",
        "The war machines roar! {player} deploys {name} with {strength} points of crushing force! {He} means business!",
        "Towers topple! {name} brings {strength} points of siege devastation for {player}!",
        "{player} rolls out the heavy artillery! {He} sets {name} at {strength} siege strength, ready to level everything!",
        "Foltest the Siegemaster would weep with joy! {name} at {strength} siege strength for {player}!",
        "The walls of Vizima couldn't withstand {name}! {strength} points of siege for {player}!",
        "Nilfgaardian engineering at its finest! {name} brings {strength} siege power for {player}!",
        "{name} thunders like a fiend's charge! {strength} points of siege annihilation for {player}!",
        "Dijkstra's gold couldn't buy a better siege weapon! {name} at {strength} for {player}!",
        "The trebuchets of Kaedwen pale in comparison! {name} at {strength} siege strength for {player}!",
        "{player} deploys {name} with a rumble felt in Novigrad! {strength} points of siege!",
        "Emhyr's invasion force had nothing on this! {name} at {strength} siege power for {player}!",
        "Even a griffin couldn't dodge this! {name} rains {strength} points of siege fire for {player}!",
        "The ground cracks beneath {name}! {strength} points of devastating siege for {player}!",
        "{player} positions {name} like the siege of La Valette! {His} {strength} strength brings pure destruction!",
        "Fire the trebuchets! {name} rains devastation for {player}! {strength} siege power!",
        "Like the siege of La Valette Castle! {name} brings {strength} points of wall-shattering force for {player}!",
        "{name} rolls into position, gears grinding! {strength} points of mechanical fury for {player}!",
        "Even Kaer Morhen's walls would crumble! {name} deploys {strength} siege strength for {player}!",
        "The dwarven engineers outdid themselves! {player} unleashes {name} at {strength} siege power!",
        "{player} sets {name} loose! {He} unleashes {strength} points of earth-shaking, bone-rattling siege devastation!",
        "The ground trembles from Novigrad to Vizima! {name} at {strength} siege strength for {player}!",
        "{name} aims at the heart of the enemy! {strength} points of siege power that would make Dijkstra weep for {player}!",
        "Fortifications? What fortifications? {name} brings {strength} points of obliterating siege force for {player}!",
        "A weapon worthy of the Nilfgaardian Empire! {player} deploys {name} at {strength} devastating siege power!",
    ]
    _ROW_PHRASES = {
        "close": _CLOSE_PHRASES,
        "ranged": _RANGED_PHRASES,
        "siege": _SIEGE_PHRASES,
    }

    # --- Spy commentary ---
    # Templates accept: {player}, {name}, {strength}
    _SPY_PHRASES = [
        "A poisoned gift! {player} sends {name} to betray the enemy from within. {strength} points of treachery!",
        "{name} whispers sweet lies and crosses enemy lines. {player} trades {strength} strength for stolen secrets!",
        "The treacherous {name} pledges false loyalty to the enemy. A wolf among sheep for {player}!",
        "{player} plays a dangerous game. {name} feigns surrender, but carries a dagger and a deck of stolen intel!",
        "Betrayal most foul! {name} sells {his} sword to the enemy, but {his} soul belongs to {player}!",
        "Like a serpent in the grass, {name} slithers into enemy ranks. {player} sacrifices {strength} points for the greater scheme!",
        "{name} kneels before the enemy commander, hiding {player}'s knife behind {his} back. Draw 2!",
        "Every court needs its traitor. {name} joins the enemy at strength {strength}, feeding {player} precious intelligence!",
        "The enemy welcomes {name} with open arms. Fools! {player} just bought two cards with {strength} points of deception!",
        "Scheming and skulduggery! {player} deploys {name} as a double agent. The enemy gains {strength}, but at what cost?",
        "Dijkstra would approve! {player} plants {name} behind enemy lines. {strength} strength sacrificed for intelligence!",
        "A spy worthy of Novigrad's underworld! {name} crosses over at {strength} strength. {player} draws fresh cards!",
        "Thaler himself couldn't do it better! {name} infiltrates at {strength} for {player}'s gain!",
        "The Lodge of Sorceresses taught {name} well! {strength} points given, but {player} gains the real prize!",
        "{name} plays both sides like a Toussaint courtier! {strength} to the enemy, two cards to {player}!",
        "Emhyr's spymaster smiles! {player} sends {name} at {strength} strength. Information is the real weapon!",
        "A move straight from Vizima's intelligence service! {name} at {strength} for the enemy, two draws for {player}!",
        "Ploughing brilliant! {player} sacrifices {name} at {strength} strength. The enemy never sees the real play!",
        "Yennefer's favorite trick! {name} at {strength} to the enemy. {player} refills {his} hand!",
        "Cold as a Skellige winter! {player} sends {name} to freeze the enemy with {strength} points of false allegiance!",
        "Every Witcher knows: information kills more than swords. {name} at {strength} for {player}'s intelligence!",
        "Dijkstra taught {name} well! A spy crosses the line for {player}, trading {strength} points for precious intel!",
        "The Redanian Secret Service strikes! {name} infiltrates for {player}! {strength} strength sacrificed for 2 cards!",
        "Trust no one on the Continent! {name} defects with {strength} points, but {player} draws the real prize!",
        "{player} plays the Great Game! {name} sells {his} loyalty for {strength} points. The intelligence is priceless!",
        "A move worthy of Philippa Eilhart! {name} spies for {player}, gifting {strength} but stealing secrets!",
        "{name} kneels before the wrong commander. {player} trades {strength} points for a hand full of possibilities!",
        "The Lodge of Sorceresses would approve! {name} weaves deception for {player}! {strength} points of calculated treachery!",
        "Ploughing brilliant! {player} sends {name} as a double agent! {strength} points lost, 2 cards gained!",
        "Like Thaler in the Temerian underground! {name} crosses enemy lines for {player}! {strength} points of espionage!",
        "The best spies are the ones you welcome! {name} betrays for {player}, carrying {strength} points of false friendship!",
    ]

    # --- Medic commentary ---
    # Templates accept: {player}, {name}, {resurrected}
    _MEDIC_PHRASES = [
        "{name} works dark magic over the fallen! {resurrected} claws back from the grave for {player}!",
        "By blood and sorcery, {name} drags {resurrected} from death's embrace!",
        "{player}'s {name} kneels over the corpse of {resurrected}. A heartbeat returns!",
        "The battlefield surgeon {name} refuses to let death have {resurrected}!",
        "From ashes to fury! {name} resurrects {resurrected}. The enemy won't believe {his} power!",
        "Death is merely an inconvenience! {name} brings {resurrected} back to fight for {player}!",
        "{resurrected} gasps for air as {name} pulls {him} from the abyss. Back in {player}'s hand!",
        "The graveyard surrenders its prize! {name} returns {resurrected} to the land of the living!",
        "Not today, death! {player}'s {name} snatches {resurrected} from the void!",
        "A miracle on the battlefield! {name} breathes life into {resurrected} once more!",
        "Yennefer's necromancy couldn't do it better! {name} brings {resurrected} back for {player}!",
        "The drowners will have to wait! {name} pulls {resurrected} from the grave for {player}!",
        "Keira Metz would be jealous! {name} restores {resurrected} to fight once more!",
        "Like the Conjunction of the Spheres! {name} tears {resurrected} from death itself for {player}!",
        "The School of the Wolf doesn't teach this! {name} resurrects {resurrected}. {player}'s ranks swell!",
        "A trick learned in Oxenfurt's forbidden library! {name} revives {resurrected} for {player}!",
        "Ciri couldn't travel between worlds faster! {name} brings {resurrected} back from the abyss!",
        "The Continent gasps! {name} defies death and {resurrected} rises again for {player}!",
        "Even Eredin fears this magic! {name} returns {resurrected} from the grave for {player}!",
        "Vesemir would call it unnatural. {player} calls it winning. {He} watches as {name} revives {resurrected}!",
        "From the graveyards of Velen! {name} summons {resurrected} back to {player}'s cause!",
        "Triss Merigold couldn't do better! {name} brings {resurrected} screaming back from the void for {player}!",
        "The dead don't stay dead on this field! {name} drags {resurrected} back to fight for {player}!",
        "By the power of Aretuza! {name} resurrects {resurrected}! The enemy stares in disbelief at {player}'s miracle!",
        "What is dead may never die! {name} restores {resurrected} to {player}'s forces from beyond the grave!",
        "{player}'s {name} refuses death's claim! {He} pulls {resurrected} back from the abyss, blade in hand!",
        "The sorceresses weep with joy! {name} pulls {resurrected} from death's cold embrace for {player}!",
        "Necromancy? No, just battlefield medicine! {name} revives {resurrected} for another fight in {player}'s name!",
        "{resurrected} returns from the grave, angrier than a fiend! {name} works wonders for {player}!",
        "Yennefer would be jealous! {player}'s {name} snatches {resurrected} right from death's dinner table!",
        "The graveyard yields its prize! {name} summons {resurrected} back for {player}! The Continent trembles!",
    ]

    # --- Muster commentary ---
    # Templates accept: {player}, {name}, {count}, {mustered}
    _MUSTER_PHRASES = [
        "{name} calls {his} fellow soldiers to battle! {mustered} answer for {player}!",
        "{name} rallies the ranks! {count} comrades rush to {player}'s side: {mustered}!",
        "Brothers in arms! {name} summons {mustered} to fight alongside {player}!",
        "{player}'s {name} lets out a war cry! {count} allies storm the field: {mustered}!",
        "The muster horn sounds! {name} brings {mustered} charging into battle for {player}!",
        "{He} hunts in packs! {name} howls and {mustered} emerge from the shadows for {player}!",
        "The earth trembles as {name} calls the swarm! {mustered} pour onto the field!",
        "Blood calls to blood! {name} summons {count} kin: {mustered}. {player}'s horde grows!",
        "One becomes many! {name} musters {mustered} from every corner of {his} forces!",
        "Where there's one, there's more! {name} brings {count} allies: {mustered}!",
        "Like drowners from a swamp! {name} calls {count} kin and {mustered} surge forth for {player}!",
        "The Wild Hunt assembles! {name} musters {mustered} to {player}'s cause!",
        "Kaer Morhen's gates swing open! {name} brings {count} reinforcements: {mustered}!",
        "A pack of wolves answers {name}'s call! {mustered} join {player}'s ranks!",
        "Skellige war drums pound! {name} summons {count} allies: {mustered} charge in for {player}!",
        "The taverns of Novigrad empty as {name} rallies {mustered} to {player}'s banner!",
        "Fiends travel in herds! {name} musters {count} more: {mustered} for {player}!",
        "The Scoia'tael know: strength in numbers! {name} calls {mustered} for {player}!",
        "Eredin's riders have nothing on this! {name} summons {count} allies: {mustered}!",
        "From every corner of the Continent! {name} musters {mustered} for {player}'s army!",
        "Zoltan would raise a mug to this! {name} rallies {count} fighters: {mustered} for {player}!",
        "The Wild Hunt rides! {name} calls {count} allies for {player}: {mustered}! The horde descends!",
        "From every corner of the Continent! {name} summons {mustered} to {player}'s banner!",
        "Like the fall of Cintra! {name} brings {count} warriors crashing onto the field: {mustered} for {player}!",
        "The pack assembles! {name} howls and {count} brothers answer: {mustered}! {player}'s army swells!",
        "Vesemir taught them to hunt together! {name} musters {mustered} for {player}! {count} strong!",
        "An army unto themselves! {name} summons {count} comrades: {mustered}. {player} floods the battlefield with {his} horde!",
        "The muster horn echoes across the Pontar! {name} calls {mustered} to {player}'s cause!",
        "Where one falls, many rise! {name} brings {count} allies: {mustered}. {player}'s forces multiply!",
        "Like cockroaches! {name} brings {mustered} swarming onto the field for {player}! {count} total!",
        "The drums of war! {name} rallies {count} fighters: {mustered}. {player} commands a legion!",
    ]

    # --- Scorch ability commentary ---
    # Templates accept: {player}, {name}, {scorched}
    _SCORCH_ABILITY_PHRASES = [
        "{name} breathes fire! {scorched} consumed by flames!",
        "Dragon fire erupts from {name}! {scorched} scorched to ashes!",
        "{player}'s {name} unleashes inferno! {scorched} burned from the battlefield!",
        "The flames of {name} spare no one! {scorched} destroyed!",
        "{name} turns the air to fire! {scorched} reduced to cinders!",
        "Burn them all! {name} incinerates {scorched} where they stand!",
        "The stench of charred armor fills the air. {name} has scorched {scorched}!",
        "{name} opens {his} maw and hellfire pours forth! {scorched} is no more!",
        "A pillar of flame erupts! {player}'s {name} annihilates {scorched}!",
        "The battlefield burns! {name} leaves nothing but ash where {scorched} once stood!",
        "Igni sign, Witcher style! {player}'s {name} scorches {scorched} to nothing!",
        "Triss Merigold's fire magic has nothing on {name}! {scorched} incinerated!",
        "The flames of Vilgefortz pale in comparison! {name} destroys {scorched} for {player}!",
        "Like dragon fire over Loc Muinne! {name} reduces {scorched} to cinders!",
        "{name} channels {his} fury like a thousand suns! {scorched} burned from existence for {player}!",
        "Yennefer smells the sulfur from Vengerberg! {name} scorches {scorched}!",
        "Even a leshen's bark would burn! {player}'s {name} annihilates {scorched} in hellfire!",
        "The forges of Mahakam couldn't burn hotter! {name} scorches {scorched}!",
        "Ploughing ashes everywhere! {name} destroys {scorched} for {player}!",
        "A fire fit for the Eternal Fire! {player}'s {name} consumes {scorched} in holy flames!",
        "The continent trembles! {name} scorches {scorched} with dragon-born fury!",
        "Igni! {name} engulfs {scorched} in Witcher fire! Nothing but ash remains for {player}!",
        "Dragon's breath! {name} turns {scorched} to cinders! {player} watches the inferno with satisfaction!",
        "The flames of Mount Carbon! {name} scorches {scorched} from existence!",
        "Like Vilgefortz at Thanedd! {name} unleashes hellfire! {scorched} is incinerated for {player}!",
        "Burn, you filth! {player}'s {name} reduces {scorched} to a pile of smoking armor!",
        "The stench of charred flesh fills the air! {name} has scorched {scorched}! {player} doesn't even flinch — {he} expected nothing less!",
        "A funeral pyre on the battlefield! {name} cremates {scorched} where {he} stands!",
        "Fire and fury! {player}'s {name} turns the air to molten hell! {scorched} is no more!",
        "Not even a higher vampire survives this! {name} annihilates {scorched} with searing flames!",
        "The temperature rises! {name} incinerates {scorched}! {player}'s enemies burn like Novigrad's pyres!",
    ]

    # --- Turn prompt quips by game state ---
    # All templates accept: {player}, {score}, {opp_score}, {margin}
    _TURN_CRUSHING = [  # >15 ahead
        "{player}'s turn. {He}'s trampling the opposition! {score} to {opp_score}.",
        "{player} is on a rampage! Up {margin} points. Can anyone stop {him}?",
        "Total domination from {player}! {score} to {opp_score}. Play on!",
        "{player}'s army is unstoppable! {margin} points ahead, the battlefield belongs to {him}!",
        "The bards will write legends of {player}'s conquest! {score} to {opp_score}!",
        "Like the Wild Hunt itself! {player} devastates at {score} to {opp_score}!",
        "{player} lords over the field! {margin} ahead. Will {he} twist the knife with another card?",
        "Nilfgaard's finest generals couldn't plan a better assault! {player} leads {margin}!",
        "Emhyr himself applauds! {player} crushes at {score} to {opp_score}!",
        "The Continent bows before {player}! {margin} ahead, this is a slaughter!",
        "Ciri could blink away and this would still be a rout! {player} at {score} to {opp_score}!",
        "A massacre worthy of the Battle of Brenna! {player} leads by {margin}!",
        "Eredin's Red Riders couldn't stop {player}! Up {margin} at {score} to {opp_score}!",
        "The White Frost itself couldn't chill {player}'s momentum! {margin} ahead!",
        "Dandelion is already composing the victory ballad! {player} at {score} to {opp_score}!",
        "Even the drowners flee from {player}'s dominance! {margin} points ahead and climbing!",
        "The Continent bows before {player}! {score} to {opp_score}. A massacre worthy of the Wild Hunt!",
        "{player} fights like a Witcher hopped on Thunderbolt! {margin} ahead. Absolute carnage!",
        "Emhyr himself would salute this campaign! {player} crushes all at {score} to {opp_score}!",
        "The bards run out of superlatives! {player} dominates by {margin}. Pure devastation!",
        "{player} is playing Gwent like Geralt fights drowners — effortlessly! {score} to {opp_score}!",
        "A slaughter at the card table! {player} leads by {margin}. Even the Crones are impressed!",
        "Lambert would buy {player} a drink for this! {score} to {opp_score}. Absolutely ploughing brutal!",
        "The Lodge of Sorceresses takes notes! {player}'s {margin}-point lead is the stuff of legend!",
    ]
    _TURN_AHEAD = [  # 5-15 ahead
        "{player}'s turn. Leading {score} to {opp_score}. Keep the pressure on!",
        "The advantage is {player}'s! {margin} ahead. Press the attack?",
        "{player} holds the upper hand at {score}. Can they seal the deal?",
        "{player} smells blood! {margin} points up. Time for {him} to go for the kill!",
        "The tide favors {player}! {score} to {opp_score}. Will they push or hold?",
        "Kaer Morhen trained warriors well. {player} leads by {margin}!",
        "{player}'s forces are gaining ground! {score} to {opp_score}. {He} should play wisely!",
        "The sorceresses of Aretuza nod approvingly. {player} leads by {margin}!",
        "Geralt's medallion hums with confidence! {player} up {margin} at {score} to {opp_score}!",
        "The taverns of Novigrad would bet on {player}! {margin} points ahead!",
        "Triss whispers encouragement! {player} leads {score} to {opp_score}!",
        "Like a griffin circling prey! {player} has the edge at {margin} points ahead!",
        "The School of the Wolf approves! {player} at {score} to {opp_score}. Solid lead!",
        "Foltest's war council couldn't plan better! {player} leads by {margin}!",
        "Zoltan raises a mug! {player} has a comfortable {margin}-point advantage!",
        "{player}'s doing better than Lambert on a good day! {score} to {opp_score}!",
        "Steady as a Witcher's hand! {player} leads {score} to {opp_score}. Keep the blade sharp!",
        "{player} has the wind at {his} back! {margin} ahead. Dandelion scribbles furiously!",
        "The Path favors {player}! Leading by {margin}. Press the advantage like a wolf on the hunt!",
        "Triss would smile at this position! {player} at {score}, opponent at {opp_score}.",
        "{player}'s medallion is humming with confidence! {He}'s {margin} points up and climbing!",
        "Like tracking a griffin — {player} is closing in! {score} to {opp_score}. The kill is near!",
        "The advantage lies with {player}! {margin} ahead. A good hand of Gwent, this!",
        "Zoltan raises his axe in approval! {player} leads {score} to {opp_score}!",
    ]
    _TURN_EVEN = [  # within 5 either way
        "{player}'s turn. It's neck and neck! {score} to {opp_score}.",
        "A tense standoff! {player} at {score}, opponent at {opp_score}. Every card matters!",
        "{player} steps up. The scores are razor thin. {score} to {opp_score}!",
        "This could go either way! {player} at {score}. {He} must choose carefully!",
        "The battlefield trembles in the balance! {player}'s move at {score} to {opp_score}.",
        "Neither side gives an inch! {player} plays at {score} to {opp_score}.",
        "Geralt would call this a true contest! {player} at {score}, deadlocked!",
        "A match worthy of Vizima's finest tavern! {player}'s turn, {he} faces nearly even scores!",
        "Both commanders eye each other across the field. {player} at {score} to {opp_score}.",
        "Tense as a crossbow string! {player}'s move. {score} to {opp_score}!",
        "The winds howl and the scores hold! {player} at {score} to {opp_score}!",
        "Vesemir strokes his beard nervously. {player} at {score}, deadlocked at {opp_score}!",
        "Like two Witchers circling a contract! {player} at {score} to {opp_score}!",
        "The Lodge of Sorceresses watches with bated breath! {player} at {score} to {opp_score}!",
        "Novigrad's bookmakers couldn't call this one! {player} at {score} to {opp_score}!",
        "A round of Gwent this close deserves a round of drinks! {player} at {score} to {opp_score}!",
        "Eskel and Lambert would argue over this match for hours! {player} at {score} to {opp_score}!",
        "The Continent holds its breath! {player} at {score} to {opp_score}!",
        "Tight as a dwarven vault! {player} at {score} to {opp_score}. One card changes everything!",
        "Ciri's Elder Blood couldn't predict this outcome! {player} at {score} to {opp_score}!",
        "Tighter than a crossbow string! {player} at {score}, opponent at {opp_score}. One card changes everything!",
        "The medallion trembles! {player}'s turn at {score} to {opp_score}. This is Gwent at its finest!",
        "Locked in combat like Geralt and a striga! {player} at {score}, dead even. Choose wisely!",
        "The tension in this tavern could kill a man! {player}'s move. {score} to {opp_score}!",
        "A contest worthy of the Passiflora's back room! {player} at {score} to {opp_score}. Who blinks first?",
        "Even Gaunter O'Dimm couldn't predict this! {player}'s turn at {score} to {opp_score}!",
        "The cards haven't been this close since Dijkstra played Thaler! {player} at {score}!",
        "A duel of wits! {player} matches blow for blow at {score} to {opp_score}! {His} next move is critical!",
        "Wind's howling, and so is the crowd! {player}'s turn. {score} to {opp_score}, razor thin!",
        "Like two Witchers circling a contract! {player} at {score}, opponent at {opp_score}. Every card counts!",
    ]
    _TURN_BEHIND = [  # 5-15 behind
        "{player}'s turn. Trailing by {margin}! Can they muster a comeback?",
        "{player} is down {margin} points. Time to dig deep!",
        "The situation looks grim for {player}! {opp_score} to {score}. What's the play?",
        "{player} needs a miracle! Down {margin}. Does {he} have a trick up {his} sleeve?",
        "The enemy presses their advantage! {player} trails {margin}. {He} must fight back!",
        "Even a cornered wolf is dangerous. {player}'s turn, down {margin}!",
        "{player} searches {his} hand desperately. {margin} behind. What can turn this around?",
        "Vesemir would say: never give up! {player} trails by {margin}. Play on!",
        "Geralt's been in worse scrapes! {player} trails {margin} at {score} to {opp_score}!",
        "The Wolf School teaches perseverance! {player} down {margin}, but the game isn't over!",
        "Triss could use a spell right about now! {player} at {score}, behind by {margin}!",
        "Like hunting a griffin without a crossbow! {player} trails by {margin}. Tough odds!",
        "Lambert would start swearing! {player} down {margin} at {score} to {opp_score}!",
        "The crows of Velen watch hungrily! {player} trails by {margin}. Dig deep!",
        "Dijkstra wouldn't bet on these odds! {player} behind {margin} at {score} to {opp_score}!",
        "A Witcher's work is never done! {player} trails {margin}. Time for something clever!",
        "The Path grows darker for {player}! Down {margin}. Time to brew some Swallow!",
        "{player} needs a miracle from Melitele! Trailing {margin} points. Dig deeper!",
        "Like facing a fiend with a broken sword! {player} trails by {margin}. Any tricks left?",
        "Eskel would tell {player} to stay calm. Down {margin}. The comeback starts now!",
        "{player} stares at {his} hand like Geralt at a crossroads. {margin} behind. Which path?",
        "The crowd murmurs. Can {player} claw back from {margin} down? {opp_score} to {score}!",
        "Tougher than a contract on a higher vampire! {player} trails by {margin}. Fight on!",
        "Lambert would say something rude about this position. {player} down {margin}. Prove him wrong!",
    ]
    _TURN_DESPERATE = [  # >15 behind
        "{player}'s turn. It's looking bleak! Down {margin} points. Can {he} claw back?",
        "A massacre on the field! {player} trails {margin}. Is there any hope?",
        "{player} stares down a {margin}-point deficit. Only a Scorch or a miracle can save {him}!",
        "The crows are circling {player}'s army! Down {margin}. This may be the end!",
        "Dandelion winces. {player} is getting destroyed! {opp_score} to {score}!",
        "Even Yennefer's magic couldn't close this gap! {player} down {margin}!",
        "The White Frost cometh for {player}! Trailing by {margin}. Desperate times!",
        "From the ashes? {player} down {margin}. The greatest comebacks start here!",
        "Eredin laughs from across the spheres! {player} down {margin} at {score} to {opp_score}!",
        "The drowners are circling! {player} trails by {margin}. The grave beckons!",
        "Not even Ciri's Elder Blood could fix this! {player} down {margin}!",
        "The fiends of Velen smell weakness! {player} at {score} to {opp_score}. A {margin}-point hole!",
        "Zoltan looks away in disgust! {player} trails {margin}. Pass or pray?",
        "The Battle of Brenna was closer than this! {player} down {margin} at {score} to {opp_score}!",
        "Emhyr would have someone executed for this performance! {player} down {margin}!",
        "The leshens of the forest couldn't care less! {player} trails {margin}. It's grim!",
        "The White Frost closes in on {player}! Down {margin}. Only legends come back from this!",
        "Ploughing hell! {player} trails by {margin}. Even Ciri's Elder Blood couldn't portal out of this!",
        "{player} needs Yennefer's magic AND Triss's luck! Down {margin} points. {He} faces desperate times!",
        "The crows feast early! {player} at {score} against {opp_score}. A funeral dirge plays!",
        "Like Geralt at Stygga Castle! {player} faces impossible odds, down {margin}. Fight or die!",
        "The bookmakers in Novigrad are already paying out! {player} trails {margin}. It would take a miracle!",
        "{player} drowning like a peasant in drowner territory! Down {margin}. Someone throw a lifeline!",
        "Vesemir's ghost whispers: never surrender! {player} down {margin}. One last stand?",
    ]
    _TURN_OPP_PASSED_AHEAD = [  # opponent passed, we're ahead
        "{player}'s turn. The enemy has passed! {score} to {opp_score}. The round is {his} to lose!",
        "The opponent retreats! {player} leads {score} to {opp_score}. Pass or pile on?",
        "With the enemy done, {player} reigns supreme at {score}! More cards, or save them?",
        "The field is {player}'s alone! Opponent passed at {opp_score}. Should {he} conserve or crush?",
        "Victory is assured! {player} at {score}. Every extra card is a waste, or is it insurance?",
        "Geralt would nod and walk away. {player} leads {score} to {opp_score}. Save those cards!",
        "The enemy fled like drowners from Igni! {player} at {score} to {opp_score}. A wise pass?",
        "Like claiming a Witcher contract with the monster already dead! {player} at {score}. Easy win?",
        "Vesemir's first lesson: don't waste resources. {player} leads {score} to {opp_score}. Pass or play?",
        "The tavern crowd cheers! {player} ahead {score} to {opp_score}. Conserve for the next round?",
        "The coward retreats! {player} stands victorious at {score} to {opp_score}. Should {he} save {his} strength or humiliate them?",
        "{player} rules the field! Enemy fled at {opp_score}. With {score} points, why waste another card?",
        "Like a Witcher after the kill! {player} ahead {score} to {opp_score}. Loot the corpse or walk away?",
        "The enemy knows when they're beaten! {player} at {score}. Every extra card played is pure showing off!",
        "The Path is clear for {player}! Leading {score} to {opp_score}. {He} can pass and save, or twist the knife!",
    ]
    _TURN_OPP_PASSED_BEHIND = [  # opponent passed, we're behind
        "{player}'s turn. The enemy passed at {opp_score}! Down {margin}. Time to catch up!",
        "The opponent bows out at {opp_score}! {player} trails by {margin}. The comeback is on!",
        "A chance to strike! Opponent passed. {player} needs {margin} more points to win!",
        "The enemy thinks they've won at {opp_score}! {player} at {score}. {He} must prove them wrong!",
        "No more interference! Opponent passed. {player} needs to close a {margin}-point gap!",
        "A Witcher never quits! {player} at {score}, needs {margin} more! The opponent rests at {opp_score}!",
        "Geralt didn't defeat the Wild Hunt by giving up! {player} trails {margin}. Fight on!",
        "The path is clear but steep! {player} needs {margin} points to overtake {opp_score}!",
        "Ciri would blink right past this deficit! {player} down {margin}. Cards in hand, hope in heart!",
        "Like climbing the walls of Kaer Morhen! {player} needs {margin} more to beat {opp_score}!",
        "The ploughing nerve of them! Opponent sits smug at {opp_score}. {player} needs {margin} to win. Time for {him} to hunt!",
        "A Witcher never quits the hunt! {player} trails by {margin}. The prey thinks it's safe. It's not.",
        "The opponent made their bed at {opp_score}! {player} at {score}. Time to burn that bed down!",
        "Like Geralt chasing the Wild Hunt! {player} down {margin}. No interference, just {him} vs the score!",
        "The tavern holds its breath! {player} needs {margin} points with no opposition. Can they find them?",
    ]

    # --- Pass quips by game state ---
    # All templates accept: {player}, {score}, {opp_score}, {margin}
    _PASS_DOMINATING = [
        "{player} passes with supreme confidence! {score} to {opp_score}. A lead of {margin}!",
        "{player} leans back and smirks. {margin} points ahead. {He} knows this round is all but won.",
        "With a {margin}-point cushion, {player} has nothing to prove. {He} passes!",
        "{player} raises a tankard. {score} to {opp_score}? That'll do nicely.",
        "Emhyr would approve of this efficiency! {player} passes at {score}, up {margin}!",
        "{player} passes like Geralt walking away from a dead monster. {margin} ahead. Done.",
        "The bards of Oxenfurt already know the winner! {player} at {score} to {opp_score}. Pass!",
        "Dijkstra counts his coin. {player} passes with {margin} to spare. A profitable round!",
        "Another Gwent victory in the bag! {player} passes at {score} to {opp_score}. {margin} points of pure dominance!",
        "{player} tosses {his} cards down and orders another ale. {margin} ahead. This round was never in doubt.",
        "Like Emhyr accepting a surrender! {player} passes with {margin} points to spare. Glorious!",
        "The whole tavern knows it's over! {player} passes at {score}. {margin} points ahead. Legendary!",
    ]
    _PASS_AHEAD = [
        "{player} passes, holding a slim lead. {score} to {opp_score}.",
        "A calculated pass from {player}. {margin} points ahead, but is it enough?",
        "{player} holds steady at {score}. {His} lead is narrow but {his} nerve is steel.",
        "Dandelion would call this bold. {player} passes with just {margin} points to spare!",
        "A Witcher's instinct! {player} passes at {score} to {opp_score}. Trust the lead!",
        "Triss raises an eyebrow. {player} passes with a slim {margin}-point edge. Risky!",
        "Like Vesemir saving potions for the next fight! {player} passes at {score} to {opp_score}.",
        "Skellige warriors respect the gamble! {player} holds at {score}, {margin} ahead!",
        "A Witcher knows when to sheathe the blade! {player} passes at {score}, {margin} ahead.",
        "Calculated like Dijkstra's spy network! {player} holds at {score} to {opp_score}. Will it hold?",
        "The gambler's instinct! {player} passes with {margin} to spare. {He} trusts {his} lead. Geralt would nod approvingly.",
        "{player} reads the board like a Witcher reads tracks. {He} passes at {score} to {opp_score}. Slim but sufficient!",
    ]
    _PASS_TIED = [
        "{player} passes on a knife's edge! {score} to {opp_score}. Dead even!",
        "All square at {score}! {player} blinks first and passes. {His} gambler's instinct takes over!",
        "{player} passes at {score} all. This could go either way!",
        "The scores are locked at {score}. {player} passes and holds {his} breath!",
        "Tied like two Witchers arm-wrestling! {player} passes at {score} to {opp_score}!",
        "Geralt would call it a draw and walk to the tavern. {player} passes at {score} all!",
        "Novigrad's gamblers gasp! {player} passes at a tied {score} to {opp_score}!",
        "The Continent's boldest bluff! {player} passes dead even at {score}!",
        "Balls of steel! {player} passes at a dead heat! {score} to {opp_score}. This takes nerve!",
        "A coinflip at the Passiflora! {player} passes at {score} all. Fortune favors the bold!",
        "Locked at {score}! {player} throws down the gauntlet. {He} lets fate decide this round!",
        "Like two Witchers arm-wrestling! {player} passes at {score} to {opp_score}. Nobody blinks!",
    ]
    _PASS_BEHIND = [
        "{player} passes, trailing by {margin}. A bluff, or out of options?",
        "Down {margin} points, {player} throws in the towel. {opp_score} to {score}.",
        "{player} concedes the ground. {margin} behind, {he} knows sometimes discretion is the better part of valor.",
        "A tactical retreat! {player} passes at {score}, hoping {his} opponent overextends.",
        "Like retreating from a leshen's grove! {player} passes down {margin}. Live to fight another round!",
        "Vesemir would call it wisdom. {player} saves cards, down {margin} at {score} to {opp_score}.",
        "The Scoia'tael know when to fade into the forest! {player} passes at {score}, down {margin}.",
        "A strategic withdrawal worthy of Kaer Morhen! {player} passes at {score} to {opp_score}.",
        "A tactical withdrawal! {player} yields at {score} to {opp_score}. Live to fight another round!",
        "Like retreating from a higher vampire! {player} passes, down {margin}. Save the silver for later!",
        "{player} swallows {his} pride. {margin} behind at {opp_score} to {score}. The war isn't over.",
        "Discretion over valor! {player} falls back at {score}. {margin} points behind, but cards in reserve!",
    ]
    _PASS_DESPERATE = [
        "{player} passes in desperation! Down {margin} points. The round looks lost.",
        "Mercy! {player} waves the white flag. {opp_score} to {score} is too much to overcome.",
        "{player} cuts {his} losses. {margin} points behind. Save the cards for next round!",
        "Even Geralt couldn't save {player} now. Down {margin}, {he} passes and prays.",
        "The White Frost takes this round! {player} surrenders at {score} to {opp_score}.",
        "Dandelion plays a mournful tune. {player} passes, down {margin}. A dark chapter!",
        "Even Yennefer's portals can't escape this loss! {player} passes at {score} to {opp_score}.",
        "The drowners feast tonight! {player} concedes at {margin} behind. Save what you can!",
        "The white flag rises over {player}'s army! Down {margin}. Not even Ciri could save this round!",
        "{player} throws in the towel like a boxer at Novigrad's arena! {opp_score} to {score}. Brutal.",
        "A mercy killing! {player} ends {his} suffering at {score}. Down {margin}, the cards have spoken.",
        "Like fleeing the Wild Hunt! {player} passes in desperation. {margin} points too far gone at {opp_score} to {score}!",
    ]

    # --- Scorch specialty (card) phrases ---
    # Templates accept: {player}, {name}, {scorched}
    _SCORCH_SPECIALTY_PHRASES = [
        "{player}: place {name} on discard. Scorched: {scorched}",
        "{player} plays {name}! The flames consume {scorched}!",
        "Fire rains down! {player}'s {name} scorches {scorched} to ashes! {He} shows no mercy!",
        "{player} unleashes {name}! {scorched} burned from the field!",
        "Igni! {player}'s {name} incinerates {scorched}!",
        "The Eternal Fire claims its due! {player}'s {name} destroys {scorched}!",
        "{player} drops {name} like Vilgefortz dropped {his} enemies! {scorched} scorched!",
        "By the flames of Loc Muinne! {player}'s {name} burns {scorched} to nothing! {His} flames spare no one!",
    ]

    # Templates accept: {player}, {name}
    _SCORCH_SPECIALTY_NO_TARGETS = [
        "{player}: place {name} on discard. No targets.",
        "{player}'s {name} finds nothing to burn. The field stands empty.",
        "{player} plays {name}, but {his} flames find no worthy prey!",
        "The fire fizzles! {player}'s {name} scorches nothing but air! {His} frustration is palpable.",
        "{player}'s {name} roars, but even drowners know to hide. No targets!",
        "Wasted flames! {player}'s {name} finds no one standing tall enough to burn! {He} scowls in frustration.",
    ]

    # --- Decoy phrases ---
    # Templates accept: {player}, {row}, {target}
    _DECOY_PHRASES = [
        "{player}: place Decoy on {row}. {target} returned to hand.",
        "{player} pulls off the old switcheroo! {target} slips back to hand from {row}!",
        "A classic Novigrad con! {player} swaps Decoy for {target} on {row}!",
        "Now you see them, now you don't! {player} recalls {target} from {row} back to {his} hand!",
        "Dijkstra taught {player} well! Decoy replaces {target} on {row}!",
        "{player} plays the shell game! {target} vanishes from {row} back to {his} hand!",
        "Misdirection worthy of Dandelion! {player}'s Decoy replaces {target} on {row}!",
        "The old bait and switch! {player} pulls {target} back from {row} into {his} hand!",
    ]

    # --- Mardroeme phrases ---
    # Templates accept: {player}, {name}
    _MARDROEME_PHRASES = [
        "{player}: place {name} on discard. Weather cleared!",
        "{player} plays {name}! The skies clear like dawn over Toussaint!",
        "Mardroeme magic! {player}'s {name} banishes all weather from the field! {His} power is undeniable!",
        "Like Keira Metz lifting a curse! {player}'s {name} clears the weather!",
        "{player} drops {name} and the storms retreat! {He} watches as the Continent breathes easy!",
        "The Lodge would approve! {player}'s {name} sweeps the weather clean!",
        "Clear skies by sorcery! {player} plays {name} and the elements obey {his} command!",
    ]

    # --- Leader ability phrases ---
    # Each key maps to a list of templates for that ability
    _LEADER_PHRASES = {
        "reshuffle_graveyards": [
            "{player}: leader ability. All graveyards reshuffled into decks.",
            "{player} invokes the ancient rite! {He} commands all discard piles to return to the decks!",
            "The dead march again! {player}'s leader reshuffles all graveyards into decks!",
            "Like the Conjunction of the Spheres! {player} reshuffles all discards back to the decks!",
            "{player}'s leader commands: rise from the graveyard! All discard piles reshuffled at {his} word!",
            "Kaer Morhen's deepest secret! {player} restores all graveyards to the living decks!",
        ],
        "clear_weather": [
            "{player}: leader ability. All weather effects cleared!",
            "{player}'s leader parts the clouds! All weather effects vanish!",
            "By royal decree! {player}'s leader clears every storm from the battlefield!",
            "The skies obey {player}'s command! All weather cleared!",
            "{player}'s leader waves a hand and the Continent's weather bends to {his} will!",
            "Triss herself couldn't clear the skies faster! {player}'s leader banishes all weather!",
        ],
        "clear_weather_none": [
            "{player}: leader ability. No weather to clear.",
            "{player}'s leader looks to clear skies. Nothing to do here!",
            "The skies are already bright! {player}'s leader ability finds no weather to clear.",
            "{player}'s leader scans the horizon. Not a cloud in sight!",
        ],
        "spy_doubling": [
            "{player}: leader ability. All spy cards now have doubled strength!",
            "{player}'s spymaster doubles down! All spies on the field surge with power!",
            "Emhyr's intelligence network at full strength! {player} doubles all spy power!",
            "The shadows grow darker! {player}'s leader doubles every spy's strength at {his} command!",
            "Dijkstra would kill for this! {player}'s leader doubles all spy card strength!",
            "Double agents, double trouble! {player}'s leader empowers every spy on the field!",
        ],
        "medic_random": [
            "{player}: leader ability. All medic cards now restore random units!",
            "{player}'s leader decrees: let fate choose the resurrected! {His} medics go random!",
            "The dice of destiny! {player}'s leader makes all medic restores random!",
            "Chaos magic! {player}'s leader ability randomizes all medic resurrections!",
            "Even Geralt can't predict who returns! {player}'s leader randomizes medic picks!",
        ],
        "cancel_leader": [
            "{player}: leader ability. {target}'s ability has been cancelled!",
            "{player} strikes first! {He} neutralizes {target}'s leader power!",
            "A pre-emptive strike! {player} cancels {target}'s leader ability!",
            "No tricks for you! {player} shuts down {target}'s leader power!",
            "The Lodge of Sorceresses intervenes! {player} cancels {target}'s ability!",
            "Like Geralt's Axii sign! {player} nullifies {target}'s leader!",
        ],
        "cancel_leader_already_used": [
            "{player}: leader ability. {target}'s ability was already used!",
            "{player} tries to cancel, but {target}'s leader already played {his} hand!",
            "Too late! {target}'s ability was already used. {player}'s cancel fizzles!",
            "The horse has bolted! {player} can't cancel what {target} already used!",
        ],
        "half_weather_penalty": [
            "{player}: leader ability. Units now lose only half strength in weather!",
            "{player}'s warriors shrug off the storm! Weather penalties halved!",
            "Skellige blood runs thick! {player}'s units resist the weather's bite!",
            "The Isles breed hardy folk! {player}'s leader halves all weather penalties!",
            "King Bran's decree! {player}'s units only lose half strength in bad weather!",
            "Storm-born warriors! {player}'s leader shields {his} army from the worst of it!",
        ],
        "optimize_agile": [
            "{player}: leader ability. Optimized agile units: {moves}!",
            "{player}'s tactical genius shines! {He} repositions agile units: {moves}!",
            "A commander's eye for the battlefield! {player} optimizes: {moves}!",
            "The School of the Wolf teaches adaptability! {player} rearranges: {moves}!",
            "Foltest's war room couldn't plan better! {player} optimizes agile units: {moves}!",
        ],
        "optimize_agile_none": [
            "{player}: leader ability. All agile units already in optimal rows.",
            "{player}'s leader surveys the field. Every unit is already perfectly placed!",
            "No repositioning needed! {player}'s forces are already in peak formation!",
            "{player}'s agile units are sharp as ever. Already optimal!",
        ],
        "view_opponent_hand": [
            "{player}: leader ability. Revealed {count} opponent card(s): {names}!",
            "{player}'s spies report! {He} glimpses {count} enemy cards: {names}!",
            "Intelligence gathered! {player} glimpses {count} of the enemy's cards: {names}!",
            "Dijkstra's network delivers! {player} sees {count} opponent cards: {names}!",
            "{player}'s leader peers behind the curtain! Revealed: {names}!",
        ],
    }

    def _play_weather(self, card):
        """Apply a weather effect."""
        cur = self._board.current_player
        label = self._player_label(cur)

        is_clear = card.is_weather and not card.ranges
        if is_clear:
            # Calculate recovery before clearing
            score_before = sum(
                self._board.calculate_player_score(p)
                for p in (PLAYER.ONE, PLAYER.TWO))
            self._board.weather_rows.clear()
            score_after = sum(
                self._board.calculate_player_score(p)
                for p in (PLAYER.ONE, PLAYER.TWO))
            recovered = score_after - score_before

            self._board.remove_from_hand(cur, card)
            self._board.players[cur].discard.append(card)

            # Publish play_card so the TUI overlay shows the weather card
            row_name = card.ranges[0] if card.ranges else ""
            play_msg = gwent.messaging.card_play.Message.with_play_card(str(cur), card, row_name)
            self.publish(gwent.game.make_channel(gwent.game.CH_CARDS_PLAY, str(cur)), play_msg)

            # Publish weather cleared
            weather_msg = gwent.messaging.card_play.Message.with_weather_change(
                str(cur), list(self._board.weather_rows))
            self.publish(gwent.game.make_channel(gwent.game.CH_CARDS_PLAY, str(cur)), weather_msg)

            if recovered > 0:
                commentary = random.choice(self._CLEAR_COMMENTARY).format(
                    recovered=recovered)
            else:
                commentary = "The skies clear, but nothing changes."

            self._announce_and_advance(
                f"{label}: {card.name}. {commentary}")
        else:
            # Calculate damage before applying
            score_before = sum(
                self._board.calculate_player_score(p)
                for p in (PLAYER.ONE, PLAYER.TWO))

            for row in card.ranges:
                if row in ROWS:
                    self._board.weather_rows.add(row)

            # Publish weather applied
            weather_msg = gwent.messaging.card_play.Message.with_weather_change(
                str(cur), list(self._board.weather_rows))
            self.publish(gwent.game.make_channel(gwent.game.CH_CARDS_PLAY, str(cur)), weather_msg)

            score_after = sum(
                self._board.calculate_player_score(p)
                for p in (PLAYER.ONE, PLAYER.TWO))
            damage = score_before - score_after

            # Count affected non-hero cards in the targeted rows
            affected = 0
            for row in card.ranges:
                if row in ROWS:
                    for p in (PLAYER.ONE, PLAYER.TWO):
                        for c in self._board.players[p].rows[row]:
                            if not (c.has_specialty and c.specialty == "hero"):
                                affected += 1

            self._board.remove_from_hand(cur, card)
            self._board.players[cur].discard.append(card)

            # Publish play_card so the TUI overlay shows the weather card
            row_name = card.ranges[0] if card.ranges else ""
            play_msg = gwent.messaging.card_play.Message.with_play_card(str(cur), card, row_name)
            self.publish(gwent.game.make_channel(gwent.game.CH_CARDS_PLAY, str(cur)), play_msg)

            # Play weather SFX
            self.publish_effect("weather")

            if damage > 0 and affected > 0:
                row_key = card.ranges[0] if card.ranges else "close"
                templates = self._WEATHER_COMMENTARY.get(
                    row_key, self._FROST_COMMENTARY)
                commentary = random.choice(templates).format(
                    affected=affected, damage=damage)
            else:
                commentary = random.choice(self._NO_IMPACT)

            self._announce_and_advance(
                f"{label}: {card.name}. {commentary}")

    def _play_mardroeme(self, card):
        """Mardroeme: clear weather AND transform all berserker cards on board."""
        cur = self._board.current_player
        label = self._player_label(cur)

        # Clear weather
        had_weather = bool(self._board.weather_rows)
        self._board.weather_rows.clear()

        # Transform berserkers on both players' boards
        from gwent.cards.util import load_card_by_name
        transforms = self._board.transform_berserkers(load_card_by_name)

        # Discard the mardroeme card
        self._board.remove_from_hand(cur, card)
        self._board.players[cur].discard.append(card)

        # Publish transform events and play SFX for each
        if transforms:
            for player, row_name, old, new in transforms:
                transform_msg = gwent.messaging.card_play.Message.with_transform(
                    str(player), old, new, row_name)
                self.publish(gwent.game.make_channel(gwent.game.CH_CARDS_PLAY, str(player)), transform_msg)
                # Play row-appropriate SFX for the transformed card
                _ROW_SFX = {"close": "close", "ranged": "ranged", "siege": "siege"}
                if row_name in _ROW_SFX:
                    self.publish_effect(_ROW_SFX[row_name])

        # Announce
        parts = []
        if had_weather:
            parts.append("Weather cleared")
        if transforms:
            for _, _, old, new in transforms:
                parts.append(f"{old.name} \u2192 {new.name} ({new.strength})")
        if parts:
            self._announce_and_advance(
                f"{label}: Mardroeme! {'. '.join(parts)}.")
        else:
            self._announce_and_advance(
                f"{label}: {card.name}. No weather or berserkers to affect.")

    def _play_decoy(self, card):
        """Start the decoy swap flow. Player scans a card on their board to swap."""
        cur = self._board.current_player
        label = self._player_label(cur)

        # Check if player has any non-hero cards on the board to swap with
        has_target = False
        for row_name in ROWS:
            for c in self._board.players[cur].rows[row_name]:
                if not (c.has_specialty and c.specialty == "hero"):
                    has_target = True
                    break
            if has_target:
                break

        if not has_target:
            self.publish_error(random.choice(self._SIMPLE_NO_DECOY_TARGET))
            return

        self._pending_card = card
        self._awaiting = self.AWAITING_DECOY_CHOICE
        self.publish_prompt(
            random.choice(self._SIMPLE_DECOY_PROMPT).format(player=label),
            ok=False, cancel=False, clear_choices=True,
            faction=self._current_faction())

    def _process_decoy_scan(self, card):
        """Handle a scanned card during decoy swap."""
        cur = self._board.current_player
        label = self._player_label(cur)
        decoy = self._pending_card

        # Find the scanned card on the player's board
        target, row_name = self._board.find_on_board(cur, card.rfid)
        if not target:
            self.publish_error(f"{card.name} is not on {label}'s board")
            return

        if target.has_specialty and target.specialty == "hero":
            self.publish_error(random.choice(self._SIMPLE_HERO_DECOY))
            return

        # Swap: remove target from board, place decoy on that row, return target to hand
        self._board.players[cur].rows[row_name].remove(target)
        self._board.place_card(cur, decoy, row_name)
        self._board.remove_from_hand(cur, decoy)
        self._board.hands[cur].append(target)

        # Publish decoy swap event
        swap_msg = gwent.messaging.card_play.Message.with_decoy_swap(str(cur), decoy, target, row_name)
        self.publish(gwent.game.make_channel(gwent.game.CH_CARDS_PLAY, str(cur)), swap_msg)

        self._pending_card = None
        pn = self._player_pronouns(cur)
        self._announce_and_advance(
            self._msg_decoy(label, target.name, row_name, **pn))

    def _play_scorch_specialty(self, card):
        """Scorch: destroy highest-strength non-hero cards across BOTH players' boards."""
        cur = self._board.current_player
        opp = self._board.opponent(cur)

        # Find the highest strength across all non-hero cards on both boards
        max_strength = 0
        candidates = []  # (player, row_name, card)
        for player in (PLAYER.ONE, PLAYER.TWO):
            for rn in ROWS:
                for c in self._board.players[player].rows[rn]:
                    if c.has_specialty and c.specialty == "hero":
                        continue
                    s = c.strength or 0
                    if s > max_strength:
                        max_strength = s
                        candidates = [(player, rn, c)]
                    elif s == max_strength and s > 0:
                        candidates.append((player, rn, c))

        # Destroy all candidates
        destroyed = []
        for player, rn, c in candidates:
            self._board.players[player].rows[rn].remove(c)
            self._board.players[player].discard.append(c)
            destroyed.append(c)
            # Publish remove_card for each scorched card
            rm_msg = gwent.messaging.card_play.Message.with_remove_card(str(player), c, rn, "scorch")
            self.publish(gwent.game.make_channel(gwent.game.CH_CARDS_PLAY, str(player)), rm_msg)

        self._board.remove_from_hand(cur, card)
        self._board.players[cur].discard.append(card)

        label = self._player_label(cur)
        pn = self._player_pronouns(cur)
        if destroyed:
            names = ", ".join(c.name for c in destroyed)
            self._announce_and_advance(
                self._msg_scorch_specialty(label, card.name, names, **pn))
        else:
            self._announce_and_advance(
                self._msg_scorch_specialty_empty(label, card.name, **pn))

    def _play_commander_card(self, card):
        """Commander's Horn: double a row's strength."""
        cur = self._board.current_player
        # Commander card has ranges — apply horn to those rows
        for row in card.ranges:
            if row in ROWS:
                self._board.commander_horn_rows[cur].add(row)
                # Publish commander horn event
                horn_msg = gwent.messaging.card_play.Message.with_commander_horn(str(cur), row)
                self.publish(gwent.game.make_channel(gwent.game.CH_CARDS_PLAY, str(cur)), horn_msg)
        self._board.remove_from_hand(cur, card)
        self._board.players[cur].discard.append(card)
        self.publish_effect("commander")
        label = self._player_label(cur)
        pn = self._player_pronouns(cur)
        faction = self._board.factions[cur]
        row_str = ', '.join(card.ranges)
        self._announce_and_advance(
            self._msg_commander(label, card.name, faction, row_str, **pn))

    def _play_leader(self, card):
        """Play a leader card ability. Dispatches to specific handler by JSON key."""
        cur = self._board.current_player
        pb = self._board.players[cur]

        if pb.leader_used:
            self.publish_error(random.choice(self._SIMPLE_LEADER_USED))
            return

        # Play leader SFX
        self.publish_effect("leader")

        pb.leader_used = True
        leader_data = card.leader if card.leader else {}

        if leader_data.get("weather_ranges"):
            self._leader_pick_weather(leader_data)
        elif leader_data.get("commander_ranges"):
            self._leader_commander_horn(leader_data)
        elif leader_data.get("draw_opponent_discard"):
            self._leader_draw_opponent_discard()
        elif leader_data.get("reshuffle_graveyards"):
            self._leader_reshuffle_graveyards()
        elif leader_data.get("clear_weather"):
            self._leader_clear_weather()
        elif leader_data.get("draw_own_discard"):
            self._leader_draw_own_discard()
        elif leader_data.get("conditional_scorch"):
            self._leader_conditional_scorch(leader_data)
        elif leader_data.get("spy_doubling"):
            self._leader_spy_doubling()
        elif leader_data.get("discard_and_draw"):
            self._leader_discard_and_draw(leader_data)
        elif leader_data.get("view_opponent_hand"):
            self._leader_view_opponent_hand(leader_data)
        elif leader_data.get("optimize_agile"):
            self._leader_optimize_agile()
        elif leader_data.get("medic_random"):
            self._leader_medic_random()
        elif leader_data.get("extra_draw"):
            self._announce_and_advance(
                f"{self._player_label(cur)}: leader ability already applied at "
                f"battle start (extra card drawn).")
        elif leader_data.get("cancel_leader"):
            self._leader_cancel_leader()
        elif leader_data.get("half_weather_penalty"):
            self._leader_half_weather_penalty()
        else:
            instructions = leader_data.get('instructions', 'No effect')
            self._log.error(f"Unimplemented leader ability for {card.name}: {instructions}")
            self.publish_error(f"Leader ability not implemented: {instructions}")
            pb.leader_used = False
            return

    def _leader_pick_weather(self, leader_data):
        """Leader ability: pick a weather card from deck and play it."""
        cur = self._board.current_player
        label = self._player_label(cur)
        allowed_ranges = set(leader_data["weather_ranges"])

        weather_cards = [
            c for c in self._board.decks[cur]
            if c.is_weather and any(r in allowed_ranges for r in (c.ranges or []))
        ]
        if len(allowed_ranges) == 3:
            weather_cards += [
                c for c in self._board.decks[cur]
                if c.is_weather and not c.ranges
                and c not in weather_cards
            ]

        if not weather_cards:
            self._announce_and_advance(
                f"{label}: leader ability. No weather cards in deck!")
        elif len(weather_cards) == 1:
            wc = weather_cards[0]
            self._board.decks[cur].remove(wc)
            self._play_weather(wc)
        else:
            self._pending_weather_cards = weather_cards
            self._awaiting = 'leader_weather_choice'
            choices = [
                gwent.messaging.choice.Message.from_properties(str(i), wc.name)
                for i, wc in enumerate(weather_cards)
            ]
            mfd = gwent.messaging.mfd.Message.with_choices(choices, clear_prompt=False)
            self.publish(gwent.game.CH_MFD_PRESENT, mfd)
            pn = self._player_pronouns(cur)
            self.publish_prompt(
                random.choice(self._SIMPLE_LEADER_WEATHER).format(player=label, **pn),
                faction=self._current_faction())

    def _process_leader_weather_scan(self, card):
        """Handle scanning a weather card during leader weather pick."""
        cur = self._board.current_player
        label = self._player_label(cur)

        if not card.is_weather:
            self.publish_error(f"{card.name} is not a weather card")
            return

        # Find this card in the pending weather cards list
        cards = getattr(self, '_pending_weather_cards', [])
        match = next((c for c in cards if c.rfid == card.rfid), None)
        if not match:
            # Also check by name in case RFID doesn't match (starter cards)
            match = next((c for c in cards if c.name == card.name), None)
        if not match:
            self.publish_error(f"{card.name} is not available in your deck")
            return

        self._board.decks[cur].remove(match)
        self._awaiting = None
        self._pending_weather_cards = None
        self._play_weather(match)

    def _leader_commander_horn(self, leader_data):
        """Leader ability: apply commander's horn to specified rows."""
        cur = self._board.current_player
        label = self._player_label(cur)
        for row in leader_data["commander_ranges"]:
            self._board.commander_horn_rows[cur].add(row)
        self._announce_and_advance(
            f"{label}: leader ability. Horn on {leader_data['commander_ranges']}.")

    def _leader_draw_opponent_discard(self):
        """Leader ability: draw a card from opponent's discard pile."""
        cur = self._board.current_player
        label = self._player_label(cur)
        opp = self._board.opponent(cur)
        opp_discard = self._board.players[opp].discard

        if opp_discard:
            self._awaiting = self.AWAITING_LEADER_DISCARD
            self.publish_prompt(
                random.choice(self._SIMPLE_LEADER_OPP_DISCARD).format(
                    player=label, count=len(opp_discard), **self._player_pronouns(cur)),
                ok=False, cancel=False, clear_choices=True,
                faction=self._current_faction())
        else:
            self._announce_and_advance(
                f"{label}: leader ability. Opponent's discard pile is empty.")

    def _leader_reshuffle_graveyards(self):
        """Leader ability: shuffle all discard piles back into decks."""
        cur = self._board.current_player
        label = self._player_label(cur)
        for player in (PLAYER.ONE, PLAYER.TWO):
            discard = self._board.players[player].discard
            if discard:
                self._board.decks[player].extend(discard)
                self._board.players[player].discard = []
                random.shuffle(self._board.decks[player])
        if self._simple:
            self._announce_and_advance(
                f"{label}: leader ability. All graveyards reshuffled into decks.")
        else:
            self._announce_and_advance(
                random.choice(self._LEADER_PHRASES["reshuffle_graveyards"]).format(
                    player=label))

    def _leader_clear_weather(self):
        """Leader ability: clear all active weather effects."""
        cur = self._board.current_player
        label = self._player_label(cur)
        had_weather = len(self._board.weather_rows) > 0
        self._board.weather_rows.clear()
        if had_weather:
            if self._simple:
                self._announce_and_advance(
                    f"{label}: leader ability. All weather effects cleared!")
            else:
                self._announce_and_advance(
                    random.choice(self._LEADER_PHRASES["clear_weather"]).format(
                        player=label))
        else:
            if self._simple:
                self._announce_and_advance(
                    f"{label}: leader ability. No weather to clear.")
            else:
                self._announce_and_advance(
                    random.choice(self._LEADER_PHRASES["clear_weather_none"]).format(
                        player=label))

    def _leader_draw_own_discard(self):
        """Leader ability: restore a card from own discard pile to hand."""
        cur = self._board.current_player
        label = self._player_label(cur)
        own_discard = self._board.players[cur].discard
        non_hero = [c for c in own_discard
                    if not (c.has_specialty and c.specialty == "hero")]

        if non_hero:
            self._awaiting = self.AWAITING_LEADER_OWN_DISCARD
            self.publish_prompt(
                random.choice(self._SIMPLE_LEADER_OWN_DISCARD).format(
                    player=label, count=len(non_hero), **self._player_pronouns(cur)),
                ok=False, cancel=False, clear_choices=True,
                faction=self._current_faction())
        else:
            self._announce_and_advance(
                f"{label}: leader ability. Your discard pile is empty.")

    def _process_leader_own_discard_scan(self, card):
        """Handle a scanned card during leader draw-from-own-discard."""
        cur = self._board.current_player
        label = self._player_label(cur)
        own_discard = self._board.players[cur].discard

        drawn = next((c for c in own_discard if c.rfid == card.rfid), None)
        if not drawn:
            self.publish_error(f"{card.name} is not in your discard pile")
            return

        own_discard.remove(drawn)
        self._board.hands[cur].append(drawn)
        self._awaiting = None
        self._announce_and_advance(
            f"{label}: leader ability. {drawn.name} restored to hand!")

    def _leader_conditional_scorch(self, leader_data):
        """Leader ability: destroy enemy's strongest units in a row if total >= threshold."""
        cur = self._board.current_player
        label = self._player_label(cur)
        opp = self._board.opponent(cur)
        scorch_cfg = leader_data["conditional_scorch"]
        row = scorch_cfg["row"]
        threshold = scorch_cfg["threshold"]

        # Sum opponent's non-hero strength in target row
        opp_row = self._board.players[opp].rows[row]
        total_strength = sum(
            c.strength or 0 for c in opp_row
            if not (c.has_specialty and c.specialty == "hero")
        )

        if total_strength < threshold:
            self._announce_and_advance(
                f"{label}: leader ability. Opponent's {row} strength is "
                f"{total_strength}, below {threshold}. No effect.")
            return

        # Find and destroy strongest non-hero in that row
        max_str = 0
        for c in opp_row:
            if c.has_specialty and c.specialty == "hero":
                continue
            s = c.strength or 0
            if s > max_str:
                max_str = s

        destroyed = []
        for c in list(opp_row):
            if c.has_specialty and c.specialty == "hero":
                continue
            if (c.strength or 0) == max_str:
                opp_row.remove(c)
                self._board.players[opp].discard.append(c)
                destroyed.append(c)

        if destroyed:
            names = ", ".join(c.name for c in destroyed)
            self._announce_and_advance(
                f"{label}: leader ability. Opponent's {row} strength was "
                f"{total_strength}. Scorched: {names}!")
        else:
            self._announce_and_advance(
                f"{label}: leader ability. No targets to scorch.")

    def _leader_spy_doubling(self):
        """Leader ability: double the strength of all spy cards (both players)."""
        cur = self._board.current_player
        label = self._player_label(cur)
        self._board.spy_doubling = True
        if self._simple:
            self._announce_and_advance(
                f"{label}: leader ability. All spy cards now have doubled strength!")
        else:
            self._announce_and_advance(
                random.choice(self._LEADER_PHRASES["spy_doubling"]).format(
                    player=label))

    def _leader_discard_and_draw(self, leader_data):
        """Leader ability: discard N cards from hand, then draw M from deck."""
        cur = self._board.current_player
        label = self._player_label(cur)
        cfg = leader_data["discard_and_draw"]
        self._leader_discards_remaining = cfg.get("discard", 2)
        self._leader_draws_remaining = cfg.get("draw", 1)

        hand_size = len(self._board.hands[cur])
        if hand_size < self._leader_discards_remaining:
            self._announce_and_advance(
                f"{label}: leader ability. Not enough cards in hand to discard "
                f"({hand_size} < {self._leader_discards_remaining}). No effect.")
            self._board.players[cur].leader_used = False
            return

        deck_size = len(self._board.decks[cur])
        if deck_size < self._leader_draws_remaining:
            self._announce_and_advance(
                f"{label}: leader ability. Not enough cards in deck to draw "
                f"({deck_size} < {self._leader_draws_remaining}). No effect.")
            self._board.players[cur].leader_used = False
            return

        self._awaiting = self.AWAITING_LEADER_DISCARD_HAND
        self.publish_prompt(
            random.choice(self._SIMPLE_LEADER_DISCARD_HAND).format(
                player=label, count=self._leader_discards_remaining, **self._player_pronouns(cur)),
            ok=False, cancel=False, clear_choices=True,
            faction=self._current_faction())

    def _process_leader_discard_hand_scan(self, card):
        """Handle a scanned card during leader discard-from-hand phase."""
        cur = self._board.current_player
        label = self._player_label(cur)

        hand_card = self._board.find_in_hand(cur, card.rfid)
        if not hand_card:
            self.publish_error(f"{card.name} is not in {label}'s hand")
            return

        self._board.hands[cur].remove(hand_card)
        self._board.players[cur].discard.append(hand_card)
        self._leader_discards_remaining -= 1
        self._log.info(
            f"Leader discard: {hand_card.name} from hand "
            f"({self._leader_discards_remaining} remaining)")

        if self._leader_discards_remaining > 0:
            self.publish_prompt(
                f"{label}: discarded {hand_card.name}. Scan "
                f"{self._leader_discards_remaining} more card(s) to discard.",
                ok=False, cancel=False, clear_choices=True,
                faction=self._current_faction())
        else:
            # Move to draw phase
            self._awaiting = self.AWAITING_LEADER_DRAW_DECK
            self.publish_prompt(
                f"{label}: discarded {hand_card.name}. Now scan "
                f"{self._leader_draws_remaining} card(s) from your deck to draw.",
                ok=False, cancel=False, clear_choices=True,
                faction=self._current_faction())

    def _process_leader_draw_deck_scan(self, card):
        """Handle a scanned card during leader draw-from-deck phase."""
        cur = self._board.current_player
        label = self._player_label(cur)

        deck_card = next(
            (c for c in self._board.decks[cur] if c.rfid == card.rfid), None)
        if not deck_card:
            self.publish_error(f"{card.name} is not in {label}'s deck")
            return

        self._board.decks[cur].remove(deck_card)
        self._board.hands[cur].append(deck_card)
        self._leader_draws_remaining -= 1
        self._log.info(
            f"Leader draw: {deck_card.name} from deck "
            f"({self._leader_draws_remaining} remaining)")

        if self._leader_draws_remaining > 0:
            self.publish_prompt(
                f"{label}: drew {deck_card.name}. Scan "
                f"{self._leader_draws_remaining} more card(s) from your deck.",
                ok=False, cancel=False, clear_choices=True,
                faction=self._current_faction())
        else:
            self._awaiting = None
            self._announce_and_advance(
                f"{label}: leader ability complete. Drew {deck_card.name}!")

    def _leader_view_opponent_hand(self, leader_data):
        """Leader ability: view N random cards from opponent's hand."""
        cur = self._board.current_player
        label = self._player_label(cur)
        opp = self._board.opponent(cur)
        count = leader_data.get("view_opponent_hand", 3)

        opp_hand = self._board.hands[opp]
        if not opp_hand:
            self._announce_and_advance(
                f"{label}: leader ability. Opponent's hand is empty!")
            return

        sample_size = min(count, len(opp_hand))
        revealed = random.sample(opp_hand, sample_size)
        names = ", ".join(c.name for c in revealed)
        self._announce_and_advance(
            f"{label}: leader ability. Revealed {sample_size} opponent card(s): {names}!")

    def _leader_optimize_agile(self):
        """Leader ability: move agile units to their optimal rows."""
        cur = self._board.current_player
        label = self._player_label(cur)
        pb = self._board.players[cur]

        moved = []
        for row_name in ("close", "ranged", "siege"):
            for card in list(pb.rows[row_name]):
                if not (card.has_abilities and "agile" in card.abilities):
                    continue
                if card.has_specialty and card.specialty == "hero":
                    continue
                if not card.ranges or len(card.ranges) < 2:
                    continue

                # Calculate score contribution in each valid row
                best_row = row_name
                best_score = self._board.calculate_row_score(cur, row_name)

                for candidate_row in card.ranges:
                    if candidate_row == row_name:
                        continue
                    # Temporarily move card to candidate row
                    pb.rows[row_name].remove(card)
                    pb.rows[candidate_row].append(card)
                    candidate_score = self._board.calculate_row_score(cur, candidate_row)
                    orig_score = self._board.calculate_row_score(cur, row_name)
                    # Restore
                    pb.rows[candidate_row].remove(card)
                    pb.rows[row_name].append(card)

                    # Compare total contribution (new row score - old row score without card)
                    if candidate_score - orig_score > best_score - self._board.calculate_row_score(cur, row_name):
                        # Simpler: just check if moving increases total player score
                        # Move temporarily and compare total
                        pb.rows[row_name].remove(card)
                        pb.rows[candidate_row].append(card)
                        new_total = self._board.calculate_player_score(cur)
                        pb.rows[candidate_row].remove(card)
                        pb.rows[row_name].append(card)
                        old_total = self._board.calculate_player_score(cur)

                        if new_total > old_total:
                            best_row = candidate_row
                            best_score = new_total

                if best_row != row_name:
                    pb.rows[row_name].remove(card)
                    pb.rows[best_row].append(card)
                    moved.append(f"{card.name} → {best_row}")

        if moved:
            moves_str = ", ".join(moved)
            self._announce_and_advance(
                f"{label}: leader ability. Optimized agile units: {moves_str}!")
        else:
            self._announce_and_advance(
                f"{label}: leader ability. All agile units already in optimal rows.")

    def _leader_medic_random(self):
        """Leader ability: all medic restores pick a random unit (both players)."""
        cur = self._board.current_player
        label = self._player_label(cur)
        self._board.medic_random = True
        if self._simple:
            self._announce_and_advance(
                f"{label}: leader ability. All medic cards now restore random units!")
        else:
            self._announce_and_advance(
                random.choice(self._LEADER_PHRASES["medic_random"]).format(
                    player=label))

    def _leader_cancel_leader(self):
        """Leader ability: cancel opponent's leader ability."""
        cur = self._board.current_player
        label = self._player_label(cur)
        opp = self._board.opponent(cur)
        opp_pb = self._board.players[opp]
        opp_leader = self._board.leaders.get(opp)
        opp_name = opp_leader.name if opp_leader else "opponent's leader"

        if opp_pb.leader_used:
            self._announce_and_advance(
                f"{label}: leader ability. {opp_name}'s ability was already used!")
        else:
            opp_pb.leader_used = True
            self._announce_and_advance(
                f"{label}: leader ability. {opp_name}'s ability has been cancelled!")

    def _leader_half_weather_penalty(self):
        """Leader ability: units only lose half strength in weather conditions."""
        cur = self._board.current_player
        label = self._player_label(cur)
        self._board.half_weather_penalty[cur] = True
        if self._simple:
            self._announce_and_advance(
                f"{label}: leader ability. Units now lose only half strength in weather!")
        else:
            self._announce_and_advance(
                random.choice(self._LEADER_PHRASES["half_weather_penalty"]).format(
                    player=label))

    def _play_unit_card(self, card):
        """Play a normal unit card (with strength)."""
        if card.has_abilities and "agile" in card.abilities and len(card.ranges) > 1:
            # Agile — player chooses row
            self._pending_card = card
            self._awaiting = self.AWAITING_ROW_CHOICE
            choices = []
            for i, row in enumerate(card.ranges):
                choices.append(
                    gwent.messaging.choice.Message.from_properties(str(i), row.capitalize()))
            mfd = gwent.messaging.mfd.Message.with_choices(choices, clear_prompt=False)
            self.publish(gwent.game.CH_MFD_PRESENT, mfd)
            self.publish_prompt(random.choice(self._SIMPLE_CHOOSE_ROW).format(name=card.name),
                               ok=False, cancel=False, clear_choices=False,
                               faction=self._current_faction())
        else:
            # Single range
            row = card.ranges[0] if card.ranges else "close"
            self._place_card_on_row(card, row)

    def _place_card_on_row(self, card, row_name):
        """Place a unit card on the board and process abilities."""
        cur = self._board.current_player
        label = self._player_label(cur)

        # Spy: place on opponent's board
        is_spy = card.has_abilities and "spy" in card.abilities
        target = self._board.opponent(cur) if is_spy else cur

        self._board.place_card(target, card, row_name)
        self._board.remove_from_hand(cur, card)

        # Play row-appropriate battle SFX
        _ROW_SFX = {"close": "close", "ranged": "ranged", "siege": "siege"}
        if row_name in _ROW_SFX:
            self.publish_effect(_ROW_SFX[row_name])

        # Publish play_card event with full card data
        play_msg = gwent.messaging.card_play.Message.with_play_card(
            str(cur), card, row_name,
            target_player=str(target) if is_spy else None)
        topic = gwent.game.make_channel(gwent.game.CH_CARDS_PLAY, str(cur))
        self.publish(topic, play_msg)

        self._log.info({
            'action': 'card_placed',
            'player': str(cur),
            'target': str(target),
            'card': card.name,
            'row': row_name,
            'spy': is_spy,
        })

        # Build placement instruction
        target_label = f"opponent's {row_name}" if is_spy else row_name
        place_msg = f"{label}: place {card.name} on {target_label}"

        # Process abilities
        pn = self._player_pronouns(cur)
        if is_spy:
            deck_size = len(self._board.decks[cur])
            if deck_size == 0:
                # No cards to draw — skip spy draw phase entirely
                msg = self._msg_spy(label, card.name, card.strength or 0, **pn)
                self._announce_and_advance(
                    f"{msg} Deck empty — no cards to draw!")
                return
            self._spy_draws_remaining = min(2, deck_size)
            self._awaiting = self.AWAITING_SPY_DRAW
            msg = self._msg_spy(label, card.name, card.strength or 0, **pn)
            self.publish_prompt(
                random.choice(self._SIMPLE_SPY_DRAW).format(msg=msg),
                ok=False, cancel=False, clear_choices=True,
                faction=self._current_faction())
            return

        if card.has_abilities and "medic" in card.abilities:
            discard = self._board.players[cur].discard
            non_hero = [c for c in discard if not (c.has_specialty and c.specialty == "hero")]
            if non_hero:
                if self._board.medic_random:
                    # Auto-pick random card from discard
                    resurrected = random.choice(non_hero)
                    discard.remove(resurrected)
                    self._board.hands[cur].append(resurrected)
                    self._announce_and_advance(
                        f"{label}: {card.name} medic. Randomly restored "
                        f"{resurrected.name} to hand!")
                    return
                self._awaiting = self.AWAITING_MEDIC_CHOICE
                self.publish_prompt(
                    self._msg_medic_prompt(label, card.name, len(non_hero), **pn),
                    ok=False, cancel=False, clear_choices=True,
                    faction=self._current_faction())
                return
            else:
                self._announce_and_advance(
                    self._msg_medic_empty(label, card.name, **pn))
                return

        if card.has_abilities and "muster" in card.abilities:
            self._process_muster(card, row_name)
            return

        # Scorch ability (not specialty): destroy strongest in opponent's same row
        if card.has_abilities and "scorch" in card.abilities:
            opp = self._board.opponent(cur)
            destroyed = self._board.destroy_strongest(opp, row_name)
            if destroyed:
                for dc in destroyed:
                    rm_msg = gwent.messaging.card_play.Message.with_remove_card(
                        str(opp), dc, row_name, "scorch_ability")
                    self.publish(gwent.game.make_channel(gwent.game.CH_CARDS_PLAY, str(opp)), rm_msg)
                scorched = ", ".join(c.name for c in destroyed)
                self._announce_and_advance(
                    self._msg_scorch(label, card.name, scorched, **pn))
            else:
                self._announce_and_advance(
                    self._msg_scorch_no_targets(card.name, **pn))
            return

        # Commander unit
        if card.has_abilities and "commander" in card.abilities:
            faction = self._board.factions[cur]
            self._announce_and_advance(
                self._msg_commander(label, card.name, faction, row_name, **pn))
            return

        # Normal card
        self._announce_and_advance(
            self._msg_placement(label, card.name, card.strength or 0, row_name, **pn))

    def _process_leader_discard_scan(self, card):
        """Handle a scanned card during leader draw-from-opponent-discard."""
        cur = self._board.current_player
        label = self._player_label(cur)
        opp = self._board.opponent(cur)
        opp_discard = self._board.players[opp].discard

        drawn = next((c for c in opp_discard if c.rfid == card.rfid), None)
        if not drawn:
            self.publish_error(f"{card.name} is not in opponent's discard pile")
            return

        opp_discard.remove(drawn)
        self._board.hands[cur].append(drawn)
        self._announce_and_advance(
            f"{label}: took {drawn.name} from opponent's discard. Return to hand.")

    def _process_spy_draw_scan(self, card):
        """Handle a scanned card during spy draw — must be from player's own deck."""
        cur = self._board.current_player
        label = self._player_label(cur)

        # Card must be in the player's deck
        deck_card = next((c for c in self._board.decks[cur] if c.rfid == card.rfid), None)
        if not deck_card:
            self.publish_error(f"{card.name} is not in {label}'s deck")
            return

        self._board.decks[cur].remove(deck_card)
        self._board.hands[cur].append(deck_card)
        self._spy_draws_remaining -= 1
        self._log.info(f"Spy draw: {deck_card.name} from deck ({self._spy_draws_remaining} remaining)")

        # Publish spy_draw event so TUI can show the card overlay
        spy_msg = gwent.messaging.card_play.Message.with_spy_draw(str(cur), deck_card)
        self.publish(gwent.game.make_channel(gwent.game.CH_CARDS_PLAY, str(cur)), spy_msg)

        if self._spy_draws_remaining > 0:
            self.publish_prompt(
                f"{label}: drew {card.name}. Scan {self._spy_draws_remaining} more card(s) from your deck.",
                ok=False, cancel=False, clear_choices=True,
                faction=self._current_faction())
        else:
            self._awaiting = None
            self._announce_and_advance(
                f"{label}: Spy! Drew {card.name}. Hand restocked.")

    def _process_medic_scan(self, card):
        """Handle a scanned card during medic resurrection."""
        cur = self._board.current_player
        label = self._player_label(cur)
        discard = self._board.players[cur].discard
        non_hero = [c for c in discard if not (c.has_specialty and c.specialty == "hero")]

        # Find the scanned card in the discard pile
        resurrected = next((c for c in non_hero if c.rfid == card.rfid), None)
        if not resurrected:
            # Check if it's a hero (immune to medic)
            is_hero = any(c.rfid == card.rfid and c.has_specialty and c.specialty == "hero"
                         for c in discard)
            if is_hero:
                self.publish_error(f"{card.name} is a Hero. Heroes cannot be resurrected.")
            else:
                self.publish_error(f"{card.name} is not in {label}'s discard pile")
            return

        discard.remove(resurrected)
        self._board.hands[cur].append(resurrected)

        # Publish medic_resurrect event so TUI can show the card overlay
        row = resurrected.ranges[0] if resurrected.ranges else ""
        medic_msg = gwent.messaging.card_play.Message.with_medic_resurrect(str(cur), resurrected, row)
        self.publish(gwent.game.make_channel(gwent.game.CH_CARDS_PLAY, str(cur)), medic_msg)

        pn = self._player_pronouns(cur)
        self._announce_and_advance(
            self._msg_medic_resurrect(label, resurrected.name, **pn))

    @staticmethod
    def _muster_base_name(name):
        """Extract muster base name by stripping ': suffix'.
        'Arachas: 1' → 'Arachas', 'Crone: Brewess' → 'Crone',
        'Vampire: Fleder' → 'Vampire', 'Vampire - Fleder: 1' → 'Vampire - Fleder',
        'Geralt of Rivia' → 'Geralt of Rivia'.
        Only the last ': X' suffix is stripped for muster matching.
        Use ' - ' (dash) for sub-variants that should muster together."""
        parts = name.rsplit(": ", 1)
        if len(parts) == 2:
            return parts[0].strip()
        return name

    @staticmethod
    def _is_muster_match(muster_base, candidate_name):
        """Check if candidate shares the same muster base name.
        'Crone' matches 'Crone: Weavess', 'Crone: Whispess', 'Crone: Brewess'.
        'Arachas' matches 'Arachas: 1', 'Arachas: 2'.
        'Vampire' matches 'Vampire: Fleder', 'Vampire: Katakan'."""
        candidate_base = PlayRound._muster_base_name(candidate_name)
        return candidate_base == muster_base

    def _process_muster(self, card, row_name):
        """Auto-play all cards with the same base name from hand and deck.
        Base name matching: 'Name: N' (numeric suffix) strips to 'Name'.
        'Name: Word' keeps full name as base (different card)."""
        cur = self._board.current_player
        muster_name = self._muster_base_name(card.name)
        mustered = []

        # From hand
        for hc in list(self._board.hands[cur]):
            if hc.rfid != card.rfid and self._is_muster_match(muster_name, hc.name):
                row = hc.ranges[0] if hc.ranges else row_name
                self._board.place_card(cur, hc, row)
                self._board.remove_from_hand(cur, hc)
                mustered.append(hc)
                muster_msg = gwent.messaging.card_play.Message.with_muster(str(cur), hc, row)
                self.publish(gwent.game.make_channel(gwent.game.CH_CARDS_PLAY, str(cur)), muster_msg)

        # From deck
        for dc in list(self._board.decks[cur]):
            if self._is_muster_match(muster_name, dc.name):
                row = dc.ranges[0] if dc.ranges else row_name
                self._board.place_card(cur, dc, row)
                self._board.decks[cur].remove(dc)
                mustered.append(dc)
                muster_msg = gwent.messaging.card_play.Message.with_muster(str(cur), dc, row)
                self.publish(gwent.game.make_channel(gwent.game.CH_CARDS_PLAY, str(cur)), muster_msg)

        label = self._player_label(cur)
        pn = self._player_pronouns(cur)
        if mustered:
            names = ", ".join(c.name for c in mustered)
            self._announce_and_advance(
                self._msg_muster(label, card.name, len(mustered), names, **pn))
        else:
            self._announce_and_advance(
                self._msg_placement(label, card.name, card.strength or 0, row_name, **pn))

    # --- Choice processing ---

    def process_choice(self, choice: gwent.messaging.choice.Message):
        super().process_choice(choice)

        if self._awaiting == self.AWAITING_CARD:
            if choice.id == 'p':
                # Player passes
                cur = self._board.current_player
                opp = self._board.opponent(cur)
                faction = self._current_faction()
                label = self._player_label(cur)

                cur_score = self._board.calculate_player_score(cur)
                opp_score = self._board.calculate_player_score(opp)
                margin = cur_score - opp_score

                self._board.players[cur].passed = True
                self._log.info(f"{label} passed")
                self._board.current_player = opp

                pn = self._player_pronouns(cur)
                quip = self._msg_pass(label, cur_score, opp_score, margin, **pn)
                self._last_action_summary = quip
                self._publish_prompt_then(
                    quip, self._prompt_turn, faction=faction)
            elif choice.id == 'h' and self._last_action_summary:
                # Help — announce last action summary
                self._publish_prompt_then(
                    self._last_action_summary,
                    self._prompt_turn, faction=self._current_faction())

        elif self._awaiting == self.AWAITING_ROW_CHOICE:
            # Agile card row selection
            card = self._pending_card
            if card and card.ranges:
                idx = int(choice.id) if choice.id.isdigit() else 0
                idx = min(idx, len(card.ranges) - 1)
                row = card.ranges[idx]
                self._awaiting = None
                self._pending_card = None
                self._place_card_on_row(card, row)

        elif self._awaiting == 'leader_weather_choice':
            # Leader weather card selection
            cards = getattr(self, '_pending_weather_cards', [])
            if cards and choice.id.isdigit():
                idx = int(choice.id)
                idx = min(idx, len(cards) - 1)
                wc = cards[idx]
                cur = self._board.current_player
                self._board.decks[cur].remove(wc)
                self._awaiting = None
                self._pending_weather_cards = None
                self._play_weather(wc)

        elif self._awaiting == self.AWAITING_MEDIC_CHOICE:
            # Medic resurrection is handled by scanning, ignore MFD choices
            pass
