#!/bin/bash
# Unified local development startup script
# Starts LocalStack, API server, and worker in one command

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting CV Builder AI Service (Local Development)${NC}"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running!${NC}"
    echo "Please start Docker Desktop first, then run this script again."
    exit 1
fi

# Check if LocalStack is running
LOCALSTACK_RUNNING=$(docker ps --filter "name=localstack-cv-builder" --format "{{.Names}}" | grep -q localstack-cv-builder && echo "yes" || echo "no")

if [ "$LOCALSTACK_RUNNING" = "no" ]; then
    echo -e "${YELLOW}LocalStack not running. Starting LocalStack...${NC}"
    docker compose -f docker-compose.localstack.yml up -d
    
    echo "Waiting for LocalStack to be ready (10 seconds)..."
    sleep 10
    
    # Check health
    if curl -s http://localhost:4566/_localstack/health > /dev/null; then
        echo -e "${GREEN}✓ LocalStack is ready!${NC}"
    else
        echo -e "${YELLOW}⚠️  LocalStack may still be starting. Continuing anyway...${NC}"
    fi
    
    # Set up LocalStack resources
    echo "Setting up LocalStack resources..."
    export AWS_ACCESS_KEY_ID=test
    export AWS_SECRET_ACCESS_KEY=test
    export AWS_DEFAULT_REGION=us-east-1
    ./scripts/setup-localstack.sh > /dev/null 2>&1
    echo -e "${GREEN}✓ LocalStack resources configured${NC}"
else
    echo -e "${GREEN}✓ LocalStack is already running${NC}"
fi

echo ""

# Cleanup function
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down...${NC}"
    if [ ! -z "$API_PID" ]; then
        kill $API_PID 2>/dev/null || true
        echo -e "${GREEN}✓ API server stopped${NC}"
    fi
    if [ ! -z "$WORKER_PID" ]; then
        kill $WORKER_PID 2>/dev/null || true
        echo -e "${GREEN}✓ Worker stopped${NC}"
    fi
    exit 0
}

# Set trap for cleanup on exit
trap cleanup EXIT INT TERM

# Start API server in background
echo -e "${GREEN}Starting API server...${NC}"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > /tmp/cv-builder-api.log 2>&1 &
API_PID=$!
echo -e "${GREEN}✓ API server started (PID: $API_PID)${NC}"
echo "   Logs: tail -f /tmp/cv-builder-api.log"
echo ""

# Wait a moment for API to start
sleep 2

# Start worker in background
echo -e "${GREEN}Starting worker...${NC}"
python3 scripts/process-localstack-queue.py > /tmp/cv-builder-worker.log 2>&1 &
WORKER_PID=$!
echo -e "${GREEN}✓ Worker started (PID: $WORKER_PID)${NC}"
echo "   Logs: tail -f /tmp/cv-builder-worker.log"
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ All services started!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "API Server: http://localhost:8000"
echo "Health Check: http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Tail logs from both processes
tail -f /tmp/cv-builder-api.log /tmp/cv-builder-worker.log 2>/dev/null &
TAIL_PID=$!

# Wait for processes (they run in background, but we wait to catch signals)
wait $API_PID $WORKER_PID

