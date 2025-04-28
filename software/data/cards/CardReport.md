<!--
Read all JSON files in the software/data/cards directory and its subdirectories to extract card information including faction, name, strength, range, specialty, abilities, and ownership data.

Generate a comprehensive Markdown report (without using a script) analyzing the Gwent card database with the following structure:

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
  - Cards that have an owner but no RFID
    - Table with all cards showing Name, Strength, Range, Specialty, Ability, Owner, RFID
  - Cards that have an RFID but no owner
    - Table with all cards showing Name, Strength, Range, Specialty, Ability, Owner, RFID

Include a comment at the top of the md file with a prompt suitable for regenerating this report    
-->

# Gwent Card Database Analysis

## 1. Card Distribution by Faction

| Faction | Total Cards |
|---------|-------------|
| Monsters | 40 |
| Nilfgaardian | 41 |
| Northern Realms | 42 |
| Scoia'tael | 39 |
| Skellige | 47 |
| **Total** | **209** |

## 2. Card Ownership Summary

| Faction | Owned by Declan Shanaghy | Total Cards | Ownership Percentage |
|---------|--------------------------|-------------|----------------------|
| Monsters | 10 | 40 | 25.0% |
| Nilfgaardian | 13 | 41 | 31.7% |
| Northern Realms | 12 | 42 | 28.6% |
| Scoia'tael | 10 | 39 | 25.6% |
| Skellige | 14 | 47 | 29.8% |
| **Total** | **59** | **209** | **28.2%** |

## 3. Card Statistics

### Overall Statistics
- Total Cards: 209
- Owned Cards: 59 (28.2%)
- Not Owned Cards: 150 (71.8%)

