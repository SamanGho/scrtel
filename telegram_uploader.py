import os
import time
import queue
import threading
import telebot
from utils import safe_delete, move_to_unsent
import logging

logger = logging.getLogger(__name__)


class TelegramScreenshotUploader:
    def __init__(self, bot: telebot.TeleBot, channel_id: str, max_retry_attempts: int = 3):
        """
        Initialize the Telegram screenshot uploader.

        Args:
            bot: Telegram bot instance.
            channel_id: Target Telegram channel ID.
            max_retry_attempts: Maximum retry attempts for sending screenshots.
        """
        self.bot = bot
        self.channel_id = channel_id
        self.screenshot_queue = queue.Queue()
        self.max_retry_attempts = max_retry_attempts
        self.unsent_directory = None
        self.stop_event = threading.Event()
        self.upload_thread = threading.Thread(target=self._upload_worker, daemon=True, name="UploadWorker")
        self.upload_thread.start()
        logger.info("TelegramScreenshotUploader initialized.")

    def set_unsent_directory(self, path: str) -> None:
        """
        Set the directory for unsent screenshots.

        Args:
            path: Directory path for unsent screenshots.
        """
        self.unsent_directory = path
        os.makedirs(path, exist_ok=True)
        logger.info(f"Unsent directory set to: {path}")

    def enqueue_screenshot(self, image_path: str, caption: str = None) -> None:
        """
        Enqueue a screenshot for upload.

        Args:
            image_path: Path to the screenshot file.
            caption: Optional caption for the screenshot.
        """
        self.screenshot_queue.put((image_path, caption))
        logger.info(f"Screenshot queued: {image_path} (Caption: {caption})")

    def stop(self) -> None:
        """Stop the upload worker thread."""
        self.stop_event.set()
        logger.info("Stopping TelegramScreenshotUploader.")

    def _upload_worker(self) -> None:
        """Worker thread to process the screenshot queue."""
        while not self.stop_event.is_set():
            try:
                image_path, caption = self.screenshot_queue.get(timeout=1)
                success = self._send_screenshot(image_path, caption)
                self.screenshot_queue.task_done()
                if not success and self.unsent_directory:
                    move_to_unsent(image_path, self.unsent_directory)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Unexpected error in upload worker: {e}")

    def _send_screenshot(self, image_path: str, caption: str = None) -> bool:
        """
        Send a screenshot to Telegram with retries.

        Args:
            image_path: Path to the screenshot file.
            caption: Optional caption for the screenshot.

        Returns:
            bool: True if successful, False otherwise.
        """
        for attempt in range(self.max_retry_attempts):
            try:
                with open(image_path, 'rb') as photo:
                    self.bot.send_photo(self.channel_id, photo, caption=caption)
                safe_delete(image_path)
                logger.info(f"Screenshot sent successfully: {image_path} (Caption: {caption})")
                return True
            except telebot.apihelper.ApiException as api_error:
                logger.warning(f"Telegram API error (Attempt {attempt + 1}/{self.max_retry_attempts}): {api_error}")
                if attempt < self.max_retry_attempts - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
            except Exception as e:
                logger.error(f"Error sending screenshot (Attempt {attempt + 1}/{self.max_retry_attempts}): {e}")
                if attempt < self.max_retry_attempts - 1:
                    time.sleep(2 ** attempt)
        logger.error(f"Failed to send screenshot after {self.max_retry_attempts} attempts: {image_path}")
        return False
