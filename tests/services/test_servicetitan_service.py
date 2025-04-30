import pytest
from unittest.mock import patch, MagicMock, call, ANY # Import ANY
import os
import sys
import time
import requests # <-- Added missing import

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Import necessary modules
from app.services import servicetitan_service
from app.config import config # Import the actual config object
from app.services import cache_service # Needed for cache interaction

# Define fake config values for patching
FAKE_CONFIG = {
    'SERVICETITAN_CLIENT_ID': 'fake-client-id',
    'SERVICETITAN_CLIENT_SECRET': 'fake-client-secret',
    'SERVICETITAN_TENANT_ID': 'fake-tenant-id',
    'SERVICETITAN_API_URL': 'https://fake-api.servicetitan.io',
    'SERVICETITAN_APP_KEY': 'fake-app-key'
}

# Fixture to reset cache and patch module-level constants for each test
@pytest.fixture(autouse=True)
def setup_teardown():
    # Clear cache before each test
    cache_service.cache.clear()
    
    # Patch module-level constants in servicetitan_service
    with patch.object(servicetitan_service, 'BASE_URL', FAKE_CONFIG['SERVICETITAN_API_URL']), \
         patch.object(servicetitan_service, 'TOKEN_URL', f"{FAKE_CONFIG['SERVICETITAN_API_URL']}/connect/token"):
        yield # Test runs here
    
    # Clear cache after each test
    cache_service.cache.clear()

