from twilio.rest import Client
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Twilio credentials and phone numbers
TWILIO_SID = os.getenv('TWILIO_SID')
TWILIO_AUTHTOKEN = os.getenv('TWILIO_AUTHTOKEN')
TWILIO_WHATSAPP_NUM = os.getenv('TWILIO_WHATSAPP_NUM')

# Initialize Twilio client
client = Client(TWILIO_SID, TWILIO_AUTHTOKEN)
