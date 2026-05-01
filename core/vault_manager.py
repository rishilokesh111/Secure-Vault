"""
SecureVault – Vault Manager
Manages multiple secured vault folders with JSON-based persistence.
Lock = moves contents to hidden storage.
Unlock = password verified → restores files to original folder.
Folders stay VISIBLE in File Explorer when locked — but can't be opened.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time



from core.paths import get_resource_path, get_data_path

DATA_DIR = os.path.dirname(get_data_path("vaults.json"))
VAULTS_FILE = get_data_path("vaults.json")
STORAGE_DIR = get_data_path("vault_storage")


def _load_vaults() -> dict:
    """Load vault configuration from JSON file."""
    if not os.path.exists(VAULTS_FILE):
        return {}
    try:
        with open(VAULTS_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_vaults(vaults: dict):
    """Save vault configuration to JSON file."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(VAULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(vaults, f, indent=2)


def _vault_id(folder_path: str) -> str:
    """Generate a unique ID for a vault based on its path."""
    return hashlib.md5(folder_path.encode()).hexdigest()


def _get_storage_path(folder_path: str) -> str:
    """Get the hidden storage path for a vault's contents."""
    vid = _vault_id(folder_path)
    return os.path.join(STORAGE_DIR, vid)


# ══════════════════════════════════════════════════
#  PUBLIC API
# ══════════════════════════════════════════════════

def add_vault(folder_path: str) -> tuple[bool, str]:
    """
    Register a folder as a secured vault.
    Returns (success, message).
    """
    folder_path = os.path.normpath(os.path.abspath(folder_path))

    if not os.path.exists(folder_path):
        return False, "Folder does not exist."

    if not os.path.isdir(folder_path):
        return False, "Path is not a folder."

    vaults = _load_vaults()

    if folder_path in vaults:
        return False, "This folder is already secured."

    # Count items in the folder
    try:
        items = os.listdir(folder_path)
        file_count = sum(1 for i in items if os.path.isfile(os.path.join(folder_path, i)))
        dir_count = sum(1 for i in items if os.path.isdir(os.path.join(folder_path, i)))
    except PermissionError:
        file_count = 0
        dir_count = 0

    vaults[folder_path] = {
        "status": "unlocked",
        "added_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "file_count": file_count,
        "dir_count": dir_count,
        "failed_attempts": 0,
    }

    _save_vaults(vaults)
    return True, f"Vault added: {folder_path}"


def remove_vault(folder_path: str) -> tuple[bool, str]:
    """
    Remove a folder from secured vaults (restores contents if locked).
    Returns (success, message).
    """
    folder_path = os.path.normpath(os.path.abspath(folder_path))
    vaults = _load_vaults()

    if folder_path not in vaults:
        return False, "Folder is not a secured vault."

    # If locked, unlock first to restore contents
    if vaults[folder_path]["status"] == "locked":
        _do_unlock(folder_path)

    del vaults[folder_path]
    _save_vaults(vaults)
    return True, f"Vault removed: {folder_path}"


def list_vaults() -> list[dict]:
    """
    Get all secured vaults with their status.
    Returns list of dicts with path, status, added_at, etc.
    """
    vaults = _load_vaults()
    result = []

    for path, info in vaults.items():
        exists = os.path.exists(path) or os.path.exists(path + ".lnk")

        result.append({
            "path": path,
            "name": os.path.basename(path),
            "status": info.get("status", "unlocked"),
            "added_at": info.get("added_at", "Unknown"),
            "file_count": info.get("file_count", 0),
            "dir_count": info.get("dir_count", 0),
            "failed_attempts": info.get("failed_attempts", 0),
            "exists": exists,
            "drive": os.path.splitdrive(path)[0] + "\\",
        })

    return result


