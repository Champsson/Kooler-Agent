import pytest
from unittest.mock import patch, MagicMock, call, ANY
import os
import sys
import json
import time

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Mock config before importing the service
with patch.dict(os.environ, {
    'OPENAI_API_KEY': 'fake-openai-key',
    'OPENAI_ASSISTANT_ID': 'fake-assistant-id' # Provide a fake ID for retrieval tests
}):
    from app.services import assistant_service
    from app.config import config
    from app.services import cache_service # Needed for cache interaction

# Fixture to reset mocks and cache for each test
@pytest.fixture(autouse=True)
def setup_teardown():
    # Clear cache before each test
    cache_service.cache.clear()
    # Reset OpenAI client mock, including nested attributes
    mock_client = MagicMock(spec=assistant_service.OpenAI)
    mock_beta = MagicMock()
    mock_client.beta = mock_beta
    mock_assistants = MagicMock()
    mock_threads = MagicMock()
    mock_messages = MagicMock()
    mock_runs = MagicMock()
    mock_beta.assistants = mock_assistants
    mock_beta.threads = mock_threads
    mock_beta.threads.messages = mock_messages # Nested under threads
    mock_beta.threads.runs = mock_runs # Nested under threads
    assistant_service.client = mock_client
    yield # Test runs here
    # Clear cache after each test
    cache_service.cache.clear()

# --- Test Assistant Creation/Retrieval --- 

def test_get_or_create_assistant_retrieve_success():
    """Test retrieving an existing assistant successfully."""
    mock_assistant = MagicMock()
    mock_assistant.id = config.OPENAI_ASSISTANT_ID
    assistant_service.client.beta.assistants.retrieve.return_value = mock_assistant

    assistant = assistant_service.get_or_create_assistant()

    assistant_service.client.beta.assistants.retrieve.assert_called_once_with(config.OPENAI_ASSISTANT_ID)
    assistant_service.client.beta.assistants.create.assert_not_called()
    assert assistant.id == config.OPENAI_ASSISTANT_ID

@patch.dict(os.environ, {"OPENAI_ASSISTANT_ID": ""}, clear=True) # Simulate no ID in env
@patch("app.services.assistant_service.config.OPENAI_ASSISTANT_ID", "") # Patch where it's used
def test_get_or_create_assistant_create_new():
    """Test creating a new assistant when no ID is provided."""
    # No reload needed, patching handles the state for this test
    # assistant_service.client = MagicMock(spec=assistant_service.OpenAI) # Fixture handles this
    
    mock_new_assistant = MagicMock()
    mock_new_assistant.id = "new-fake-id"
    assistant_service.client.beta.assistants.create.return_value = mock_new_assistant

    # Ensure the config object reflects the patched value *before* calling the function
    assert config.OPENAI_ASSISTANT_ID == ""

    assistant = assistant_service.get_or_create_assistant()

    assistant_service.client.beta.assistants.retrieve.assert_not_called()
    assistant_service.client.beta.assistants.create.assert_called_once_with(
        name=assistant_service.ASSISTANT_NAME,
        instructions=assistant_service.ASSISTANT_INSTRUCTIONS,
        tools=assistant_service.TOOLS_SCHEMA,
        model="gpt-4o"
    )
    assert assistant.id == "new-fake-id"
    # Check if the function updated the config object in memory as intended
    assert config.OPENAI_ASSISTANT_ID == "new-fake-id"

@patch.dict(os.environ, {"OPENAI_ASSISTANT_ID": "fake-assistant-id"}) # Ensure ID is set in env
@patch("app.services.assistant_service.config.OPENAI_ASSISTANT_ID", "fake-assistant-id") # Patch where it's used
def test_get_or_create_assistant_retrieve_fail_create_new():
    """Test creating a new assistant after failing to retrieve."""
    # No reload needed
    # assistant_service.client = MagicMock(spec=assistant_service.OpenAI) # Fixture handles this

    assistant_service.client.beta.assistants.retrieve.side_effect = Exception("Not Found")
    mock_new_assistant = MagicMock()
    mock_new_assistant.id = "new-fake-id-after-fail"
    assistant_service.client.beta.assistants.create.return_value = mock_new_assistant

    # Ensure config has the initial value before call
    assert config.OPENAI_ASSISTANT_ID == "fake-assistant-id"

    assistant = assistant_service.get_or_create_assistant()

    assistant_service.client.beta.assistants.retrieve.assert_called_once_with("fake-assistant-id")
    assistant_service.client.beta.assistants.create.assert_called_once()
    assert assistant.id == "new-fake-id-after-fail"
    # Check if the function updated the config object in memory as intended
    assert config.OPENAI_ASSISTANT_ID == "new-fake-id-after-fail"

