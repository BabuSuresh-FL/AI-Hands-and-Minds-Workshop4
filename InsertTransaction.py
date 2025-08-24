import os
import json
import pg8000.native
from datetime import datetime

# InsertTransaction function

def lambda_handler(event, context):
    try:
        print(f"My Received event: {json.dumps(event, default=str)}")
        
        # Extract parameters from Bedrock's format (same as GetRecentTransactions)
        account_id = None
        amount = None
        transaction_type = "Debit"  # default
        description = ""
        related_party = ""
        
        # Parse the requestBody properties
        if 'requestBody' in event and 'content' in event['requestBody']:
            properties = event['requestBody']['content']['application/json']['properties']
            for prop in properties:
                if prop['name'] == 'accountId':
                    account_id = int(prop['value'])
                elif prop['name'] == 'amount':
                    amount = float(prop['value'])
                elif prop['name'] == 'transactionType':
                    transaction_type = prop['value']
                elif prop['name'] == 'description':
                    description = prop['value']
                elif prop['name'] == 'relatedParty':
                    related_party = prop['value']
        
        # Validate required parameters
        if account_id is None or amount is None:
            raise ValueError("accountId and amount are required parameters")
        
        print(f"Processing: accountId={account_id}, amount={amount}, type={transaction_type}")
        # Connect to PostgreSQL 
        conn = pg8000.native.Connection(
            host=os.environ['PG_HOST'],
            database=os.environ['PG_DATABASE'],
            user=os.environ['PG_USER'],
            password=os.environ['PG_PASSWORD']
        )        
        
        # Insert transaction
        insert_query = """
        INSERT INTO public.transactions 
        (accountid, amount, transactiontype, description, relatedparty, createdat)
        VALUES (:account_id, :amount, :transaction_type, :description, :related_party, :created_at)
        RETURNING transactionid
        """
        
        result = conn.run(insert_query,
                         account_id=account_id,
                         amount=amount,
                         transaction_type=transaction_type,
                         description=description,
                         related_party=related_party,
                         created_at=datetime.now())
        
        transaction_id = result[0][0]
        
        # Update account balance
        update_query = """
        UPDATE public.accounts 
        SET balance = balance + :amount 
        WHERE accountid = :account_id
        """
        
        conn.run(update_query, amount=amount, account_id=account_id)
        conn.close()
        
        # Format response (friendly message)
        action_word = "credited to" if amount >= 0 else "debited from" 
        response_text = f"Transaction #{transaction_id} successfully created! ${abs(amount):.2f} {action_word} account {account_id}. Description: {description} ({related_party})"
        
        # Return in Bedrock's expected format (EXACT same as GetRecentTransactions)
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
                "actionGroup": event.get("actionGroup", "InsertTransaction"),
                "apiPath": event.get("apiPath", "/insert-transaction"),
                "httpMethod": event.get("httpMethod", "POST"),
                "httpStatusCode": 500,
                "responseBody": {
                    "application/json": {
                        "body": f"Error creating transaction: {str(e)}"
                    }
                }
            }
        }