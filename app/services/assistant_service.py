import os
import time
import json
from openai import OpenAI
from openai.lib.streaming import AssistantEventHandler # Import EventHandler
# from typing import override # Removed, not available in Python 3.10
from ..config import config
from ..utils import get_logger
from ..tools.knowledge_tool import query_knowledge_base
from ..tools.servicetitan_tool import check_availability, book_appointment, lookup_customer
from .cache_service import cache_response # Import the cache decorator

logger = get_logger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=config.OPENAI_API_KEY)

# --- Streaming Event Handler ---
class WeggyEventHandler(AssistantEventHandler):
    """Handles streaming events from the Assistant API."""
    def __init__(self):
        super().__init__()
        self.current_response = ""
        self.run_id = None
        self.thread_id = None

    def on_text_created(self, text) -> None:
        # logger.debug(f"\nassistant > ")
        self.current_response = "" # Reset response when new text block starts
        pass

    def on_text_delta(self, delta, snapshot):
        # logger.debug(delta.value, end="", flush=True)
        self.current_response += delta.value
        pass

    def on_tool_call_created(self, tool_call):
        # logger.debug(f"\nassistant > {tool_call.type}\n")
        pass

    def on_tool_call_delta(self, delta, snapshot):
        if delta.type == 'function':
            # logger.debug(f"assistant > {delta.function.name}")
            # logger.debug(delta.function.arguments, end="", flush=True)
            pass
        elif delta.type == 'code_interpreter':
            # logger.debug(f"assistant > {delta.type}")
            # logger.debug(delta.code_interpreter.input)
            # logger.debug(f"\nOutput:\n{delta.code_interpreter.outputs}")
            pass
            
    def on_run_step_created(self, run_step):
        self.run_id = run_step.run_id
        self.thread_id = run_step.thread_id
        # logger.debug(f"Run step created: {run_step.id} for Run ID: {self.run_id}")
        pass
        
    # Add other event handlers if needed (on_message_done, on_end, etc.)
    # For now, we mainly care about text deltas and final run status

# --- Assistant Functions --- 

ASSISTANT_NAME = "Weggy (Kooler Agent)"

ASSISTANT_NAME = "Weggy (Kooler Agent)"
ASSISTANT_INSTRUCTIONS = """
You are Weggy, AI assistant for Kooler Garage Doors, helping customers and technicians.

**Persona:**
- **Identify User:** If role (customer/technician) is unclear, ask politely.
- **Customers:** Use simple language, avoid jargon. Focus on solutions, scheduling, product info.
- **Technicians:** Use technical terms. Provide specific procedures, diagnostics, part numbers from KB.
- **Tone:** Friendly, helpful, professional, adapted to user.

**Core Tasks:**
- Answer questions on products, troubleshooting, scheduling (customers).
- Provide technical info, procedures, diagnostics from KB (technicians).
- Use tools: `query_knowledge_base` for info, ServiceTitan tools (`check_availability`, `lookup_customer`, `book_appointment`) for actions.
- State clearly if info is not found in KB.
- If ServiceTitan tools can't fulfill a request, guide user to contact Kooler directly.
- Be concise and clear in voice/text.
"""

