import os
import shutil
import random
import string


def _overwrite_file(filepath: str, passes: int = 3):
    """
    Securely overwrite a file's contents before deletion.
    - 3 passes of random bytes
    - 1 pass of zero bytes
    - Rename to a random name to obscure the original filename
    """
    try:
        file_size = os.path.getsize(filepath)
        if file_size == 0:
            return filepath  # nothing to overwrite

        # Random byte passes
        for _ in range(passes):
            with open(filepath, 'wb') as f:
                f.write(os.urandom(file_size))
                f.flush()
                os.fsync(f.fileno())

        # Zero byte pass
        with open(filepath, 'wb') as f:
            f.write(b'\x00' * file_size)
            f.flush()
            os.fsync(f.fileno())

        # Rename to random name to obscure original filename
        directory = os.path.dirname(filepath)
        random_name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))
        new_path = os.path.join(directory, random_name)
        os.rename(filepath, new_path)
        return new_path

    except (PermissionError, OSError) as e:
        print(f"  [!] Could not overwrite {filepath}: {e}")
        return filepath


def secure_nuke(folder_path: str):
    """
    Securely destroy a folder:
    1. Overwrite every file with random then zero bytes
    2. Rename files to random names
    3. Remove the entire directory tree
    4. Clean up data files (hash, attempts log)
    """
    if not os.path.exists(folder_path):
        print("[!] Vault folder not found. Nothing to delete.")
        return

    print("[*] Shredding vault files...")

    # Walk through all files and overwrite them
    for root, dirs, files in os.walk(folder_path):
        for filename in files:
            filepath = os.path.join(root, filename)
            print(f"  [*] Shredding: {filename}")
            _overwrite_file(filepath)

    # Remove the directory tree
    shutil.rmtree(folder_path, ignore_errors=True)
    print("[*] Vault directory removed.")

    # Clean up data files
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    for data_file in ["hash.txt", "attempts.log"]:
        data_path = os.path.join(data_dir, data_file)
        if os.path.exists(data_path):
            _overwrite_file(data_path)
            try:
                os.remove(data_path)
            except OSError:
                pass

    print("!!! VAULT PERMANENTLY DESTROYED – NO RECOVERY POSSIBLE !!!")