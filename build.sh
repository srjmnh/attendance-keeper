#!/bin/bash

# Install Python dependencies
echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt

# Download Real-ESRGAN pre-trained weights
echo "Downloading Real-ESRGAN pre-trained weights..."
curl -L -o RealESRGAN_x4.pth https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.4/RealESRGAN_x4.pth

if [ -f "RealESRGAN_x4.pth" ]; then
    echo "Real-ESRGAN weights downloaded successfully."
else
    echo "Failed to download Real-ESRGAN weights. Exiting..."
    exit 1
fi

echo "Build script completed successfully."