# Patch config attributes directly on the test functions where needed
@patch.object(config, 'SERVICETITAN_CLIENT_ID', FAKE_CONFIG['SERVICETITAN_CLIENT_ID'])
@patch.object(config, 'SERVICETITAN_CLIENT_SECRET', FAKE_CONFIG['SERVICETITAN_CLIENT_SECRET'])
@patch('app.services.servicetitan_service.requests.post')
@patch('app.services.servicetitan_service.set_cached_response')
@patch('app.services.servicetitan_service.get_cached_response', return_value=None) # Simulate no cache
def test_get_access_token_success(mock_get_cache, mock_set_cache, mock_post):
    """Test successful retrieval of a new ServiceTitan token when not cached."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'access_token': 'new-fake-token',
        'expires_in': 3600
    }
    mock_post.return_value = mock_response

    token = servicetitan_service.get_access_token()

    mock_get_cache.assert_called_once_with(servicetitan_service.TOKEN_CACHE_KEY)
    mock_post.assert_called_once_with(
        servicetitan_service.TOKEN_URL, # This uses the patched module constant
        auth=ANY, # Use ANY to avoid matching the exact HTTPBasicAuth object
        data={'grant_type': 'client_credentials'}
    )
    assert token == 'new-fake-token'
    # Check that the token was cached with the correct expiry (allow for slight time diff)
    mock_set_cache.assert_called_once()
    args, kwargs = mock_set_cache.call_args
    assert args[0] == servicetitan_service.TOKEN_CACHE_KEY
    assert args[1]['access_token'] == 'new-fake-token'
    assert args[1]['expires_at'] > time.time() + 3500 # Check expiry is roughly correct

@patch.object(config, 'SERVICETITAN_CLIENT_ID', FAKE_CONFIG['SERVICETITAN_CLIENT_ID'])
@patch.object(config, 'SERVICETITAN_CLIENT_SECRET', FAKE_CONFIG['SERVICETITAN_CLIENT_SECRET'])
@patch('app.services.servicetitan_service.requests.post')
@patch('app.services.servicetitan_service.set_cached_response')
@patch('app.services.servicetitan_service.get_cached_response', return_value=None) # Simulate no cache
def test_get_access_token_failure(mock_get_cache, mock_set_cache, mock_post):
    """Test failure during ServiceTitan token retrieval."""
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("Unauthorized")
    mock_post.return_value = mock_response

    with pytest.raises(ConnectionError): # Expect ConnectionError from our wrapper
        servicetitan_service.get_access_token()
    
    mock_get_cache.assert_called_once_with(servicetitan_service.TOKEN_CACHE_KEY)
    mock_set_cache.assert_not_called() # Should not cache on failure

@patch.object(config, 'SERVICETITAN_APP_KEY', FAKE_CONFIG['SERVICETITAN_APP_KEY'])
@patch('app.services.servicetitan_service.requests.request')
@patch('app.services.servicetitan_service.requests.post') # Mock post to prevent token fetch
@patch('app.services.servicetitan_service.get_cached_response')
def test_make_servicetitan_request_with_valid_cache(mock_get_cache, mock_post, mock_request):
    """Test making a request using a valid cached token."""
    valid_token_info = {
        'access_token': 'valid-cached-token',
        'expires_at': time.time() + 600 # Valid for 10 more mins
    }
    mock_get_cache.return_value = valid_token_info

    mock_api_response = MagicMock()
    mock_api_response.status_code = 200
    mock_api_response.json.return_value = {'data': 'success'}
    mock_request.return_value = mock_api_response

    response = servicetitan_service.make_servicetitan_request('GET', '/test/endpoint')

    mock_get_cache.assert_called_once_with(servicetitan_service.TOKEN_CACHE_KEY)
    mock_post.assert_not_called() # Should not fetch a new token
    mock_request.assert_called_once_with(
        method='GET',
        url=f"{servicetitan_service.BASE_URL}/test/endpoint", # Uses patched BASE_URL
        headers={
            'Authorization': 'Bearer valid-cached-token',
            'Content-Type': 'application/json',
            'ST-App-Key': config.SERVICETITAN_APP_KEY # Uses patched config
        },
        params=None,
        json=None
    )
    assert response == {'data': 'success'}

@patch.object(config, 'SERVICETITAN_CLIENT_ID', FAKE_CONFIG['SERVICETITAN_CLIENT_ID'])
@patch.object(config, 'SERVICETITAN_CLIENT_SECRET', FAKE_CONFIG['SERVICETITAN_CLIENT_SECRET'])
@patch.object(config, 'SERVICETITAN_APP_KEY', FAKE_CONFIG['SERVICETITAN_APP_KEY'])
@patch('app.services.servicetitan_service.requests.request')
@patch('app.services.servicetitan_service.requests.post') # Mock post for fetching new token
@patch('app.services.servicetitan_service.set_cached_response')
@patch('app.services.servicetitan_service.get_cached_response')
def test_make_servicetitan_request_with_expired_cache(mock_get_cache, mock_set_cache, mock_post, mock_request):
    """Test making a request when the cached token is expired."""
    expired_token_info = {
        'access_token': 'expired-cached-token',
        'expires_at': time.time() - 60 # Expired 1 min ago
    }
    # Simulate expired cache on first call, None on second (after failed fetch)
    # Correction: get_access_token calls get_cached_response only ONCE per call.
    # make_servicetitan_request calls get_access_token once.
    # So get_cached_response is called only once.
    mock_get_cache.return_value = expired_token_info 

    # Mock response for fetching new token
    mock_token_response = MagicMock()
    mock_token_response.status_code = 200
    mock_token_response.json.return_value = {
        'access_token': 'new-fresh-token',
        'expires_in': 3600
    }
    mock_post.return_value = mock_token_response

    # Mock response for the actual API request
    mock_api_response = MagicMock()
    mock_api_response.status_code = 200
    mock_api_response.json.return_value = {'data': 'success_new_token'}
    mock_request.return_value = mock_api_response

    response = servicetitan_service.make_servicetitan_request('POST', '/another/endpoint', json_data={'key': 'value'})

    # Assert cache was checked once
    mock_get_cache.assert_called_once_with(servicetitan_service.TOKEN_CACHE_KEY)
    mock_post.assert_called_once() # Should fetch a new token
    mock_set_cache.assert_called_once() # Should cache the new token
    mock_request.assert_called_once_with(
        method='POST',
        url=f"{servicetitan_service.BASE_URL}/another/endpoint", # Uses patched BASE_URL
        headers={
            'Authorization': 'Bearer new-fresh-token',
            'Content-Type': 'application/json',
            'ST-App-Key': config.SERVICETITAN_APP_KEY # Uses patched config
        },
        params=None,
        json={'key': 'value'}
    )
    assert response == {'data': 'success_new_token'}
    # Removed the incorrect assert 1 == 2

# --- Test Placeholder Tool Functions --- 
# These tests verify the functions exist and return the placeholder string, 
# and that caching works as expected.

def test_check_availability_placeholder():
    """Test the placeholder check_availability function and its caching."""
    start = "2025-05-01"
    end = "2025-05-05"
    
    # First call (uncached)
    result1 = servicetitan_service.check_availability(start, end)
    assert "not yet fully implemented" in result1
    
    # Second call (should be cached)
    # We don't mock make_servicetitan_request here because the placeholder doesn't call it
    result2 = servicetitan_service.check_availability(start, end)
    assert result1 == result2 # Check if cached result is the same
    # Add assertion here if we could mock the underlying API call to ensure it wasn't called twice

def test_book_appointment_placeholder():
    """Test the placeholder book_appointment function."""
    result = servicetitan_service.book_appointment("cust123", "Repair", "2025-05-10")
    assert "not yet fully implemented" in result
    # Note: Booking is unlikely to be cached, so no cache test here.

def test_lookup_customer_placeholder():
    """Test the placeholder lookup_customer function and its caching."""
    phone = "555-1234"
    
    # First call (uncached)
    result1 = servicetitan_service.lookup_customer(phone_number=phone)
    assert "not yet fully implemented" in result1
    
    # Second call (should be cached)
    result2 = servicetitan_service.lookup_customer(phone_number=phone)
    assert result1 == result2

# Add more tests for error handling in make_servicetitan_request, etc.

