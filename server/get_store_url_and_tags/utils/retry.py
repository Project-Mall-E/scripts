import asyncio
import functools
from typing import Callable, Type, Tuple, Any

from .logger import get_logger

logger = get_logger(__name__)


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 2.0,
    max_delay: float = 30.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
):
    """
    Decorator for async functions that retries with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds (doubles each retry)
        max_delay: Maximum delay cap in seconds
        exceptions: Tuple of exception types to catch and retry
    
    Example:
        @retry_with_backoff(max_retries=3, exceptions=(TimeoutError, ConnectionError))
        async def fetch_page(url):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        logger.error(
                            f"{func.__name__} failed after {max_retries + 1} attempts: {e}"
                        )
                        raise
                    
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    logger.warning(
                        f"{func.__name__} attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    await asyncio.sleep(delay)
            
            raise last_exception
        
        return wrapper
    return decorator


async def retry_async(
    coro_func: Callable,
    *args,
    max_retries: int = 3,
    base_delay: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    **kwargs
) -> Any:
    """
    Retry an async function with exponential backoff (non-decorator version).
    
    Args:
        coro_func: Async function to call
        *args: Positional arguments for the function
        max_retries: Maximum retry attempts
        base_delay: Initial delay in seconds
        exceptions: Exception types to catch
        **kwargs: Keyword arguments for the function
    
    Returns:
        The return value of the function
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return await coro_func(*args, **kwargs)
        except exceptions as e:
            last_exception = e
            
            if attempt == max_retries:
                raise
            
            delay = base_delay * (2 ** attempt)
            logger.warning(
                f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.1f}s..."
            )
            await asyncio.sleep(delay)
    
    raise last_exception
