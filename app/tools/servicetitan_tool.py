# This module acts as a wrapper around the ServiceTitan service functions,
# making them suitable for use as tools by the OpenAI Assistant.

from ..services import servicetitan_service
from ..utils import get_logger

logger = get_logger(__name__)

# Note: The functions here directly call the placeholder functions in servicetitan_service.py.
# When the actual ServiceTitan API calls are implemented in servicetitan_service.py,
# these tool functions will automatically use the real implementation.

def check_availability(start_date: str, end_date: str, service_type: str = None, zip_code: str = None) -> str:
    """Tool function to check appointment availability in ServiceTitan.
    Calls the underlying service function.
    Args:
        start_date (str): Start date (YYYY-MM-DD).
        end_date (str): End date (YYYY-MM-DD).
        service_type (str, optional): Type of service.
        zip_code (str, optional): Customer zip code.
    Returns:
        str: Summary of availability or status message.
    """
    logger.info(f"Tool: check_availability called with args: {locals()}")
    try:
        return servicetitan_service.check_availability(start_date, end_date, service_type, zip_code)
    except Exception as e:
        logger.error(f"Error in check_availability tool: {e}", exc_info=True)
        return f"An error occurred while checking availability: {e}"

def book_appointment(customer_id: str, job_type: str, preferred_date: str, preferred_time: str = None, notes: str = None) -> str:
    """Tool function to book an appointment in ServiceTitan.
    Calls the underlying service function.
    Args:
        customer_id (str): ServiceTitan customer ID.
        job_type (str): Type of job/service.
        preferred_date (str): Preferred date (YYYY-MM-DD).
        preferred_time (str, optional): Preferred time.
        notes (str, optional): Appointment notes.
    Returns:
        str: Confirmation or error message.
    """
    logger.info(f"Tool: book_appointment called with args: {locals()}")
    try:
        return servicetitan_service.book_appointment(customer_id, job_type, preferred_date, preferred_time, notes)
    except Exception as e:
        logger.error(f"Error in book_appointment tool: {e}", exc_info=True)
        return f"An error occurred while booking the appointment: {e}"

def lookup_customer(phone_number: str = None, email: str = None, name: str = None) -> str:
    """Tool function to look up customer information in ServiceTitan.
    Calls the underlying service function.
    Args:
        phone_number (str, optional): Customer phone number.
        email (str, optional): Customer email.
        name (str, optional): Customer name.
    Returns:
        str: Customer information summary or status message.
    """
    logger.info(f"Tool: lookup_customer called with args: {locals()}")
    try:
        return servicetitan_service.lookup_customer(phone_number, email, name)
    except Exception as e:
        logger.error(f"Error in lookup_customer tool: {e}", exc_info=True)
        return f"An error occurred while looking up the customer: {e}"

