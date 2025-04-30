import requests
import time
from requests.auth import HTTPBasicAuth
from ..config import config
from ..utils import get_logger
from ..services.cache_service import get_cached_response, set_cached_response, cache_response # Import cache_response

logger = get_logger(__name__)

# ServiceTitan API Configuration
BASE_URL = f"https://api.servicetitan.io"
TOKEN_URL = f"{BASE_URL}/connect/token"

# Cache key for the access token
TOKEN_CACHE_KEY = "servicetitan_access_token"

def get_access_token():
    """Retrieves a ServiceTitan access token, using cache if available."""
    # Check cache first
    cached_token_info = get_cached_response(TOKEN_CACHE_KEY)
    if cached_token_info and cached_token_info.get("expires_at", 0) > time.time():
        logger.info("Using cached ServiceTitan access token.")
        return cached_token_info["access_token"]

    logger.info("Requesting new ServiceTitan access token...")
    if not all([config.SERVICETITAN_CLIENT_ID, config.SERVICETITAN_CLIENT_SECRET]):
        logger.error("ServiceTitan Client ID or Client Secret not configured.")
        raise ValueError("Missing ServiceTitan credentials.")

    try:
        response = requests.post(
            TOKEN_URL,
            auth=HTTPBasicAuth(config.SERVICETITAN_CLIENT_ID, config.SERVICETITAN_CLIENT_SECRET),
            data={
                "grant_type": "client_credentials",
                # Add scope if required by ServiceTitan API endpoints
                # "scope": "api.servicetitan.com/read api.servicetitan.com/write"
            }
        )
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        token_data = response.json()
        
        access_token = token_data.get("access_token")
        expires_in = token_data.get("expires_in", 3600) # Default to 1 hour
        expires_at = time.time() + expires_in - 60 # Subtract 60s buffer

        if not access_token:
            logger.error("Failed to retrieve access token from ServiceTitan response.")
            raise ValueError("No access token in ServiceTitan response.")

        # Cache the new token
        set_cached_response(TOKEN_CACHE_KEY, {"access_token": access_token, "expires_at": expires_at})
        logger.info("Successfully obtained and cached new ServiceTitan access token.")
        return access_token

    except requests.exceptions.RequestException as e:
        logger.error(f"Error requesting ServiceTitan access token: {e}", exc_info=True)
        raise ConnectionError(f"Failed to connect to ServiceTitan for authentication: {e}")
    except Exception as e:
        logger.error(f"Error processing ServiceTitan token response: {e}", exc_info=True)
        raise

def make_servicetitan_request(method, endpoint, params=None, json_data=None):
    """Makes an authenticated request to the ServiceTitan API."""
    access_token = get_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "ST-App-Key": config.SERVICETITAN_APP_KEY, # App Key might be required
        "Content-Type": "application/json"
    }
    url = f"{BASE_URL}{endpoint}"

    try:
        logger.info(f"Making ServiceTitan API request: {method} {url} Params: {params}")
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json=json_data
        )
        response.raise_for_status()
        logger.info(f"ServiceTitan API request successful ({response.status_code}).")
        # Handle potential empty responses for certain methods (e.g., 204 No Content)
        if response.status_code == 204:
            return None 
        return response.json()
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error during ServiceTitan API request to {url}: {e.response.status_code} - {e.response.text}", exc_info=True)
        # Re-raise or handle specific errors (e.g., 401 Unauthorized might mean token expired)
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error during ServiceTitan API request to {url}: {e}", exc_info=True)
        raise ConnectionError(f"Failed to connect to ServiceTitan API: {e}")
    except Exception as e:
        logger.error(f"Error during ServiceTitan API request processing: {e}", exc_info=True)
        raise

# --- Placeholder Functions for Agent Tools --- 
# These need to be implemented based on specific ServiceTitan API endpoints and requirements

