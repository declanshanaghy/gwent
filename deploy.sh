#!/usr/bin/env bash

set -e

# Target Raspberry Pi
TARGET_HOST="dshanaghy@192.168.1.225"
TARGET_DIR="/home/dshanaghy/gwent"

# Local directory
LOCAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

echo "Deploying to $TARGET_HOST:$TARGET_DIR..."

# Create the target directory if it doesn't exist
ssh $TARGET_HOST "mkdir -p $TARGET_DIR"

# Sync the code to the Raspberry Pi
rsync -avz --exclude '.git' --exclude 'node_modules' --exclude '__pycache__' \
    --exclude '*.pyc' --exclude '*.pyo' --exclude '*.pyd' \
    $LOCAL_DIR/ $TARGET_HOST:$TARGET_DIR/

# Copy the service file to the systemd directory
ssh $TARGET_HOST "sudo cp $TARGET_DIR/gwent.service /etc/systemd/system/"

# Run the installation scripts on the Raspberry Pi
ssh $TARGET_HOST "cd $TARGET_DIR && ./install.sh"

# Enable and start the service
ssh $TARGET_HOST "sudo systemctl daemon-reload && \
                  sudo systemctl enable gwent.service && \
                  sudo systemctl restart gwent.service"

echo "Deployment complete. Service status:"
ssh $TARGET_HOST "sudo systemctl status gwent.service"