import os
import json
import pg8000.native
from datetime import datetime

def lambda_handler(event, context):
    try:
        print(f"Received event: {json.dumps(event, default=str)}")
        
        # Extract input parameters
        user_desired_section_number = None
        user_desired_number_of_seats = None
        person_name = None
        person_phone = None
        person_email = None
        
        # Parse the requestBody properties 
        if 'requestBody' in event and 'content' in event['requestBody']:
            properties = event['requestBody']['content']['application/json']['properties']
            for prop in properties:
                if prop['name'] == 'user_desired_section_number':
                    user_desired_section_number = int(prop['value'])
                elif prop['name'] == 'user_desired_number_of_seats':
                    user_desired_number_of_seats = int(prop['value'])
                elif prop['name'] == 'person_name':
                    person_name = prop['value']
                elif prop['name'] == 'person_phone':
                    person_phone = prop['value']
                elif prop['name'] == 'person_email':
                    person_email = prop['value']
        
        # Validate required parameters
        if (user_desired_section_number is None or user_desired_number_of_seats is None or 
            person_name is None or person_phone is None or person_email is None):
            raise ValueError("All parameters are required: user_desired_section_number, user_desired_number_of_seats, person_name, person_phone, person_email")
        
        print(f"Processing ticket purchase: section={user_desired_section_number}, seats={user_desired_number_of_seats}, name={person_name}")
        
        # Connect to PostgreSQL
        conn = pg8000.native.Connection(
            host=os.environ['PG_HOST'],
            database=os.environ['PG_DATABASE'],
            user=os.environ['PG_USER'],
            password=os.environ['PG_PASSWORD']
        )
        
        # Query ticket_availability for availability
        availability_query = """
        SELECT section_number, total_available_seats, ticket_price
        FROM ticket_availability 
        WHERE section_number = :section_number 
        AND total_available_seats >= :required_seats
        """
        
        availability_result = conn.run(availability_query,
                                     section_number=user_desired_section_number,
                                     required_seats=user_desired_number_of_seats)
        
        # (A1) If no records are returned
        if not availability_result:
            conn.close()
            response_text = "Your requested section seats are all sold out. Please choose a different section."
            
            return {
                "messageVersion": "1.0",
                "response": {
                    "actionGroup": event.get("actionGroup", "TicketPurchase"),
                    "apiPath": event.get("apiPath", "/purchase-ticket"),
                    "httpMethod": event.get("httpMethod", "POST"),
                    "httpStatusCode": 200,
                    "responseBody": {
                        "application/json": {
                            "body": response_text
                        }
                    }
                }
            }
        
        # (A2.1) If one record is returned
        section_info = availability_result[0]
        section_number = section_info[0]
        current_available_seats = section_info[1]
        ticket_price = section_info[2]
        
        # Begin transaction for atomicity
        conn.run("BEGIN")
        
        try:
            # (A2.1.1) Update ticket_availability to reduce available seats
            update_seats_query = """
            UPDATE ticket_availability 
            SET total_available_seats = total_available_seats - :seats_to_purchase
            WHERE section_number = :section_number
            """
            
            conn.run(update_seats_query,
                    seats_to_purchase=user_desired_number_of_seats,
                    section_number=user_desired_section_number)
            
            # (A2.1.2) Insert new record into ticket_transactions
            insert_transaction_query = """
            INSERT INTO ticket_transactions (
                section_number, purchased_price, purchaser_name, purchaser_phone, purchaser_email
            ) VALUES (
                :section_number, :purchased_price, :purchaser_name, :purchaser_phone, :purchaser_email
            ) RETURNING transaction_id, section_number, seat_number, purchased_price, 
                       purchaser_name, purchaser_phone, purchaser_email
            """
            
            transaction_result = conn.run(insert_transaction_query,
                                        section_number=user_desired_section_number,
                                        purchased_price=ticket_price,
                                        purchaser_name=person_name,
                                        purchaser_phone=person_phone,
                                        purchaser_email=person_email)
            
            # Commit the transaction
            conn.run("COMMIT")
            
            # Extract the inserted record details
            inserted_record = transaction_result[0]
            transaction_id = inserted_record[0]
            returned_section_number = inserted_record[1]
            seat_number = inserted_record[2]
            returned_purchased_price = inserted_record[3]
            returned_purchaser_name = inserted_record[4]
            returned_purchaser_phone = inserted_record[5]
            returned_purchaser_email = inserted_record[6]
            
            conn.close()
            
            # (A2.1.3) Return success message with seat details
            response_text = """Your requested section has available seats. We have successfully purchased your ticket. Congratulations. Here is your seat details.

Transaction Number: {}
section_number: {}
seat_number: {}
purchased_price: {}
purchaser_name: {}
purchaser_phone: {}
purchaser_email: {}""".format(
                transaction_id,
                returned_section_number,
                seat_number,
                returned_purchased_price,
                returned_purchaser_name,
                returned_purchaser_phone,
                returned_purchaser_email
            )
            
            return {
                "messageVersion": "1.0",
                "response": {
                    "actionGroup": event.get("actionGroup", "TicketPurchase"),
                    "apiPath": event.get("apiPath", "/purchase-ticket"),
                    "httpMethod": event.get("httpMethod", "POST"),
                    "httpStatusCode": 200,
                    "responseBody": {
                        "application/json": {
                            "body": response_text
                        }
                    }
                }
            }
            
        except Exception as transaction_error:
            # Rollback on any error during the transaction
            conn.run("ROLLBACK")
            conn.close()
            raise transaction_error
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": event.get("actionGroup", "TicketPurchase"),
                "apiPath": event.get("apiPath", "/purchase-ticket"),
                "httpMethod": event.get("httpMethod", "POST"),
                "httpStatusCode": 500,
                "responseBody": {
                    "application/json": {
                        "body": f"Error processing ticket purchase: {str(e)}"
                    }
                }
            }
        }