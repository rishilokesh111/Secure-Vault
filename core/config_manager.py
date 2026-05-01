import json
import base64
import os
from core.paths import get_data_path

# A unique obfuscation key for SecureVault
_SECRET_KEY = "SV_SECRET_KEY_2026_!@#"

CONFIG_FILE = get_data_path("settings.bin")

def _xor_cipher(data_bytes: bytes) -> bytes:
    """Simple XOR cipher for obfuscation working on bytes."""
    key_bytes = _SECRET_KEY.encode("utf-8")
    return bytes(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(data_bytes))

def save_config(config_dict: dict):
    """Encrypt and save configuration to a binary file."""
    try:
        json_data = json.dumps(config_dict).encode("utf-8")
        encrypted_bytes = _xor_cipher(json_data)
        encoded_data = base64.b64encode(encrypted_bytes)
        # Unhide the file before writing to avoid PermissionError on Windows
        try:
            import ctypes
            if os.path.exists(CONFIG_FILE):
                ctypes.windll.kernel32.SetFileAttributesW(CONFIG_FILE, 0x80) # NORMAL (128)
        except:
            pass
            
        with open(CONFIG_FILE, "wb") as f:
            f.write(encoded_data)
        
        # Set file to hidden on Windows
        try:
            import ctypes
            ctypes.windll.kernel32.SetFileAttributesW(CONFIG_FILE, 0x02) # HIDDEN
        except:
            pass
            
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False

def load_config() -> dict:
    """Load and decrypt configuration from binary file."""
    if not os.path.exists(CONFIG_FILE):
        return {}
    
    try:
        with open(CONFIG_FILE, "rb") as f:
            encoded_data = f.read()
        
        encrypted_bytes = base64.b64decode(encoded_data)
        json_bytes = _xor_cipher(encrypted_bytes)
        return json.loads(json_bytes.decode("utf-8"))
    except Exception as e:
        print(f"Error loading config: {e}")
        return {}

def delete_env_file():
    """Delete the old .env file if it exists (migration)."""
    env_path = get_data_path(".env")
    if os.path.exists(env_path):
        try:
            os.remove(env_path)
            print("[✓] Migrated: Old .env file deleted.")
        except:
            pass
