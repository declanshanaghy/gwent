# Gwent Companion - Product Requirements Document

## 1. Product Overview

The Gwent Companion is a digital device that enhances the physical card game Gwent from The Witcher III by combining physical cards with digital tracking capabilities. It maintains the authentic feel of physical card play while adding modern digital features.

## 2. Target Users

- Gwent card game enthusiasts
- Players who want to enhance their gameplay experience
- New players who need guidance through the game process
- Players who want to track their game statistics

## 3. Hardware Requirements

### 3.1 Core Components
- Raspberry Pi (model to be determined)
- Integrated RFID card reader
- Round score display
- Game score display
- LCD menu system
- Rotary dial for navigation
- Power management system

### 3.2 Physical Components
- RFID-enabled Gwent cards
- Cloth game mat
- Companion device housing

## 4. Software Requirements

### 4.1 Game Server (gwent)
- System service for game state management
- Hardware interfacing capabilities
- REST API implementation
- Game state persistence
- Event logging

### 4.2 Front-end Application (glory-gate)
- React-based Single Page Application
- Web-based interface
- REST API integration
- Real-time game state updates
- User authentication

## 5. Functional Requirements

### 5.1 Core Features
- Automatic score tracking
- Deck management
- Game history recording
- Rule reference access
- Player statistics tracking
- Game process guidance
- Web interface access

### 5.2 Game Flow
1. System initialization
2. Player authentication
3. Deck selection
4. Game state management
5. Score tracking
6. Round management
7. Game completion

## 6. Non-Functional Requirements

### 6.1 Performance
- Real-time card detection
- Responsive UI
- Low latency API responses

### 6.2 Security
- Secure API endpoints
- User authentication
- Data encryption

### 6.3 Reliability
- System uptime requirements
- Error handling
- Data backup

## 7. User Interface Requirements

### 7.1 Physical Interface
- Clear score displays
- Intuitive menu navigation
- Responsive rotary dial

### 7.2 Web Interface
- Modern, responsive design
- Real-time updates
- Intuitive navigation

## 8. Integration Requirements

### 8.1 Hardware Integration
- RFID reader integration
- Display integration
- Input device integration

### 8.2 Software Integration
- REST API endpoints
- Database integration
- Front-end communication

## 9. Future Considerations

- Additional game modes
- Tournament support
- Mobile application
- Cloud synchronization

## 10. Success Metrics

- User adoption rate
- Game completion rate
- System reliability
- User satisfaction