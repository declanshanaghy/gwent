---
description: Generate a comprehensive card collection report from the card JSON database
user_invocable: true
---

# Card Report Skill

Generate a comprehensive Markdown report analyzing the Gwent card database.

## Instructions

Read all JSON files in `software/data/cards/` and its subdirectories to extract card information including faction, name, strength, range, specialty, abilities, and ownership data.

Generate the report with the following structure and write it to `software/data/cards/CardReport.md`.

**IMPORTANT**: Include the regeneration prompt comment block at the top of the output file (see section 0 below).

### 0. Report Header

Start the file with this HTML comment block so future regeneration is self-documenting:

```markdown
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
```

### 1. Card Distribution by Faction

Create a summary table with columns: Faction, Card Count, Percentage. Include a **Total** row. Factions: Monsters, Nilfgaardian, Northern Realms, Scoia'tael, Skellige.

### 2. Card Ownership Summary

Table with columns: Faction, Owned Cards, Total Cards, Percentage Owned. A card is "owned" if it has an `"owner"` field. Include a **Total** row.

### 3. Card Statistics

Include these subsections:

- **Overall Statistics**: Total cards, owned vs not owned with percentages
- **Card Types**: Unit cards, weather cards, leader cards, hero cards
- **Leader Cards Analysis**: Total count, distribution by faction, owned leaders listed by name, leaders with RFID
- **Hero Cards Analysis**: Total count, distribution by faction
- **Weather Cards Breakdown**: Total count, distribution by faction
- **RFID Registered Cards Analysis**: Total with RFID, distribution by faction
- **Starter Cards Analysis**: Total starters, distribution by faction
- **Interesting Observations**: Notable patterns in the data

### 4. Cards by Faction

For each faction, create:
1. **Leader Cards** table: Name, Owner, RFID
2. **Regular Cards** table (all non-leaders): Name, Strength, Range, Specialty, Ability, Owner, RFID

**IMPORTANT**: Do NOT abbreviate with placeholder text like "Due to the large number of cards...". List every single card in the tables.

### 5. Anomalies

Three tables, each with columns Name, Faction, Owner, RFID:
1. **Cards with Owner but No RFID**
2. **Cards with RFID but No Owner**
3. **Misconfigured Starter Cards** — cards where (owner or rfid is set) AND (starter is true AND the card is not a leader)

### Cross-referencing

In the Section 4 faction tables, any card that appears in the "Misconfigured Starter Cards" anomaly table should have its name linked to the anomalies section using a markdown anchor: `[Card Name](#misconfigured-starter-cards)`. This makes it easy to identify misconfigured cards while browsing faction tables.
