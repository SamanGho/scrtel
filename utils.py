import os
import time
import logging

def safe_delete(file_path, attempts=3, delay=1):
    for _ in range(attempts):
        try:
            os.remove(file_path)
            logging.info(f"File deleted: {file_path}")
            return
        except Exception as e:
            logging.warning(f"Delete failed: {e}")
            time.sleep(delay)
    logging.error(f"Failed to delete file after {attempts} attempts: {file_path}")

def move_to_unsent(file_path, unsent_directory):
    try:
        os.rename(file_path, os.path.join(unsent_directory, os.path.basename(file_path)))
        logging.warning(f"Screenshot moved to unsent: {file_path}")
    except Exception as e:
        logging.error(f"Failed to move unsent screenshot: {e}")
def retry_operation(func, *args, attempts=3, delay=1, **kwargs):
    for _ in range(attempts):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.warning(f"Operation failed: {e}")
            time.sleep(delay)
    logging.error(f"Operation failed after {attempts} attempts.")