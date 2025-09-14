#!/bin/bash

# Script to create AWS Lambda layer with LangChain and related dependencies for Python 3.13
# This reduces the main deployment package size by moving heavy dependencies to a layer

set -e

echo "🚀 Creating LangChain Lambda layer for Python 3.13 in eu-north-1..."

# Configuration
LAYER_NAME="langchain-dependencies-313"
REGION="eu-north-1"
RUNTIME="python3.13"

# Create layer directory structure
echo "📁 Creating layer directory structure..."
rm -rf layer/
mkdir -p layer/python

# Install LangChain and related dependencies in the layer directory
echo "📥 Installing LangChain and dependencies for Python 3.13..."
docker run --rm -v $(pwd):/var/task -w /var/task --platform linux/amd64 python:3.13 sh -c "
pip install --no-cache-dir --target layer/python/ \
    langchain==0.3.27 \
    langchain-community==0.3.29 \
    langchain-core==0.3.76 \
    langchain-openai==0.3.33 \
    langchain-pinecone==0.2.12 \
    langchain-text-splitters==0.3.11 \
    langsmith==0.4.27 \
    openai==1.107.2 \
    pinecone==7.3.0 \
    tiktoken==0.11.0 \
    numpy==2.3.3 \
    simsimd==6.5.3
"

# Create layer zip
echo "📦 Creating layer zip file..."
cd layer
zip -r ../langchain-layer-313.zip python/
cd ..

# Get layer size
LAYER_SIZE=$(du -h langchain-layer-313.zip | cut -f1)
echo "📊 Layer size: $LAYER_SIZE"

# Publish layer to AWS Lambda
echo "☁️ Publishing layer to AWS Lambda..."
LAYER_ARN=$(aws lambda publish-layer-version \
    --layer-name "$LAYER_NAME" \
    --description "LangChain and AI dependencies for Python 3.13" \
    --zip-file fileb://langchain-layer-313.zip \
    --compatible-runtimes "$RUNTIME" \
    --region "$REGION" \
    --query 'LayerVersionArn' \
    --output text)

echo "✅ Layer published successfully!"
echo "📋 Layer ARN: $LAYER_ARN"

# Save layer ARN for deployment
echo "$LAYER_ARN" > layer-arn-313.txt

# Verify layer contents
echo "🔍 Verifying layer contents..."
unzip -l langchain-layer-313.zip | head -20

echo "🎉 LangChain layer for Python 3.13 created and published successfully!"
echo "📝 Layer ARN saved to layer-arn-313.txt"
