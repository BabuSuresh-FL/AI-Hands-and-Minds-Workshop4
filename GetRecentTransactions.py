import os
import json
import pg8000.native

# GetRecentTransactions function

def lambda_handler(event, context):
    try:
        print(f"My Received event: {json.dumps(event, default=str)}")
        
        # Extract parameters from Bedrock's format.
        account_id = 1  # default
        limit = 100      # default
        
        # Parse the requestBody properties
        if 'requestBody' in event and 'content' in event['requestBody']:
            properties = event['requestBody']['content']['application/json']['properties']
            for prop in properties:
                if prop['name'] == 'accountId':
                    account_id = int(prop['value'])  # Convert string to int
                elif prop['name'] == 'limit':
                    limit = int(prop['value'])
        
        print(f"My accountId: {account_id}, limit: {limit}")
        
        # Connect to PostgreSQL 
        conn = pg8000.native.Connection(
            host=os.environ['PG_HOST'],
            database=os.environ['PG_DATABASE'],
            user=os.environ['PG_USER'],
            password=os.environ['PG_PASSWORD']
        )
        
        # Query transactions
        query = """
        SELECT transactionid, amount, transactiontype, description, 
               relatedparty, createdat
        FROM public.transactions 
        WHERE accountid = :account_id 
        ORDER BY createdat DESC 
        LIMIT :limit_val
        """
        
        rows = conn.run(query, account_id=account_id, limit_val=limit)
        conn.close()
        
        # Format response for Bedrock
        if rows:
            response_text = f"Recent transactions for My account {account_id}:\n\n"
            for row in rows:
                response_text += f"• ${row[1]} - {row[3]} ({row[4]}) on {str(row[5])[:10]}\n"
        else:
            response_text = f"No transactions found for My account {account_id}"
        
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
                "actionGroup": event.get("actionGroup", "GetRecentTransactions"),
                "apiPath": event.get("apiPath", "/transactions"),
                "httpMethod": event.get("httpMethod", "POST"),
                "httpStatusCode": 500,
                "responseBody": {
                    "application/json": {
                        "body": f"Error retrieving transactions: {str(e)}"
                    }
                }
            }
        }