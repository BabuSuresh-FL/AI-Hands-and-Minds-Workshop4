import os
import json
import pg8000.native

# GetAccountBalance function

def lambda_handler(event, context):
    try:
        print(f"Received event: {json.dumps(event, default=str)}")

        # Default account_id if none provided
        account_id = 1
        
        # Parse the accountId from requestBody in Bedrock format
        if 'requestBody' in event and 'content' in event['requestBody']:
            properties = event['requestBody']['content']['application/json']['properties']
            for prop in properties:
                if prop['name'] == 'accountId':
                    account_id = int(prop['value'])  # Convert string to int

        if account_id is None:
            raise ValueError("Account ID must be provided")

        print(f"Fetching balance for accountId: {account_id}")

        # Connect to PostgreSQL 
        conn = pg8000.native.Connection(
            host=os.environ['PG_HOST'],
            database=os.environ['PG_DATABASE'],
            user=os.environ['PG_USER'],
            password=os.environ['PG_PASSWORD']
        )

        # Query to get the balance for the given account ID
        query = """
            SELECT balance
            FROM public.accounts
            WHERE accountid = :account_id
        """

        rows = conn.run(query, account_id=account_id)
        conn.close()

        # rows is a list of rows, each row is a list of columns
        if rows and len(rows) > 0:
            balance = rows[0][0]  # Extract the balance value from first row, first column
            response_text = f"Account balance for account {account_id} is ${balance:.2f}"
        else:
            response_text = f"No account found with account ID {account_id}"

        # Return in Bedrock's expected format
        return {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": event["actionGroup"],
                "apiPath": event["apiPath"], 
                "httpMethod": event["httpMethod"],
                "httpStatusCode": 200,
                "responseBody": {
                    "application/json": {
                        "body": response_text
                    }
                }
            }
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": event.get("actionGroup", "GetAccountBalance"),
                "apiPath": event.get("apiPath", "/accountBalance"),
                "httpMethod": event.get("httpMethod", "POST"),
                "httpStatusCode": 500,
                "responseBody": {
                    "application/json": {
                        "body": f"Error retrieving account balance: {str(e)}"
                    }
                }
            }
        }