import time
import logging
import json
from functools import wraps

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def timer_decorator(func):
    """Decorator to measure function execution time for latency monitoring"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = (end_time - start_time) * 1000  # Convert to ms
        logger.info(f"Function {func.__name__} executed in {execution_time:.2f} ms")
        return result
    return wrapper

def safe_json_loads(json_str, default=None):
    """Safely load JSON string"""
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default if default is not None else {}
