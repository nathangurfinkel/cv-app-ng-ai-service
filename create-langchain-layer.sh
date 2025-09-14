#!/bin/bash

# Script to create AWS Lambda layer with LangChain and related dependencies
# This reduces the main deployment package size by moving heavy dependencies to a layer

set -e

echo "🚀 Creating LangChain Lambda layer for eu-north-1..."

# Configuration
LAYER_NAME="langchain-dependencies"
REGION="eu-north-1"
RUNTIME="python3.11"

# Create layer directory structure
echo "📁 Creating layer directory structure..."
rm -rf layer/
mkdir -p layer/python

# Install LangChain and related dependencies in the layer directory
echo "📥 Installing LangChain and dependencies..."
docker run --rm -v $(pwd):/var/task -w /var/task --platform linux/amd64 python:3.11 sh -c "
pip install --no-cache-dir --target layer/python/ \
    langchain==0.3.27 \
    langchain-community==0.3.29 \
    langchain-core==0.3.76 \
    langchain-openai==0.3.33 \
    langchain-pinecone==0.2.12 \
    langchain-text-splitters==0.3.11 \
    langsmith==0.4.27 \
    openai==1.107.1 \
    pinecone==7.3.0 \
    pinecone-client==6.0.0 \
    pinecone-plugin-assistant==1.8.0 \
    pinecone-plugin-interface==0.0.7 \
    tiktoken==0.11.0 \
    numpy==2.3.3 \
    pydantic==2.11.7 \
    pydantic-core==2.33.2 \
    pydantic-settings==2.10.1 \
    tenacity==9.1.2 \
    tqdm==4.67.1 \
    regex==2025.9.1 \
    requests==2.32.5 \
    urllib3==2.5.0 \
    certifi==2025.8.3 \
    charset-normalizer==3.4.3 \
    idna==3.10 \
    packaging==24.2 \
    python-dateutil==2.9.0.post0 \
    six==1.17.0 \
    attrs==25.3.0 \
    typing-extensions==4.15.0 \
    anyio==4.10.0 \
    sniffio==1.3.1 \
    h11==0.16.0 \
    httpcore==1.0.9 \
    httpx==0.28.1 \
    httpx-sse==0.4.1 \
    simsimd==6.5.3 \
    zstandard==0.24.0 \
    orjson==3.11.3 \
    pyyaml==6.0.2 \
    sqlalchemy==2.0.43 \
    marshmallow==3.26.1 \
    dataclasses-json==0.6.7 \
    click==8.2.1 \
    deprecated==1.2.18 \
    distro==1.9.0 \
    propcache==0.3.2 \
    limits==5.5.0 \
    slowapi==0.1.9 \
    starlette==0.47.3 \
    fastapi==0.116.1 \
    uvicorn==0.35.0 \
    mangum==0.19.0 \
    python-multipart==0.0.20 \
    python-dotenv==1.1.1 \
    aiohttp==3.12.15 \
    aiohttp-retry==2.9.1 \
    aiosignal==1.4.0 \
    aiohappyeyeballs==2.6.1 \
    frozenlist==1.7.0 \
    multidict==6.6.4 \
    yarl==1.20.1 \
    greenlet==3.2.4 \
    httptools==0.6.4 \
    uvloop==0.21.0 \
    websockets==15.0.1 \
    watchfiles==1.1.0 \
    jiter==0.10.0 \
    jsonpatch==1.33 \
    jsonpointer==3.0.0 \
    mypy-extensions==1.1.0 \
    typing-inspect==0.9.0 \
    typing-inspection==0.4.1 \
    wrapt==1.17.3 \
    requests-toolbelt==1.0.0
"

# Clean up unnecessary files to reduce layer size
echo "🧹 Cleaning up layer..."
find layer/python/ -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find layer/python/ -type f -name "*.pyc" -delete 2>/dev/null || true
find layer/python/ -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
find layer/python/ -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find layer/python/ -type d -name "test" -exec rm -rf {} + 2>/dev/null || true
find layer/python/ -type f -name "*.md" -delete 2>/dev/null || true
find layer/python/ -type f -name "*.txt" -not -name "requirements.txt" -delete 2>/dev/null || true

# Create layer zip file
echo "🗜️ Creating layer package..."
cd layer
zip -r ../langchain-layer.zip python/
cd ..

echo "✅ LangChain layer created: langchain-layer.zip"

# Deploy layer to AWS Lambda
if command -v aws &> /dev/null; then
    echo "☁️ Publishing layer to AWS Lambda..."
    
    LAYER_ARN=$(aws lambda publish-layer-version \
        --layer-name $LAYER_NAME \
        --description "LangChain and AI dependencies for CV Builder" \
        --zip-file fileb://langchain-layer.zip \
        --compatible-runtimes $RUNTIME \
        --region $REGION \
        --query 'LayerVersionArn' \
        --output text)
    
    echo "✅ Layer published successfully!"
    echo "🔗 Layer ARN: $LAYER_ARN"
    echo "📝 Add this ARN to your Lambda function layers:"
    echo "   $LAYER_ARN"
    
    # Save the ARN for later use
    echo "$LAYER_ARN" > layer-arn.txt
    echo "💾 Layer ARN saved to layer-arn.txt"
else
    echo "⚠️ AWS CLI not found. Please install and configure AWS CLI to deploy the layer."
    echo "📦 Layer package ready: langchain-layer.zip"
    echo "📝 To deploy manually:"
    echo "   aws lambda publish-layer-version --layer-name $LAYER_NAME --zip-file fileb://langchain-layer.zip --compatible-runtimes $RUNTIME --region $REGION"
fi

echo "🎉 LangChain layer creation completed!"
