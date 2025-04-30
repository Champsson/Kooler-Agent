from twilio.rest import Client
from ..config import config
from ..utils import get_logger

logger = get_logger(__name__)

# Initialize Twilio client
twilio_client = None
if config.TWILIO_ACCOUNT_SID and config.TWILIO_AUTH_TOKEN:
    try:
        twilio_client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
        logger.info("Twilio client initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize Twilio client: {e}", exc_info=True)
        # Depending on requirements, you might want to raise an error here
else:
    logger.warning("Twilio credentials not found. Twilio functionality will be disabled.")

def send_sms(to_number: str, body: str):
    """Sends an SMS message using Twilio."""
    if not twilio_client:
        logger.error("Twilio client not initialized. Cannot send SMS.")
        raise ConnectionError("Twilio client is not available.")

    if not config.TWILIO_PHONE_NUMBER:
        logger.error("Twilio phone number not configured. Cannot send SMS.")
        raise ValueError("Twilio phone number not set.")

    try:
        logger.info(f"Sending SMS to {to_number} from {config.TWILIO_PHONE_NUMBER}")
        message = twilio_client.messages.create(
            body=body,
            from_=config.TWILIO_PHONE_NUMBER,
            to=to_number
        )
        logger.info(f"SMS sent successfully. SID: {message.sid}")
        return message.sid
    except Exception as e:
        logger.error(f"Failed to send SMS to {to_number}: {e}", exc_info=True)
        raise

# Add other Twilio functions as needed (e.g., initiating calls, fetching call logs)

# Example usage (for testing)
if __name__ == "__main__":
    # Replace with a test phone number
    test_to_number = "+15559876543" 
    test_body = "Hello from Weggy (Twilio Test)!"
    
    if twilio_client and config.TWILIO_PHONE_NUMBER:
        print(f"Attempting to send test SMS to {test_to_number}...")
        try:
            sid = send_sms(test_to_number, test_body)
            print(f"Test SMS sent successfully. SID: {sid}")
        except Exception as e:
            print(f"Failed to send test SMS: {e}")
    else:
        print("Twilio client not configured. Skipping SMS test.")

