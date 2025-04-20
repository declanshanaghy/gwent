#!/usr/bin/env bash

# Install the gaugette dependency from GitHub
echo "Installing gaugette dependency from GitHub..."
pip install git+https://github.com/guyc/py-gaugette.git

# Install the package in development mode
echo "Installing gwent-elements in development mode..."
pip install -e .

# Print success message
echo "Gwent Elements installed in development mode."
echo "You can now import the package with: import gwent_elements"