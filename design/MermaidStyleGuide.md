# 🎨 Gwent Companion Mermaid Style Guide 🧙‍♂️

This document defines the standard styling for all mermaid diagrams in the Gwent Companion project, ensuring visual consistency across all documentation.

## 🔮 Base Template

Include this initialization directive at the beginning of all mermaid diagrams:

```mermaid
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#6d1a36',
    'primaryTextColor': '#fff',
    'primaryBorderColor': '#7C4DFF',
    'lineColor': '#7C4DFF',
    'secondaryColor': '#D7CCC8',
    'tertiaryColor': '#EFEBE9',
    'fontFamily': 'Courier New',
    'fontSize': '16px'
  }
}}%%
```

## 🎭 Standard Class Definitions

Use these standard class definitions for consistent styling across all diagrams:

```mermaid
classDef hardware fill:#A1887F,stroke:#5D4037,stroke-width:2px,color:#fff,font-family:'Courier New',font-weight:bold
classDef software fill:#BCAAA4,stroke:#5D4037,stroke-width:2px,color:#3E2723,font-family:'Courier New',font-weight:bold
classDef data fill:#D7CCC8,stroke:#5D4037,stroke-width:2px,color:#3E2723,font-family:'Courier New',font-style:italic
classDef process fill:#EFEBE9,stroke:#5D4037,stroke-width:2px,color:#3E2723,font-family:'Courier New'
classDef ui fill:#F5F5F5,stroke:#5D4037,stroke-width:2px,color:#3E2723,font-family:'Courier New'
classDef start fill:#d5e8d4,stroke:#82b366,stroke-width:2px,font-family:'Courier New'
classDef endNode fill:#f8cecc,stroke:#b85450,stroke-width:2px,font-family:'Courier New'
classDef decision fill:#fff2cc,stroke:#d6b656,stroke-width:1px,font-family:'Courier New'
```

## 🎨 Color Palette

Use these standard colors for all diagrams:

| Element Type | Background | Border | Text |
|--------------|------------|--------|------|
| Primary | #6d1a36 (Burgundy) | #5D4037 (Dark Brown) | #FFFFFF (White) |
| Secondary | #d4af37 (Gold) | #7C4DFF (Purple) | #3E2723 (Dark Brown) |
| Hardware | #A1887F (Light Brown) | #5D4037 (Dark Brown) | #FFFFFF (White) |
| Software | #BCAAA4 (Tan) | #5D4037 (Dark Brown) | #3E2723 (Dark Brown) |
| Data | #D7CCC8 (Light Tan) | #5D4037 (Dark Brown) | #3E2723 (Dark Brown) |
| Process | #EFEBE9 (Off-White) | #5D4037 (Dark Brown) | #3E2723 (Dark Brown) |
| UI | #F5F5F5 (White) | #5D4037 (Dark Brown) | #3E2723 (Dark Brown) |
| Start | #d5e8d4 (Light Green) | #82b366 (Green) | #333333 (Dark Gray) |
| End | #f8cecc (Light Red) | #b85450 (Red) | #333333 (Dark Gray) |
| Decision | #fff2cc (Light Yellow) | #d6b656 (Yellow) | #333333 (Dark Gray) |

## 📊 Diagram Types and Styling

### Flowcharts

For flowcharts, use the following structure:

