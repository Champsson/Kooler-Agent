import os
import time
import json
import openai
from app.config import Config
from app.utils import timer_decorator, logger

# Initialize OpenAI client
openai.api_key = Config.OPENAI_API_KEY

# Cache for assistant IDs
ASSISTANT_CACHE = {}

@timer_decorator
def create_or_get_assistant(assistant_name="Kooler Agent"):
    """Create or retrieve an OpenAI Assistant"""
    #asst_ZvBCMQHlSt8xfPTjYbpet6se from the OpenAI platform
    return "asst_ZvBCMQHlSt8xfPTjYbpet6se"

@timer_decorator
def create_thread():
    """Create a new conversation thread"""
    try:
        thread = openai.beta.threads.create()
        return thread.id
    except Exception as e:
        logger.error(f"Error creating thread: {str(e)}")
        # Return a mock thread ID for testing without API key
        return "thread_mock_for_testing"

@timer_decorator
def add_message_to_thread(thread_id, message, role="user"):
    """Add a message to a thread"""
    try:
        message = openai.beta.threads.messages.create(
            thread_id=thread_id,
            role=role,
            content=message
        )
        return message.id
    except Exception as e:
        logger.error(f"Error adding message to thread: {str(e)}")
        return "message_mock_for_testing"

@timer_decorator
def run_assistant(thread_id, assistant_id):
    """Run the assistant on a thread and return the response"""
    try:
        # Create a run
        run = openai.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id
        )
        
        # Poll for completion
        while True:
            run_status = openai.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )
            
            if run_status.status == 'completed':
                # Get messages
                messages = openai.beta.threads.messages.list(
                    thread_id=thread_id
                )
                # Return the latest assistant message
                for message in messages.data:
                    if message.role == "assistant":
                        return message.content[0].text.value
                
            elif run_status.status == 'requires_action':
                # Handle function calls
                required_actions = run_status.required_action.submit_tool_outputs.tool_calls
                tool_outputs = []
                
                for action in required_actions:
                    function_name = action.function.name
                    function_args = json.loads(action.function.arguments)
                    
                    # Execute the appropriate function
                    if function_name == 'schedule_appointment':
                        result = handle_schedule_appointment(function_args)
                    elif function_name == 'get_technical_info':
                        result = handle_get_technical_info(function_args)
                    elif function_name == 'check_appointment_status':
                        result = handle_check_appointment_status(function_args)
                    else:
                        result = {"error": "Unknown function"}
                    
                    tool_outputs.append({
                        "tool_call_id": action.id,
                        "output": json.dumps(result)
                    })
                
                # Submit the outputs back to the assistant
                openai.beta.threads.runs.submit_tool_outputs(
                    thread_id=thread_id,
                    run_id=run.id,
                    tool_outputs=tool_outputs
                )
            
            elif run_status.status in ['failed', 'cancelled', 'expired']:
                return f"Error: Run ended with status {run_status.status}"
            
            time.sleep(1)  # Poll every second
            
    except Exception as e:
        logger.error(f"Error running assistant: {str(e)}")
        # For testing without API key, return a mock response
        if Config.OPENAI_API_KEY == "your_openai_api_key":
            if "hours" in thread_id.lower():
                return "Kooler Garage Doors is open Monday through Friday from 8am to 6pm, and Saturday from 9am to 2pm."
            elif "warranty" in thread_id.lower():
                return "Kooler Garage Doors offers a 5-year warranty on all installations and a 1-year warranty on repairs."
            else:
                return "Thank you for contacting Kooler Garage Doors. How can I assist you with your garage door needs today?"
        return "I'm sorry, I encountered an error processing your request."

@timer_decorator
def process_with_assistant(message, thread_id=None):
    """Process a message with the OpenAI Assistant"""
    try:
        # Create a thread if not provided
        if not thread_id:
            thread_id = create_thread()
        
        # Add the message to the thread
        add_message_to_thread(thread_id, message)
        
        # Get the assistant ID
        assistant_id = create_or_get_assistant()
        
        # Run the assistant
        response = run_assistant(thread_id, assistant_id)
        
        return response, thread_id
    except Exception as e:
        logger.error(f"Error processing with assistant: {str(e)}")
        # For testing without API key, return a mock response
        if "hours" in message.lower():
            response = "Kooler Garage Doors is open Monday through Friday from 8am to 6pm, and Saturday from 9am to 2pm."
        elif "warranty" in message.lower():
            response = "Kooler Garage Doors offers a 5-year warranty on all installations and a 1-year warranty on repairs."
        elif "appointment" in message.lower() or "schedule" in message.lower():
            response = "I'd be happy to help you schedule an appointment. Please provide your preferred date and time, and I'll check our availability."
        else:
            response = "Thank you for contacting Kooler Garage Doors. How can I assist you with your garage door needs today?"
        
        return response, thread_id

# Function handlers for the assistant functions

def handle_schedule_appointment(args):
    """Handle the schedule_appointment function"""
    try:
        # In a real implementation, this would call ServiceTitan's API
        # For now, just return a mock response
        customer_name = args.get('customer_name', 'Unknown')
        service_type = args.get('service_type', 'Unknown')
        preferred_date = args.get('preferred_date', 'Unknown')
        preferred_time = args.get('preferred_time', 'Unknown')
        
        # Log the appointment request
        logger.info(f"Appointment request: {customer_name}, {service_type}, {preferred_date}, {preferred_time}")
        
        return {
            "success": True,
            "appointment_id": "appt_" + str(int(time.time())),
            "message": f"Appointment scheduled for {customer_name} on {preferred_date} at {preferred_time} for {service_type} service."
        }
    except Exception as e:
        logger.error(f"Error scheduling appointment: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def handle_get_technical_info(args):
    """Handle the get_technical_info function"""
    try:
        # In a real implementation, this would search your knowledge base
        # For now, just return a mock response
        search_query = args.get('search_query', '')
        model_number = args.get('model_number', '')
        part_name = args.get('part_name', '')
        
        # Log the technical info request
        logger.info(f"Technical info request: {search_query}, {model_number}, {part_name}")
        
        # Simple mock responses based on query
        if "spring" in search_query.lower():
            return {
                "success": True,
                "info": "Garage door springs typically last 7-9 years or 10,000 cycles. Signs of wear include gaps in the spring, stretched springs, or door balance issues."
            }
        elif "opener" in search_query.lower():
            return {
                "success": True,
                "info": "Standard garage door openers have a 1/2 HP motor and can lift most residential doors. For heavier doors, consider a 3/4 HP or 1 HP model."
            }
        else:
            return {
                "success": True,
                "info": "Please check the Kooler Garage Doors technical manual for detailed information on this topic."
            }
    except Exception as e:
        logger.error(f"Error getting technical info: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def handle_check_appointment_status(args):
    """Handle the check_appointment_status function"""
    try:
        # In a real implementation, this would call ServiceTitan's API
        # For now, just return a mock response
        phone_number = args.get('phone_number', '')
        appointment_id = args.get('appointment_id', '')
        
        # Log the appointment status request
        logger.info(f"Appointment status request: {phone_number}, {appointment_id}")
        
        return {
            "success": True,
            "status": "scheduled",
            "technician": "John Smith",
            "eta": "2025-04-24 between 9:00 AM and 11:00 AM",
            "message": "Your appointment is confirmed. Our technician John Smith will arrive on April 24th between 9:00 AM and 11:00 AM."
        }
    except Exception as e:
        logger.error(f"Error checking appointment status: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