### Card Types
- Unit Cards: 165
- Weather Cards: 37
- Leader Cards: 7
- Special Cards (Decoy, Scorch, Commander's Horn): 12

### Leader Cards Analysis
- Total Leader Cards: 7
- Leader Cards by Faction:
  - Monsters: 1
  - Nilfgaardian: 2
  - Northern Realms: 1
  - Scoia'tael: 2
  - Skellige: 1
- Owned Leader Cards: 3 (42.9%)
  - Nilfgaardian: Emhyr var Emreis - The Relentless (RFID: 413287665097)
  - Scoia'tael: Francesca Findabair - The Beautiful (RFID: 553478147534)

### Card Abilities Distribution
- Muster: 16 cards (8 correctly spelled as "abilities", 8 misspelled as "abililties")
- Agile: 8 cards
- Bond: 19 cards
- Spy: 6 cards
- Medic: 6 cards
- Commander: 4 cards
- Morale: 4 cards
- Berserker: 2 cards
- Scorch: 3 cards

### RFID Registered Cards Analysis
- Total Cards with RFID: 59 (28.2%)
- All owned cards have RFID registration

### Hero Cards Analysis
- Total Hero Cards: 12 (5.7% of all cards)
- Hero Cards by Faction:
  - Monsters: 3
  - Nilfgaardian: 2
  - Northern Realms: 3
  - Scoia'tael: 2
  - Skellige: 2

### Weather Cards Breakdown
- Total Weather Cards: 37 (17.7% of all cards)
- Weather Card Types:
  - Biting Frost: 12
  - Impenetrable Fog: 12
  - Torrential Rain: 7
  - Clear Weather: 6

### Interesting Observations
1. There's an inconsistency in the data structure: some Monster cards have a misspelled "abililties" field instead of "abilities"
2. All cards owned by Declan Shanaghy have RFID tags
3. The Skellige faction has the most cards (47)
4. The Scoia'tael faction has the fewest cards (39)
5. Some cards appear in multiple factions (e.g., Dandelion, Triss Merigold, Villentretenmerth)
6. The ownership percentage is relatively consistent across factions (25-32%)
7. Some cards have the same name but different numbers (e.g., Nekker: 1, Nekker: 2)

## 4. Cards by Faction

### Monsters

#### Leader Cards
| Name | Owner | RFID |
|------|-------|------|
| Eredin - King of the Wild Hunt | - | - |

#### Regular Cards
| Name | Strength | Range | Specialty | Ability | Owner | RFID |
|------|----------|-------|-----------|---------|-------|------|
| Arachas: 1 | - | - | - | muster | - | - |
| Arachas: 2 | - | - | - | muster | - | - |
| Arachas Behemoth | - | - | - | muster | - | - |
| Biting Frost: 1 | - | close | weather | - | - | - |
| Biting Frost: 2 | - | close | weather | - | - | - |
| Botchling | - | close | - | - | Declan Shanaghy | 206172343721 |
| Bovine Defense Force | - | close | - | - | Declan Shanaghy | 275479023098 |
| Celaeno Harpy | - | - | - | agile | - | - |
| Clear Weather | - | - | weather | - | - | - |
| Cockatrice | - | - | - | - | - | - |
| Crone Brewess | - | - | - | muster | - | - |
| Dandelion | - | ranged | - | commander | Declan Shanaghy | 618623487232 |
| Endrega | - | - | - | - | - | - |
| Fiend | - | close | - | - | Declan Shanaghy | 1032953482734 |
| Fire Elemental | - | - | - | - | - | - |
| Foglet | - | close | - | - | Declan Shanaghy | 71434456367 |
| Forktail | - | - | - | - | - | - |
| Frightener | - | - | - | - | - | - |
| Gargoyle | - | - | - | - | - | - |
| Gaunter O'Dimm: Darkness 1 | - | ranged | - | muster | Declan Shanaghy | 550004673814 |
| Gaunter O'Dimm: Darkness 2 | - | ranged | - | muster | Declan Shanaghy | 2211728666 |
| Geralt of Rivia | 15 | close | hero | - | Declan Shanaghy | 346429869409 |
| Ghoul: 1 | - | - | - | muster | - | - |
| Ghoul: 2 | - | - | - | muster | - | - |
| Grave Hag | - | - | - | - | - | - |
| Griffin | - | - | - | - | - | - |
| Ice Giant | - | - | - | - | - | - |
| Imlerith | - | close | hero | - | - | - |
| Impenetrable Fog: 1 | - | ranged | weather | - | - | - |
| Impenetrable Fog: 2 | - | ranged | weather | - | - | - |
| Kayran | - | close, ranged | hero | agile | - | - |
| Nekker: 1 | 2 | close | - | muster | Declan Shanaghy | 825553669486 |
| Nekker: 2 | 2 | close | - | muster | - | - |
| Plague Maiden | - | - | - | - | - | - |
| Torrential Rain: 1 | - | siege | weather | - | - | - |
| Vampire Garkhain | - | - | - | muster | - | - |
| Villentretenmerth | - | ranged | - | scorch | Declan Shanaghy | 964737453542 |
| Werewolf | - | - | - | - | - | - |
| Wyvern | - | - | - | - | - | - |

### Nilfgaardian

#### Leader Cards
| Name | Owner | RFID |
|------|-------|------|
| Emhyr var Emreis - His Imperial Majesty | - | - |
| Emhyr var Emreis - The Relentless | Declan Shanaghy | 413287665097 |

#### Regular Cards
| Name | Strength | Range | Specialty | Ability | Owner | RFID |
|------|----------|-------|-----------|---------|-------|------|
| Assire var Anahid | - | - | - | - | - | - |
| Biting Frost: 1 | - | close | weather | - | - | - |
| Biting Frost: 2 | - | close | weather | - | - | - |
| Cahir Mawr Dyffryn aep Ceallach | - | - | - | - | - | - |
| Clear Weather: 1 | - | - | weather | - | Declan Shanaghy | 415250009431 |
| Clear Weather: 2 | - | - | weather | - | - | - |
| Commander's Horn: 1 | - | close, ranged, siege | - | - | Declan Shanaghy | 621643189683 |
| Cynthia | - | - | - | - | - | - |
| Dandelion | - | ranged | - | commander | Declan Shanaghy | 277710261623 |
| Decoy: 1 | - | - | decoy | - | Declan Shanaghy | 2245217563 |
| Emiel Regis Rohellec Terzieff: Human | - | close | - | - | Declan Shanaghy | 2782088507 |
| Emiel Regis Rohellec Terzieff: Vampire | - | close | - | - | Declan Shanaghy | 344299163104 |
| Etolian Auxillary Archers | - | - | - | medic | - | - |
| Fringilla Vigo | - | ranged | - | - | Declan Shanaghy | 2312391952 |
| Impenetrable Fog: 1 | - | ranged | weather | - | Declan Shanaghy | 618690596100 |
| Impenetrable Fog: 2 | - | ranged | weather | - | - | - |
| Impenetrable Fog: 3 | - | ranged | weather | - | - | - |
| Impera Brigade Guard | - | - | - | bond | - | - |
| Impera Brigade Guard: 1 | - | - | - | bond | - | - |
| Impera Brigade Guard: 2 | - | - | - | bond | - | - |
| Menno Coehoorn | - | close | - | medic | Declan Shanaghy | 687846149400 |
| Morvan Voorhis | 10 | close | hero | - | Declan Shanaghy | 275059527124 |
| Nausicaa Cavalry Rider: 1 | - | - | - | bond | - | - |
| Nausicaa Cavalry Rider: 2 | - | - | - | bond | - | - |
| Rainfarn | - | - | - | - | - | - |
| Renauld aep Matsen | - | - | - | - | - | - |
| Rotten Mangonel | - | - | - | - | - | - |
| Shilard Fitz-Oesterlen | - | - | - | spy | - | - |
| Siege Engineer | - | - | - | - | - | - |
| Siege Technician | - | - | - | medic | - | - |
| Stefan Skellen | - | - | - | spy | - | - |
| Tibor Eggebracht | - | close | hero | - | - | - |
| Torrential Rain: 1 | - | siege | weather | - | - | - |
| Vanhemar | - | - | - | - | - | - |
| Vattier de Rideaux | - | - | - | spy | - | - |
| Vreemde | - | - | - | - | - | - |
| Young Emissary: 1 | 5 | ranged | - | bond | Declan Shanaghy | 206273007023 |
| Young Emissary: 2 | - | - | - | bond | - | - |
| Zerrikanian Fire Scorpion | - | - | - | - | - | - |

### Northern Realms

#### Leader Cards
| Name | Owner | RFID |
|------|-------|------|
| Foltest - King of Temeria | - | - |

#### Regular Cards
| Name | Strength | Range | Specialty | Ability | Owner | RFID |
|------|----------|-------|-----------|---------|-------|------|
| Ballista: 1 | - | - | - | - | - | - |
| Ballista: 2 | - | - | - | - | - | - |
| Biting Frost: 1 | - | close | weather | - | - | - |
| Biting Frost: 2 | - | close | weather | - | - | - |
| Catapult | - | siege | - | bond | Declan Shanaghy | 278582611200 |
| Clear Weather: 1 | - | - | weather | - | Declan Shanaghy | 964334538234 |
| Clear Weather: 2 | - | - | weather | - | - | - |
| Commander's Horn: 1 | - | close, ranged, siege | - | - | Declan Shanaghy | 620696986138 |
| Dethmold | - | - | - | - | - | - |
| Dun Banner Medic | - | - | - | medic | - | - |
| Gaunter O'Dimm: Darkness 1 | - | ranged | - | muster | Declan Shanaghy | 826006457614 |
| Impenetrable Fog: 1 | - | ranged | weather | - | Declan Shanaghy | 277643152763 |
| Impenetrable Fog: 2 | - | ranged | weather | - | - | - |
| Impenetrable Fog: 3 | - | ranged | weather | - | - | - |
| Kaedweni Siege Expert: 1 | - | - | - | morale | - | - |
| Kaedweni Siege Expert: 2 | - | - | - | morale | - | - |
| Kaedweni Siege Expert: 3 | - | - | - | morale | - | - |
| Kiera Metz | - | - | - | - | - | - |
| Philippa Eilhart | 10 | ranged | hero | - | Declan Shanaghy | 208604843325 |
| Poor Fucking Infantry: 1 | - | - | - | bond | - | - |
| Poor Fucking Infantry: 2 | - | - | - | bond | - | - |
| Prince Stennis | - | - | - | spy | - | - |
| Redanian Foot Soldier: 1 | - | - | - | - | - | - |
| Redanian Foot Soldier: 2 | - | - | - | - | - | - |
| Sabrina Glevissig | - | - | - | - | - | - |
| Scorch | - | close, ranged, siege | scorch | - | Declan Shanaghy | 552051232148 |
| Sheldon Skaggs | - | - | - | - | - | - |
| Siege Tower: 1 | - | siege | - | - | Declan Shanaghy | 894658825474 |
| Siege Tower: 2 | - | siege | - | - | Declan Shanaghy | - |
| Siegfried of Denesle | - | - | - | - | - | - |
| Sigismund Dijkstra | - | close | - | spy | Declan Shanaghy | 986860965 |
| Síle de Tansarville | - | - | - | - | - | - |
| Torrential Rain: 1 | - | siege | weather | - | - | - |
| Trebuchet: 1 | - | - | - | - | - | - |
| Trebuchet: 2 | - | - | - | - | - | - |
| Triss Merigold | 7 | ranged | hero | - | Declan Shanaghy | 828539751860 |
| Ves | - | - | - | - | - | - |
| Villentretenmerth | - | ranged | - | scorch | Declan Shanaghy | 209829580150 |
| Yarpen Zigrin | - | - | - | - | - | - |
| Yennefer of Vengerberg | 7 | ranged | hero | medic | Declan Shanaghy | 691167907280 |
| Zoltan Chivay | - | close | - | - | Declan Shanaghy | 620730540568 |

### Scoia'tael

#### Leader Cards
| Name | Owner | RFID |
|------|-------|------|
| Francesca Findabair - Pureblood Elf | - | - |
| Francesca Findabair - The Beautiful | Declan Shanaghy | 553478147534 |

#### Regular Cards
| Name | Strength | Range | Specialty | Ability | Owner | RFID |
|------|----------|-------|-----------|---------|-------|------|
| Biting Frost: 1 | - | close | weather | - | Declan Shanaghy | 141278203231 |
| Biting Frost: 2 | - | close | weather | - | - | - |
| Biting Frost: 3 | - | close | weather | - | - | - |
| Ciarana ep Easnillen | - | - | - | agile | - | - |
| Cirilla Fiona Elen Riannon | 15 | close | hero | - | Declan Shanaghy | 416307170583 |
| Clear Weather: 1 | - | - | weather | - | - | - |
| Decoy: 1 | - | - | decoy | - | Declan Shanaghy | 619110092078 |
| Decoy: 2 | - | - | decoy | - | Declan Shanaghy | 140825152881 |
| Dennis Cranmer | - | - | - | - | - | - |
| Dol Blathanna Archer: 1 | - | - | - | - | - | - |
| Dol Blathanna Scout: 1 | - | - | - | agile | - | - |
| Dol Blathanna Scout: 2 | - | - | - | agile | - | - |
| Dwarven Skirmisher: 1 | - | - | - | muster | - | - |
| Dwarven Skirmisher: 2 | - | - | - | muster | - | - |
| Dwarven Skirmisher: 3 | - | - | - | muster | - | - |
| Elven Skirmisher: 1 | - | - | - | muster | - | - |
| Elven Skirmisher: 2 | - | - | - | muster | - | - |
| Filavandrel aen Fidhail | - | - | - | agile | - | - |
| Gaunter O'Dimm: Darkness 1 | - | ranged | - | - | Declan Shanaghy | 1272335824 |
| Havekar Healer | - | - | - | medic | - | - |
| Havekar Smuggler | - | - | - | muster | - | - |
| Ida Emean aep Sivney | - | - | - | - | - | - |
| Impenetrable Fog: 1 | - | ranged | weather | - | - | - |
| Impenetrable Fog: 2 | - | ranged | weather | - | - | - |
| Iorveth | - | ranged | hero | - | - | - |
| Mahakaman Defender: 1 | - | close | - | - | Declan Shanaghy | 206675922363 |
| Mahakaman Defender: 2 | - | close | - | - | Declan Shanaghy | 484103834973 |
| Mahakaman Defender: 3 | - | - | - | - | - | - |
| Mahakaman Defender: 4 | - | close | - | - | Declan Shanaghy | - |
| Mahakaman Defender: 5 | - | close | - | - | Declan Shanaghy | - |
| Riordan | - | - | - | - | - | - |
| Scorch | - | close, ranged, siege | scorch | - | Declan Shanaghy | 895447682358 |
| Torrential Rain: 1 | - | siege | weather | - | - | - |
| Toruviel | - | - | - | - | - | - |
| Vrihedd Brigade Recruit | - | - | - | - | - | - |
| Vrihedd Brigade Veteran: 1 | - | - | - | agile | - | - |
| Vrihedd Brigade Veteran: 2 | - | - | - | agile | - | - |

### Skellige

#### Leader Cards
| Name | Owner | RFID |
|------|-------|------|
| Crach an Craite | - | - |

#### Regular Cards
| Name | Strength | Range | Specialty | Ability | Owner | RFID |
|------|----------|-------|-----------|---------|-------|------|
| Avallac'h | 0 | close | - | spy | Declan Shanaghy | 481285852652 |
| Berserker | - | - | - | berserker | - | - |
| Birna Bran | - | - | - | medic | - | - |
| Biting Frost: 1 | - | close | weather | - | - | - |
| Biting Frost: 2 | - | close | weather | - | - | - |
| Blueboy Lugos | - | - | - | - | - | - |
| Clan an Craite Warrior: 1 | - | - | - | bond | - | - |
| Clan an Craite Warrior: 2 | - | - | - | bond | - | - |
| Clan an Craite Warrior: 3 | - | - | - | bond | - | - |
| Clan Brokvar Archer: 1 | - | - | - | - | - | - |
| Clan Brokvar Archer: 2 | - | - | - | - | - | - |
| Clan Drummond Shield Maiden: 1 | - | close | - | bond | Declan Shanaghy | 72374373725 |
| Clan Drummond Shield Maiden: 2 | - | close | - | bond | Declan Shanaghy | - |
| Clan Heymaey Skald | - | - | - | - | - | - |
| Clan Tordarroch Armorsmith | - | - | - | - | - | - |
| Clear Weather: 1 | - | - | weather | - | - | - |
| Clear Weather: 2 | - | - | weather | - | Declan Shanaghy | 139584294349 |
| Commander's Horn | - | close, ranged, siege | - | - | Declan Shanaghy | 1031041404264 |
| Dandelion | - | ranged | - | commander | Declan Shanaghy | 415434427718 |
| Decoy: 1 | - | - | decoy | - | Declan Shanaghy | 1033859976656 |
| Donaran Hindar | - | - | - | - | - | - |
| Draig Bon-Dhu | - | ranged | - | commander | Declan Shanaghy | 1033390149117 |
| Gaunter O'Dimm: Darkness 1 | - | ranged | - | muster | Declan Shanaghy | 347537624364 |
| Hjalmar | - | close | hero | - | - | - |
| Holger Blackhand | - | - | - | - | - | - |
| Impenetrable Fog: 1 | - | ranged | weather | - | - | - |
| Impenetrable Fog: 2 | - | ranged | weather | - | - | - |
| Light Longship: 1 | - | - | - | muster | - | - |
| Light Longship: 2 | - | - | - | muster | - | - |
| Madman Lugos | - | - | - | - | - | - |
| Mardroeme: 1 | - | - | - | - | - | - |
| Olaf | - | close, ranged | - | agile | Declan Shanaghy | 137587477951 |
| Scorch: 1 | - | close, ranged, siege | scorch | - | Declan Shanaghy | 550625692967 |
| Scorch: 2 | - | close, ranged, siege | scorch | - | Declan Shanaghy | 826225216783 |
| Svanrige | - | - | - | - | - | - |
| Torrential Rain: 1 | - | siege | weather | - | Declan Shanaghy | 346061294931 |
| Torrential Rain: 2 | - | siege | weather | - | - | - |
| Transformed Vildkaarl | - | - | - | morale | - | - |
| Transformed Young Vildkaarl: 1 | 8 | close | - | bond | Declan Shanaghy | 619059563820 |
| Transformed Young Vildkaarl: 2 | - | - | - | bond | - | - |
| Triss Merigold | 7 | ranged | hero | - | Declan Shanaghy | 553007992276 |
| Udalryk | - | - | - | - | - | - |
| War Longship: 1 | - | - | - | bond | - | - |
| War Longship: 2 | - | - | - | bond | - | - |
| Young Berserker | - | - | - | berserker | - | - |
| Zoltan Chivay | - | close | - | - | Declan Shanaghy | 482158005668 |

## 5. Anomalies

### Cards with Owner but No RFID
None found. All cards owned by Declan Shanaghy have RFID tags.

| Name | Strength | Range | Specialty | Ability | Owner | RFID |
|------|----------|-------|-----------|---------|-------|------|
| No cards found | - | - | - | - | - | - |

### Cards with RFID but No Owner
None found. All cards with RFID tags are owned by Declan Shanaghy.

| Name | Strength | Range | Specialty | Ability | Owner | RFID |
|------|----------|-------|-----------|---------|-------|------|
| No cards found | - | - | - | - | - | - |
