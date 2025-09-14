# Use the official AWS Lambda Python 3.13 base image for x86_64 architecture
FROM public.ecr.aws/lambda/python:3.13-x86_64

# Install build tools needed for compiling packages
RUN microdnf update -y && microdnf install -y gcc gcc-c++ make

# Set the working directory
WORKDIR /app

# Copy your requirements file into the container
COPY requirements-layer.txt .

# Install dependencies into a "python" directory, which is the required structure for a Lambda layer
RUN pip install --no-cache-dir -r requirements-layer.txt --target ./python

# Verify that pydantic_core compiled binary exists
RUN find ./python -name "*.so" | head -10
