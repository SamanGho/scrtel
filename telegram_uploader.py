import os
import time
import queue
import threading
import telebot
from utils import safe_delete, move_to_unsent, retry_operation
import logging
class TelegramScreenshotUploader:
    def __init__(self, bot, channel_id, max_retry_attempts=3):
        self.bot = bot
        self.channel_id = channel_id
        self.screenshot_queue = queue.Queue()
        self.max_retry_attempts = max_retry_attempts
        self.unsent_directory = None
        self.upload_thread = threading.Thread(target=self._upload_worker, daemon=True)
        self.upload_thread.start()

    def set_unsent_directory(self, path):
        self.unsent_directory = path
        os.makedirs(path, exist_ok=True)


    def enqueue_screenshot(self, image_path, caption=None):
        """
        Add a screenshot to the upload queue with an optional caption.
        :param image_path: Path to the screenshot image
        :param caption: Optional caption for the image
        """
        self.screenshot_queue.put((image_path, caption))
        logging.info(f"Screenshot queued: {image_path} (Caption: {caption})")

    def _upload_worker(self):
        while True:
            try:
                # Unpack the tuple from the queue
                image_path, caption = self.screenshot_queue.get()
                success = self._send_screenshot(image_path, caption)
                self.screenshot_queue.task_done()
                if not success and self.unsent_directory:
                    move_to_unsent(image_path, self.unsent_directory)
            except Exception as e:
                logging.error(f"Error in upload worker: {e}")
            time.sleep(1)


    def _send_screenshot(self, image_path, caption=None):
        """
        Attempt to send a screenshot with retry mechanism and optional caption.
        :param image_path: Path to the screenshot image
        :param caption: Optional caption for the image
        :return: Boolean indicating successful send
        """
        for attempt in range(self.max_retry_attempts):
            try:
                with open(image_path, 'rb') as photo:
                    self.bot.send_photo(self.channel_id, photo, caption=caption)
                retry_operation(safe_delete, image_path)
                logging.info(f"Screenshot sent successfully: {image_path} (Caption: {caption})")
                return True
            except telebot.apihelper.ApiException as api_error:
                logging.warning(f"Telegram API error (Attempt {attempt + 1}): {api_error}")
                time.sleep(2 ** attempt)
            except Exception as e:
                logging.error(f"Error sending screenshot (Attempt {attempt + 1}): {e}")
                time.sleep(2 ** attempt)
        return False