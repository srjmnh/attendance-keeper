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

# Verify the binary exists in the correct directory
if [ ! -f "./realesrgan-ncnn-vulkan-v0.2.0-ubuntu/realesrgan-ncnn-vulkan" ]; then
    echo "Error: realesrgan-ncnn-vulkan binary not found in the extracted directory."
    exit 1
fi

# Make the binary executable
chmod +x realesrgan-ncnn-vulkan-v0.2.0-ubuntu/realesrgan-ncnn-vulkan

echo "Real-ESRGAN binary setup completed successfully."