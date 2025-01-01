#!/bin/bash

# Install dependencies
pip install -r requirements.txt

# Download realesrgan-ncnn-vulkan binary
echo "Downloading realesrgan-ncnn-vulkan binary..."
curl -L -o realesrgan-ncnn-vulkan.zip https://github.com/xinntao/realesrgan-ncnn-vulkan/releases/download/v1.3.0/realesrgan-ncnn-vulkan-20220424-linux.zip

# Unzip the binary
unzip realesrgan-ncnn-vulkan.zip -d realesrgan-ncnn-vulkan
chmod +x realesrgan-ncnn-vulkan/realesrgan-ncnn-vulkan

echo "Real-ESRGAN binary setup completed."