# Define the tool schemas for the Assistant
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "query_knowledge_base",
            "description": "Queries the Kooler Garage Doors knowledge base to find relevant information based on a user query. Use this for questions about products, troubleshooting, technical procedures, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The user's question or query to search for in the knowledge base."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": "Checks appointment availability in ServiceTitan within a given date range. Use this when a user asks about scheduling an appointment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date for availability check (YYYY-MM-DD)."
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date for availability check (YYYY-MM-DD)."
                    },
                    "service_type": {
                        "type": "string",
                        "description": "(Optional) Type of service requested (e.g., 'Repair', 'Installation')."
                    },
                    "zip_code": {
                        "type": "string",
                        "description": "(Optional) Customer's zip code."
                    }
                },
                "required": ["start_date", "end_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": "Books an appointment in ServiceTitan for a given customer. Requires customer_id. If customer_id is unknown, use lookup_customer first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "The ServiceTitan ID of the customer."
                    },
                    "job_type": {
                        "type": "string",
                        "description": "The type of job/service to book (e.g., 'Garage Door Repair', 'New Opener Installation')."
                    },
                    "preferred_date": {
                        "type": "string",
                        "description": "The customer's preferred date (YYYY-MM-DD)."
                    },
                    "preferred_time": {
                        "type": "string",
                        "description": "(Optional) The customer's preferred time (e.g., 'Morning', 'Afternoon', 'Any')."
                    },
                    "notes": {
                        "type": "string",
                        "description": "(Optional) Any notes for the appointment (e.g., 'Gate code is 1234', 'Customer requests specific technician')."
                    }
                },
                "required": ["customer_id", "job_type", "preferred_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_customer",
            "description": "Looks up customer information in ServiceTitan using phone number, email, or name. Needed to get customer_id before booking.",
            "parameters": {
                "type": "object",
                "properties": {
                    "phone_number": {
                        "type": "string",
                        "description": "(Optional) Customer's phone number."
                    },
                    "email": {
                        "type": "string",
                        "description": "(Optional) Customer's email address."
                    },
                    "name": {
                        "type": "string",
                        "description": "(Optional) Customer's name."
                    }
                },
                "required": [] # At least one parameter should ideally be provided by the user context
            }
        }
    }
]

AVAILABLE_TOOLS = {
    "query_knowledge_base": query_knowledge_base,
    "check_availability": check_availability,
    "book_appointment": book_appointment,
    "lookup_customer": lookup_customer
}

@cache_response(ttl=86400) # Cache assistant object for 24 hours
def get_or_create_assistant(assistant_id_env_var="OPENAI_ASSISTANT_ID"):
    """Retrieves the assistant ID from env vars or creates a new assistant."""
    assistant_id = config.OPENAI_ASSISTANT_ID

    if assistant_id:
        try:
            assistant = client.beta.assistants.retrieve(assistant_id)
            logger.info(f"Retrieved existing assistant with ID: {assistant.id}")
            # Optionally update the assistant if needed (e.g., instructions, tools)
            # assistant = client.beta.assistants.update(
            #     assistant_id=assistant.id,
            #     name=ASSISTANT_NAME,
            #     instructions=ASSISTANT_INSTRUCTIONS,
            #     tools=TOOLS_SCHEMA,
            #     model="gpt-4o" # Or desired model
            # )
            # logger.info(f"Updated assistant {assistant.id}")
            return assistant
        except Exception as e:
            logger.warning(f"Failed to retrieve assistant {assistant_id}: {e}. Creating a new one.")
            # Fall through to create a new one if retrieval fails

    logger.info("Creating a new OpenAI Assistant...")
    try:
        assistant = client.beta.assistants.create(
            name=ASSISTANT_NAME,
            instructions=ASSISTANT_INSTRUCTIONS,
            tools=TOOLS_SCHEMA,
            model="gpt-4o" # Use a powerful model like gpt-4o
        )
        logger.info(f"Created new assistant with ID: {assistant.id}")
        # IMPORTANT: Update the .env file or inform the user to update it
        logger.warning(f"Please update your .env file with: OPENAI_ASSISTANT_ID={assistant.id}")
        # Update the config object in memory for the current session
        config.OPENAI_ASSISTANT_ID = assistant.id 
        return assistant
    except Exception as e:
        logger.error(f"Failed to create assistant: {e}", exc_info=True)
        raise

def create_thread():
    """Creates a new conversation thread."""
    try:
        thread = client.beta.threads.create()
        logger.info(f"Created new thread with ID: {thread.id}")
        return thread
    except Exception as e:
        logger.error(f"Failed to create thread: {e}", exc_info=True)
        raise

