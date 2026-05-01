import os
import sys

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return os.path.join(base_path, relative_path)

def get_data_path(relative_path):
    """ 
    Get absolute path to data file. 
    In EXE mode: Uses %LOCALAPPDATA%/SecureVault (Standard Windows storage).
    In Script mode: Uses root or data/ folder.
    """
    if getattr(sys, 'frozen', False):
        # Running as EXE: Use standard Windows AppData to prevent accidental deletion
        base_path = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
        data_dir = os.path.join(base_path, "SecureVault")
        
        # Migration: Check if old data folder exists next to EXE and move it
        old_data_dir = os.path.join(os.path.dirname(sys.executable), "data")
        if os.path.exists(old_data_dir) and not os.path.exists(data_dir):
            try:
                import shutil
                shutil.move(old_data_dir, data_dir)
                print(f"Migrated data from {old_data_dir} to {data_dir}")
            except Exception:
                pass
    else:
        # Running as Script: prefer root if file exists, else use data/
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        root_file = os.path.join(base_path, relative_path)
        if os.path.exists(root_file):
            return root_file
        data_dir = os.path.join(base_path, "data")
    
    if not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)
        
    return os.path.join(data_dir, relative_path)
