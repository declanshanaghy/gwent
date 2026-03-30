
# Gwent Synergy Catalog

Only RFID-equipped cards are eligible. Card counts reflect actual RFID inventory.

## Muster Chains (play 1, auto-summon all same-named from hand + deck)

- **Monsters**: Arachas x2 (4 ea, close=8), Behemoth (6, siege — standalone), Crone:Brewess (6) + Crone:Weavess (6) — standalone each, Vampire:Fleder x2 (4 ea, close=8), Vampire:Garkhain (4 — standalone), Ghoul x2 (1 ea=2), Nekker x2 (2 ea=4), Gaunter Darkness x2 (4 ea, ranged=8)
- **Scoia'tael**: Dwarven Skirmisher x3 (3 ea, close=9), Elven Skirmisher x3 (2 ea, ranged=6), Havekar Smuggler x1 (5, close — no muster target), Gaunter Darkness x1 (4, ranged — only 1 copy)
- **Skellige**: Light Longship x2 (4 ea, ranged=8), Gaunter Darkness x1 (4, ranged — only 1 copy)
- **NR**: Gaunter Darkness x1 (4, ranged — only 1 copy)

Muster floods the board instantly. Best with Commander Horn to double the row. Risk: depletes hand/deck quickly.

## Bond Multipliers (strength x count of same-named in row)

- **Skellige**: Clan an Craite Warrior x3 (6 ea → 6+12+18=**36** close), War Longship x2 (6 ea → 6+12=**18** siege), Transformed Young Vildkaarl x3 (8 ea → 8+16+24=**48** ranged), Clan Drummond Shield Maiden x2 (4 ea → 4+8=**12** close)
- **Nilfgaardian**: Impera Brigade Guard x3 (3 ea → 3+6+9=**18** close), Young Emissary x2 (5 ea → 5+10=**15** close), Nausicaa Cavalry Rider x2 (2 ea → 2+4=**6** close)
- **NR**: Catapult x1 (8, siege — only 1 copy, bond useless), Blue Stripes Commando x1 (4 — only 1 copy), Poor Fucking Infantry x2 (1 ea → 1+2=**3** close — weak)

Bond is the highest damage multiplier. Stack all copies + Commander Horn to double. Counter: weather reduces base to 1.

## Spy Draw Engine (play on opponent's board, draw 2 cards)

Avallac'h (0, hero spy) available in Monsters, NR, Skellige (hero versions); Skellige also has non-hero Avallac'h (0). Nilfgaardian has deepest spy pool: Vattier (4), Shilard (7), Stefan (9) + Avallac'h. NR has Prince Stennis (5), Dijkstra (4), Emiel Regis (5). Spies trade board strength for card advantage — best in round 1.

## Medic Recursion (resurrect non-hero from own discard)

- **Nilfgaardian**: Etolian Archers x2 (1 ea, ranged), Siege Technician (0, siege), Yennefer x2 (7 ea, ranged hero), Menno Coehoorn (10, close — abilities field malformed as individual letters)
- **NR**: Dun Banner Medic (5, siege), Yennefer (7, ranged hero)
- **Scoia'tael**: Havekar Healer (0, ranged), Isengrim Faoiltiarna:2 (10, close)
- **Skellige**: Birna Bran (2, close)

Medic + Decoy = play medic, resurrect, decoy medic back, replay for another resurrect.

## Morale Boost (+1 to all other non-heroes in same row)

Kayran (8, Monsters hero agile), Olaf (12, Skellige agile), Transformed Vildkaarl (14, Skellige close), Milva (10, Scoia'tael ranged), Kaedweni Siege Expert x3 (1 ea, NR siege — 3 morale = +3 to all siege units).

## Commander Horn Doubling (doubles all non-hero strength in row)

Dandelion (2, close) available in Monsters x2, Nilfgaardian, Skellige. Draig Bon-Dhu (2, Skellige siege). Commander's Horn specialty card available in most factions. Best combos: Skellige CaC 3x (36) + Horn = **72**, TYV 3x (48) + Horn = **96**, NR Kaedweni morale stack + siege units + Horn.

## Weather, Scorch, Decoy

Weather (Frost/Fog/Rain) reduces all non-heroes in targeted row to 1. Heroes immune. Every faction has weather + Clear Weather cards. Scorch (specialty) hits ALL highest non-heroes on board (both players). Villentretenmerth (7, scorch ability) hits opponent's row only — safer. Decoys: Scoia'tael x3, Skellige x2, Nilfgaardian x1. Best targets: medic (re-resurrect), spy (re-spy +2 cards).

## Faction Passives

- **Monsters**: Keep strongest non-hero on board between rounds
- **Northern Realms**: Draw 1 extra card on round win
- **Skellige**: Resurrect 2 random non-heroes from discard each round
- **Nilfgaardian**: Win all tied rounds
- **Scoia'tael**: Choose who goes first

## Implemented Leaders (have game-mechanical abilities)

- **Monsters**: Eredin - King of the Wild Hunt (weather_ranges), Eredin: Commander of the Red Riders (commander_ranges)
- **Nilfgaardian**: Emhyr - His Imperial Majesty (weather_ranges)
- **NR**: Foltest - King of Temeria (weather_ranges), Foltest: the Siegemaster x2 (commander_ranges), Foltest: Son of Medell (conditional_scorch), Foltest: The Steel-Forged x2 (conditional_scorch)
- **Scoia'tael**: Francesca - Pureblood Elf (weather_ranges), Francesca - The Beautiful (commander_ranges), Francesca: Queen of Dol Blathanna (conditional_scorch)
- **Skellige**: Crach an Craite (unimplemented — only leader)

## Archetype Recommendations

- **Monsters "Muster Swarm"**: Eredin KotWH leader, Arachas/Crone/Vampire muster chains, heroes (Geralt 15, Imlerith 10, Draug 10, Kayran 8 morale), Dandelion commander. Passive keeps strongest hero between rounds.
- **Nilfgaardian "Spy Engine"**: Emhyr HIM leader, 4 spies (Avallac'h+Vattier+Shilard+Stefan) for +8 cards, Impera 3x bond (18) + Young Emissary 2x bond (15), Dandelion commander to double close. Win ties enables conservative play after spy advantage.
- **NR "Siege Fortress"**: Foltest Siegemaster leader (horn on siege), 3 spies + 3x Kaedweni morale in siege + Ballista/Trebuchet/Siege Tower units. Leader horn + morale stack = devastating siege row.
- **Scoia'tael "Guerrilla Flex"**: Francesca Beautiful leader (horn on ranged), agile units (DBS x3, Filavandrel, Vrihedd x2) flex to ranged for horn, Dwarven Skirmisher x3 muster + Elven Skirmisher x3 muster, 3 Decoys for medic/spy replay.
- **Skellige "Berserker Blitz"**: Crach an Craite leader, CaC Warrior 3x bond (36 close) + TYV 3x bond (48 ranged) + War Longship 2x bond (18 siege), Dandelion + Commander's Horn, Olaf agile morale. Passive resurrects 2 per round to recycle bond cards.