```mermaid
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#6d1a36',
    'primaryTextColor': '#fff',
    'primaryBorderColor': '#7C4DFF',
    'lineColor': '#7C4DFF',
    'secondaryColor': '#D7CCC8',
    'tertiaryColor': '#EFEBE9',
    'fontFamily': 'Courier New',
    'fontSize': '16px'
  }
}}%%

flowchart LR
    %% Nodes and connections here
    
    %% Apply standard classes
    classDef hardware fill:#A1887F,stroke:#5D4037,stroke-width:2px,color:#fff,font-family:'Courier New',font-weight:bold
    classDef software fill:#BCAAA4,stroke:#5D4037,stroke-width:2px,color:#3E2723,font-family:'Courier New',font-weight:bold
    classDef data fill:#D7CCC8,stroke:#5D4037,stroke-width:2px,color:#3E2723,font-family:'Courier New',font-style:italic
    classDef process fill:#EFEBE9,stroke:#5D4037,stroke-width:2px,color:#3E2723,font-family:'Courier New'
    classDef ui fill:#F5F5F5,stroke:#5D4037,stroke-width:2px,color:#3E2723,font-family:'Courier New'
    
    %% Apply classes to nodes
    class hardwareNodes hardware
    class softwareNodes software
    class dataNodes data
    class processNodes process
    class uiNodes ui
```

### Sequence Diagrams

For sequence diagrams, use the following structure:

```mermaid
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#6d1a36',
    'primaryTextColor': '#fff',
    'primaryBorderColor': '#7C4DFF',
    'lineColor': '#7C4DFF',
    'secondaryColor': '#D7CCC8',
    'tertiaryColor': '#EFEBE9',
    'fontFamily': 'Courier New',
    'fontSize': '16px',
    'actorBkg': '#A1887F',
    'actorBorder': '#5D4037',
    'actorTextColor': '#fff',
    'noteBkgColor': '#EFEBE9',
    'noteBorderColor': '#5D4037',
    'noteTextColor': '#3E2723'
  }
}}%%

sequenceDiagram
    %% Participants and interactions here
```

### Gantt Charts

For gantt charts, use the following structure:

```mermaid
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#6d1a36',
    'primaryTextColor': '#fff',
    'primaryBorderColor': '#7C4DFF',
    'lineColor': '#7C4DFF',
    'secondaryColor': '#D7CCC8',
    'tertiaryColor': '#EFEBE9',
    'fontFamily': 'Courier New',
    'fontSize': '16px',
    'ganttBkg': '#F5F5F5',
    'ganttFontSize': '16px',
    'sectionBkgColor': '#A1887F',
    'sectionFontColor': '#fff',
    'taskBkgColor': '#BCAAA4',
    'taskBorderColor': '#5D4037',
    'taskTextColor': '#3E2723',
    'activeTaskBkgColor': '#d4af37',
    'activeTaskBorderColor': '#5D4037',
    'gridColor': '#EFEBE9'
  }
}}%%

gantt
    title Project Timeline
    dateFormat YYYY-MM-DD
    
    %% Sections and tasks here
```

## 📱 Emoji Usage Guidelines

Use these standard emojis for different component types:

| Component Type | Emoji | Example |
|----------------|-------|---------|
| Hardware | 🔧 | 🔧 Hardware Components |
| Display | 📱 | 📱 OLED Display |
| Input | 🎛️ | 🎛️ Rotary Encoder |
| RFID | 📡 | 📡 RFID Reader |
| Software | 💻 | 💻 Software Components |
| Game Logic | 🎮 | 🎮 Game Control |
| Audio | 🎵 | 🎵 Sound System |
| Data | 📊 | 📊 Data Flow |
| User | 👤 | 👤 Player |
| Cards | 🃏 | 🃏 Card Components |
| Process | ⚙️ | ⚙️ Process Flow |
| Documentation | 📚 | 📚 Documentation |

## 🔄 Implementation Example

See [GwentPubSub.md](GwentPubSub.md) for a complete example of these styling guidelines applied to a complex diagram.

## 🧪 Testing Your Diagrams

To ensure your mermaid diagrams render correctly:

1. Use the [Mermaid Live Editor](https://mermaid.live/) to test your diagrams
2. Copy the base template and your diagram code
3. Verify the styling is applied correctly
4. Make adjustments as needed before adding to documentation

## 🔗 Integration with Development Workflow

This style guide is referenced in the development workflow documentation (`.cursor/rules/dev_workflow.mdc`) and MUST be followed for all mermaid diagrams in the project to maintain visual consistency.