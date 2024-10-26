from flask import Blueprint, request, jsonify
from services.whatsapp_bot_service import setup_whatsapp_service, process_whatsapp_message
import logging

# Initialize Flask Blueprint
whatsapp_bot_bp = Blueprint('whatsapp_bot', __name__)

# Logging configuration
log_handler = logging.FileHandler('whatsapp_bot.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
log_handler.setFormatter(formatter)
logging.getLogger().addHandler(log_handler)
logging.getLogger().setLevel(logging.INFO)

# Dictionary to hold user sessions data
user_sessions = {}

# API route to start WhatsApp interaction when a user provides their phone number
@whatsapp_bot_bp.route('/setup_whatsapp', methods=['POST'])
def setup_whatsapp():
    try:
        data = request.json
        user_phone = data.get('phone_number')
        process_id = data.get('process_id')
        para_id = data.get('para_id')
        data_collection_id = data.get('data_collection_id')

        if not user_phone:
            logging.error("Phone number not provided")
            return jsonify({'status': 'error', 'message': 'Phone number is required'}), 400


        # Set up WhatsApp service
        response = setup_whatsapp_service(user_phone, process_id, para_id, data_collection_id)
        return jsonify(response), 200
    except Exception as e:
        logging.error(f"Error in setup_whatsapp: {str(e)}")
        return jsonify({'status': 'error', 'message': 'An error occurred while setting up WhatsApp.'}), 500

@whatsapp_bot_bp.route('/webhooks', methods=['POST'])
def webhooks():
    try:
        incoming_msg = request.form.get('Body').strip().lower()
        from_number = request.form.get('From')

        logging.info(f"Received message from {from_number}: {incoming_msg}")

        # Pass the message and phone number to service for processing
        response = process_whatsapp_message(from_number, incoming_msg)
        return jsonify(response), 200
    except Exception as e:
        logging.error(f"Error in webhooks: {str(e)}")
        return jsonify({'status': 'error', 'message': 'An error occurred while processing the message.'}), 500