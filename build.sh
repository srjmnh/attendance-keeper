#!/bin/bash

# Install Python dependencies
pip install -r requirements.txt

# Download realesrgan-ncnn-vulkan binary
echo "Downloading realesrgan-ncnn-vulkan binary..."
curl -L -o realesrgan-ncnn-vulkan.zip https://github.com/xinntao/realesrgan-ncnn-vulkan/releases/download/v1.3.0/realesrgan-ncnn-vulkan-20220424-ubuntu.zip

# Check if the ZIP file exists
if [ ! -f "realesrgan-ncnn-vulkan.zip" ]; then
    echo "Error: realesrgan-ncnn-vulkan.zip file not downloaded."
    exit 1
fi

# Debugging: Check the size of the downloaded file
echo "Downloaded file size:"
ls -lh realesrgan-ncnn-vulkan.zip

# Validate the ZIP file
if ! unzip -t realesrgan-ncnn-vulkan.zip > /dev/null 2>&1; then
    echo "Error: realesrgan-ncnn-vulkan.zip is invalid or corrupt."
    echo "Attempting to download again..."
    curl -L -o realesrgan-ncnn-vulkan.zip https://github.com/xinntao/realesrgan-ncnn-vulkan/releases/download/v1.3.0/realesrgan-ncnn-vulkan-20220424-ubuntu.zip
    if ! unzip -t realesrgan-ncnn-vulkan.zip > /dev/null 2>&1; then
        echo "Error: File is still corrupt after retrying."
        exit 1
    fi
fi

# Extract the ZIP file
echo "Extracting realesrgan-ncnn-vulkan binary..."
unzip -o realesrgan-ncnn-vulkan.zip -d realesrgan-ncnn-vulkan
chmod +x realesrgan-ncnn-vulkan/realesrgan-ncnn-vulkan

# Verify the binary
if [ ! -f "./realesrgan-ncnn-vulkan/realesrgan-ncnn-vulkan" ]; then
    echo "Error: realesrgan-ncnn-vulkan binary not found after extraction."
    exit 1
fi

echo "Real-ESRGAN binary setup completed successfully."