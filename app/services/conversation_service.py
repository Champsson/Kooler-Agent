from app.utils import timer_decorator, logger
from app.services.assistant_service import process_with_assistant
import json

# Simple in-memory session store (replace with Redis in production)
SESSION_STORE = {}

@timer_decorator
def process_conversation(message, mode='api', session_id=None):
    """Process a conversation message and return a response"""
    try:
        # Get existing thread ID from session if available
        thread_id = None
        if session_id and session_id in SESSION_STORE:
            thread_id = SESSION_STORE.get(session_id, {}).get('thread_id')
        
        # Process the message with the OpenAI Assistant
        response, new_thread_id = process_with_assistant(message, thread_id)
        
        # Store the thread ID in the session
        if session_id:
            if session_id not in SESSION_STORE:
                SESSION_STORE[session_id] = {}
            SESSION_STORE[session_id]['thread_id'] = new_thread_id
        
        # Log the conversation
        logger.info(f"Mode: {mode}, Message: {message}, Response: {response}")
        
        return response
    except Exception as e:
        logger.error(f"Error processing conversation: {str(e)}")
        # Fallback responses if there's an error
        if "hours" in message.lower():
            return "Kooler Garage Doors is open Monday through Friday from 8am to 6pm, and Saturday from 9am to 2pm."
        elif "warranty" in message.lower():
            return "Kooler Garage Doors offers a 5-year warranty on all installations and a 1-year warranty on repairs."
        elif "appointment" in message.lower() or "schedule" in message.lower():
            return "I'd be happy to help you schedule an appointment. Please provide your preferred date and time, and I'll check our availability."
        else:
            return "Thank you for contacting Kooler Garage Doors. How can I assist you with your garage door needs today?"