def add_message_to_thread(thread_id, content, role="user"):
    """Adds a message to a specific thread."""
    try:
        message = client.beta.threads.messages.create(
            thread_id=thread_id,
            role=role,
            content=content
        )
        logger.info(f"Added message to thread {thread_id}: 	{content[:50]}...	")
        return message
    except Exception as e:
        logger.error(f"Failed to add message to thread {thread_id}: {e}", exc_info=True)
        raise

def run_assistant_stream(thread_id, assistant_id):
    """Runs the assistant on the specified thread using streaming and handles events."""
    try:
        logger.info(f"Running assistant {assistant_id} on thread {thread_id} with streaming...")
        event_handler = WeggyEventHandler()
        
        with client.beta.threads.runs.stream(
            thread_id=thread_id,
            assistant_id=assistant_id,
            # instructions="Override assistant instructions here if needed",
            event_handler=event_handler,
        ) as stream:
            # stream.until_done() # Process events as they come in via the handler
            # Instead of blocking with until_done(), we let the handler accumulate the response.
            # We need to handle the final state and potential tool calls after the stream context.
            for event in stream:
                # The handler updates its state, we might log specific events here if needed
                # logger.debug(f"Stream event: {event.event}")
                # Handle requires_action specifically after the stream context
                pass 

        # After the stream context, check for required actions
        run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=event_handler.run_id)
        logger.debug(f"Stream finished. Final Run status: {run.status}")

        if run.status == "requires_action":
            tool_outputs = []
            for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                tool_call_id = tool_call.id
                
                logger.info(f"Assistant requested tool call: {function_name}({arguments}) [{tool_call_id}] ")
                
                if function_name in AVAILABLE_TOOLS:
                    function_to_call = AVAILABLE_TOOLS[function_name]
                    try:
                        # Note: Tool execution itself is blocking and not streamed
                        output = function_to_call(**arguments)
                        tool_outputs.append({"tool_call_id": tool_call_id, "output": str(output)})
                    except Exception as e:
                        logger.error(f"Error executing tool {function_name}: {e}", exc_info=True)
                        tool_outputs.append({"tool_call_id": tool_call_id, "output": f"Error: {e}"})
                else:
                    logger.warning(f"Unknown tool requested: {function_name}")
                    tool_outputs.append({"tool_call_id": tool_call_id, "output": f"Error: Unknown tool 	{function_name}	"})
            
            # Submit tool outputs back to the run and stream the subsequent response
            if tool_outputs:
                logger.info("Submitting tool outputs and continuing stream...")
                with client.beta.threads.runs.submit_tool_outputs_stream(
                    thread_id=thread_id,
                    run_id=run.id,
                    tool_outputs=tool_outputs,
                    event_handler=event_handler, # Reuse the handler
                ) as stream:
                    # stream.until_done()
                    for event in stream:
                        # logger.debug(f"Tool output stream event: {event.event}")
                        pass
                    
                # Retrieve the final run status after submitting tool outputs
                run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=event_handler.run_id)
                logger.debug(f"Stream after tool submission finished. Final Run status: {run.status}")

        # Check final run status after potential tool calls
        if run.status == "completed":
            logger.info(f"Run {run.id} completed successfully.")
            # The response is accumulated in event_handler.current_response
            return event_handler.current_response, run.status
        else:
            logger.error(f"Run {run.id} did not complete successfully. Status: {run.status}. Last error: {run.last_error}")
            return f"Error: Assistant run failed with status {run.status}", run.status

    except Exception as e:
        logger.error(f"An error occurred while running assistant stream: {e}", exc_info=True)
        return f"Error: An unexpected error occurred during assistant processing.", "failed"


