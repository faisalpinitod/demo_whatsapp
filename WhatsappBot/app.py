from flask import Flask
from api.routes.whatsapp_bot import whatsapp_bot_bp  # Import the WhatsApp bot blueprint
from flask_cors import CORS
import logging

# Create the Flask app
app = Flask(__name__)

# Enable CORS for cross-origin requests if needed (optional)
CORS(app)

# Register the WhatsApp bot blueprint
app.register_blueprint(whatsapp_bot_bp, url_prefix='/api')

# Set up logging
log_handler = logging.FileHandler('whatsapp_bot.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
log_handler.setFormatter(formatter)
app.logger.addHandler(log_handler)
app.logger.setLevel(logging.INFO)

@app.route('/', methods=['GET'])
def home():
    return "Welcome to the WhatsApp Bot Service!"

if __name__ == '__main__':
    # You can set debug to False for production
    app.run(debug=True,host='0.0.0.0', port=5000)
