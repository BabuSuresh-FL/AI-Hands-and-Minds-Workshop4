import os
import json
import pg8000.native

# GetByUserID function

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

        print(f"Fetching user details for userId: {user_id}")

        # Connect to PostgreSQL 
        conn = pg8000.native.Connection(
            host=os.environ['PG_HOST'],
            database=os.environ['PG_DATABASE'],
            user=os.environ['PG_USER'],
            password=os.environ['PG_PASSWORD']
        )

        # Query to get user details for the given user ID
        query = """
            SELECT userid, fullname, email, phone, createdat
            FROM public.users
            WHERE userid = :user_id
        """

        rows = conn.run(query, user_id=user_id)
        conn.close()

        # rows is a list of rows, each row is a list of columns
        if rows and len(rows) > 0:
            user_row = rows[0]  # Get the first (and should be only) row
            user_details = {
                "userId": user_row[0],
                "fullName": user_row[1],
                "email": user_row[2],
                "phone": user_row[3],
                "createdAt": user_row[4].isoformat() if user_row[4] else None
            }
            
            response_text = json.dumps(user_details)
        else:
            response_data = {
                "error": f"No user found with user ID {user_id}"
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
                "actionGroup": event.get("actionGroup", "GetUserById"),
                "apiPath": event.get("apiPath", "/getUserById"),
                "httpMethod": event.get("httpMethod", "POST"),
                "httpStatusCode": 500,
                "responseBody": {
                    "application/json": {
                        "body": f"Error retrieving user details: {str(e)}"
                    }
                }
            }
        }