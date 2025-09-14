#!/bin/bash

# Script to create AWS Lambda layer with LangChain dependencies but WITHOUT numpy for Python 3.13
# This avoids the numpy source directory conflict

set -e

echo "🚀 Creating LangChain Lambda layer WITHOUT numpy for Python 3.13 in eu-north-1..."

# Configuration
LAYER_NAME="langchain-dependencies-313-no-numpy"
REGION="eu-north-1"
RUNTIME="python3.13"

# Create layer directory structure
echo "📁 Creating layer directory structure..."
rm -rf layer/
mkdir -p layer/python

# Install LangChain and related dependencies but exclude numpy
echo "📥 Installing LangChain dependencies WITHOUT numpy for Python 3.13..."
docker run --rm -v $(pwd):/var/task -w /var/task --platform linux/amd64 python:3.13 sh -c "
pip install --no-cache-dir --target layer/python/ \\
    langchain-core==0.3.76 \\
    langchain-openai==0.3.33 \\
    langchain-pinecone==0.2.12 \\
    openai==1.107.2 \\
    langsmith==0.4.27 \\
    --no-deps
"

# Install only the essential dependencies that don't require numpy
echo "📥 Installing essential dependencies..."
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
    aiohttp==3.12.15 \\
    aiohttp-retry==2.9.1 \\
    aiosignal==1.4.0 \\
    aiohappyeyeballs==2.6.1 \\
    frozenlist==1.7.0 \\
    multidict==6.6.4 \\
    yarl==1.20.1 \\
    attrs==25.3.0 \\
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
    zstandard==0.24.0
"

# Create the layer zip
echo "📦 Creating layer zip file..."
cd layer
zip -r ../langchain-layer-313-no-numpy.zip python/
cd ..

# Check layer size
LAYER_SIZE=$(du -h langchain-layer-313-no-numpy.zip | cut -f1)
echo "📊 Layer size: $LAYER_SIZE"

# Publish the layer
echo "🚀 Publishing layer to AWS Lambda..."
LAYER_ARN=$(aws lambda publish-layer-version \
    --layer-name "$LAYER_NAME" \
    --description "LangChain dependencies for Python 3.13 (no numpy)" \
    --zip-file fileb://langchain-layer-313-no-numpy.zip \
    --compatible-runtimes "$RUNTIME" \
    --region "$REGION" \
    --query 'LayerVersionArn' \
    --output text)

echo "✅ Layer published successfully!"
echo "📋 Layer ARN: $LAYER_ARN"

# Save layer ARN for deployment
echo "$LAYER_ARN" > layer-arn-313-no-numpy.txt

# List layer contents
echo "📁 Layer contents:"
unzip -l langchain-layer-313-no-numpy.zip | head -20

echo "🎉 Layer creation completed!"
echo "📋 Use this ARN in your deployment: $LAYER_ARN"
