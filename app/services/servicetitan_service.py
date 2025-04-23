import requests
import json
import time
from datetime import datetime, timedelta
from app.config import Config
from app.utils import timer_decorator, logger

# Token cache
TOKEN_CACHE = {
    "access_token": None,
    "expires_at": 0
}

@timer_decorator
def get_access_token():
    """Get OAuth access token for ServiceTitan API"""
    # This is a simplified version for initial setup
    # In a real implementation, this would call ServiceTitan's API
    return "mock_access_token"

@timer_decorator
def get_available_slots(service_id, date_from, date_to):
    """Get available appointment slots"""
    # This is a simplified version for initial setup
    # In a real implementation, this would call ServiceTitan's API
    return [
        {
            "id": "slot_1",
            "start": "2025-04-24T09:00:00",
            "end": "2025-04-24T11:00:00"
        },
        {
            "id": "slot_2",
            "start": "2025-04-24T13:00:00",
            "end": "2025-04-24T15:00:00"
        },
        {
            "id": "slot_3",
            "start": "2025-04-25T10:00:00",
            "end": "2025-04-25T12:00:00"
        }
    ]

@timer_decorator
def create_appointment(customer_id, service_id, start_time, end_time, notes=None):
    """Create a new appointment in ServiceTitan"""
    # This is a simplified version for initial setup
    # In a real implementation, this would call ServiceTitan's API
    return {
        "id": "appointment_123",
        "customer_id": customer_id,
        "service_id": service_id,
        "start_time": start_time,
        "end_time": end_time,
        "notes": notes
    }
