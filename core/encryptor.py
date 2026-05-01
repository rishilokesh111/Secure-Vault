"""
SecureVault – AES-256 File Encryptor
Encrypts and decrypts files using AES-256-CBC with PBKDF2 key derivation.
Each file gets a unique salt and IV, stored in the encrypted file header.

File format: [16-byte salt][16-byte IV][encrypted data + PKCS7 padding]
"""

import os
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes

# Key derivation parameters
KDF_ITERATIONS = 100_000
KEY_SIZE = 32  # AES-256
SALT_SIZE = 16
IV_SIZE = 16
ENCRYPTED_EXT = ".svault"


def _derive_key(password: str, salt: bytes) -> bytes:
    """Derive a 256-bit AES key from password using PBKDF2."""
    return PBKDF2(
        password.encode("utf-8"),
        salt,
        dkLen=KEY_SIZE,
        count=KDF_ITERATIONS
    )


def encrypt_file(filepath: str, password: str) -> str:
    """
    Encrypt a file in-place using AES-256-CBC.
    Returns the new filepath (with .svault extension).
    The original file is securely overwritten and deleted.
    """
    # Generate random salt and IV
    salt = get_random_bytes(SALT_SIZE)
    iv = get_random_bytes(IV_SIZE)

    # Derive key from password
    key = _derive_key(password, salt)
    cipher = AES.new(key, AES.MODE_CBC, iv)

    # Read original file
    with open(filepath, "rb") as f:
        plaintext = f.read()

    # Encrypt with PKCS7 padding
    ciphertext = cipher.encrypt(pad(plaintext, AES.block_size))

    # Write encrypted file: salt + iv + ciphertext
    enc_path = filepath + ENCRYPTED_EXT
    with open(enc_path, "wb") as f:
        f.write(salt)
        f.write(iv)
        f.write(ciphertext)

    # Securely overwrite and delete the original file
    _secure_delete(filepath)

    return enc_path


def decrypt_file(enc_filepath: str, password: str) -> str:
    """
    Decrypt a .svault file back to its original form.
    Returns the restored filepath (without .svault extension).
    The encrypted file is deleted after decryption.
    """
    # Read encrypted file
    with open(enc_filepath, "rb") as f:
        salt = f.read(SALT_SIZE)
        iv = f.read(IV_SIZE)
        ciphertext = f.read()

    # Derive key
    key = _derive_key(password, salt)
    cipher = AES.new(key, AES.MODE_CBC, iv)

    # Decrypt and remove padding
    try:
        plaintext = unpad(cipher.decrypt(ciphertext), AES.block_size)
    except (ValueError, KeyError):
        raise ValueError("Decryption failed — wrong password or corrupted file")

    # Write decrypted file (strip .svault extension)
    if enc_filepath.endswith(ENCRYPTED_EXT):
        original_path = enc_filepath[: -len(ENCRYPTED_EXT)]
    else:
        original_path = enc_filepath + ".decrypted"

    with open(original_path, "wb") as f:
        f.write(plaintext)

    # Delete encrypted file
    try:
        os.remove(enc_filepath)
    except OSError:
        pass

    return original_path


def encrypt_directory(dir_path: str, password: str) -> int:
    """
    Encrypt all files in a directory recursively.
    Returns count of files encrypted.
    """
    count = 0
    for root, dirs, files in os.walk(dir_path):
        for filename in files:
            filepath = os.path.join(root, filename)
            # Skip already encrypted files
            if filepath.endswith(ENCRYPTED_EXT):
                continue
            try:
                encrypt_file(filepath, password)
                count += 1
            except Exception:
                pass
    return count


def decrypt_directory(dir_path: str, password: str) -> int:
    """
    Decrypt all .svault files in a directory recursively.
    Returns count of files decrypted.
    """
    count = 0
    for root, dirs, files in os.walk(dir_path):
        for filename in files:
            if filename.endswith(ENCRYPTED_EXT):
                filepath = os.path.join(root, filename)
                try:
                    decrypt_file(filepath, password)
                    count += 1
                except Exception:
                    pass
    return count


def _secure_delete(filepath: str):
    """Overwrite a file with random bytes then delete it."""
    try:
        size = os.path.getsize(filepath)
        if size > 0:
            with open(filepath, "wb") as f:
                f.write(os.urandom(size))
                f.flush()
                os.fsync(f.fileno())
        os.remove(filepath)
    except OSError:
        try:
            os.remove(filepath)
        except OSError:
            pass
