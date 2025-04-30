import logging
import sys
import time
from functools import wraps

# Basic Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)

def get_logger(name):
    """Returns a logger instance."""
    return logging.getLogger(name)

# Example Timer Decorator (Optional)
def timing_decorator(func):
    """A decorator that logs the execution time of a function."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        logger.info(f"Function 	{func.__name__}	 executed in {end_time - start_time:.4f} seconds")
        return result
    return wrapper