# Keep the old non-streaming function for potential fallback or testing
def run_assistant(thread_id, assistant_id):
    """Runs the assistant on the specified thread and handles tool calls (Non-streaming)."""
    try:
        logger.info(f"Running assistant {assistant_id} on thread {thread_id}...")
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id,
            # instructions="Override assistant instructions here if needed"
        )

        # Poll for completion or required actions
        while run.status in ["queued", "in_progress", "requires_action"]:
            time.sleep(1) # Wait before checking status again
            run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
            logger.debug(f"Run status: {run.status}")

            if run.status == "requires_action":
                tool_outputs = []
                for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                    function_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)
                    tool_call_id = tool_call.id
                    
                    logger.info(f"Assistant requested tool call: {function_name}({arguments}) [{tool_call_id}] ")
                    
                    if function_name in AVAILABLE_TOOLS:
                        function_to_call = AVAILABLE_TOOLS[function_name]
                        try:
                            output = function_to_call(**arguments)
                            tool_outputs.append({"tool_call_id": tool_call_id, "output": str(output)})
                        except Exception as e:
                            logger.error(f"Error executing tool {function_name}: {e}", exc_info=True)
                            tool_outputs.append({"tool_call_id": tool_call_id, "output": f"Error: {e}"})
                    else:
                        logger.warning(f"Unknown tool requested: {function_name}")
                        tool_outputs.append({"tool_call_id": tool_call_id, "output": f"Error: Unknown tool 	{function_name}	"})
                
                # Submit tool outputs back to the run
                if tool_outputs:
                    try:
                        run = client.beta.threads.runs.submit_tool_outputs(
                            thread_id=thread_id,
                            run_id=run.id,
                            tool_outputs=tool_outputs
                        )
                        logger.info("Submitted tool outputs.")
                    except Exception as e:
                        logger.error(f"Failed to submit tool outputs: {e}", exc_info=True)
                        # Handle failure - maybe cancel the run?
                        run = client.beta.threads.runs.cancel(thread_id=thread_id, run_id=run.id)
                        return run # Return the cancelled run

        # Check final run status
        if run.status == "completed":
            logger.info(f"Run {run.id} completed successfully.")
        elif run.status == "failed":
            logger.error(f"Run {run.id} failed. Reason: {run.last_error}")
        elif run.status == "cancelled":
            logger.warning(f"Run {run.id} was cancelled.")
        elif run.status == "expired":
            logger.error(f"Run {run.id} expired.")
            
        return run

    except Exception as e:
        logger.error(f"An error occurred while running assistant: {e}", exc_info=True)
        raise

def get_latest_response(thread_id):
    """Retrieves the latest message added by the assistant from the thread."""
    try:
        messages = client.beta.threads.messages.list(thread_id=thread_id, order="desc", limit=1)
        # The latest message should be from the assistant
        if messages.data and messages.data[0].role == "assistant":
            response_content = messages.data[0].content[0].text.value
            logger.info(f"Retrieved latest assistant response from thread {thread_id}: 	{response_content[:50]}...	")
            return response_content
        else:
            logger.warning(f"No assistant response found as the latest message in thread {thread_id}.")
            return None
    except Exception as e:
        logger.error(f"Failed to retrieve messages from thread {thread_id}: {e}", exc_info=True)
        raise

# Example usage (for testing)
if __name__ == '__main__':
    try:
        print("Getting or creating assistant...")
        assistant = get_or_create_assistant()
        print(f"Using Assistant ID: {assistant.id}")

        print("\nCreating new thread...")
        thread = create_thread()
        print(f"Thread ID: {thread.id}")

        user_query = "How do I pair a new remote to my Kooler 5000 opener?"
        print(f"\nAdding message: 	{user_query}	")
        add_message_to_thread(thread.id, user_query)

        print("\nRunning assistant...")
        run = run_assistant(thread.id, assistant.id)

        if run.status == 'completed':
            print("\nAssistant run completed. Getting response...")
            response = get_latest_response(thread.id)
            print(f"\nAssistant Response:\n{response}")
        else:
            print(f"\nAssistant run did not complete successfully. Status: {run.status}")
            if run.last_error:
                print(f"Error: {run.last_error.message}")

    except Exception as e:
        print(f"An error occurred during testing: {e}")

