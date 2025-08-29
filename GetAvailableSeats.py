import os
import json
import pg8000.native

# GetAvailableSeats function

def lambda_handler(event, context):
    try:
        print(f"My Received event: {json.dumps(event, default=str)}")
        
        print("Fetching available seats from ticket_availability")
        
        # Connect to PostgreSQL 
        conn = pg8000.native.Connection(
            host=os.environ['PG_HOST'],
            database=os.environ['PG_DATABASE'],
            user=os.environ['PG_USER'],
            password=os.environ['PG_PASSWORD']
        )
        
        # Query ticket_availability for rows with total_available_seats > 0
        query = """
        SELECT section_number, total_available_seats, how_far_is_it_from_ground, ticket_price
        FROM public.ticket_availability 
        WHERE total_available_seats > 0 
        ORDER BY section_number ASC
        """
        
        rows = conn.run(query)
        conn.close()
        
        # Format response for Bedrock
        if rows:
            response_text = f"Available sections with seats (total: {len(rows)} sections):\n\n"
            for row in rows:
                section_number = row[0]
                available_seats = row[1]
                distance_from_ground = row[2]
                price = row[3]
                response_text += f"• Section {section_number}: {available_seats} seats available, {distance_from_ground}, ${price}\n"
        else:
            response_text = "No sections with available seats found"
        
        # Return in Bedrock's expected format
        return {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": event.get("actionGroup", "GetAvailableSeats"),
                "apiPath": event.get("apiPath", "/available-seats"),
                "httpMethod": event.get("httpMethod", "GET"),
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
                "actionGroup": event.get("actionGroup", "GetAvailableSeats"),
                "apiPath": event.get("apiPath", "/available-seats"),
                "httpMethod": event.get("httpMethod", "GET"),
                "httpStatusCode": 500,
                "responseBody": {
                    "application/json": {
                        "body": f"Error retrieving available seats: {str(e)}"
                    }
                }
            }
        }