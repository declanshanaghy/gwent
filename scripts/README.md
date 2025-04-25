# 🛠️ Gwent Scripts Collection

This directory contains various scripts used for development, deployment, and maintenance of the Gwent project. These scripts automate common tasks and provide utilities for working with the hardware and software components.

## 🚀 Installation Scripts

| Script | Description |
|--------|-------------|
| `install.sh` | Main installation script that calls both system and app installation scripts |
| `install-system.sh` | Installs system dependencies, configures hardware interfaces, and sets up required services |
| `install-app.sh` | Installs the Gwent application and its Python dependencies |
| `install-vars.sh` | Contains shared variables used by installation scripts |

## 📦 Deployment Scripts

| Script | Description |
|--------|-------------|
| `deploy-to-raspi.sh` | Deploys the application to a Raspberry Pi device |
| `update-service.sh` | Updates the systemd service configuration |
| `validate-gwent.sh` | Validates that the Gwent service is running correctly |

## 🔧 System Configuration

| Script | Description |
|--------|-------------|
| `gwent.service` | Systemd service definition for the Gwent application |
| `ssd1306_luma.sh` | Configuration script for the SSD1306 OLED display using luma.oled library |
| `rebase_script.sh` | Helper script for rebasing Git branches |

## 🧪 Testing Scripts

| Script | Description |
|--------|-------------|
| `test_hardware.py` | Tests all hardware components to ensure they're working correctly |

## 📚 Development Workflow

The Gwent project uses a task-based development workflow powered by the Task Master system. This system helps manage development tasks, track progress, and coordinate work between developers.

For detailed information about the development workflow and task management system, see the [Task Master Documentation](../README-task-master.md).

## 🎮 Using the Scripts

Most scripts can be executed directly from the command line:

```bash
# Run the installation script
./scripts/install.sh

# Deploy to a Raspberry Pi
./scripts/deploy-to-raspi.sh

# Update the systemd service
./scripts/update-service.sh
```

Many scripts are also accessible through the Makefile targets for convenience:

```bash
# Install the application
make install

# Deploy to a Raspberry Pi
make deploy

# Test the hardware
make test-hardware
```

## 🔍 Font Resources

The `fonts/` subdirectory contains various font files used by the display components:

- `C&C Red Alert [INET].ttf`: Red Alert font for game displays
- `ChiKareGo.ttf`: Pixel font for menu systems
- `FreePixel.ttf`: Free pixel font for general text
- `pixelmix.ttf`: Pixel font used for the main menu display
- And several others for different display purposes

These fonts are used by the OLED display and LED matrix components to render text and UI elements.
