from datetime import datetime
import re
from supabase import create_client, Client
from twilio_config import client, TWILIO_WHATSAPP_NUM
import logging
import threading
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants for message intervals (in seconds)
COLLECT_DATA_INTERVAL = 86400  # 24 hours in seconds

# Supabase credentials
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
join_code = os.getenv('WHATSAPP_JOIN_CODE')
# Create Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# A dictionary to hold temporary user sessions for WhatsApp interaction
user_sessions = {}
user_data = {}

# Schema for the fields we expect from users (order matters)
schema_fields = ['value', 'log_unit', 'log_date', 'evidence_url', 'evidence_name']

# Static user joined status (for testing purposes, you can adjust as needed)
USER_JOINED = True  # Set to True if the user is joined, False otherwise

# Reset user session
def reset_user_session(phone_number):
    user_sessions[phone_number] = {
        'field_index': 0,
        'data': {},
        'status': 'waiting_for_join_code'
    }
    logging.info(f"User session reset for {phone_number}")

# Check if the user is joined (static logic)
def is_user_joined(phone_number):
    return USER_JOINED

# Update user's join status (no-op for static logic)
def update_user_join_status(phone_number, joined_status):
    pass  # No-op for static logic

# Setup WhatsApp service for a user
def setup_whatsapp_service(user_phone, process_id, para_id, data_collection_id):
    user_data['whatsapp'] = {
                'process_id': process_id,
                'para_id': para_id,
                'data_collection_id': data_collection_id
        }
  
    try:
        if is_user_joined(user_phone):
            reset_user_session(f"whatsapp:{user_phone}")
            client.messages.create(
                body="Welcome! Let's start by collecting some information. Please say hello.",
                from_=TWILIO_WHATSAPP_NUM,
                to=f"whatsapp:{user_phone}"
            )
            return {'status': 'success', 'message': f"Please send the message '{join_code}' to this WhatsApp number {TWILIO_WHATSAPP_NUM} to join the sandbox and say Hello!"}
        else:
              # Fetch from environment variables
            sandbox_number = TWILIO_WHATSAPP_NUM
            client.messages.create(
                body=f"Please send the message '{join_code}' to {sandbox_number} to join the sandbox.",
                from_=TWILIO_WHATSAPP_NUM,
                to=f"whatsapp:{user_phone}"
            )
            reset_user_session(f"whatsapp:{user_phone}")
            return {'status': 'success', 'message': f"Join code sent to {TWILIO_WHATSAPP_NUM} with {join_code}. Please follow the instructions to join WhatsApp bot, and say Hello!."}
        
       
    except Exception as e:
        logging.error(f"Error setting up WhatsApp service for {user_phone}: {e}")
        return {'status': 'error', 'message': 'Failed to send join instructions.'}



# Process incoming WhatsApp messages
def process_whatsapp_message(from_number, incoming_msg):
    try:
        if from_number not in user_sessions:
            reset_user_session(from_number)

        user_session = user_sessions[from_number]

        if user_session['status'] == 'waiting_for_join_code':
            if is_user_joined(from_number):
                user_session['status'] = 'collecting_data'
                client.messages.create(
                    body="Welcome! Let's start by collecting some information. Please provide the value.",
                    from_=TWILIO_WHATSAPP_NUM,
                    to=from_number
                )
                return {'status': 'welcome sent, collecting data'}
            else:
                client.messages.create(
                    body="Please join the sandbox by sending the join code.",
                    from_=TWILIO_WHATSAPP_NUM,
                    to=from_number
                )
                return {'status': 'waiting for join code'}

        if user_session['status'] == 'collecting_data':
            return handle_data_collection(from_number, incoming_msg)
    except Exception as e:
        logging.error(f"Error processing message from {from_number}: {e}")
        return {'status': 'error'}

