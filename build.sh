#!/bin/bash

# Install Python dependencies
pip install -r requirements.txt

# Download realesrgan-ncnn-vulkan binary
echo "Downloading realesrgan-ncnn-vulkan binary..."
curl -L -o realesrgan-ncnn-vulkan.zip https://github.com/xinntao/realesrgan-ncnn-vulkan/releases/download/v1.3.0/realesrgan-ncnn-vulkan-20220424-linux.zip

# Extract the binary
echo "Extracting realesrgan-ncnn-vulkan binary..."
unzip -o realesrgan-ncnn-vulkan.zip -d realesrgan-ncnn-vulkan
chmod +x realesrgan-ncnn-vulkan/realesrgan-ncnn-vulkan

# Verify binary existence
if [ ! -f "./realesrgan-ncnn-vulkan/realesrgan-ncnn-vulkan" ]; then
    echo "Error: realesrgan-ncnn-vulkan binary not found."
    exit 1
fi

echo "Real-ESRGAN binary setup completed."