#!/usr/bin/env bash

# Install the package in development mode
echo "Installing gwent-elements in development mode..."
pip install -e ../software/gwent-elements

# Print success message
echo "Gwent Elements installed in development mode."
echo "You can now import the package with: import gwent_elements"