def handle_data_collection(from_number, incoming_msg):
    user_session = user_sessions[from_number]
    field_index = user_session['field_index']
    current_field = schema_fields[field_index]

    try:
        # Process value
        if current_field == 'value':
            if not re.search(r'\d+', incoming_msg):
                return request_field(from_number, 'Invalid value. Please provide a numeric value.', 'value')
            user_session['data']['value'] = incoming_msg
        # Process log_unit
        elif current_field == 'log_unit':
            user_session['data']['log_unit'] = incoming_msg
        # Process log_date
        elif current_field == 'log_date':
            log_date = validate_date(incoming_msg)
            if not log_date:
                return request_field(from_number, 'Invalid date format. Please provide the log date in YYYY-MM-DD format.', 'log_date')
            user_session['data']['log_date'] = log_date
        # Process evidence_url
        elif current_field == 'evidence_url':
            if incoming_msg == 'no evidence':
                user_session['data']['evidence_url'] = None
            elif incoming_msg.startswith('http'):
                user_session['data']['evidence_url'] = incoming_msg
            else:
                return request_field(from_number, 'Invalid URL. Please provide a valid URL or type "No evidence".', 'evidence_url')
        # Process evidence_name
        elif current_field == 'evidence_name':
            user_session['data']['evidence_name'] = incoming_msg
        

        # Proceed to the next field
        if field_index < len(schema_fields) - 1:
            user_session['field_index'] += 1
            next_field = schema_fields[user_session['field_index']]
            return request_field(from_number, f"Please provide {next_field.replace('_', ' ')}.", next_field)

        # All fields collected
        save_user_data_to_db(from_number, user_session['data'])
        reset_user_session(from_number)

    except Exception as e:
        logging.error(f"Error collecting data from {from_number}: {e}")
        client.messages.create(
            body="An unexpected error occurred. Please try again later.",
            from_=TWILIO_WHATSAPP_NUM,
            to=from_number
        )
        return {'status': 'error'}

def validate_date(date_str):
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').strftime('%Y-%m-%d')
    except ValueError:
        return None

def request_field(phone_number, message, field):
    client.messages.create(
        body=message,
        from_=TWILIO_WHATSAPP_NUM,
        to=phone_number
    )
    logging.info(f"Requested {field} from {phone_number}")
    return {'status': 'waiting for correct data'}

# Save collected data to the database
def save_user_data_to_db(from_number, data):
    try:
        supabase.table('parameter_log').insert({
            'log_date': data['log_date'],
            'value': data['value'],
            'log_unit': data['log_unit'],
            'evidence_url': data.get('evidence_url'),
            'evidence_name': data.get('evidence_name'),
            'process_id': user_data["whatsapp"].get('process_id'),  # Accessing user_data
            'para_id': user_data["whatsapp"].get('para_id'),
            'data_collection_id': user_data["whatsapp"].get('data_collection_id')
        }).execute()

        client.messages.create(
            body="Data saved successfully! We'll ask for new data in 24 hours.",
            from_=TWILIO_WHATSAPP_NUM,
            to=from_number
        )
        logging.info(f"Data saved for {from_number}")
        schedule_next_data_request(from_number)

    except Exception as e:
        logging.error(f"Error saving data: {e}")
        client.messages.create(
            body="Error saving data. Please try again later.",
            from_=TWILIO_WHATSAPP_NUM,
            to=from_number
        )

# Schedule the next data request in 24 hours
def schedule_next_data_request(phone_number):
    def ask_for_data():
        reset_user_session(phone_number)
        client.messages.create(
            body="Let's collect new information. Please provide the value.",
            from_=TWILIO_WHATSAPP_NUM,
            to=phone_number
        )
        logging.info(f"Next data request sent to {phone_number}")

    timer = threading.Timer(COLLECT_DATA_INTERVAL, ask_for_data)  # 24-hour delay
    timer.start()
    logging.info(f"Scheduled next data request for {phone_number} in 24 hours.")