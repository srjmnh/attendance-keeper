#!/bin/bash

# Install Python dependencies
pip install -r requirements.txt

# Create a directory for the model files
mkdir -p models/super_resolution

# Download EDSR_x4.pb model
echo "Downloading EDSR_x4.pb model..."
curl -L -o models/super_resolution/EDSR_x4.pb https://github.com/Saafke/EDSR_Tensorflow/raw/refs/heads/master/models/EDSR_x4.pb

# Validate model download
if [ ! -f "models/super_resolution/EDSR_x4.pb" ]; then
    echo "Error: EDSR_x4.pb model not downloaded successfully."
    exit 1
fi

echo "Model setup completed successfully."