#!/usr/bin/env python3
"""
Local script to manually process SQS messages from LocalStack.
This simulates what Lambda would do in production.
"""
import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import boto3
from app.worker import handler
from app.core.config import settings

def process_queue():
    """Poll SQS queue and process messages."""
    if not settings.JOBS_QUEUE_URL:
        print("ERROR: JOBS_QUEUE_URL not configured")
        return

    if not settings.AWS_ENDPOINT_URL:
        print("WARNING: AWS_ENDPOINT_URL is not set. Worker will use real AWS. For LocalStack, set AWS_ENDPOINT_URL=http://localhost:4566 in .env or run via dev.sh.")

    print(f"Polling queue: {settings.JOBS_QUEUE_URL}")
    print(f"Using AWS_ENDPOINT_URL: {settings.AWS_ENDPOINT_URL or '(default/real AWS)'}")
    print("Press Ctrl+C to stop\n")
    
    sqs_kwargs = {}
    if settings.AWS_ENDPOINT_URL:
        sqs_kwargs["endpoint_url"] = settings.AWS_ENDPOINT_URL
    
    sqs = boto3.client("sqs", **sqs_kwargs)
    
    while True:
        try:
            # Receive messages
            response = sqs.receive_message(
                QueueUrl=settings.JOBS_QUEUE_URL,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=20,  # Long polling
                VisibilityTimeout=300,  # 5 minutes
            )
            
            messages = response.get("Messages", [])
            if not messages:
                print("No messages, waiting...")
                continue
            
            for msg in messages:
                receipt_handle = msg["ReceiptHandle"]
                body = msg["Body"]
                
                print(f"Processing message: {msg['MessageId']}")
                
                # Format as Lambda event
                lambda_event = {
                    "Records": [
                        {
                            "body": body,
                            "messageId": msg["MessageId"],
                            "receiptHandle": receipt_handle,
                        }
                    ]
                }
                
                try:
                    # Process the message
                    result = handler(lambda_event, None)
                    print(f"✓ Processed successfully: {result}")
                    
                    # Delete message from queue
                    sqs.delete_message(
                        QueueUrl=settings.JOBS_QUEUE_URL,
                        ReceiptHandle=receipt_handle,
                    )
                    print(f"✓ Deleted message from queue\n")
                    
                except Exception as e:
                    print(f"✗ Error processing message: {e}")
                    import traceback
                    traceback.print_exc()
                    # Don't delete on error - let it become visible again
                    print("Message will be retried\n")
                    
        except KeyboardInterrupt:
            print("\nStopping...")
            break
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    process_queue()

