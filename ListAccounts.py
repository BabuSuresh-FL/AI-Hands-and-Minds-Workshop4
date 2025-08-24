import os
import json
import pg8000.native

# ListAccounts function

def lambda_handler(event, context):
    try:
        print(f"Received event: {json.dumps(event, default=str)}")

        # Default user_id if none provided
        user_id = None
        
        # Parse the userId from requestBody in Bedrock format
        if 'requestBody' in event and 'content' in event['requestBody']:
            properties = event['requestBody']['content']['application/json']['properties']
            for prop in properties:
                if prop['name'] == 'userId':
                    user_id = int(prop['value'])  # Convert string to int

        if user_id is None:
            raise ValueError("User ID must be provided")

        print(f"Fetching accounts for userId: {user_id}")

        # Connect to PostgreSQL 
        conn = pg8000.native.Connection(
            host=os.environ['PG_HOST'],
            database=os.environ['PG_DATABASE'],
            user=os.environ['PG_USER'],
            password=os.environ['PG_PASSWORD']
        )

        # Query to get all accounts for the given user ID
        query = """
            SELECT accountid, accounttype, currency, balance, createdat
            FROM public.accounts
            WHERE userid = :user_id
            ORDER BY createdat ASC
        """

        rows = conn.run(query, user_id=user_id)
        conn.close()

        # rows is a list of rows, each row is a list of columns
        if rows and len(rows) > 0:
            accounts = []
            for row in rows:
                account = {
                    "accountId": row[0],
                    "accountType": row[1],
                    "currency": row[2],
                    "balance": float(row[3]),  # Convert Decimal to float for JSON serialization
                    "createdAt": row[4].isoformat() if row[4] else None  # Convert timestamp to ISO string
                }
                accounts.append(account)
            
            response_data = {
                "userId": user_id,
                "totalAccounts": len(accounts),
                "accounts": accounts
            }
            response_text = json.dumps(response_data)
        else:
            response_data = {
                "userId": user_id,
                "totalAccounts": 0,
                "accounts": []
            }
            response_text = json.dumps(response_data)

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
                "actionGroup": event.get("actionGroup", "ListAccounts"),
                "apiPath": event.get("apiPath", "/listAccounts"),
                "httpMethod": event.get("httpMethod", "POST"),
                "httpStatusCode": 500,
                "responseBody": {
                    "application/json": {
                        "body": f"Error retrieving user accounts: {str(e)}"
                    }
                }
            }
        }