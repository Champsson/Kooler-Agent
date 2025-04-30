import pytest
from unittest.mock import patch, MagicMock
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock config before importing app components
# Ensure all necessary keys are mocked
with patch.dict(os.environ, {
    'OPENAI_API_KEY': 'fake-openai-key',
    'OPENAI_ASSISTANT_ID': 'fake-assistant-id',
    'PINECONE_API_KEY': 'fake-pinecone-key',
    'PINECONE_ENVIRONMENT': 'fake-pinecone-env',
    'PINECONE_INDEX_NAME': 'fake-index',
    'TWILIO_ACCOUNT_SID': 'fake-twilio-sid',
    'TWILIO_AUTH_TOKEN': 'fake-twilio-token',
    'TWILIO_PHONE_NUMBER': '+15550001111',
    'SERVICETITAN_CLIENT_ID': 'fake-st-client-id',
    'SERVICETITAN_CLIENT_SECRET': 'fake-st-client-secret',
    'SERVICETITAN_TENANT_ID': 'fake-st-tenant-id',
    'SERVICETITAN_API_URL': 'https://fake-api.servicetitan.io',
    'SERVICETITAN_APP_KEY': 'fake-st-app-key',
    'FLASK_ENV': 'testing' # Important for Flask app context
}):
    from app import create_app
    from app.services import orchestration_service, cache_service, assistant_service

@pytest.fixture(scope='module')
def test_client():
    """Create a Flask test client fixture."""
    # Need to reload config within the patched environment for the app factory
    with patch.dict(os.environ, {
        'OPENAI_API_KEY': 'fake-openai-key',
        'OPENAI_ASSISTANT_ID': 'fake-assistant-id',
        'PINECONE_API_KEY': 'fake-pinecone-key',
        'PINECONE_ENVIRONMENT': 'fake-pinecone-env',
        'PINECONE_INDEX_NAME': 'fake-index',
        'TWILIO_ACCOUNT_SID': 'fake-twilio-sid',
        'TWILIO_AUTH_TOKEN': 'fake-twilio-token',
        'TWILIO_PHONE_NUMBER': '+15550001111',
        'SERVICETITAN_CLIENT_ID': 'fake-st-client-id',
        'SERVICETITAN_CLIENT_SECRET': 'fake-st-client-secret',
        'SERVICETITAN_TENANT_ID': 'fake-st-tenant-id',
        'SERVICETITAN_API_URL': 'https://fake-api.servicetitan.io',
        'SERVICETITAN_APP_KEY': 'fake-st-app-key',
        'FLASK_ENV': 'testing'
    }):
        flask_app = create_app()
        flask_app.config.update({
            "TESTING": True,
        })
        testing_client = flask_app.test_client()
        
        # Establish an application context
        ctx = flask_app.app_context()
        ctx.push()
        yield testing_client  # this is where the testing happens!
        ctx.pop()

@pytest.fixture(autouse=True)
def reset_state():
    """Reset cache and conversation threads before each test."""
    cache_service.cache.clear()
    orchestration_service.conversation_threads = {}
    # Reset mocks if they are module-level or persistent
    if hasattr(assistant_service, 'client'):
         assistant_service.client = MagicMock(spec=assistant_service.OpenAI)
    # Add resets for other services if needed
    yield
    cache_service.cache.clear()
    orchestration_service.conversation_threads = {}

# --- Integration Tests --- 

@patch('app.services.assistant_service.run_assistant_stream')
def test_integration_kb_query(mock_run_assistant_stream, test_client):
    """Test a workflow involving a knowledge base query."""
    session_key = "sms_user_kb"
    user_input = "How do I program my remote?"
    expected_kb_response = "To program your remote, follow these steps... (from KB)"
    
    # Mock the assistant stream to return a KB query result
    mock_run_assistant_stream.return_value = (expected_kb_response, "completed")
    
    # Simulate calling the orchestration service directly (simpler than mocking Flask routes)
    response = orchestration_service.handle_interaction(session_key, user_input)
    
    # Assertions
    mock_run_assistant_stream.assert_called_once() # Check if assistant was run
    # We could add more detailed checks here: 
    # - Check if add_message_to_thread was called with correct input
    # - If we mocked the tool call itself, check if query_knowledge_base was invoked by the assistant mock
    assert response == expected_kb_response
    assert session_key in orchestration_service.conversation_threads # Check thread creation

@patch('app.services.assistant_service.run_assistant_stream')
def test_integration_check_availability(mock_run_assistant_stream, test_client):
    """Test a workflow involving checking ServiceTitan availability."""
    session_key = "voice_user_avail"
    user_input = "Can I get an appointment tomorrow?"
    expected_avail_response = "Checking availability... Yes, we have openings tomorrow afternoon. (Simulated)"
    
    # Mock the assistant stream to return the availability info (simulating tool use)
    mock_run_assistant_stream.return_value = (expected_avail_response, "completed")
    
    response = orchestration_service.handle_interaction(session_key, user_input)
    
    # Assertions
    mock_run_assistant_stream.assert_called_once()
    # Ideally, mock the assistant run to simulate calling the 'check_availability' tool 
    # and verify the tool mock was called.
    assert response == expected_avail_response
    assert session_key in orchestration_service.conversation_threads

@patch('app.services.assistant_service.run_assistant_stream')
def test_integration_sms_webhook(mock_run_assistant_stream, test_client):
    """Test the /twilio/sms webhook endpoint."""
    assistant_response = "Hello from Weggy via SMS!"
    mock_run_assistant_stream.return_value = (assistant_response, "completed")

    # Simulate incoming Twilio SMS request
    response = test_client.post('/twilio/sms', data={
        'From': '+15551234567',
        'Body': 'Hi Weggy'
    })

    assert response.status_code == 200
    assert response.content_type == 'text/xml; charset=utf-8'
    # Check TwiML response
    assert '<Response>' in response.data.decode()
    assert f'<Message>{assistant_response}</Message>' in response.data.decode()
    # Check if orchestration was called (implicitly via thread creation)
    assert '+15551234567' in orchestration_service.conversation_threads
    mock_run_assistant_stream.assert_called_once()

# TODO: Add integration test for /twilio/voice and /twilio/voice/process
# This is more complex due to the multi-step nature and audio generation/serving.
# It might require mocking requests.post for Twilio callbacks, tts_service, etc.

# Add more integration tests for different scenarios (technician vs customer, errors, etc.)

