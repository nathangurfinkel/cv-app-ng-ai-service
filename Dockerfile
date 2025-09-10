# AI Service Dockerfile for AWS Lambda
# This container is optimized for Lambda deployment with all dependencies

# Use AWS Lambda Python base image with specific architecture
FROM --platform=linux/amd64 public.ecr.aws/lambda/python:3.11

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set working directory
WORKDIR ${LAMBDA_TASK_ROOT}

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Create a simple lambda_handler.py that imports our app
RUN echo 'from app.main import handler' > lambda_handler.py

# Set the CMD to your handler
CMD ["lambda_handler.handler"]