def lock_vault(folder_path: str, password: str = "") -> tuple[bool, str]:
    """
    Lock a vault:
    1. Move all contents to hidden storage
    2. Place unlock script in the original folder
    Returns (success, message).
    """
    folder_path = os.path.normpath(os.path.abspath(folder_path))
    vaults = _load_vaults()

    if folder_path not in vaults:
        return False, "Not a secured vault."

    if vaults[folder_path]["status"] == "locked":
        return False, "Vault is already locked."

    # Update counts before locking
    try:
        items = os.listdir(folder_path)
        vaults[folder_path]["file_count"] = sum(
            1 for i in items if os.path.isfile(os.path.join(folder_path, i))
        )
        vaults[folder_path]["dir_count"] = sum(
            1 for i in items if os.path.isdir(os.path.join(folder_path, i))
        )
    except (PermissionError, OSError):
        pass

    success, err = _do_lock(folder_path, password)
    if success:
        vaults[folder_path]["status"] = "locked"
        _save_vaults(vaults)
        return True, f"🔒 Vault locked: {os.path.basename(folder_path)}"
    else:
        return False, f"Failed to lock vault: {err}"


def unlock_vault(folder_path: str, password: str = "") -> tuple[bool, str]:
    """
    Unlock a vault:
    1. Move contents back to original folder from hidden storage
    Returns (success, message).
    """
    folder_path = os.path.normpath(os.path.abspath(folder_path))
    vaults = _load_vaults()

    if folder_path not in vaults:
        return False, "Not a secured vault."

    if vaults[folder_path]["status"] == "unlocked":
        return False, "Vault is already unlocked."

    success, err = _do_unlock(folder_path, password)
    if success:
        vaults[folder_path]["status"] = "unlocked"
        vaults[folder_path]["failed_attempts"] = 0
        _save_vaults(vaults)
        return True, f"🔓 Vault unlocked: {os.path.basename(folder_path)}"
    else:
        return False, f"Failed to unlock vault: {err}"


def record_failed_attempt(folder_path: str) -> int:
    """Record a failed access attempt. Returns total failed attempts."""
    folder_path = os.path.normpath(os.path.abspath(folder_path))
    vaults = _load_vaults()

    if folder_path not in vaults:
        return 0

    vaults[folder_path]["failed_attempts"] = vaults[folder_path].get("failed_attempts", 0) + 1
    _save_vaults(vaults)
    return vaults[folder_path]["failed_attempts"]


def reset_attempts(folder_path: str):
    """Reset failed attempts for a vault."""
    folder_path = os.path.normpath(os.path.abspath(folder_path))
    vaults = _load_vaults()

    if folder_path in vaults:
        vaults[folder_path]["failed_attempts"] = 0
        _save_vaults(vaults)


def get_vault_info(folder_path: str) -> dict | None:
    """Get info about a specific vault."""
    folder_path = os.path.normpath(os.path.abspath(folder_path))
    vaults = _load_vaults()
    return vaults.get(folder_path)


def update_vault_counts(folder_path: str):
    """Refresh the file/dir counts for a vault."""
    folder_path = os.path.normpath(os.path.abspath(folder_path))
    vaults = _load_vaults()

    if folder_path not in vaults:
        return

    if vaults[folder_path].get("status") == "locked":
        return  # Don't try to count a locked vault

    try:
        items = os.listdir(folder_path)
        vaults[folder_path]["file_count"] = sum(
            1 for i in items if os.path.isfile(os.path.join(folder_path, i))
        )
        vaults[folder_path]["dir_count"] = sum(
            1 for i in items if os.path.isdir(os.path.join(folder_path, i))
        )
        _save_vaults(vaults)
    except (PermissionError, OSError):
        pass


# ══════════════════════════════════════════════════
#  INTERNAL: Lock/Unlock via content move + unlock script
# ══════════════════════════════════════════════════

# Path to the unlock prompt script
UNLOCK_SCRIPT = get_resource_path("unlock_prompt.py")

LOCK_MARKER = ".securevault_locked"


