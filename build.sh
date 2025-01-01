#!/bin/bash

# Install Python dependencies
pip install -r requirements.txt

# Download realesrgan-ncnn-vulkan binary
echo "Downloading realesrgan-ncnn-vulkan binary..."
curl -L -o realesrgan-ncnn-vulkan.zip https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan/releases/download/v0.2.0/realesrgan-ncnn-vulkan-v0.2.0-ubuntu.zip

# Check if the ZIP file exists
if [ ! -f "realesrgan-ncnn-vulkan.zip" ]; then
    echo "Error: realesrgan-ncnn-vulkan.zip file not downloaded."
    exit 1
fi

# Validate the ZIP file
if ! unzip -t realesrgan-ncnn-vulkan.zip > /dev/null 2>&1; then
    echo "Error: realesrgan-ncnn-vulkan.zip is invalid or corrupt."
    exit 1
fi

# Extract the ZIP file
echo "Extracting realesrgan-ncnn-vulkan binary..."
unzip -o realesrgan-ncnn-vulkan.zip

# Debugging: List the contents of the current directory
echo "Contents of the current directory after extraction:"
ls -l

# Dynamically find the directory containing the binary
BINARY_PATH=$(find . -type f -name "realesrgan-ncnn-vulkan" | head -n 1)

if [ -z "$BINARY_PATH" ]; then
    echo "Error: realesrgan-ncnn-vulkan binary not found in the extracted directory."
    exit 1
fi

# Make the binary executable
chmod +x "$BINARY_PATH"

echo "Real-ESRGAN binary setup completed successfully. Binary located at: $BINARY_PATH"