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

    def _announce_and_advance(self, prompt):
        """Announce a card play, save as last action summary, then advance turn."""
        self._last_action_summary = prompt
        self._publish_prompt_then(prompt, self._advance_turn,
                                  faction=self._current_faction())

    @property
    def _simple(self):
        return gwent.game.BaseComponent.simple_mode

    # --- Announcement helpers (SRP: one method per announcement type) ---

    def _msg_turn_prompt(self, label, score, opp_score, margin, opp_passed):
        if self._simple:
            return f"{label}'s turn."
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
            player=label, score=score, opp_score=opp_score, margin=abs(margin))

    def _msg_pass(self, label, score, opp_score, margin):
        if self._simple:
            return f"{label} passed."
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
            player=label, score=score, opp_score=opp_score, margin=abs(margin))

    def _msg_placement(self, label, name, strength, row):
        if self._simple:
            return f"{label}: {name} on {row}, strength {strength}."
        row_phrases = self._ROW_PHRASES.get(row, self._CLOSE_PHRASES)
        return random.choice(row_phrases).format(
            player=label, name=name, strength=strength)

    def _msg_spy(self, label, name, strength):
        if self._simple:
            return f"{label}: {name}, spy. Draw 2."
        return random.choice(self._SPY_PHRASES).format(
            player=label, name=name, strength=strength)

    def _msg_medic_prompt(self, label, name, count):
        if self._simple:
            return f"{label}: {name}, medic. Scan discard. {count} available."
        return (f"{label} deploys {name} the battlefield medic! "
                f"Scan a card from discard to resurrect. {count} available.")

    def _msg_medic_resurrect(self, label, resurrected):
        if self._simple:
            return f"{label}: {resurrected} resurrected."
        return random.choice(self._MEDIC_PHRASES).format(
            player=label, name="the medic", resurrected=resurrected)

    def _msg_medic_empty(self, label, name):
        if self._simple:
            return f"{label}: {name}, medic. No targets."
        return f"{label} deploys {name}, but the graveyard offers no one to save."

    def _msg_muster(self, label, name, count, mustered):
        if self._simple:
            return f"{label}: {name}, muster. {mustered}."
        return random.choice(self._MUSTER_PHRASES).format(
            player=label, name=name, count=count, mustered=mustered)

    def _msg_scorch(self, label, name, scorched):
        if self._simple:
            return f"{label}: {name}, scorch. {scorched}."
        return random.choice(self._SCORCH_ABILITY_PHRASES).format(
            player=label, name=name, scorched=scorched)

    def _msg_scorch_no_targets(self, name):
        if self._simple:
            return f"{name}, scorch. No targets."
        return f"{name} breathes fire, but finds no worthy targets!"

    def _msg_commander(self, label, name, faction, row):
        if self._simple:
            return f"{label}: {name}, horn on {row}."
        return random.choice(self._COMMANDER_PHRASES).format(
            name=name, faction=faction, row=row)

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

        prompt = self._msg_turn_prompt(label, cur_score, opp_score, margin, opp_passed)

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
            self.publish_error("Choose a row from the menu first")
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
    ]
    _FOG_COMMENTARY = [
        "An impenetrable fog rolls in! {affected} archers blinded, {damage} strength lost!",
        "Visibility drops to nothing! {affected} ranged units lose {damage} strength!",
        "The mist swallows the field! {affected} cards lose their aim, {damage} strength gone!",
    ]
    _RAIN_COMMENTARY = [
        "Torrential rain pounds the siege! {affected} engines flooded, {damage} strength lost!",
        "The downpour is relentless! {affected} siege units lose {damage} strength!",
        "Rain hammers the war machines! {affected} cards drenched, {damage} strength washed away!",
    ]
    _CLEAR_COMMENTARY = [
        "The skies clear! Soldiers rally, regaining {recovered} strength!",
        "Sunshine breaks through! {recovered} strength restored across the field!",
        "The storm passes! Forces recover {recovered} total strength!",
    ]
    _WEATHER_COMMENTARY = {
        "close": _FROST_COMMENTARY,
        "ranged": _FOG_COMMENTARY,
        "siege": _RAIN_COMMENTARY,
    }
    _COMMANDER_PHRASES = [
        "{faction}'s fearless commander {name} sounds the horn! All {row} units double their strength!",
        "The horn of {name} echoes across the {row} line! {faction} warriors fight with renewed fury!",
        "{name} rallies the troops! {faction}'s {row} combat forces surge with power!",
        "A mighty blast from {name}'s horn! {faction}'s {row} warriors are inspired to fight harder!",
        "Commander {name} takes the field! The {row} line roars with doubled strength for {faction}!",
        "{name} raises the banner of {faction}! Every {row} soldier fights with the strength of two!",
    ]
    _NO_IMPACT = [
        "The weather shifts, but no one is affected.",
        "The elements rage, but the battlefield is empty.",
        "Nature's fury finds no targets.",
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
        "Into the breach! {player} throws {name} at the enemy! Strength {strength}.",
        "{name} shoulders past the shield wall! {strength} points of melee might for {player}!",
    ]
    _RANGED_PHRASES = [
        "{name} takes aim from the ridge! {strength} points of ranged power for {player}.",
        "{player} positions {name} among the archers. Strength {strength}, arrows nocked!",
        "From beyond the treeline, {name} rains down fire! Strength {strength} for {player}.",
        "{name} joins {player}'s ranged line. {strength} strength, eyes on the enemy.",
        "{player} sends {name} to high ground! {strength} points of deadly precision.",
        "A volley of death! {name} draws back and lets fly for {player}! Strength {strength}.",
        "{name} picks their target from afar. {strength} points of cold, calculated fury for {player}.",
        "The arrows of {name} darken the sky! {strength} ranged strength for {player}!",
        "{player} stations {name} on the hill. {strength} points of eagle-eyed destruction!",
        "No one is safe from {name}'s reach! {strength} ranged power rains down for {player}!",
    ]
    _SIEGE_PHRASES = [
        "{name} rolls onto the battlefield! {strength} siege power for {player}.",
        "{player} deploys {name} behind the walls. Strength {strength}, ready to bombard!",
        "The ground shakes as {name} takes position! {strength} points of siege for {player}.",
        "{name} locks onto enemy fortifications! Strength {strength} for {player}.",
        "{player} unleashes {name}! {strength} points of devastating siege force.",
        "Walls crumble as {name} opens fire! {strength} siege power for {player}!",
        "{name} hurls destruction from afar! {strength} points of earth-shattering siege for {player}!",
        "The war machines roar! {player} deploys {name} with {strength} points of crushing force!",
        "Towers topple! {name} brings {strength} points of siege devastation for {player}!",
        "{player} rolls out the heavy artillery! {name} at {strength} siege strength, ready to level everything!",
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
        "Betrayal most foul! {name} sells their sword to the enemy, but their soul belongs to {player}!",
        "Like a serpent in the grass, {name} slithers into enemy ranks. {player} sacrifices {strength} points for the greater scheme!",
        "{name} kneels before the enemy commander, hiding {player}'s knife behind their back. Draw 2!",
        "Every court needs its traitor. {name} joins the enemy at strength {strength}, feeding {player} precious intelligence!",
        "The enemy welcomes {name} with open arms. Fools! {player} just bought two cards with {strength} points of deception!",
        "Scheming and skulduggery! {player} deploys {name} as a double agent. The enemy gains {strength}, but at what cost?",
    ]

    # --- Medic commentary ---
    # Templates accept: {player}, {name}, {resurrected}
    _MEDIC_PHRASES = [
        "{name} works dark magic over the fallen! {resurrected} claws back from the grave for {player}!",
        "By blood and sorcery, {name} drags {resurrected} from death's embrace!",
        "{player}'s {name} kneels over the corpse of {resurrected}. A heartbeat returns!",
        "The battlefield surgeon {name} refuses to let death have {resurrected}!",
        "From ashes to fury! {name} resurrects {resurrected}. The enemy won't believe their eyes!",
        "Death is merely an inconvenience! {name} brings {resurrected} back to fight for {player}!",
        "{resurrected} gasps for air as {name} pulls them from the abyss. Back in {player}'s hand!",
        "The graveyard surrenders its prize! {name} returns {resurrected} to the land of the living!",
        "Not today, death! {player}'s {name} snatches {resurrected} from the void!",
        "A miracle on the battlefield! {name} breathes life into {resurrected} once more!",
    ]

    # --- Muster commentary ---
    # Templates accept: {player}, {name}, {count}, {mustered}
    _MUSTER_PHRASES = [
        "{name} calls their fellow soldiers to battle! {mustered} answer for {player}!",
        "{name} rallies the ranks! {count} comrades rush to {player}'s side: {mustered}!",
        "Brothers in arms! {name} summons {mustered} to fight alongside {player}!",
        "{player}'s {name} lets out a war cry! {count} allies storm the field: {mustered}!",
        "The muster horn sounds! {name} brings {mustered} charging into battle for {player}!",
        "They hunt in packs! {name} howls and {mustered} emerge from the shadows for {player}!",
        "The earth trembles as {name} calls the swarm! {mustered} pour onto the field!",
        "Blood calls to blood! {name} summons {count} kin: {mustered}. {player}'s horde grows!",
        "One becomes many! {name} musters {mustered} from every corner of {player}'s forces!",
        "Where there's one, there's more! {name} brings {count} allies: {mustered}!",
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
        "{name} opens their maw and hellfire pours forth! {scorched} is no more!",
        "A pillar of flame erupts! {player}'s {name} annihilates {scorched}!",
        "The battlefield burns! {name} leaves nothing but ash where {scorched} once stood!",
    ]

    # --- Turn prompt quips by game state ---
    # All templates accept: {player}, {score}, {opp_score}, {margin}
    _TURN_CRUSHING = [  # >15 ahead
        "{player}'s turn. They're trampling the opposition! {score} to {opp_score}.",
        "{player} is on a rampage! Up {margin} points. Can anyone stop them?",
        "Total domination from {player}! {score} to {opp_score}. Play on!",
        "{player}'s army is unstoppable! {margin} points ahead, the battlefield belongs to them!",
        "The bards will write legends of {player}'s conquest! {score} to {opp_score}!",
        "Like the Wild Hunt itself! {player} devastates at {score} to {opp_score}!",
        "{player} lords over the field! {margin} ahead. Another card to twist the knife?",
        "Nilfgaard's finest generals couldn't plan a better assault! {player} leads {margin}!",
    ]
    _TURN_AHEAD = [  # 5-15 ahead
        "{player}'s turn. Leading {score} to {opp_score}. Keep the pressure on!",
        "The advantage is {player}'s! {margin} ahead. Press the attack?",
        "{player} holds the upper hand at {score}. Can they seal the deal?",
        "{player} smells blood! {margin} points up. Time to go for the kill!",
        "The tide favors {player}! {score} to {opp_score}. Will they push or hold?",
        "Kaer Morhen trained warriors well. {player} leads by {margin}!",
        "{player}'s forces are gaining ground! {score} to {opp_score}, play wisely!",
        "The sorceresses of Aretuza nod approvingly. {player} leads by {margin}!",
    ]
    _TURN_EVEN = [  # within 5 either way
        "{player}'s turn. It's neck and neck! {score} to {opp_score}.",
        "A tense standoff! {player} at {score}, opponent at {opp_score}. Every card matters!",
        "{player} steps up. The scores are razor thin. {score} to {opp_score}!",
        "This could go either way! {player} at {score}. Choose carefully!",
        "The battlefield trembles in the balance! {player}'s move at {score} to {opp_score}.",
        "Neither side gives an inch! {player} plays at {score} to {opp_score}.",
        "Geralt would call this a true contest! {player} at {score}, deadlocked!",
        "A match worthy of Vizima's finest tavern! {player}'s turn, scores nearly even!",
        "Both commanders eye each other across the field. {player} at {score} to {opp_score}.",
        "Tense as a crossbow string! {player}'s move. {score} to {opp_score}!",
    ]
    _TURN_BEHIND = [  # 5-15 behind
        "{player}'s turn. Trailing by {margin}! Can they muster a comeback?",
        "{player} is down {margin} points. Time to dig deep!",
        "The situation looks grim for {player}! {opp_score} to {score}. What's the play?",
        "{player} needs a miracle! Down {margin}. Do they have a trick up their sleeve?",
        "The enemy presses their advantage! {player} trails {margin}. Fight back!",
        "Even a cornered wolf is dangerous. {player}'s turn, down {margin}!",
        "{player} searches their hand desperately. {margin} behind. What can turn this around?",
        "Vesemir would say: never give up! {player} trails by {margin}. Play on!",
    ]
    _TURN_DESPERATE = [  # >15 behind
        "{player}'s turn. It's looking bleak! Down {margin} points. Can they claw back?",
        "A massacre on the field! {player} trails {margin}. Is there any hope?",
        "{player} stares down a {margin}-point deficit. Only a Scorch or a miracle can save them!",
        "The crows are circling {player}'s army! Down {margin}. This may be the end!",
        "Dandelion winces. {player} is getting destroyed! {opp_score} to {score}!",
        "Even Yennefer's magic couldn't close this gap! {player} down {margin}!",
        "The White Frost cometh for {player}! Trailing by {margin}. Desperate times!",
        "From the ashes? {player} down {margin}. The greatest comebacks start here!",
    ]
    _TURN_OPP_PASSED_AHEAD = [  # opponent passed, we're ahead
        "{player}'s turn. The enemy has passed! {score} to {opp_score}. The round is yours to lose!",
        "The opponent retreats! {player} leads {score} to {opp_score}. Pass or pile on?",
        "With the enemy done, {player} reigns supreme at {score}! More cards, or save them?",
        "The field is {player}'s alone! Opponent passed at {opp_score}. Conserve or crush?",
        "Victory is assured! {player} at {score}. Every extra card is a waste, or is it insurance?",
    ]
    _TURN_OPP_PASSED_BEHIND = [  # opponent passed, we're behind
        "{player}'s turn. The enemy passed at {opp_score}! Down {margin}. Time to catch up!",
        "The opponent bows out at {opp_score}! {player} trails by {margin}. The comeback is on!",
        "A chance to strike! Opponent passed. {player} needs {margin} more points to win!",
        "The enemy thinks they've won at {opp_score}! {player} at {score}. Prove them wrong!",
        "No more interference! Opponent passed. {player} needs to close a {margin}-point gap!",
    ]

    # --- Pass quips by game state ---
    # All templates accept: {player}, {score}, {opp_score}, {margin}
    _PASS_DOMINATING = [
        "{player} passes with supreme confidence! {score} to {opp_score}. A lead of {margin}!",
        "{player} leans back and smirks. {margin} points ahead. This round is all but won.",
        "With a {margin}-point cushion, {player} has nothing to prove. Pass!",
        "{player} raises a tankard. {score} to {opp_score}? That'll do nicely.",
    ]
    _PASS_AHEAD = [
        "{player} passes, holding a slim lead. {score} to {opp_score}.",
        "A calculated pass from {player}. {margin} points ahead, but is it enough?",
        "{player} holds steady at {score}. The lead is narrow but the nerve is steel.",
        "Dandelion would call this bold. {player} passes with just {margin} points to spare!",
    ]
    _PASS_TIED = [
        "{player} passes on a knife's edge! {score} to {opp_score}. Dead even!",
        "All square at {score}! {player} blinks first and passes. A gambler's move!",
        "{player} passes at {score} all. This could go either way!",
        "The scores are locked at {score}. {player} passes and holds their breath!",
    ]
    _PASS_BEHIND = [
        "{player} passes, trailing by {margin}. A bluff, or out of options?",
        "Down {margin} points, {player} throws in the towel. {opp_score} to {score}.",
        "{player} concedes the ground. {margin} behind, sometimes discretion is the better part of valor.",
        "A tactical retreat! {player} passes at {score}, hoping the opponent overextends.",
    ]
    _PASS_DESPERATE = [
        "{player} passes in desperation! Down {margin} points. The round looks lost.",
        "Mercy! {player} waves the white flag. {opp_score} to {score} is too much to overcome.",
        "{player} cuts their losses. {margin} points behind. Save the cards for next round!",
        "Even Geralt couldn't save {player} now. Down {margin}, they pass and pray.",
    ]

    def _play_weather(self, card):
        """Apply a weather effect."""
        cur = self._board.current_player
        label = self._player_label(cur)

        is_clear = card.is_weather and not card.ranges
        if is_clear or (card.has_specialty and card.specialty == "mardroeme"):
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
        """Mardroeme clears weather."""
        cur = self._board.current_player
        self._board.weather_rows.clear()
        self._board.remove_from_hand(cur, card)
        self._board.players[cur].discard.append(card)
        self._announce_and_advance(
            f"{self._player_label(cur)}: place {card.name} on discard. Weather cleared!")

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
            self.publish_error("No non-hero cards on your board to swap with Decoy")
            return

        self._pending_card = card
        self._awaiting = self.AWAITING_DECOY_CHOICE
        self.publish_prompt(
            f"{label}: Decoy! Scan a card on your board to return to hand.",
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
            self.publish_error("Cannot swap a hero card with Decoy")
            return

        # Swap: remove target from board, place decoy on that row, return target to hand
        self._board.players[cur].rows[row_name].remove(target)
        self._board.place_card(cur, decoy, row_name)
        self._board.remove_from_hand(cur, decoy)
        self._board.hands[cur].append(target)

        self._pending_card = None
        self._announce_and_advance(
            f"{label}: place Decoy on {row_name}. {target.name} returned to hand.")

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

        self._board.remove_from_hand(cur, card)
        self._board.players[cur].discard.append(card)

        label = self._player_label(cur)
        if destroyed:
            names = ", ".join(c.name for c in destroyed)
            self._announce_and_advance(
                f"{label}: place {card.name} on discard. Scorched: {names}")
        else:
            self._announce_and_advance(
                f"{label}: place {card.name} on discard. No targets.")

    def _play_commander_card(self, card):
        """Commander's Horn: double a row's strength."""
        cur = self._board.current_player
        # Commander card has ranges — apply horn to those rows
        for row in card.ranges:
            if row in ROWS:
                self._board.commander_horn_rows[cur].add(row)
        self._board.remove_from_hand(cur, card)
        self._board.players[cur].discard.append(card)
        self._announce_and_advance(
            f"{self._player_label(cur)}: place {card.name} on discard. "
            f"Horn on {', '.join(card.ranges)}.")

    def _play_leader(self, card):
        """Play a leader card ability. Dispatches to specific handler by JSON key."""
        cur = self._board.current_player
        pb = self._board.players[cur]

        if pb.leader_used:
            self.publish_error("Leader ability already used this game")
            return

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
            self.publish_prompt(
                f"{label}: leader ability. Scan a weather card from your deck.",
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
                f"{label}: leader ability. Scan a card from opponent's discard to take. "
                f"{len(opp_discard)} available.",
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
        self._announce_and_advance(
            f"{label}: leader ability. All graveyards reshuffled into decks.")

    def _leader_clear_weather(self):
        """Leader ability: clear all active weather effects."""
        cur = self._board.current_player
        label = self._player_label(cur)
        had_weather = len(self._board.weather_rows) > 0
        self._board.weather_rows.clear()
        if had_weather:
            self._announce_and_advance(
                f"{label}: leader ability. All weather effects cleared!")
        else:
            self._announce_and_advance(
                f"{label}: leader ability. No weather to clear.")

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
                f"{label}: leader ability. Scan a card from your discard to restore. "
                f"{len(non_hero)} available.",
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
        self._announce_and_advance(
            f"{label}: leader ability. All spy cards now have doubled strength!")

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
            f"{label}: leader ability. Scan {self._leader_discards_remaining} "
            f"card(s) from your hand to discard.",
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
        self._announce_and_advance(
            f"{label}: leader ability. All medic cards now restore random units!")

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
            self.publish_prompt(f"Choose row for {card.name}",
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
        if is_spy:
            self._spy_draws_remaining = 2
            self._awaiting = self.AWAITING_SPY_DRAW
            msg = self._msg_spy(label, card.name, card.strength or 0)
            self.publish_prompt(
                f"{msg} Scan 2 cards from your deck to draw.",
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
                    self._msg_medic_prompt(label, card.name, len(non_hero)),
                    ok=False, cancel=False, clear_choices=True,
                    faction=self._current_faction())
                return
            else:
                self._announce_and_advance(
                    self._msg_medic_empty(label, card.name))
                return

        if card.has_abilities and "muster" in card.abilities:
            self._process_muster(card, row_name)
            return

        # Scorch ability (not specialty): destroy strongest in opponent's same row
        if card.has_abilities and "scorch" in card.abilities:
            opp = self._board.opponent(cur)
            destroyed = self._board.destroy_strongest(opp, row_name)
            if destroyed:
                scorched = ", ".join(c.name for c in destroyed)
                self._announce_and_advance(
                    self._msg_scorch(label, card.name, scorched))
            else:
                self._announce_and_advance(
                    self._msg_scorch_no_targets(card.name))
            return

        # Commander unit
        if card.has_abilities and "commander" in card.abilities:
            faction = self._board.factions[cur]
            self._announce_and_advance(
                self._msg_commander(label, card.name, faction, row_name))
            return

        # Normal card
        self._announce_and_advance(
            self._msg_placement(label, card.name, card.strength or 0, row_name))

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
        self._announce_and_advance(
            self._msg_medic_resurrect(label, resurrected.name))

    def _process_muster(self, card, row_name):
        """Auto-play all cards with the same name from hand and deck."""
        cur = self._board.current_player
        muster_name = card.name.split(":")[0].strip()  # "Arachas: 1" → "Arachas"
        mustered = []

        # From hand
        for hc in list(self._board.hands[cur]):
            if hc.rfid != card.rfid and hc.name.startswith(muster_name):
                row = hc.ranges[0] if hc.ranges else row_name
                self._board.place_card(cur, hc, row)
                self._board.remove_from_hand(cur, hc)
                mustered.append(hc)

        # From deck
        for dc in list(self._board.decks[cur]):
            if dc.name.startswith(muster_name):
                row = dc.ranges[0] if dc.ranges else row_name
                self._board.place_card(cur, dc, row)
                self._board.decks[cur].remove(dc)
                mustered.append(dc)

        label = self._player_label(cur)
        if mustered:
            names = ", ".join(c.name for c in mustered)
            self._announce_and_advance(
                self._msg_muster(label, card.name, len(mustered), names))
        else:
            self._announce_and_advance(
                self._msg_placement(label, card.name, card.strength or 0, row_name))

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

                quip = self._msg_pass(label, cur_score, opp_score, margin)
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
