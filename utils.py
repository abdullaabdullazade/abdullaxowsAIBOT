import asyncio


async def async_wrap_blocking(func, *args, **kwargs):
    """
    Safely run blocking functions inside asyncio event loop.

    Args:
        func: The blocking function to run.
        *args: Positional arguments for the function.
        **kwargs: Keyword arguments for the function.

    Returns:
        The result of the blocking function, executed asynchronously.
    """
    return await asyncio.to_thread(func, *args, **kwargs)