@cache_response(ttl=900) # Cache availability for 15 minutes
def check_availability(start_date: str, end_date: str, service_type: str = None, zip_code: str = None) -> str:
    """Checks appointment availability in ServiceTitan within a given date range.
    
    Args:
        start_date (str): Start date for availability check (e.g., "YYYY-MM-DD").
        end_date (str): End date for availability check (e.g., "YYYY-MM-DD").
        service_type (str, optional): Type of service requested.
        zip_code (str, optional): Customer's zip code.

    Returns:
        str: A summary of available slots or a message indicating unavailability.
    """
    logger.info(f"Checking ServiceTitan availability: {start_date} to {end_date}, Type: {service_type}, Zip: {zip_code}")
    # TODO: Implement actual API call to ServiceTitan booking/availability endpoint
    # Example endpoint (hypothetical): /jpm/v1/tenants/{tenantId}/operations/scheduling/availability
    # params = {"startDate": start_date, "endDate": end_date, ...}
    # response = make_servicetitan_request("GET", f"/jpm/v1/tenants/{config.SERVICETITAN_TENANT_ID}/operations/scheduling/availability", params=params)
    # Process response and return formatted string
    return "Availability check function is not yet fully implemented. Please ask the user to call Kooler directly for scheduling."

def book_appointment(customer_id: str, job_type: str, preferred_date: str, preferred_time: str = None, notes: str = None) -> str:
    """Books an appointment in ServiceTitan for a given customer.

    Args:
        customer_id (str): The ServiceTitan ID of the customer.
        job_type (str): The type of job/service to book.
        preferred_date (str): The customer's preferred date (e.g., "YYYY-MM-DD").
        preferred_time (str, optional): The customer's preferred time (e.g., "Morning", "Afternoon").
        notes (str, optional): Any notes for the appointment.

    Returns:
        str: Confirmation message with booking details or an error message.
    """
    logger.info(f"Booking ServiceTitan appointment for customer {customer_id}, Job: {job_type}, Date: {preferred_date}")
    # TODO: Implement actual API call to ServiceTitan booking endpoint
    # Example endpoint (hypothetical): /jpm/v1/tenants/{tenantId}/jobs
    # data = {"customerId": customer_id, "jobType": job_type, ...}
    # response = make_servicetitan_request("POST", f"/jpm/v1/tenants/{config.SERVICETITAN_TENANT_ID}/jobs", json_data=data)
    # Process response and return formatted string
    return "Booking function is not yet fully implemented. Please ask the user to call Kooler directly to book an appointment."

@cache_response(ttl=1800) # Cache customer lookups for 30 minutes
def lookup_customer(phone_number: str = None, email: str = None, name: str = None) -> str:
    """Looks up customer information in ServiceTitan.

    Args:
        phone_number (str, optional): Customer's phone number.
        email (str, optional): Customer's email address.
        name (str, optional): Customer's name.

    Returns:
        str: Summary of customer information found or a message indicating customer not found.
    """
    logger.info(f"Looking up ServiceTitan customer: Phone={phone_number}, Email={email}, Name={name}")
    # TODO: Implement actual API call to ServiceTitan customer lookup endpoint
    # Example endpoint (hypothetical): /crm/v1/tenants/{tenantId}/customers
    # params = {"phone": phone_number, "email": email, "name": name, ...}
    # response = make_servicetitan_request("GET", f"/crm/v1/tenants/{config.SERVICETITAN_TENANT_ID}/customers", params=params)
    # Process response and return formatted string
    return "Customer lookup function is not yet fully implemented."

# Example usage (for testing authentication)
if __name__ == '__main__':
    try:
        print("Attempting to get ServiceTitan access token...")
        token = get_access_token()
        print(f"Successfully obtained token (first few chars): {token[:10]}...")
        # Optional: Make a simple test request if a known safe GET endpoint exists
        # print("\nAttempting a test API call...")
        # test_endpoint = f"/crm/v1/tenants/{config.SERVICETITAN_TENANT_ID}/settings/company" # Example endpoint
        # company_info = make_servicetitan_request("GET", test_endpoint)
        # print("Test API call successful:", company_info)
    except Exception as e:
        print(f"An error occurred during ServiceTitan testing: {e}")

