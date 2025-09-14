# Use the AWS Lambda Python 3.13 base image
FROM --platform=linux/amd64 public.ecr.aws/lambda/python:3.13-x86_64

# Copy requirements file
COPY requirements.txt .

# Install dependencies directly in the Lambda environment
RUN pip install --no-cache-dir -r requirements.txt

# Copy your application code
COPY ./app ./app

# Set the command that Lambda will execute when the function is invoked
CMD ["app.main.handler"]