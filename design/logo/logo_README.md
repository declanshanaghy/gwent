# Gwent Companion Logo

This directory contains two HTML files that generate a quippy logo for the Gwent Companion project:

## 1. logo_generator.html

This is the main logo generator with dynamic animations and a download button that uses the html2canvas library to capture the logo as a PNG file.

### Features:
- Animated RFID waves
- Gradient text effects
- Card visualization
- Raspberry Pi emoji
- "Download Logo" button for direct PNG saving

### How to Use:
1. Open `logo_generator.html` in a web browser
2. Click the "Download Logo" button in the top right corner
3. The PNG file will be automatically downloaded as `gwent_logo.png`

## 2. logo_generator_simple.html

This is a simplified version that doesn't rely on external libraries. It provides two options for saving the logo:

### Features:
- Same visual design as the main generator
- Animated version at the top
- Static SVG version below
- No external dependencies

### How to Save as PNG:
1. Open `logo_generator_simple.html` in a web browser
2. Take a screenshot of the logo (Mac: Cmd+Shift+4, Windows: Win+Shift+S)
3. Crop the screenshot to include just the logo
4. Save the cropped image as `gwent_logo.png`

### How to Save as SVG:
1. Open `logo_generator_simple.html` in a web browser
2. Scroll down to see the SVG version
3. Click the "Download SVG Version" button
4. The SVG file will be automatically downloaded as `gwent_logo.svg`

## Logo Design Elements

The logo incorporates several elements that represent the Gwent Companion project:

- **GWENT Text**: Bold gradient text in burgundy (#6d1a36) to gold (#d4af37) representing the premium feel of the game
- **Tagline**: "Cards & Circuits: The Digital Companion" highlighting the fusion of physical cards and digital technology
- **RFID Waves**: Animated circles representing the RFID card reading functionality
- **Card**: A stylized game card in burgundy/gold gradient representing the physical cards
- **Raspberry Pi**: The raspberry pi emoji (🥧) acknowledging the hardware platform

## Usage Guidelines

- Use the PNG format for most digital applications (website, documentation, etc.)
- Use the SVG format when scalability is needed (printing, large displays, etc.)
- The logo should be displayed on dark backgrounds for best contrast
- Maintain the aspect ratio when resizing