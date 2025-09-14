#!/bin/bash

# Script to create AWS Lambda layer with pre-compiled dependencies
# This avoids the need to compile dependencies from source in the Lambda environment

set -e

echo "Creating Lambda layer with pre-compiled dependencies..."

# Create layer directory structure
mkdir -p layer/python

# Install dependencies in the layer directory
pip install --target layer/python scipy==1.11.4 pandas==2.1.4

# Create layer zip file
cd layer
zip -r ../dependencies-layer.zip python/
cd ..

echo "Layer created: dependencies-layer.zip"
echo "Upload this layer to AWS Lambda and note the ARN for use in your Lambda function"

# Show layer contents
echo "Layer contents:"
unzip -l dependencies-layer.zip