def _do_lock(folder_path: str, password: str = "") -> tuple[bool, str]:
    """
    Lock a folder:
    1. Move all contents into hidden storage (data/vault_storage/<id>/)
    2. Delete the empty original folder
    3. Create a .lnk shortcut that looks like the folder but runs the unlock script
    """
    storage_path = _get_storage_path(folder_path)

    try:
        # Step 1: Create hidden storage directory
        os.makedirs(storage_path, exist_ok=True)

        # Step 2: Move all contents from the vault folder to hidden storage
        try:
            items = os.listdir(folder_path)
        except PermissionError:
            return False, "Cannot read folder (permission denied)"

        for item in items:
            src = os.path.join(folder_path, item)
            dst = os.path.join(storage_path, item)
            try:
                shutil.move(src, dst)
            except Exception as e:
                _rollback_move(storage_path, folder_path)
                return False, f"Failed to move '{item}': {e}"

        # Step 3: Delete the empty original folder
        try:
            shutil.rmtree(folder_path, ignore_errors=True)
        except Exception:
            pass

        # Step 4: Create the shortcut
        _create_folder_shortcut(folder_path)

        # Hide the storage directory
        try:
            import ctypes
            ctypes.windll.kernel32.SetFileAttributesW(STORAGE_DIR, 0x06)  # HIDDEN + SYSTEM
        except Exception:
            pass

        return True, ""

    except Exception as e:
        return False, str(e)


def _do_unlock(folder_path: str, password: str = "") -> tuple[bool, str]:
    """
    Unlock a folder:
    1. Remove the .lnk shortcut
    2. Re-create the folder
    3. Move contents back to the folder from hidden storage
    """
    storage_path = _get_storage_path(folder_path)

    try:
        # Step 1: Remove the shortcut
        lnk_path = folder_path + ".lnk"
        if os.path.exists(lnk_path):
            try:
                os.remove(lnk_path)
            except Exception:
                pass

        # Step 2: Recreate the original folder
        os.makedirs(folder_path, exist_ok=True)

        # Step 3: Move files back from storage
        if os.path.exists(storage_path):
            # Move contents back
            for item in os.listdir(storage_path):
                src = os.path.join(storage_path, item)
                dst = os.path.join(folder_path, item)
                try:
                    shutil.move(src, dst)
                except Exception as e:
                    return False, f"Failed to restore '{item}': {e}"

            # Clean up the storage directory
            try:
                shutil.rmtree(storage_path)
            except Exception:
                pass

        return True, ""

    except Exception as e:
        return False, str(e)


def _create_folder_shortcut(folder_path: str):
    """
    Replace the locked folder with a Windows Shortcut (.lnk).
    When double-clicked, it runs unlock_prompt.py.
    """
    python_dir = os.path.dirname(sys.executable)
    pythonw = os.path.join(python_dir, "pythonw.exe")
    if not os.path.exists(pythonw):
        pythonw = sys.executable

    lnk_path = folder_path + ".lnk"
    
    # We create the shortcut using a small temporary VBS script because python 
    # doesn't natively create .lnk files without pywin32, which might not be installed.
    vbs_creator = os.path.join(DATA_DIR, "create_lnk.vbs")
    vbs_content = f'''Set oWS = WScript.CreateObject("WScript.Shell")
Set oLink = oWS.CreateShortcut("{lnk_path}")
oLink.TargetPath = "{pythonw}"
'''

    if getattr(sys, 'frozen', False):
        # In EXE mode, we call the same EXE with a special flag
        vbs_content += f'oLink.Arguments = "--unlock ""{folder_path}"""\n'
    else:
        # In script mode, we call pythonw.exe with the script path
        vbs_content += f'oLink.Arguments = """{UNLOCK_SCRIPT}"" ""{folder_path}"""\n'

    vbs_content += 'oLink.IconLocation = "shell32.dll, 3"\noLink.Save\n'
    try:
        with open(vbs_creator, "w", encoding="utf-8") as f:
            f.write(vbs_content)
        
        # Execute the VBS script to create the shortcut
        subprocess.run(["cscript", "//nologo", vbs_creator], capture_output=True)
        
        # Clean up the temporary VBS
        os.remove(vbs_creator)
    except Exception as e:
        print(f"Error creating shortcut: {e}")


def _rollback_move(storage_path: str, folder_path: str):
    """Roll back a partial move: move items back from storage to the folder."""
    try:
        if os.path.exists(storage_path):
            for item in os.listdir(storage_path):
                src = os.path.join(storage_path, item)
                dst = os.path.join(folder_path, item)
                try:
                    shutil.move(src, dst)
                except Exception:
                    pass
            shutil.rmtree(storage_path, ignore_errors=True)
    except Exception:
        pass
