"""
SecureVault – Drive Scanner
Detects all mounted drives (HDD, SSD, USB, SD cards) on Windows
using ctypes + kernel32 API. No external dependencies required.
"""

import ctypes
import os
import string


# Drive type constants from Windows API
DRIVE_TYPES = {
    0: "Unknown",
    1: "No Root",
    2: "Removable",    # USB, SD card, floppy
    3: "Fixed",        # HDD, SSD
    4: "Network",
    5: "CD-ROM",
    6: "RAM Disk",
}

DRIVE_ICONS = {
    "Unknown": "💾",
    "No Root": "💾",
    "Removable": "🔌",
    "Fixed": "💻",
    "Network": "🌐",
    "CD-ROM": "💿",
    "RAM Disk": "⚡",
}


def get_drives() -> list[dict]:
    """
    Detect all mounted drives on the system.
    Returns a list of dicts: {letter, path, type, type_name, icon, label}
    """
    drives = []

    # Use kernel32 to get logical drives bitmask
    try:
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    except Exception:
        # Fallback: check all letters
        bitmask = 0
        for i, letter in enumerate(string.ascii_uppercase):
            if os.path.exists(f"{letter}:\\"):
                bitmask |= (1 << i)

    for i, letter in enumerate(string.ascii_uppercase):
        if bitmask & (1 << i):
            drive_path = f"{letter}:\\"

            # Get drive type
            try:
                drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive_path)
            except Exception:
                drive_type = 0

            type_name = DRIVE_TYPES.get(drive_type, "Unknown")
            icon = DRIVE_ICONS.get(type_name, "💾")

            # Get volume label
            label = _get_volume_label(drive_path)

            # Build display name
            if label:
                display = f"{icon} {label} ({letter}:)"
            else:
                display = f"{icon} {type_name} Drive ({letter}:)"

            drives.append({
                "letter": letter,
                "path": drive_path,
                "type": drive_type,
                "type_name": type_name,
                "icon": icon,
                "label": label,
                "display": display,
            })

    return drives


def _get_volume_label(drive_path: str) -> str:
    """Get the volume label for a drive using Windows API."""
    try:
        volume_name = ctypes.create_unicode_buffer(1024)
        ctypes.windll.kernel32.GetVolumeInformationW(
            drive_path,
            volume_name,
            1024,
            None, None, None, None, 0
        )
        return volume_name.value or ""
    except Exception:
        return ""


def get_directory_contents(path: str) -> list[dict]:
    """
    List contents of a directory.
    Returns list of dicts: {name, path, is_dir, size, icon}
    Sorted: directories first, then files, both alphabetical.
    """
    items = []

    try:
        entries = os.listdir(path)
    except PermissionError:
        return [{"name": "⛔ Access Denied", "path": "", "is_dir": False, "size": 0, "icon": "🚫"}]
    except OSError:
        return [{"name": "⚠ Cannot Read", "path": "", "is_dir": False, "size": 0, "icon": "⚠"}]

    dirs = []
    files = []

    for entry in entries:
        full_path = os.path.join(path, entry)
        try:
            is_dir = os.path.isdir(full_path)
            size = 0
            if not is_dir:
                try:
                    size = os.path.getsize(full_path)
                except OSError:
                    size = 0

            item = {
                "name": entry,
                "path": full_path,
                "is_dir": is_dir,
                "size": size,
                "icon": "📁" if is_dir else "📄",
            }

            if is_dir:
                dirs.append(item)
            else:
                files.append(item)
        except (PermissionError, OSError):
            continue

    # Sort alphabetically, case-insensitive
    dirs.sort(key=lambda x: x["name"].lower())
    files.sort(key=lambda x: x["name"].lower())

    return dirs + files


def format_size(size_bytes: int) -> str:
    """Format bytes into human-readable size."""
    if size_bytes == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    while size >= 1024 and i < len(units) - 1:
        size /= 1024
        i += 1
    return f"{size:.1f} {units[i]}"


def is_removable_drive(drive_path: str) -> bool:
    """Check if a drive is removable (USB/SD card)."""
    try:
        drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive_path)
        return drive_type == 2  # DRIVE_REMOVABLE
    except Exception:
        return False
