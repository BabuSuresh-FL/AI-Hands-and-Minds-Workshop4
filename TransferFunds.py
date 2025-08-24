import os
import json
import pg8000.native
from datetime import datetime

# TransferFunds function

def lambda_handler(event, context):
    try:
        print(f"Received event: {json.dumps(event, default=str)}")
        
        # Extract parameters from Bedrock's format
        from_account_id = None
        to_account_id = None
        amount = None
        description = "Account transfer"  # default
        
        # Parse the requestBody properties
        if 'requestBody' in event and 'content' in event['requestBody']:
            properties = event['requestBody']['content']['application/json']['properties']
            for prop in properties:
                if prop['name'] == 'fromAccountId':
                    from_account_id = int(prop['value'])
                elif prop['name'] == 'toAccountId':
                    to_account_id = int(prop['value'])
                elif prop['name'] == 'amount':
                    amount = float(prop['value'])
                elif prop['name'] == 'description':
                    description = prop['value']
        
        # Validate required parameters
        if from_account_id is None or to_account_id is None or amount is None:
            raise ValueError("fromAccountId, toAccountId, and amount are required parameters")
        
        if amount <= 0:
            raise ValueError("Transfer amount must be positive")
            
        print(f"Transfer: ${amount} from account {from_account_id} to account {to_account_id}")
 
        # Connect to PostgreSQL 
        conn = pg8000.native.Connection(
            host=os.environ['PG_HOST'],
            database=os.environ['PG_DATABASE'],
            user=os.environ['PG_USER'],
            password=os.environ['PG_PASSWORD']
        )
              
        current_time = datetime.now()
        
        # Step 1: Check source account balance
        balance_query = "SELECT balance FROM public.accounts WHERE accountid = :account_id"
        balance_result = conn.run(balance_query, account_id=from_account_id)
        
        if not balance_result:
            raise Exception(f"Source account {from_account_id} not found")
            
        current_balance = float(balance_result[0][0])
        if current_balance < amount:
            raise Exception(f"Insufficient funds. Current balance: ${current_balance:.2f}, Transfer amount: ${amount:.2f}")
        
        # Step 2: Create debit transaction (source account)
        debit_query = """
        INSERT INTO public.transactions 
        (accountid, amount, transactiontype, description, relatedparty, createdat)
        VALUES (:account_id, :amount, 'Transfer Out', :description, :related_party, :created_at)
        RETURNING transactionid
        """
        
        debit_result = conn.run(debit_query,
                               account_id=from_account_id,
                               amount=-amount,  # Negative for debit
                               description=description,
                               related_party=f"Transfer to Account {to_account_id}",
                               created_at=current_time)
        
        debit_transaction_id = debit_result[0][0]
        
        # Step 3: Create credit transaction (destination account)
        credit_query = """
        INSERT INTO public.transactions 
        (accountid, amount, transactiontype, description, relatedparty, createdat)
        VALUES (:account_id, :amount, 'Transfer In', :description, :related_party, :created_at)
        RETURNING transactionid
        """
        
        credit_result = conn.run(credit_query,
                                account_id=to_account_id,
                                amount=amount,  # Positive for credit
                                description=description,
                                related_party=f"Transfer from Account {from_account_id}",
                                created_at=current_time)
        
        credit_transaction_id = credit_result[0][0]
        
        # Step 4: Update account balances
        update_source = "UPDATE public.accounts SET balance = balance - :amount WHERE accountid = :account_id"
        conn.run(update_source, amount=amount, account_id=from_account_id)
        
        update_dest = "UPDATE public.accounts SET balance = balance + :amount WHERE accountid = :account_id"
        conn.run(update_dest, amount=amount, account_id=to_account_id)
        
        conn.close()
        
        # Format response
        response_text = f"Transfer completed successfully! ${amount:.2f} transferred from account {from_account_id} to account {to_account_id}. Transactions created: #{debit_transaction_id} (debit) and #{credit_transaction_id} (credit). Description: {description}"
        
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
                "actionGroup": event.get("actionGroup", "TransferFunds"),
                "apiPath": event.get("apiPath", "/transfer-funds"),
                "httpMethod": event.get("httpMethod", "POST"),
                "httpStatusCode": 500,
                "responseBody": {
                    "application/json": {
                        "body": f"Error processing transfer: {str(e)}"
                    }
                }
            }
        }