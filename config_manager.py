import os
import json
import bcrypt
import base64
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Constants
CONFIG_FILE = "config.json"
logger = logging.getLogger(__name__)


def load_config(password: str) -> dict:
    """
    Load and decrypt the configuration from the config file.

    Args:
        password: User-provided password to decrypt the configuration.

    Returns:
        Decrypted configuration as a dictionary.

    Raises:
        FileNotFoundError: If the config file does not exist.
        ValueError: If the password is invalid or decryption fails.
    """
    if not os.path.exists(CONFIG_FILE):
        logger.error("Configuration file not found.")
        raise FileNotFoundError("Configuration file not found.")

    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)

        hashed_pw = config.get('password_hash', '').encode('utf-8')
        salt = base64.b64decode(config.get('salt', ''))
        encrypted_data = config.get('encrypted_data', '').encode('utf-8')

        if not bcrypt.checkpw(password.encode('utf-8'), hashed_pw):
            logger.warning("Password verification failed.")
            raise ValueError("Invalid password.")

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode('utf-8')))
        fernet = Fernet(key)
        decrypted_data = fernet.decrypt(encrypted_data).decode('utf-8')
        logger.info("Configuration loaded and decrypted successfully.")
        return json.loads(decrypted_data)

    except ValueError as e:
        logger.error(f"Failed to load configuration: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error loading configuration: {e}")
        raise ValueError(f"Failed to load configuration: {e}")


def save_config(api_token: str, channel_id: str, save_path: str, password: str) -> None:
    """
    Save and encrypt the configuration to the config file.

    Args:
        api_token: Telegram API token.
        channel_id: Telegram channel ID.
        save_path: File path for saving screenshots.
        password: User-provided password to encrypt the configuration.

    Raises:
        RuntimeError: If saving the configuration fails.
    """
    try:
        salt = os.urandom(16)
        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        logger.debug(f"Type of hashed_pw: {type(hashed_pw)}, Value: {hashed_pw}")

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode('utf-8')))
        fernet = Fernet(key)

        config_data = {
            "api_token": api_token,
            "channel_id": channel_id,
            "save_path": save_path
        }
        encrypted_data = fernet.encrypt(json.dumps(config_data).encode('utf-8'))

        # Ensure hashed_pw is a string for JSON serialization
        password_hash = hashed_pw.decode('utf-8') if isinstance(hashed_pw, bytes) else hashed_pw

        config = {
            "password_hash": password_hash,
            "salt": base64.b64encode(salt).decode('utf-8'),
            "encrypted_data": encrypted_data.decode('utf-8')
        }

        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)

        logger.info("Configuration saved and encrypted successfully.")

    except Exception as e:
        logger.error(f"Failed to save configuration: {e}")
        raise RuntimeError(f"Failed to save configuration: {e}")
