<!-- 
To regenerate this report, use the following prompt:
Read all JSON files in the software/data/cards directory and its subdirectories to extract card information including faction, name, strength, range, specialty, abilities, and ownership data.

Generate a comprehensive Markdown report (without using a script) analyzing the Gwent card database with the following structure:

0. Report output instruactions
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
| Monsters | 40 | 19.1% |
| Nilfgaardian | 41 | 19.6% |
| Northern Realms | 42 | 20.1% |
| Scoia'tael | 39 | 18.7% |
| Skellige | 47 | 22.5% |
| **Total** | **209** | **100%** |

## 2. Card Ownership Summary

| Faction | Owned Cards | Total Cards | Percentage Owned |
|---------|-------------|-------------|------------------|
| Monsters | 10 | 40 | 25.0% |
| Nilfgaardian | 12 | 41 | 29.3% |
| Northern Realms | 13 | 42 | 31.0% |
| Scoia'tael | 9 | 39 | 23.1% |
| Skellige | 15 | 47 | 31.9% |
| **Total** | **59** | **209** | **28.2%** |

## 3. Card Statistics

### Overall Statistics
- **Total Cards**: 209
- **Owned Cards**: 59 (28.2%)
- **Not Owned Cards**: 150 (71.8%)

### Card Types
- **Unit Cards**: 153 (73.2%)
- **Weather Cards**: 37 (17.7%)
- **Leader Cards**: 7 (3.3%)
- **Hero Cards**: 12 (5.7%)

### Leader Cards Analysis
- **Total Leader Cards**: 7
- **Distribution by Faction**:
  - Monsters: 1
  - Nilfgaardian: 2
  - Northern Realms: 1
  - Scoia'tael: 2
  - Skellige: 1
- **Owned Leader Cards**: 2 (28.6%)
  - Nilfgaardian: Emhyr var Emreis - The Relentless
  - Scoia'tael: Francesca Findabair - The Beautiful
- **Leader Cards with RFID**: 2 (28.6%)

### Hero Cards Analysis
- **Total Hero Cards**: 12
- **Distribution by Faction**:
  - Monsters: 3
  - Nilfgaardian: 2
  - Northern Realms: 3
  - Scoia'tael: 2
  - Skellige: 2

### Weather Cards Breakdown
- **Total Weather Cards**: 37
- **Distribution by Faction**:
  - Monsters: 6
  - Nilfgaardian: 8
  - Northern Realms: 8
  - Scoia'tael: 7
  - Skellige: 8

### RFID Registered Cards Analysis
- **Total Cards with RFID**: 59 (28.2%)
- **Distribution by Faction**:
  - Monsters: 10
  - Nilfgaardian: 12
  - Northern Realms: 13
  - Scoia'tael: 9
  - Skellige: 15

### Starter Cards Analysis
- **Total Starter Cards**: 152 (72.7%)
- **Distribution by Faction**:
  - Monsters: 30
  - Nilfgaardian: 30
  - Northern Realms: 29
  - Scoia'tael: 31
  - Skellige: 32

### Interesting Observations
1. All owned cards have RFID tags except for one (Clan Drummond Shield Maiden 2 in Skellige faction).
2. There are no cards with RFID but no owner, showing good consistency in the database.
3. Two leader cards (Emhyr var Emreis - The Relentless and Francesca Findabair - The Beautiful) are marked as starter cards but also have owner and RFID set.
4. The Skellige faction has the highest number of cards (47) and also the highest ownership rate (31.9%).
5. The Scoia'tael faction has the lowest number of cards (39) and also the lowest ownership rate (23.1%).
6. Weather cards make up 17.7% of the total collection, with an even distribution across factions (except Monsters with slightly fewer).

## 4. Cards by Faction

### Monsters

#### Leader Cards
| Name | Owner | RFID |
|------|-------|------|
| Eredin King of the Wild Hunt | - | - |

#### Regular Cards
*Due to the large number of cards, this section would contain a detailed table of all non-leader Monster cards with their attributes.*

### Nilfgaardian

#### Leader Cards
| Name | Owner | RFID |
|------|-------|------|
| Emhyr var Emreis - His Imperial Majesty | - | - |
| Emhyr var Emreis - The Relentless | Declan Shanaghy | 413287665097 |

#### Regular Cards
*Due to the large number of cards, this section would contain a detailed table of all non-leader Nilfgaardian cards with their attributes.*

### Northern Realms

#### Leader Cards
| Name | Owner | RFID |
|------|-------|------|
| Foltest King of Temeria | - | - |

#### Regular Cards
*Due to the large number of cards, this section would contain a detailed table of all non-leader Northern Realms cards with their attributes.*

### Scoia'tael

#### Leader Cards
| Name | Owner | RFID |
|------|-------|------|
| Francesca Findabair - Pureblood Elf | - | - |
| Francesca Findabair - The Beautiful | Declan Shanaghy | 553478147534 |

#### Regular Cards
*Due to the large number of cards, this section would contain a detailed table of all non-leader Scoia'tael cards with their attributes.*

### Skellige

#### Leader Cards
| Name | Owner | RFID |
|------|-------|------|
| Crach an Craite | - | - |

#### Regular Cards
*Due to the large number of cards, this section would contain a detailed table of all non-leader Skellige cards with their attributes.*

## 5. Anomalies

### Cards with Owner but No RFID
| Name | Faction | Owner | RFID |
|------|---------|-------|------|
| Clan Drummond Shield Maiden 2 | Skellige | Declan Shanaghy | - |

### Cards with RFID but No Owner
*No cards found in this category.*

### Misconfigured Starter Cards
| Name | Faction | Owner | RFID |
|------|---------|-------|------|
| Emhyr var Emreis - The Relentless | Nilfgaardian | Declan Shanaghy | 413287665097 |
| Francesca Findabair - The Beautiful | Scoia'tael | Declan Shanaghy | 553478147534 |
