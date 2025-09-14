#!/bin/bash

# Define some variables
IMAGE_NAME="lambda-layer-builder"
LAYER_ZIP_NAME="minimal-dependencies-313-with-numpy.zip"

echo "🚀 Building the Docker image for the Lambda layer..."
# Build the image using the Dockerfile we created
docker build -t $IMAGE_NAME -f layer.Dockerfile .

echo "📦 Creating a container to copy dependencies from..."
# Create a container from the image. We'll give it a name to easily reference it.
docker create --name builder_container $IMAGE_NAME

echo "📋 Copying the 'python' directory out of the container..."
# First, remove any old layer artifacts to ensure a clean build
rm -rf ./python ./${LAYER_ZIP_NAME}
# Copy the generated /app/python directory from the container to your current directory
docker cp builder_container:/app/python ./

echo "🧹 Cleaning up the container..."
# Remove the container, we don't need it anymore
docker rm builder_container

echo "📦 Zipping the layer contents..."
# Create the zip file for the Lambda layer
zip -r ${LAYER_ZIP_NAME} ./python

echo "✅ Successfully created ${LAYER_ZIP_NAME}"

# Verify the compiled binary exists
echo "🔍 Verifying pydantic_core compiled binary exists..."
if find ./python -name "*pydantic_core*.so" | grep -q .; then
    echo "✅ pydantic_core compiled binary found!"
    find ./python -name "*pydantic_core*.so" | head -5
else
    echo "❌ pydantic_core compiled binary NOT found!"
fi

echo "📊 Layer size: $(du -h ${LAYER_ZIP_NAME} | cut -f1)"
