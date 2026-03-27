<!--
To regenerate this report, use the following prompt:
Read all JSON files in the software/data/cards directory and its subdirectories to extract card information including faction, name, strength, range, specialty, abilities, and ownership data.

Generate a comprehensive Markdown report (without using a script) analyzing the Gwent card database with the following structure:

0. Report output instructions
  - Output the report to software/data/cards/CardReport.md.
  - Include these instructions when the prompt is regenerated

1. Card Distribution by Faction:
   - Create a summary table showing the total number of cards in each faction (Monsters, Nilfgaardian, Northern Realms, Scoia'tael, Skellige)

2. Card Ownership Summary:
   - Table showing cards owned by Declan Shanaghy by faction with counts and percentages

3. Card Statistics:
   - Overall statistics (total cards, owned vs. not owned)
   - Card types (unit, weather, leader, special cards)
   - Leader cards analysis (total count, distribution by faction, ownership, rfid)
   - Card abilities distribution (muster, agile, bond, spy, rfid)
   - RFID registered cards analysis
   - Hero cards analysis
   - Weather cards breakdown
   - Interesting observations about the collection

4. Cards by Faction:
   - For each faction, create two sections:
     a. Leaders section first - Table showing all leader cards with their owners
     b. Regular cards section without leaders - Table with all cards showing Name, Strength, Range, Specialty, Ability, Owner, RFID

5. Anomalies
  - The following tables all cards showing Name, Faction, Owner, RFID
    - Cards that have an owner but no RFID
    - Cards that have an RFID but no owner
    - Cards that have (the owner or rfid set) and (starter is true and leader is false)
      - Title this one: Misconfigured starter cards
-->

# Gwent Card Collection Analysis

## 1. Card Distribution by Faction

| Faction | Card Count | Percentage |
|---------|------------|------------|
| Monsters | 57 | 20.7% |
| Nilfgaardian | 55 | 20.0% |
| Northern Realms | 54 | 19.6% |
| Scoia'tael | 55 | 20.0% |
| Skellige | 54 | 19.6% |
| **Total** | **275** | **100%** |

## 2. Card Ownership Summary

| Faction | Owned Cards | Total Cards | Percentage Owned |
|---------|-------------|-------------|------------------|
| Monsters | 16 | 57 | 28.1% |
| Nilfgaardian | 12 | 55 | 21.8% |
| Northern Realms | 13 | 54 | 24.1% |
| Scoia'tael | 9 | 55 | 16.4% |
| Skellige | 15 | 54 | 27.8% |
| **Total** | **65** | **275** | **23.6%** |

## 3. Card Statistics

### Overall Statistics
- **Total Cards**: 275
- **Owned Cards**: 65 (23.6%)
- **Not Owned Cards**: 210 (76.4%)

### Card Types
- **Unit Cards**: 205 (74.5%)
- **Weather Cards**: 37 (13.5%)
- **Leader Cards**: 21 (7.6%)
- **Special Cards**: 12 (4.4%) — Decoy, Scorch, Commander's Horn, Mardroeme

### Leader Cards Analysis
- **Total Leader Cards**: 21
- **Distribution by Faction**:
  - Monsters: 5 (Eredin variants)
  - Nilfgaardian: 5 (Emhyr var Emreis variants)
  - Northern Realms: 5 (Foltest variants)
  - Scoia'tael: 5 (Francesca Findabair variants)
  - Skellige: 1 (Crach an Craite)
- **Owned Leader Cards**: 2 (9.5%)
  - Emhyr var Emreis - The Relentless (Nilfgaardian)
  - Francesca Findabair - The Beautiful (Scoia'tael)
- **Leader Cards with RFID**: 7 (33.3%)

### Hero Cards Analysis
- **Total Hero Cards**: 23
- **Distribution by Faction**:
  - Monsters: 5 (Draug, Geralt of Rivia, Imlerith, Kayran, Leshen)
  - Nilfgaardian: 4 (Letho of Gulet, Morvan Voorhis, Morvran Voorhis, Tibor Eggebracht)
  - Northern Realms: 6 (Esterad Thyssen, John Natalis, Philippa Eilhart, Triss Merigold, Vernon Roche, Yennefer of Vengerberg)
  - Scoia'tael: 4 (Cirilla Fiona Elen Riannon, Eithne, Iorveth, Isengrim Faoiltiarna)
  - Skellige: 4 (Cerys, Ermion, Hjalmar, Triss Merigold)

### Weather Cards Breakdown
- **Total Weather Cards**: 37
- **Distribution by Faction**:
  - Monsters: 6
  - Nilfgaardian: 8
  - Northern Realms: 8
  - Scoia'tael: 7
  - Skellige: 8

### RFID Registered Cards Analysis
- **Total Cards with RFID**: 210 (76.4%)
- **Distribution by Faction**:
  - Monsters: 40
  - Nilfgaardian: 41
  - Northern Realms: 43
  - Scoia'tael: 39
  - Skellige: 47

### Starter Cards Analysis
- **Total Starter Cards**: 157 (57.1%)
- **Distribution by Faction**:
  - Monsters: 30
  - Nilfgaardian: 30
  - Northern Realms: 32
  - Scoia'tael: 31
  - Skellige: 34

### Card Abilities Distribution
| Ability | Count |
|---------|-------|
| muster | 32 |
| bond | 23 |
| agile | 15 |
| morale | 9 |
| medic | 7 |
| spy | 7 |
| scorch | 5 |
| commander | 4 |
| berserker | 2 |

### Interesting Observations
1. The collection has two owners: Declan Shanaghy (59 cards) and Dylan Shanaghy (6 cards, all Monsters faction).
2. RFID coverage is high at 76.4% (210 of 275 cards), with Skellige at 87.0% (47/54) being the most complete.
3. There are duplicate/variant card entries for several cards (e.g., Morvan Voorhis/Morvran Voorhis, Keira Metz/Kiera Metz, Udalryk/Udalyrk, Riordain/Riordan) suggesting data normalization opportunities.
4. Six cards have owners but no RFID tags — all owned by Dylan Shanaghy in the Monsters faction.
5. Menno Coehoorn has a data entry bug — the ability "medic" was stored as individual characters ["m","e","d","i","c"] instead of ["medic"].
6. Monsters has the most cards overall (57) while Northern Realms and Skellige are tied for fewest (54).
7. Skellige has only 1 leader card (Crach an Craite) compared to 5 for every other faction.

## 4. Cards by Faction

### Monsters

#### Leader Cards
| Name | Owner | RFID |
|------|-------|------|
| Eredin Breacc Glas: the Treacherous | - | - |
| Eredin: Bringer of Death | - | - |
| Eredin: Commander of the Red Riders | - | - |
| Eredin: Destroyer of Worlds | - | - |
| Eredin - King of the Wild Hunt | - | 209511075183 |

#### Regular Cards
| Name | Strength | Range | Specialty | Ability | Owner | RFID |
|------|----------|-------|-----------|---------|-------|------|
| [Arachas: 1](#misconfigured-starter-cards) | 4 | close | - | muster | - | 622264733154 |
| [Arachas: 2](#misconfigured-starter-cards) | 4 | close | - | muster | - | 482409860530 |
| Arachas: 3 | 4 | close | - | muster | - | - |
| [Arachas: Behemoth](#misconfigured-starter-cards) | 6 | siege | - | muster | - | 345675550136 |
| [Biting Frost: 1](#misconfigured-starter-cards) | - | close | weather | - | - | 965039967680 |
| [Biting Frost: 2](#misconfigured-starter-cards) | - | close | weather | - | - | 553578745331 |
| Botchling | 4 | close | - | - | Declan Shanaghy | 206172343721 |
| Bovine Defense Force | 8 | close | - | - | Declan Shanaghy | 275479023098 |
| [Celaeno Harpy](#misconfigured-starter-cards) | 2 | close, ranged | - | agile | - | 482074250717 |
| [Clear Weather: 1](#misconfigured-starter-cards) | - | - | weather | - | - | 206340705706 |
| [Cockatrice](#misconfigured-starter-cards) | 2 | ranged | - | - | - | 346128403799 |
| [Crone: Brewess](#misconfigured-starter-cards) | 6 | close | - | muster | - | 895011802403 |
| Crone: Weavess | 6 | close | - | muster | Dylan Shanaghy | - |
| Crone: Whispess | 6 | close | - | muster | - | - |
| Dandelion | 2 | close | - | commander | Declan Shanaghy | 618623487232 |
| Draug | 10 | close | hero | - | Dylan Shanaghy | - |
| Earth Elemental | 6 | siege | - | - | Dylan Shanaghy | - |
| [Endrega](#misconfigured-starter-cards) | 2 | ranged | - | - | - | 416324209944 |
| Fiend | 6 | close | - | - | Declan Shanaghy | 1032953482734 |
| [Fire Elemental](#misconfigured-starter-cards) | 6 | siege | - | - | - | 3151711533 |
| Foglet | 2 | close | - | - | Declan Shanaghy | 71434456367 |
| [Forktail](#misconfigured-starter-cards) | 5 | close | - | - | - | 550944591184 |
| [Frightener](#misconfigured-starter-cards) | 5 | close | - | - | - | 333139333 |
| [Gargoyle](#misconfigured-starter-cards) | 2 | ranged | - | - | - | 2681883912 |
| Gaunter O'Dimm: Darkness 1 | 4 | ranged | - | muster | Declan Shanaghy | 550004673814 |
| Gaunter O'Dimm: Darkness 2 | 4 | ranged | - | muster | Declan Shanaghy | 2211728666 |
| Geralt of Rivia | 15 | close | hero | - | Declan Shanaghy | 346429869409 |
| [Ghoul: 1](#misconfigured-starter-cards) | 1 | close | - | muster | - | 414176660889 |
| [Ghoul: 2](#misconfigured-starter-cards) | 1 | close | - | muster | - | 206374063531 |
| [Grave Hag](#misconfigured-starter-cards) | 5 | ranged | - | - | - | 141160959337 |
| [Griffin](#misconfigured-starter-cards) | 5 | close | - | - | - | 1032567999757 |
| Harpy | 2 | close, ranged | - | agile | - | - |
| [Ice Giant](#misconfigured-starter-cards) | 5 | siege | - | - | - | 550692801827 |
| [Imlerith](#misconfigured-starter-cards) | 10 | close | hero | - | - | 964553100774 |
| [Impenetrable Fog: 1](#misconfigured-starter-cards) | - | ranged | weather | - | - | 275462508023 |
| [Impenetrable Fog: 2](#misconfigured-starter-cards) | - | ranged | weather | - | - | 621794577856 |
| [Kayran](#misconfigured-starter-cards) | 8 | close, ranged | hero | agile, morale | - | 485093756187 |
| Leshen | 10 | ranged | hero | - | Dylan Shanaghy | - |
| [Nekker: 1](#misconfigured-starter-cards) | 2 | close | - | muster | - | 964234268154 |
| Nekker: 2 | 2 | close | - | muster | Declan Shanaghy | 825553669486 |
| [Plague Maiden](#misconfigured-starter-cards) | 5 | close | - | - | - | 482409401787 |
| Toad | 7 | ranged | - | scorch | - | - |
| [Torrential Rain](#misconfigured-starter-cards) | - | siege | weather | - | - | 278683602233 |
| Vampire: Bruxa | 4 | close | - | muster | - | - |
| Vampire: Ekimmara | 4 | close | - | muster | - | - |
| Vampire: Fleder | 4 | close | - | muster | Dylan Shanaghy | - |
| Vampire: Garkain | 4 | close | - | muster | - | - |
| [Vampire: Garkhain](#misconfigured-starter-cards) | 4 | close | - | muster | - | 552789757359 |
| Vampire: Katakan | 5 | close | - | muster | Dylan Shanaghy | - |
| Villentretenmerth | 7 | close | - | scorch | Declan Shanaghy | 964737453542 |
| [Werewolf](#misconfigured-starter-cards) | 5 | close | - | - | - | 69958258114 |
| [Wyvern](#misconfigured-starter-cards) | 2 | ranged | - | - | - | 962673921368 |

### Nilfgaardian

#### Leader Cards
| Name | Owner | RFID |
|------|-------|------|
| Emhyr var Emreis: Emperor of Nilfgaard | - | - |
| Emhyr var Emreis: Invader of the North | - | - |
| Emhyr var Emreis: The White Flame | - | - |
| Emhyr var Emreis - His Imperial Majesty | - | 137554120118 |
| Emhyr var Emreis - The Relentless | Declan Shanaghy | 413287665097 |

#### Regular Cards
| Name | Strength | Range | Specialty | Ability | Owner | RFID |
|------|----------|-------|-----------|---------|-------|------|
| Albrich | 2 | ranged | - | - | - | - |
| [Assire var Anahid](#misconfigured-starter-cards) | 6 | ranged | - | - | - | 414915579218 |
| [Biting Frost: 1](#misconfigured-starter-cards) | - | close | weather | - | - | 2430946616 |
| [Biting Frost: 2](#misconfigured-starter-cards) | - | close | weather | - | - | 1032149355784 |
| Black Infantry Archer | 10 | ranged | - | - | - | - |
| [Cahir Mawr Dyffryn aep Ceallach](#misconfigured-starter-cards) | 6 | close | - | - | - | 963194998026 |
| [Clear Weather: 1](#misconfigured-starter-cards) | - | - | weather | - | - | 347420839195 |
| Clear Weather: 2 | - | - | weather | - | Declan Shanaghy | 415250009431 |
| Commander's Horn: 1 | - | close, ranged, siege | commander | - | Declan Shanaghy | 621643189683 |
| [Cynthia](#misconfigured-starter-cards) | 4 | ranged | - | - | - | 278651030792 |
| Dandelion | 2 | close | - | commander | Declan Shanaghy | 620267982189 |
| Decoy: 1 | 0 | - | decoy | - | Declan Shanaghy | 2245217563 |
| Emiel Regis Rohellec Terzieff: Human | 5 | close | - | - | Declan Shanaghy | 2782088507 |
| Emiel Regis Rohellec Terzieff: Vampire | 5 | close | - | - | Declan Shanaghy | 344299163104 |
| Etolian Auxiliary Archers | 1 | ranged | - | medic | - | - |
| [Etolian Auxillary Archers](#misconfigured-starter-cards) | 1 | ranged | - | medic | - | 345759829369 |
| Fringilla Vigo | 6 | ranged | - | - | Declan Shanaghy | 2312391952 |
| Heavy Zerrikanian Fire Scorpion | 10 | siege | - | - | - | - |
| [Impenetrable Fog: 1](#misconfigured-starter-cards) | - | ranged | weather | - | - | 482762575295 |
| [Impenetrable Fog: 2](#misconfigured-starter-cards) | - | ranged | weather | - | - | 412499594691 |
| Impenetrable Fog: 3 | - | ranged | weather | - | Declan Shanaghy | 618690596100 |
| [Impera Brigade Guard: 1](#misconfigured-starter-cards) | 3 | close | - | bond | - | 895314251018 |
| [Impera Brigade Guard: 2](#misconfigured-starter-cards) | 3 | close | - | bond | - | 824933830015 |
| [Impera Brigade Guard: 3](#misconfigured-starter-cards) | 3 | close | - | bond | - | 414798007645 |
| Letho of Gulet | 10 | close | hero | - | - | - |
| Menno Coehoorn | 10 | close | - | medic* | Declan Shanaghy | 687846149400 |
| Morteisen | 3 | close | - | - | - | - |
| Morvan Voorhis | 10 | siege | hero | - | Declan Shanaghy | 275059527124 |
| Morvran Voorhis | 10 | siege | hero | - | - | - |
| [Nausicaa Cavalry Rider: 1](#misconfigured-starter-cards) | 2 | close | - | bond | - | 897428114829 |
| [Nausicaa Cavalry Rider: 2](#misconfigured-starter-cards) | 2 | close | - | bond | - | 2380418338 |
| Puttkamer | 3 | ranged | - | - | - | - |
| [Rainfarn](#misconfigured-starter-cards) | 4 | close | - | - | - | 414227516862 |
| [Renauld aep Matsen](#misconfigured-starter-cards) | 5 | ranged | - | - | - | 893804236133 |
| Renuald aep Matsen | 5 | ranged | - | - | - | - |
| [Rotten Mangonel](#misconfigured-starter-cards) | 3 | siege | - | - | - | 553813888477 |
| [Shilard Fitz-Oesterlen](#misconfigured-starter-cards) | 7 | close | - | spy | - | 4024454466 |
| [Siege Engineer](#misconfigured-starter-cards) | 6 | siege | - | - | - | 1033055063514 |
| [Siege Technician](#misconfigured-starter-cards) | 0 | siege | - | medic | - | 688736259415 |
| [Stefan Skellen](#misconfigured-starter-cards) | 9 | close | - | spy | - | 965291822578 |
| Sweers | 2 | ranged | - | - | - | - |
| [Tibor Eggebracht](#misconfigured-starter-cards) | 10 | ranged | hero | - | - | 414982688086 |
| [Torrential Rain](#misconfigured-starter-cards) | - | siege | weather | - | - | 71217532204 |
| [Vanhemar](#misconfigured-starter-cards) | 4 | ranged | - | - | - | 757287898444 |
| [Vattier de Rideaux](#misconfigured-starter-cards) | 4 | close | - | spy | - | 138040855982 |
| [Vreemde](#misconfigured-starter-cards) | 2 | close | - | - | - | 71737232689 |
| [Young Emissary: 1](#misconfigured-starter-cards) | 5 | close | - | bond | - | 208370879777 |
| Young Emissary: 2 | 5 | close | - | bond | Declan Shanaghy | 206273007023 |
| Young Emmisary | 5 | close | - | bond | - | - |
| [Zerrikanian Fire Scorpion](#misconfigured-starter-cards) | 5 | siege | - | - | - | 550072438016 |

*\* Menno Coehoorn: ability stored as ["m","e","d","i","c"] in JSON — should be ["medic"]*

### Northern Realms

#### Leader Cards
| Name | Owner | RFID |
|------|-------|------|
| Foltest - King of Temeria | - | 894239591804 |
| Foltest: Lord Commander of the North | - | - |
| Foltest: Son of Medell | - | - |
| Foltest: the Siegemaster | - | - |
| Foltest: The Steel-Forged | - | - |

#### Regular Cards
| Name | Strength | Range | Specialty | Ability | Owner | RFID |
|------|----------|-------|-----------|---------|-------|------|
| [Ballista: 1](#misconfigured-starter-cards) | 6 | ranged | - | - | - | 687410072884 |
| [Ballista: 2](#misconfigured-starter-cards) | 6 | ranged | - | - | - | 415216454997 |
| [Biting Frost](#misconfigured-starter-cards) | - | close | weather | - | - | 70998314254 |
| [Biting Frost](#misconfigured-starter-cards) | - | close | weather | - | - | 344265608686 |
| [Blue Stripes Commando](#misconfigured-starter-cards) | 4 | close | - | bond | - | 274958929373 |
| Blue Stripes Commando: 2 | 4 | close | - | bond | - | - |
| Catapult | 8 | ranged | - | bond | Declan Shanaghy | 278582611200 |
| [Clear Weather](#misconfigured-starter-cards) | - | - | weather | - | - | 2748534077 |
| [Clear Weather](#misconfigured-starter-cards) | - | - | weather | - | Declan Shanaghy | 964334538234 |
| Commander's Horn: 1 | - | close, ranged, siege | commander | - | Declan Shanaghy | 620696986138 |
| Crinfrid Reavers Dragon Hunter | 5 | ranged | - | bond | - | - |
| [Dethmold](#misconfigured-starter-cards) | 6 | ranged | - | - | - | 2211663133 |
| [Dun Banner Medic](#misconfigured-starter-cards) | 5 | siege | - | medic | - | 687812594970 |
| Esterad Thyssen | 10 | close | hero | - | - | - |
| Gaunter O'Dimm: Darkness 1 | 4 | ranged | - | muster | Declan Shanaghy | 826006457614 |
| [Impenetrable Fog](#misconfigured-starter-cards) | - | ranged | weather | - | - | 622533365197 |
| [Impenetrable Fog](#misconfigured-starter-cards) | - | ranged | weather | - | - | 2279689515 |
| [Impenetrable Fog](#misconfigured-starter-cards) | - | ranged | weather | - | Declan Shanaghy | 277643152763 |
| John Natalis | 10 | close | hero | - | - | - |
| [Kaedweni Siege Expert: 1](#misconfigured-starter-cards) | 1 | siege | - | morale | - | 275025972694 |
| [Kaedweni Siege Expert: 2](#misconfigured-starter-cards) | 1 | siege | - | morale | - | 3151121700 |
| [Kaedweni Siege Expert: 3](#misconfigured-starter-cards) | 1 | siege | - | morale | - | 277676707193 |
| Keira Metz | 5 | ranged | - | - | - | - |
| [Kiera Metz](#misconfigured-starter-cards) | 5 | ranged | - | - | - | 757455736135 |
| Philippa Eilhart | 10 | ranged | hero | - | Declan Shanaghy | 208604843325 |
| [Poor Fucking Infantry: 1](#misconfigured-starter-cards) | 1 | close | - | bond | - | 962523712853 |
| [Poor Fucking Infantry: 2](#misconfigured-starter-cards) | 1 | close | - | bond | - | 482946993582 |
| [Prince Stennis](#misconfigured-starter-cards) | 5 | close | - | spy | - | 71099895090 |
| [Redanian Foot Soldier: 1](#misconfigured-starter-cards) | 1 | close | - | - | - | 966147591613 |
| [Redanian Foot Soldier: 2](#misconfigured-starter-cards) | 1 | close | - | - | - | 893653306735 |
| [Sabrina Glevissig](#misconfigured-starter-cards) | 4 | ranged | - | - | - | 964033727802 |
| Scorch | - | close, ranged, siege | scorch | - | Declan Shanaghy | 552051232148 |
| [Sheldon Skaggs](#misconfigured-starter-cards) | 4 | ranged | - | - | - | 483517484365 |
| [Siege Tower: 1](#misconfigured-starter-cards) | 6 | siege | - | - | - | 482863238581 |
| Siege Tower: 2 | 6 | siege | - | - | Declan Shanaghy | 894658825474 |
| [Siegfried of Denesle](#misconfigured-starter-cards) | 5 | close | - | - | - | 483265891677 |
| Sigismund Dijkstra | 4 | close | - | spy | Declan Shanaghy | 986860965 |
| Sile de Tansarville | 5 | ranged | - | - | - | 828708703644 |
| Thaler | 1 | siege | - | spy | - | - |
| [Torrential Rain](#misconfigured-starter-cards) | - | siege | weather | - | - | 343880781289 |
| [Trebuchet: 1](#misconfigured-starter-cards) | 6 | siege | - | - | - | 416022809877 |
| [Trebuchet: 2](#misconfigured-starter-cards) | 6 | siege | - | - | - | 966164499898 |
| Triss Merigold | 7 | close | hero | - | Declan Shanaghy | 828539751860 |
| Vernon Roche | 10 | close | hero | - | - | - |
| [Ves](#misconfigured-starter-cards) | 5 | close | - | - | - | 1031981583646 |
| Villentretenmerth | 7 | close | - | scorch | Declan Shanaghy | 209829580150 |
| [Yarpen Zigrin](#misconfigured-starter-cards) | 2 | close | - | - | - | 138863267292 |
| Yennefer of Vengerberg | 7 | ranged | hero | medic | Declan Shanaghy | 691167907280 |
| Zoltan Chivay | 5 | close | - | - | Declan Shanaghy | 620730540568 |

### Scoia'tael

#### Leader Cards
| Name | Owner | RFID |
|------|-------|------|
| Francesca Findabair: Daisy of the Valley | - | - |
| Francesca Findabair: Hope of the aen Seidhe | - | - |
| Francesca Findabair - Pureblood Elf | - | 141127404911 |
| Francesca Findabair: Queen of Dol Blathanna | - | - |
| Francesca Findabair - The Beautiful | Declan Shanaghy | 553478147534 |

#### Regular Cards
| Name | Strength | Range | Specialty | Ability | Owner | RFID |
|------|----------|-------|-----------|---------|-------|------|
| Barclay Els | 6 | close, ranged | - | agile | - | - |
| [Biting Frost](#misconfigured-starter-cards) | - | close | weather | - | Declan Shanaghy | 141278203231 |
| [Biting Frost](#misconfigured-starter-cards) | - | close | weather | - | - | 482376306092 |
| [Biting Frost](#misconfigured-starter-cards) | - | close | weather | - | - | 553545190897 |
| Ciaran aep Easnillien | 3 | close, ranged | - | agile | - | - |
| [Ciaran aep Easnilie](#misconfigured-starter-cards) | 3 | close, ranged | - | agile | - | 965006413278 |
| Cirilla Fiona Elen Riannon | 15 | close | hero | - | Declan Shanaghy | 416307170583 |
| [Clear Weather](#misconfigured-starter-cards) | - | - | weather | - | - | 482040696283 |
| Decoy: 1 | - | - | decoy | - | Declan Shanaghy | 619110092078 |
| Decoy: 2 | - | - | decoy | - | Declan Shanaghy | 140825152881 |
| [Dennis Cranmer](#misconfigured-starter-cards) | 6 | close | - | - | - | 206307151272 |
| [Dol Blathanna Archer: 1](#misconfigured-starter-cards) | 4 | ranged | - | - | - | 414814326117 |
| [Dol Blathanna Scout: 1](#misconfigured-starter-cards) | 6 | close, ranged | - | agile | - | 894978247969 |
| [Dol Blathanna Scout: 2](#misconfigured-starter-cards) | 6 | close, ranged | - | agile | - | 416290655514 |
| [Dwarven Skirmisher: 1](#misconfigured-starter-cards) | 3 | close | - | muster | - | 3118157103 |
| [Dwarven Skirmisher: 2](#misconfigured-starter-cards) | 3 | close | - | muster | - | 550911036754 |
| [Dwarven Skirmisher: 3](#misconfigured-starter-cards) | 3 | close | - | muster | - | 299584903 |
| Eithne | 10 | ranged | hero | - | - | - |
| [Elven Skirmisher: 1](#misconfigured-starter-cards) | 2 | ranged | - | muster | - | 2648329482 |
| [Elven Skirmisher: 2](#misconfigured-starter-cards) | 2 | ranged | - | muster | - | 414143106459 |
| [Filavandrel aen Fidhail](#misconfigured-starter-cards) | 2 | close, ranged | - | agile | - | - |
| [Filavandrel aen Fidhail](#misconfigured-starter-cards) | 6 | close, ranged | - | agile | - | 206340509101 |
| Gaunter O'Dimm: Darkness 1 | 4 | ranged | - | - | Declan Shanaghy | 1272335824 |
| [Havekar Healer](#misconfigured-starter-cards) | 0 | ranged | - | medic | - | 1032534445315 |
| [Havekar Smuggler](#misconfigured-starter-cards) | 5 | close | - | muster | - | 619378724145 |
| Havekar Smuggler: 2 | 5 | close | - | muster | - | - |
| Havekar Smuggler: 3 | 5 | close | - | muster | - | - |
| [Ida Emean aep Sivney](#misconfigured-starter-cards) | 6 | ranged | - | - | - | 621761023430 |
| [Impenetrable Fog](#misconfigured-starter-cards) | - | ranged | weather | - | - | 964519546340 |
| [Impenetrable Fog](#misconfigured-starter-cards) | - | ranged | weather | - | - | 275428953589 |
| [Iorveth](#misconfigured-starter-cards) | 10 | ranged | hero | - | - | 485060201733 |
| Isengrim Faoiltiarna | 10 | close | hero | morale | - | - |
| [Mahakaman Defender: 1](#misconfigured-starter-cards) | 5 | close | - | - | - | 964200713476 |
| [Mahakaman Defender: 2](#misconfigured-starter-cards) | 5 | close | - | - | - | 482375847333 |
| [Mahakaman Defender: 3](#misconfigured-starter-cards) | 5 | close | - | - | - | 278650047803 |
| Mahakaman Defender: 4 | 5 | close | - | - | Declan Shanaghy | 484103834973 |
| Mahakaman Defender: 5 | 5 | close | - | - | Declan Shanaghy | 206675922363 |
| Mahakaman Defender: 6 | 5 | close | - | muster | - | - |
| Milva | 10 | ranged | - | morale | - | - |
| Riordain | 1 | ranged | - | - | - | - |
| [Riordan](#misconfigured-starter-cards) | 1 | ranged | - | - | - | 552756202921 |
| Saesenthessis | 10 | ranged | - | - | - | - |
| Schirru | 8 | siege | - | scorch | - | - |
| Scorch | - | close, ranged, siege | scorch | - | Declan Shanaghy | 895447682358 |
| [Torrential Rain](#misconfigured-starter-cards) | - | siege | weather | - | - | 69924703692 |
| [Toruviel](#misconfigured-starter-cards) | 2 | ranged | - | - | - | 206742900105 |
| [Vrihedd Brigade Recruit](#misconfigured-starter-cards) | 4 | ranged | - | - | - | 209477520749 |
| [Vrihedd Brigade Veteran: 1](#misconfigured-starter-cards) | 5 | close, ranged | - | agile | - | 71333924115 |
| [Vrihedd Brigade Veteran: 2](#misconfigured-starter-cards) | 5 | close, ranged | - | agile | - | 894206037370 |
| Yaevinn | 10 | close, ranged | - | agile | - | - |

### Skellige

#### Leader Cards
| Name | Owner | RFID |
|------|-------|------|
| Crach an Craite | - | 1033423375860 |

#### Regular Cards
| Name | Strength | Range | Specialty | Ability | Owner | RFID |
|------|----------|-------|-----------|---------|-------|------|
| Avallac'h | 0 | close | - | spy | Dylan Shanaghy | 481285852652 |
| [Berserker](#misconfigured-starter-cards) | 4 | close | - | berserker | - | 690934336982 |
| [Birna Bran](#misconfigured-starter-cards) | 2 | close | - | medic | - | 622315523548 |
| [Biting Frost: 1](#misconfigured-starter-cards) | - | close | weather | - | - | 622214860262 |
| [Biting Frost: 2](#misconfigured-starter-cards) | - | close | weather | - | - | 483601501504 |
| [Blueboy Lugos](#misconfigured-starter-cards) | 6 | close | - | - | - | 139836345606 |
| Cerys | 4 | close | hero | - | - | - |
| [Clan Brokvar Archer: 1](#misconfigured-starter-cards) | 6 | ranged | - | - | - | 1340427751 |
| [Clan Brokvar Archer: 2](#misconfigured-starter-cards) | 6 | ranged | - | - | - | 963161443592 |
| Clan Dimun Pirate | 6 | ranged | - | scorch | - | - |
| [Clan Drummond Shield Maiden: 1](#misconfigured-starter-cards) | 4 | close | - | bond | - | 347303333157 |
| Clan Drummond Shield Maiden: 2 | 4 | close | - | bond | Declan Shanaghy | 72374373725 |
| Clan Heymaey Skald | 4 | close | - | - | - | - |
| [Clan Heymaey Skals](#misconfigured-starter-cards) | 4 | close | - | - | - | 759989226988 |
| [Clan Tordarroch Armorsmith](#misconfigured-starter-cards) | 4 | close | - | - | - | 483483929935 |
| [Clan an Craite Warrior: 1](#misconfigured-starter-cards) | 6 | close | - | bond | - | 414546414925 |
| [Clan an Craite Warrior: 2](#misconfigured-starter-cards) | 6 | close | - | bond | - | 414143761829 |
| [Clan an Craite Warrior: 3](#misconfigured-starter-cards) | 6 | close | - | bond | - | 275161304569 |
| [Clear Weather: 1](#misconfigured-starter-cards) | - | - | weather | - | - | 895280696588 |
| Clear Weather: 2 | - | - | weather | - | Declan Shanaghy | 139584294349 |
| Commander's Horn | - | close, ranged, siege | commander | - | Declan Shanaghy | 1031041404264 |
| Dandelion | 2 | close | - | commander | Declan Shanaghy | 415434427718 |
| Decoy: 1 | - | - | decoy | - | Declan Shanaghy | 1033859976656 |
| [Donar an Hindar](#misconfigured-starter-cards) | 4 | close | - | - | - | 824900275553 |
| Draig Bon-Dhu | 2 | siege | - | commander | Declan Shanaghy | 1033390149117 |
| Ermion | 8 | ranged | hero | - | - | - |
| Gaunter O'Dimm: Darkness 1 | 4 | ranged | - | muster | Declan Shanaghy | 347537624364 |
| [Hjalmar](#misconfigured-starter-cards) | 10 | ranged | hero | - | - | 2346863908 |
| [Holger Blackhand](#misconfigured-starter-cards) | 4 | siege | - | - | - | 897394560399 |
| [Impenetrable Fog: 1](#misconfigured-starter-cards) | - | ranged | weather | - | - | 689071869280 |
| [Impenetrable Fog: 2](#misconfigured-starter-cards) | - | ranged | weather | - | - | 893770681703 |
| Kambi | 12 | close, ranged | - | morale, agile | - | - |
| King Bran | - | - | - | - | - | - |
| [Light Longship: 1](#misconfigured-starter-cards) | 4 | ranged | - | muster | - | 1033021509080 |
| [Light Longship: 2](#misconfigured-starter-cards) | 4 | ranged | - | muster | - | 688702704981 |
| [Madman Lugos](#misconfigured-starter-cards) | 6 | close | - | - | - | 3990900032 |
| [Mardroeme: 1](#misconfigured-starter-cards) | - | - | mardroeme | - | - | 965258268144 |
| Olaf | 12 | close, ranged | - | agile, morale | Declan Shanaghy | 137587477951 |
| Scorch: 1 | - | close, ranged, siege | scorch | - | Declan Shanaghy | 550625692967 |
| Scorch: 2 | - | close, ranged, siege | scorch | - | Declan Shanaghy | 826225216783 |
| [Svanrige](#misconfigured-starter-cards) | 4 | close | - | - | - | 757254344018 |
| [Torrential Rain: 1](#misconfigured-starter-cards) | - | siege | weather | - | - | 553780334019 |
| Torrential Rain: 2 | - | siege | weather | - | Declan Shanaghy | 346061294931 |
| [Transformed Vildkaarl](#misconfigured-starter-cards) | 14 | close | - | morale | - | 138007301548 |
| [Transformed Young Vildkaarl: 1](#misconfigured-starter-cards) | 8 | ranged | - | bond | - | 71703678259 |
| Transformed Young Vildkaarl: 2 | 8 | ranged | - | bond | Declan Shanaghy | 619059563820 |
| Triss Merigold | 7 | close | hero | - | Declan Shanaghy | 553007992276 |
| Udalryk | 4 | close | - | - | - | - |
| [Udalyrk](#misconfigured-starter-cards) | 4 | close | - | - | - | 208337325347 |
| [War Longship: 1](#misconfigured-starter-cards) | 6 | siege | - | bond | - | 550038883586 |
| [War Longship: 2](#misconfigured-starter-cards) | 6 | siege | - | bond | - | 622231178716 |
| [Young Berserker](#misconfigured-starter-cards) | 2 | ranged | - | berserker | - | 895397809466 |
| Zoltan Chivay | 5 | close | - | - | Declan Shanaghy | 482158005668 |

## 5. Anomalies

### Cards with Owner but No RFID
| Name | Faction | Owner | RFID |
|------|---------|-------|------|
| Crone: Weavess | Monsters | Dylan Shanaghy | - |
| Draug | Monsters | Dylan Shanaghy | - |
| Earth Elemental | Monsters | Dylan Shanaghy | - |
| Leshen | Monsters | Dylan Shanaghy | - |
| Vampire: Fleder | Monsters | Dylan Shanaghy | - |
| Vampire: Katakan | Monsters | Dylan Shanaghy | - |

### Cards with RFID but No Owner
*No cards found in this category.*

### Misconfigured Starter Cards
Cards where (owner or RFID is set) AND (starter is true AND the card is not a leader):

| Name | Faction | Owner | RFID |
|------|---------|-------|------|
| Arachas: 1 | Monsters | - | 622264733154 |
| Arachas: 2 | Monsters | - | 482409860530 |
| Arachas: Behemoth | Monsters | - | 345675550136 |
| Biting Frost: 1 | Monsters | - | 965039967680 |
| Biting Frost: 2 | Monsters | - | 553578745331 |
| Celaeno Harpy | Monsters | - | 482074250717 |
| Clear Weather: 1 | Monsters | - | 206340705706 |
| Cockatrice | Monsters | - | 346128403799 |
| Crone: Brewess | Monsters | - | 895011802403 |
| Endrega | Monsters | - | 416324209944 |
| Fire Elemental | Monsters | - | 3151711533 |
| Forktail | Monsters | - | 550944591184 |
| Frightener | Monsters | - | 333139333 |
| Gargoyle | Monsters | - | 2681883912 |
| Ghoul: 1 | Monsters | - | 414176660889 |
| Ghoul: 2 | Monsters | - | 206374063531 |
| Grave Hag | Monsters | - | 141160959337 |
| Griffin | Monsters | - | 1032567999757 |
| Ice Giant | Monsters | - | 550692801827 |
| Imlerith | Monsters | - | 964553100774 |
| Impenetrable Fog: 1 | Monsters | - | 275462508023 |
| Impenetrable Fog: 2 | Monsters | - | 621794577856 |
| Kayran | Monsters | - | 485093756187 |
| Nekker: 1 | Monsters | - | 964234268154 |
| Plague Maiden | Monsters | - | 482409401787 |
| Torrential Rain | Monsters | - | 278683602233 |
| Vampire: Garkhain | Monsters | - | 552789757359 |
| Werewolf | Monsters | - | 69958258114 |
| Wyvern | Monsters | - | 962673921368 |
| Assire var Anahid | Nilfgaardian | - | 414915579218 |
| Biting Frost: 1 | Nilfgaardian | - | 2430946616 |
| Biting Frost: 2 | Nilfgaardian | - | 1032149355784 |
| Cahir Mawr Dyffryn aep Ceallach | Nilfgaardian | - | 963194998026 |
| Clear Weather: 1 | Nilfgaardian | - | 347420839195 |
| Cynthia | Nilfgaardian | - | 278651030792 |
| Etolian Auxillary Archers | Nilfgaardian | - | 345759829369 |
| Impenetrable Fog: 1 | Nilfgaardian | - | 482762575295 |
| Impenetrable Fog: 2 | Nilfgaardian | - | 412499594691 |
| Impera Brigade Guard: 1 | Nilfgaardian | - | 895314251018 |
| Impera Brigade Guard: 2 | Nilfgaardian | - | 824933830015 |
| Impera Brigade Guard: 3 | Nilfgaardian | - | 414798007645 |
| Nausicaa Cavalry Rider: 1 | Nilfgaardian | - | 897428114829 |
| Nausicaa Cavalry Rider: 2 | Nilfgaardian | - | 2380418338 |
| Rainfarn | Nilfgaardian | - | 414227516862 |
| Renauld aep Matsen | Nilfgaardian | - | 893804236133 |
| Rotten Mangonel | Nilfgaardian | - | 553813888477 |
| Shilard Fitz-Oesterlen | Nilfgaardian | - | 4024454466 |
| Siege Engineer | Nilfgaardian | - | 1033055063514 |
| Siege Technician | Nilfgaardian | - | 688736259415 |
| Stefan Skellen | Nilfgaardian | - | 965291822578 |
| Tibor Eggebracht | Nilfgaardian | - | 414982688086 |
| Torrential Rain | Nilfgaardian | - | 71217532204 |
| Vanhemar | Nilfgaardian | - | 757287898444 |
| Vattier de Rideaux | Nilfgaardian | - | 138040855982 |
| Vreemde | Nilfgaardian | - | 71737232689 |
| Young Emissary: 1 | Nilfgaardian | - | 208370879777 |
| Zerrikanian Fire Scorpion | Nilfgaardian | - | 550072438016 |
| Ballista: 1 | Northern Realms | - | 687410072884 |
| Ballista: 2 | Northern Realms | - | 415216454997 |
| Biting Frost | Northern Realms | - | 70998314254 |
| Biting Frost | Northern Realms | - | 344265608686 |
| Blue Stripes Commando | Northern Realms | - | 274958929373 |
| Clear Weather | Northern Realms | - | 2748534077 |
| Dethmold | Northern Realms | - | 2211663133 |
| Dun Banner Medic | Northern Realms | - | 687812594970 |
| Impenetrable Fog | Northern Realms | - | 622533365197 |
| Impenetrable Fog | Northern Realms | - | 2279689515 |
| Kaedweni Siege Expert: 1 | Northern Realms | - | 275025972694 |
| Kaedweni Siege Expert: 2 | Northern Realms | - | 3151121700 |
| Kaedweni Siege Expert: 3 | Northern Realms | - | 277676707193 |
| Kiera Metz | Northern Realms | - | 757455736135 |
| Poor Fucking Infantry: 1 | Northern Realms | - | 962523712853 |
| Poor Fucking Infantry: 2 | Northern Realms | - | 482946993582 |
| Prince Stennis | Northern Realms | - | 71099895090 |
| Redanian Foot Soldier: 1 | Northern Realms | - | 966147591613 |
| Redanian Foot Soldier: 2 | Northern Realms | - | 893653306735 |
| Sabrina Glevissig | Northern Realms | - | 964033727802 |
| Sheldon Skaggs | Northern Realms | - | 483517484365 |
| Siege Tower: 1 | Northern Realms | - | 482863238581 |
| Siegfried of Denesle | Northern Realms | - | 483265891677 |
| Sile de Tansarville | Northern Realms | - | 828708703644 |
| Torrential Rain | Northern Realms | - | 343880781289 |
| Trebuchet: 1 | Northern Realms | - | 416022809877 |
| Trebuchet: 2 | Northern Realms | - | 966164499898 |
| Ves | Northern Realms | - | 1031981583646 |
| Yarpen Zigrin | Northern Realms | - | 138863267292 |
| Biting Frost | Scoia'tael | - | 482376306092 |
| Biting Frost | Scoia'tael | - | 553545190897 |
| Ciaran aep Easnilie | Scoia'tael | - | 965006413278 |
| Clear Weather | Scoia'tael | - | 482040696283 |
| Dennis Cranmer | Scoia'tael | - | 206307151272 |
| Dol Blathanna Archer: 1 | Scoia'tael | - | 414814326117 |
| Dol Blathanna Scout: 1 | Scoia'tael | - | 894978247969 |
| Dol Blathanna Scout: 2 | Scoia'tael | - | 416290655514 |
| Dwarven Skirmisher: 1 | Scoia'tael | - | 3118157103 |
| Dwarven Skirmisher: 2 | Scoia'tael | - | 550911036754 |
| Dwarven Skirmisher: 3 | Scoia'tael | - | 299584903 |
| Elven Skirmisher: 1 | Scoia'tael | - | 2648329482 |
| Elven Skirmisher: 2 | Scoia'tael | - | 414143106459 |
| Filavandrel aen Fidhail | Scoia'tael | - | 206340509101 |
| Havekar Healer | Scoia'tael | - | 1032534445315 |
| Havekar Smuggler | Scoia'tael | - | 619378724145 |
| Ida Emean aep Sivney | Scoia'tael | - | 621761023430 |
| Impenetrable Fog | Scoia'tael | - | 964519546340 |
| Impenetrable Fog | Scoia'tael | - | 275428953589 |
| Iorveth | Scoia'tael | - | 485060201733 |
| Mahakaman Defender: 1 | Scoia'tael | - | 964200713476 |
| Mahakaman Defender: 2 | Scoia'tael | - | 482375847333 |
| Mahakaman Defender: 3 | Scoia'tael | - | 278650047803 |
| Riordan | Scoia'tael | - | 552756202921 |
| Torrential Rain | Scoia'tael | - | 69924703692 |
| Toruviel | Scoia'tael | - | 206742900105 |
| Vrihedd Brigade Recruit | Scoia'tael | - | 209477520749 |
| Vrihedd Brigade Veteran: 1 | Scoia'tael | - | 71333924115 |
| Vrihedd Brigade Veteran: 2 | Scoia'tael | - | 894206037370 |
| Berserker | Skellige | - | 690934336982 |
| Birna Bran | Skellige | - | 622315523548 |
| Biting Frost: 1 | Skellige | - | 622214860262 |
| Biting Frost: 2 | Skellige | - | 483601501504 |
| Blueboy Lugos | Skellige | - | 139836345606 |
| Clan Brokvar Archer: 1 | Skellige | - | 1340427751 |
| Clan Brokvar Archer: 2 | Skellige | - | 963161443592 |
| Clan Drummond Shield Maiden: 1 | Skellige | - | 347303333157 |
| Clan Heymaey Skals | Skellige | - | 759989226988 |
| Clan Tordarroch Armorsmith | Skellige | - | 483483929935 |
| Clan an Craite Warrior: 1 | Skellige | - | 414546414925 |
| Clan an Craite Warrior: 2 | Skellige | - | 414143761829 |
| Clan an Craite Warrior: 3 | Skellige | - | 275161304569 |
| Clear Weather: 1 | Skellige | - | 895280696588 |
| Donar an Hindar | Skellige | - | 824900275553 |
| Hjalmar | Skellige | - | 2346863908 |
| Holger Blackhand | Skellige | - | 897394560399 |
| Impenetrable Fog: 1 | Skellige | - | 689071869280 |
| Impenetrable Fog: 2 | Skellige | - | 893770681703 |
| Light Longship: 1 | Skellige | - | 1033021509080 |
| Light Longship: 2 | Skellige | - | 688702704981 |
| Madman Lugos | Skellige | - | 3990900032 |
| Mardroeme: 1 | Skellige | - | 965258268144 |
| Svanrige | Skellige | - | 757254344018 |
| Torrential Rain: 1 | Skellige | - | 553780334019 |
| Transformed Vildkaarl | Skellige | - | 138007301548 |
| Transformed Young Vildkaarl: 1 | Skellige | - | 71703678259 |
| Udalyrk | Skellige | - | 208337325347 |
| War Longship: 1 | Skellige | - | 550038883586 |
| War Longship: 2 | Skellige | - | 622231178716 |
| Young Berserker | Skellige | - | 895397809466 |
