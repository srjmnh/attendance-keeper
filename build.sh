#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Define model directory
MODEL_DIR="models"
MODEL_URL="https://github.com/Saafke/EDSR_Tensorflow/raw/refs/heads/master/models/EDSR_x4.pb"

# Create the model directory if it doesn't exist
if [ ! -d "$MODEL_DIR" ]; then
    echo "Creating model directory..."
    mkdir -p "$MODEL_DIR"
fi

# Download the EDSR model
if [ ! -f "$MODEL_DIR/EDSR_x4.pb" ]; then
    echo "Downloading EDSR model..."
    curl -L -o "$MODEL_DIR/EDSR_x4.pb" "$MODEL_URL"
else
    echo "EDSR model already exists. Skipping download."
fi

# Install required Python packages
echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "Build script completed successfully!"