# --- Test Thread and Message Management --- 

def test_create_thread():
    """Test creating a new thread."""
    mock_thread = MagicMock()
    mock_thread.id = "thread-123"
    assistant_service.client.beta.threads.create.return_value = mock_thread

    thread = assistant_service.create_thread()

    assistant_service.client.beta.threads.create.assert_called_once()
    assert thread.id == "thread-123"

def test_add_message_to_thread():
    """Test adding a message to a thread."""
    mock_message = MagicMock()
    assistant_service.client.beta.threads.messages.create.return_value = mock_message
    thread_id = "thread-123"
    content = "Hello Weggy!"

    message = assistant_service.add_message_to_thread(thread_id, content)

    assistant_service.client.beta.threads.messages.create.assert_called_once_with(
        thread_id=thread_id,
        role="user",
        content=content
    )
    assert message == mock_message

# --- Test Streaming Run --- 

# Mock stream context manager and events for streaming tests
class MockStreamingManager:
    def __init__(self, events):
        self.events = events
        self.handler = None

    def __enter__(self):
        return self.events # Return the iterable events

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def __iter__(self): # Make the manager itself iterable for the loop
        return iter(self.events)

@patch('app.services.assistant_service.WeggyEventHandler')
def test_run_assistant_stream_completed(MockEventHandler):
    """Test a successful streaming run without tool calls."""
    mock_handler_instance = MockEventHandler.return_value
    mock_handler_instance.current_response = "Final streamed response."
    mock_handler_instance.run_id = "run-comp-123"
    mock_handler_instance.thread_id = "thread-comp-123"

    # Mock the stream context manager
    mock_stream_events = [
        MagicMock(event='thread.run.created'),
        MagicMock(event='thread.message.delta', data=MagicMock(delta=MagicMock(value='Final '))) , # Simulate some events
        MagicMock(event='thread.message.delta', data=MagicMock(delta=MagicMock(value='streamed response.'))),
        MagicMock(event='thread.run.completed')
    ]
    mock_stream_manager = MockStreamingManager(mock_stream_events)
    assistant_service.client.beta.threads.runs.stream.return_value = mock_stream_manager

    # Mock the final run retrieval after stream
    mock_final_run = MagicMock(status='completed', id='run-comp-123')
    assistant_service.client.beta.threads.runs.retrieve.return_value = mock_final_run

    response, status = assistant_service.run_assistant_stream("thread-comp-123", "asst-abc")

    assistant_service.client.beta.threads.runs.stream.assert_called_once_with(
        thread_id="thread-comp-123",
        assistant_id="asst-abc",
        event_handler=mock_handler_instance
    )
    # Ensure retrieve is called after stream context
    assistant_service.client.beta.threads.runs.retrieve.assert_called_once_with(thread_id="thread-comp-123", run_id="run-comp-123")
    assert status == "completed"
    assert response == "Final streamed response."

