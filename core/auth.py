import hashlib
import os


def hash_password(password: str) -> str:
    """
    Hash a password using SHA-256 with a random 32-byte salt.
    Returns a string in the format: salt_hex$hash_hex
    """
    salt = os.urandom(32)
    pw_hash = hashlib.sha256(salt + password.encode('utf-8')).hexdigest()
    return f"{salt.hex()}${pw_hash}"


def verify_password(password: str, stored: str) -> bool:
    """
    Verify a password against a stored salt$hash string.
    Returns True if the password matches, False otherwise.
    """
    try:
        salt_hex, stored_hash = stored.split('$')
        salt = bytes.fromhex(salt_hex)
        pw_hash = hashlib.sha256(salt + password.encode('utf-8')).hexdigest()
        return pw_hash == stored_hash
    except (ValueError, AttributeError):
        return False
