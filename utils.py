import os
import time
import logging

logger = logging.getLogger(__name__)


def safe_delete(file_path: str, attempts: int = 3, delay: float = 1) -> None:
    """
    Safely delete a file with retries.

    Args:
        file_path: Path to the file to delete.
        attempts: Number of retry attempts.
        delay: Delay between retries in seconds.
    """
    for attempt in range(attempts):
        try:
            os.remove(file_path)
            logger.info(f"File deleted successfully: {file_path}")
            return
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1}/{attempts} to delete {file_path} failed: {e}")
            if attempt < attempts - 1:
                time.sleep(delay)
    logger.error(f"Failed to delete file after {attempts} attempts: {file_path}")


def move_to_unsent(file_path: str, unsent_directory: str) -> None:
    """
    Move a file to the unsent directory if sending fails.

    Args:
        file_path: Path to the file to move.
        unsent_directory: Destination directory for unsent files.
    """
    try:
        destination = os.path.join(unsent_directory, os.path.basename(file_path))
        os.rename(file_path, destination)
        logger.warning(f"Screenshot moved to unsent directory: {destination}")
    except Exception as e:
        logger.error(f"Failed to move screenshot to unsent directory: {e}")


def retry_operation(func, *args, attempts: int = 3, delay: float = 1, **kwargs):
    """
    Retry a function operation with delays.

    Args:
        func: Function to retry.
        attempts: Number of retry attempts.
        delay: Delay between retries in seconds.
        *args: Positional arguments for the function.
        **kwargs: Keyword arguments for the function.

    Returns:
        The function's return value if successful.

    Raises:
        Exception: If all attempts fail.
    """
    for attempt in range(attempts):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Operation {func.__name__} failed (Attempt {attempt + 1}/{attempts}): {e}")
            if attempt < attempts - 1:
                time.sleep(delay)
    logger.error(f"Operation {func.__name__} failed after {attempts} attempts.")
    raise Exception(f"Operation failed after {attempts} attempts.")
