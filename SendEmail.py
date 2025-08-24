import json
import boto3
from botocore.exceptions import ClientError
import os

# SendEmail function

def lambda_handler(event, context):
    try:
        print(f"Received event: {json.dumps(event, default=str)}")
        
        # Initialize SES client
        ses_client = boto3.client('ses', region_name=os.environ.get('MY_AWS_REGION', 'us-east-1'))
        
        # Default values
        recipient_email = None
        subject = "Banking Notification"
        message_body = "This is a test email from your banking system."
        
        # Parse parameters from requestBody in Bedrock format
        if 'requestBody' in event and 'content' in event['requestBody']:
            properties = event['requestBody']['content']['application/json']['properties']
            for prop in properties:
                if prop['name'] == 'recipientEmail':
                    recipient_email = prop['value']
                elif prop['name'] == 'subject':
                    subject = prop['value']
                elif prop['name'] == 'messageBody':
                    message_body = prop['value']
        
        # Validate required parameters
        if not recipient_email:
            raise ValueError("Recipient email address must be provided")
        
        # Get sender email from environment variable
        sender_email = os.environ.get('SENDER_EMAIL')
        if not sender_email:
            raise ValueError("SENDER_EMAIL environment variable must be set")
        
        print(f"Sending email from {sender_email} to {recipient_email}")
        print(f"Subject: {subject}")
        
        # Send email via SES
        response = ses_client.send_email(
            Source=sender_email,
            Destination={
                'ToAddresses': [recipient_email]
            },
            Message={
                'Subject': {
                    'Data': subject,
                    'Charset': 'UTF-8'
                },
                'Body': {
                    'Text': {
                        'Data': message_body,
                        'Charset': 'UTF-8'
                    },
                    'Html': {
                        'Data': f"""
                        <html>
                            <body>
                                <h2>Banking System Notification</h2>
                                <p>{message_body}</p>
                                <hr>
                                <p><small>This email was sent from your Banking AI System</small></p>
                            </body>
                        </html>
                        """,
                        'Charset': 'UTF-8'
                    }
                }
            }
        )
        
        message_id = response['MessageId']
        success_message = f"Email sent successfully to {recipient_email}. Message ID: {message_id}"
        print(success_message)
        
        # Return success response in Bedrock format
        return {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": event.get("actionGroup", "SendEmail"),
                "apiPath": event.get("apiPath", "/sendEmail"),
                "httpMethod": event.get("httpMethod", "POST"),
                "httpStatusCode": 200,
                "responseBody": {
                    "application/json": {
                        "body": json.dumps({
                            "success": True,
                            "message": success_message,
                            "messageId": message_id,
                            "recipientEmail": recipient_email
                        })
                    }
                }
            }
        }
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        print(f"SES ClientError: {error_code} - {error_message}")
        
        # Return error response
        return {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": event.get("actionGroup", "SendEmail"),
                "apiPath": event.get("apiPath", "/sendEmail"),
                "httpMethod": event.get("httpMethod", "POST"),
                "httpStatusCode": 500,
                "responseBody": {
                    "application/json": {
                        "body": f"SES Error: {error_code} - {error_message}"
                    }
                }
            }
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": event.get("actionGroup", "SendEmail"),
                "apiPath": event.get("apiPath", "/sendEmail"),
                "httpMethod": event.get("httpMethod", "POST"),
                "httpStatusCode": 500,
                "responseBody": {
                    "application/json": {
                        "body": f"Error sending email: {str(e)}"
                    }
                }
            }
        }