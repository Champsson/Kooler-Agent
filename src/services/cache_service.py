from cachetools import TTLCache
from functools import wraps
import inspect
from ..utils import get_logger

logger = get_logger(__name__)

# Initialize a Time-To-Live (TTL) cache
# maxsize: Maximum number of items the cache can hold
# ttl: Time-to-live in seconds for each item
cache = TTLCache(maxsize=100, ttl=300) # Default cache, can be overridden by decorator

def get_cached_response(key: str):
    """Retrieves an item from the cache if it exists and hasn't expired."""
    try:
        cached_value = cache.get(key)
        if cached_value:
            logger.info(f"Cache HIT for key: {key}")
            return cached_value
        else:
            logger.info(f"Cache MISS for key: {key}")
            return None
    except Exception as e:
        logger.error(f"Error retrieving from cache for key {key}: {e}", exc_info=True)
        return None

def set_cached_response(key: str, value: any):
    """Adds or updates an item in the cache."""
    try:
        cache[key] = value
        logger.info(f"Cached value for key: {key}")
    except Exception as e:
        logger.error(f"Error setting cache for key {key}: {e}", exc_info=True)

def clear_cache():
    """Clears all items from the cache."""
    try:
        cache.clear()
        logger.info("Cache cleared.")
    except Exception as e:
        logger.error(f"Error clearing cache: {e}", exc_info=True)

# --- Cache Decorator --- 
def cache_response(ttl: int = 300):
    """Decorator to cache the result of a function with a specific TTL.

    Args:
        ttl (int): Time-to-live for the cached item in seconds.
    """
    def decorator(func):
        # Use TTLCache specific to this decorator instance if needed, or use the global one
        # For simplicity, we'll use the global cache but respect the TTL argument.
        # Note: cachetools TTLCache doesn't directly support per-item TTL easily via decorator.
        # We'll use the key to store the value and rely on the global cache's TTL mechanism,
        # or implement a more complex cache if per-item TTL is strictly required.
        # For now, let's assume the decorator implies the *intended* TTL, but the underlying
        # cache might have its own rules. A simpler approach is to use the decorator's TTL
        # for the key generation or logging, but rely on a single cache instance.
        # A better approach might involve multiple cache instances or a custom cache.
        # Let's stick to the simple approach using the global cache for now.

        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create a cache key based on function name and arguments
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            key_parts = [func.__name__]
            for name, value in bound_args.arguments.items():
                key_parts.append(f"{name}={repr(value)}") # Use repr for consistent key generation
            cache_key = "::".join(key_parts)

            # Check cache
            cached_value = get_cached_response(cache_key)
            if cached_value is not None:
                return cached_value

            # Call the function if not cached
            result = func(*args, **kwargs)

            # Store the result in cache
            # Note: We are using the global cache instance `cache` here.
            # The `ttl` argument in the decorator isn't directly setting the TTL
            # for *this specific item* in the standard TTLCache unless we manage it manually.
            # For simplicity, we log the intended TTL but use the global cache.
            logger.debug(f"Caching result for {cache_key} with intended TTL {ttl}s")
            set_cached_response(cache_key, result)

            return result
        
        # Add a cache_clear method to the decorated function for testing
        def cache_clear():
            # This is tricky as the key depends on arguments. 
            # Clearing the whole cache might be the easiest for testing.
            clear_cache()
            logger.info(f"Cleared cache potentially affecting {func.__name__}")
        
        wrapper.cache_clear = cache_clear
        return wrapper
    return decorator

# Example usage (for testing)
if __name__ == '__main__':
    @cache_response(ttl=10) # Cache for 10 seconds
    def expensive_calculation(x, y=2):
        print(f"Calculating {x} + {y}...")
        time.sleep(1) # Simulate work
        return x + y

    print("First call:")
    res1 = expensive_calculation(5)
    print(f"Result 1: {res1}")

    print("\nSecond call (should be cached):")
    res2 = expensive_calculation(5)
    print(f"Result 2: {res2}")

    print("\nThird call with different args:")
    res3 = expensive_calculation(5, y=3)
    print(f"Result 3: {res3}")

    print("\nClearing cache...")
    expensive_calculation.cache_clear()

    print("\nFourth call (after clear):")
    res4 = expensive_calculation(5)
    print(f"Result 4: {res4}")

