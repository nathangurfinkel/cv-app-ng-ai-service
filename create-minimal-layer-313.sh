#!/bin/bash

# Script to create a minimal AWS Lambda layer for Python 3.13
# This includes only the essential dependencies needed for the AI service

set -e

echo "🚀 Creating minimal Lambda layer for Python 3.13 in eu-north-1..."

# Configuration
LAYER_NAME="minimal-dependencies-313"
REGION="eu-north-1"
RUNTIME="python3.13"

# Create layer directory structure
echo "📁 Creating layer directory structure..."
rm -rf layer/
mkdir -p layer/python

# Install only the absolutely essential dependencies
echo "📥 Installing minimal essential dependencies..."
docker run --rm -v $(pwd):/var/task -w /var/task --platform linux/amd64 python:3.13 sh -c "
pip install --no-cache-dir --target layer/python/ \\
    pydantic==2.11.7 \\
    pydantic-core==2.33.2 \\
    typing-extensions==4.15.0 \\
    anyio==4.10.0 \\
    sniffio==1.3.1 \\
    httpx==0.28.1 \\
    httpcore==1.0.9 \\
    h11==0.16.0 \\
    certifi==2025.8.3 \\
    idna==3.10 \\
    urllib3==2.5.0 \\
    charset-normalizer==3.4.3 \\
    requests==2.32.5 \\
    tenacity==9.1.2 \\
    tqdm==4.67.1 \\
    click==8.2.1 \\
    deprecated==1.2.18 \\
    distro==1.9.0 \\
    propcache==0.3.2 \\
    packaging==24.2 \\
    pyyaml==6.0.2 \\
    python-dotenv==1.1.1 \\
    orjson==3.11.3 \\
    python-multipart==0.0.20 \\
    python-dateutil==2.9.0.post0 \\
    six==1.17.0 \\
    greenlet==3.2.4 \\
    uvloop==0.21.0 \\
    websockets==15.0.1 \\
    watchfiles==1.1.0 \\
    httptools==0.6.4 \\
    jiter==0.10.0 \\
    slowapi==0.1.9 \\
    limits==5.5.0 \\
    wrapt==1.17.3 \\
    mypy-extensions==1.1.0 \\
    typing-inspect==0.9.0 \\
    typing-inspection==0.4.1 \\
    jsonpatch==1.33 \\
    jsonpointer==3.0.0 \\
    annotated-types==0.7.0
"

# Install LangChain packages with minimal dependencies
echo "📥 Installing LangChain packages with minimal dependencies..."
docker run --rm -v $(pwd):/var/task -w /var/task --platform linux/amd64 python:3.13 sh -c "
pip install --no-cache-dir --target layer/python/ \\
    langchain-core==0.3.76 \\
    langchain-openai==0.3.33 \\
    langchain-pinecone==0.2.12 \\
    openai==1.107.2 \\
    langsmith==0.4.27 \\
    --no-deps
"

# Install only the essential dependencies for the packages above
echo "📥 Installing essential dependencies for LangChain packages..."
docker run --rm -v $(pwd):/var/task -w /var/task --platform linux/amd64 python:3.13 sh -c "
pip install --no-cache-dir --target layer/python/ \\
    tiktoken==0.11.0 \\
    regex==2025.9.1 \\
    zstandard==0.24.0 \\
    requests-toolbelt==1.0.0 \\
    pinecone==7.3.0 \\
    simsimd==6.5.3
"

# Clean up __pycache__ and dist-info directories to reduce size
echo "🧹 Cleaning up unnecessary files..."
find layer/python -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find layer/python -name "*.dist-info" -type d -exec rm -rf {} + 2>/dev/null || true
find layer/python -name "*.pyc" -type f -delete 2>/dev/null || true

# Create the layer zip
echo "📦 Creating layer zip file..."
cd layer
zip -r ../minimal-layer-313.zip python/
cd ..

# Check layer size
LAYER_SIZE=$(du -h minimal-layer-313.zip | cut -f1)
echo "📊 Layer size: $LAYER_SIZE"

# Publish the layer
echo "🚀 Publishing layer to AWS Lambda..."
LAYER_ARN=$(aws lambda publish-layer-version \
    --layer-name "$LAYER_NAME" \
    --description "Minimal dependencies for Python 3.13" \
    --zip-file fileb://minimal-layer-313.zip \
    --compatible-runtimes "$RUNTIME" \
    --region "$REGION" \
    --query 'LayerVersionArn' --output text)

if [ -z "$LAYER_ARN" ]; then
    echo "❌ Failed to publish layer."
    exit 1
fi

echo "✅ Layer published successfully!"
echo "📋 Layer ARN: $LAYER_ARN"

# Save layer ARN to a file for later use
echo "$LAYER_ARN" > minimal-layer-arn-313.txt
echo "🎉 Minimal layer creation completed!"
echo "📋 Use this ARN in your deployment: $LAYER_ARN"