@patch('app.services.assistant_service.WeggyEventHandler')
@patch('app.services.assistant_service.AVAILABLE_TOOLS', new_callable=dict) # Patch AVAILABLE_TOOLS as a dict
def test_run_assistant_stream_requires_action(MockAvailableTools, MockEventHandler):
    """Test a streaming run that requires a tool call."""
    mock_handler_instance = MockEventHandler.return_value
    mock_handler_instance.run_id = "run-tool-123"
    mock_handler_instance.thread_id = "thread-tool-123"
    
    # Mock the tool function itself and add it to the patched AVAILABLE_TOOLS
    mock_tool_function = MagicMock(return_value="Tool result data.")
    MockAvailableTools['query_knowledge_base'] = mock_tool_function

    # Simulate response accumulated after tool call (using a side effect on the handler)
    def update_response_after_tool(*args, **kwargs):
        # This simulates the handler accumulating text during the tool output stream
        mock_handler_instance.current_response = "Response after tool call."
        return mock_tool_stream_manager # Return the context manager itself

    # Mock the initial stream context manager (ends before requires_action)
    mock_initial_stream_events = [MagicMock(event='thread.run.created')]
    mock_initial_stream_manager = MockStreamingManager(mock_initial_stream_events)
    assistant_service.client.beta.threads.runs.stream.return_value = mock_initial_stream_manager

    # Mock the run retrieval showing requires_action
    # Explicitly create mock for function details
    mock_function_details = MagicMock()
    mock_function_details.name = 'query_knowledge_base' # Ensure name is a string
    mock_function_details.arguments = '{"query": "test query"}'
    mock_tool_call = MagicMock(id="call_abc", type='function', function=mock_function_details)
    
    mock_run_requires_action = MagicMock(
        status='requires_action', 
        id='run-tool-123', 
        required_action=MagicMock(submit_tool_outputs=MagicMock(tool_calls=[mock_tool_call]))
    )
    # First retrieve shows requires_action, second shows completed after tool submit
    mock_run_completed_after_tool = MagicMock(status='completed', id='run-tool-123')
    assistant_service.client.beta.threads.runs.retrieve.side_effect = [mock_run_requires_action, mock_run_completed_after_tool]

    # Mock the submit_tool_outputs_stream context manager
    mock_tool_stream_events = [
        MagicMock(event='thread.message.delta', data=MagicMock(delta=MagicMock(value='Response '))) , 
        MagicMock(event='thread.message.delta', data=MagicMock(delta=MagicMock(value='after tool call.'))),
        MagicMock(event='thread.run.completed')
    ]
    mock_tool_stream_manager = MockStreamingManager(mock_tool_stream_events)
    # Attach the side effect to the stream call itself
    assistant_service.client.beta.threads.runs.submit_tool_outputs_stream.side_effect = update_response_after_tool

    response, status = assistant_service.run_assistant_stream("thread-tool-123", "asst-xyz")

    # Check initial stream call
    assistant_service.client.beta.threads.runs.stream.assert_called_once_with(
        thread_id="thread-tool-123",
        assistant_id="asst-xyz",
        event_handler=mock_handler_instance
    )
    # Check retrieve calls (first for requires_action, second after tool submit)
    assert assistant_service.client.beta.threads.runs.retrieve.call_count == 2
    assistant_service.client.beta.threads.runs.retrieve.assert_has_calls([
        call(thread_id="thread-tool-123", run_id="run-tool-123"),
        call(thread_id="thread-tool-123", run_id="run-tool-123")
    ])
    
    # Check tool execution
    mock_tool_function.assert_called_once_with(query="test query")
    
    # Check tool output submission stream call
    assistant_service.client.beta.threads.runs.submit_tool_outputs_stream.assert_called_once_with(
        thread_id="thread-tool-123",
        run_id="run-tool-123",
        tool_outputs=[{"tool_call_id": "call_abc", "output": "Tool result data."}],
        event_handler=mock_handler_instance
    )
    
    assert status == "completed"
    # This assertion depends on the side effect updating the handler's response
    assert response == "Response after tool call."


# --- Test Non-Streaming Fallback (Optional but good practice) ---

@patch('app.services.assistant_service.AVAILABLE_TOOLS')
def test_run_assistant_non_streaming_completed(MockAvailableTools):
    """Test the non-streaming run_assistant function completion."""
    mock_run_created = MagicMock(status='in_progress', id='run-nonstream-1')
    mock_run_completed = MagicMock(status='completed', id='run-nonstream-1')
    assistant_service.client.beta.threads.runs.create.return_value = mock_run_created
    assistant_service.client.beta.threads.runs.retrieve.return_value = mock_run_completed

    run = assistant_service.run_assistant("thread-ns-1", "asst-ns-1")

    assistant_service.client.beta.threads.runs.create.assert_called_once()
    assistant_service.client.beta.threads.runs.retrieve.assert_called() # Called in the polling loop
    assert run.status == 'completed'

# Add tests for failure cases, unknown tools, etc.

# --- Test Get Latest Response --- 

def test_get_latest_response_success():
    """Test retrieving the latest assistant message."""
    mock_msg_content = MagicMock(text=MagicMock(value="Latest assistant reply."))
    mock_assistant_message = MagicMock(role='assistant', content=[mock_msg_content])
    mock_user_message = MagicMock(role='user') # Simulate user message before assistant
    assistant_service.client.beta.threads.messages.list.return_value = MagicMock(data=[mock_assistant_message, mock_user_message])

    response = assistant_service.get_latest_response("thread-resp-1")

    assistant_service.client.beta.threads.messages.list.assert_called_once_with(thread_id="thread-resp-1", order="desc", limit=1)
    assert response == "Latest assistant reply."

def test_get_latest_response_no_assistant_message():
    """Test case where the latest message is not from the assistant."""
    mock_user_message = MagicMock(role='user')
    assistant_service.client.beta.threads.messages.list.return_value = MagicMock(data=[mock_user_message])

    response = assistant_service.get_latest_response("thread-resp-2")

    assistant_service.client.beta.threads.messages.list.assert_called_once_with(thread_id="thread-resp-2", order="desc", limit=1)
    assert response is None

