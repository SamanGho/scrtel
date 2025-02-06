import os
import json
import bcrypt
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Configuration file name
CONFIG_FILE = "config.json"

def load_config(password):
    """
    Load and decrypt the configuration from the config file.
    :param password: User-provided password to decrypt the configuration.
    :return: Decrypted configuration as a dictionary.
    """
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError("Configuration file not found.")

    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)

        hashed_pw = config.get('password_hash', '').encode()
        salt = base64.b64decode(config.get('salt', ''))
        encrypted_data = config.get('encrypted_data', '').encode()

        if not bcrypt.checkpw(password.encode(), hashed_pw):
            raise ValueError("Invalid password.")

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        fernet = Fernet(key)
        decrypted_data = fernet.decrypt(encrypted_data).decode()
        return json.loads(decrypted_data)

    except Exception as e:
        raise ValueError(f"Failed to load configuration: {e}")

def save_config(api_token, channel_id, save_path, password):
    """
    Save and encrypt the configuration to the config file.
    :param api_token: Telegram API token.
    :param channel_id: Telegram channel ID.
    :param save_path: File path for saving screenshots.
    :param password: User-provided password to encrypt the configuration.
    """
    try:
        salt = os.urandom(16)
        hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        fernet = Fernet(key)

        config_data = {
            "api_token": api_token,
            "channel_id": channel_id,
            "save_path": save_path
        }
        encrypted_data = fernet.encrypt(json.dumps(config_data).encode())

        with open(CONFIG_FILE, 'w') as f:
            json.dump({
                "password_hash": hashed_pw.decode(),
                "salt": base64.b64encode(salt).decode(),
                "encrypted_data": encrypted_data.decode()
            }, f, indent=4)

    except Exception as e:
        raise RuntimeError(f"Failed to save configuration: {e}")