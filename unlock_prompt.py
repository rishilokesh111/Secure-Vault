"""
SecureVault – Standalone Unlock Prompt
Launched when user opens a locked folder in Windows Explorer.
Shows a password prompt with 3 attempts. On success, restores the folder,
opens it, and monitors the Explorer window — auto-relocks when closed.

Usage: pythonw unlock_prompt.py <vault_path>
"""

import customtkinter as ctk
import os
import subprocess
import sys
import threading
import time
from PIL import Image, ImageDraw

from core.paths import get_resource_path, get_data_path

# Setup paths relative to this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.dirname(get_data_path("hash.txt"))
HASH_FILE = get_data_path("hash.txt")
MAX_ATTEMPTS = 3

# Add base dir to path for imports
sys.path.insert(0, BASE_DIR)

from core.auth import verify_password
from core.vault_manager import unlock_vault, lock_vault
from core.mailer import send_vault_backup
from core.shredder import secure_nuke
from core.vault_manager import list_vaults

# Theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

BG_DARK = "#0A0908"
BG_CARD = "#14120E"
ACCENT = "#F59E0B"
ACCENT_HOVER = "#FBBF24"
SUCCESS = "#10B981"
DANGER = "#EF4444"
DANGER_HOVER = "#F87171"
WARNING = "#F59E0B"
TEXT_PRIMARY = "#FEF3C7"
TEXT_SECONDARY = "#D4D4D8"
TEXT_DIM = "#A1A1AA"
BORDER = "#453514"


def is_folder_open_in_explorer(folder_path: str) -> bool:
    """
    Check if a folder is currently open in any Windows Explorer window.
    Uses PowerShell + Shell.Application COM object to query open Explorer windows.
    """
    try:
        # Normalize the path for comparison
        norm_path = os.path.normpath(folder_path).replace("\\", "/").lower()

        # Query all open Explorer windows via COM
        ps_cmd = (
            '(New-Object -ComObject Shell.Application).Windows() | '
            'ForEach-Object { $_.LocationURL } '
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=5,
            creationflags=0x08000000  # CREATE_NO_WINDOW
        )

        if result.returncode != 0:
            return False

        # Explorer returns file:/// URLs — decode and compare
        for line in result.stdout.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            # Convert file:///C:/path/to/folder -> C:/path/to/folder
            explorer_path = line.replace("file:///", "").replace("%20", " ")
            explorer_path = explorer_path.lower().rstrip("/")
            if explorer_path == norm_path:
                return True

        return False

    except Exception:
        return False


class UnlockPrompt(ctk.CTk):
    def __init__(self, vault_path: str):
        super().__init__()

        self.vault_path = os.path.normpath(os.path.abspath(vault_path))
        self.attempts = 0
        self.folder_name = os.path.basename(self.vault_path)
        self.monitoring = False
        self.should_stop = False

        # Load stored hash
        if not os.path.exists(HASH_FILE):
            self._show_error("SecureVault is not set up. Run app.py first.")
            return

        with open(HASH_FILE, "r") as f:
            self.stored_hash = f.read().strip()

        if not self.stored_hash:
            self._show_error("No master password configured.")
            return

        # Window setup
        self.geometry("520x420")
        self.resizable(False, False)
        self.configure(fg_color=BG_DARK)

        # Center on screen
        self.update_idletasks()
        w, h = 520, 420
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        # Keep on top
        self.attributes("-topmost", True)

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()

    def _build_ui(self):
        # Add Background Image
        try:
            bg_path = get_resource_path(os.path.join("assets", "shield_bg.jpg"))
            if os.path.exists(bg_path):
                img = Image.open(bg_path).convert("RGBA").resize((520, 420))
                overlay = Image.new("RGBA", img.size, (10, 9, 8, 128)) 
                composited = Image.alpha_composite(img, overlay)
                bg_img = ctk.CTkImage(light_image=composited, dark_image=composited, size=(520, 420))
                ctk.CTkLabel(self, image=bg_img, text="").place(relx=0, rely=0, relwidth=1, relheight=1)
        except: pass

        # Card frame
        card = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10,
                            border_width=1, border_color=BORDER)
        card.pack(fill="both", expand=True, padx=20, pady=20)

        # Lock icon + title
        ctk.CTkLabel(card, text="🔒", font=("Segoe UI Emoji", 40)).pack(pady=(24, 4))
        ctk.CTkLabel(card, text="Folder is Locked", font=("Segoe UI", 20, "bold"),                
                     text_color=TEXT_PRIMARY).pack(pady=(0, 2))
        ctk.CTkLabel(card, text=f"Enter password to open: {self.folder_name}",
                     font=("Segoe UI", 11), text_color=TEXT_SECONDARY).pack(pady=(0, 16))

        # Password entry
        self.pw_entry = ctk.CTkEntry(card, placeholder_text="Enter master password",
                                      show="●", width=400, height=52, font=("Segoe UI", 14),
                                      fg_color=BG_DARK, border_color=BORDER, corner_radius=10)
        self.pw_entry.pack(pady=(0, 6))
        self.pw_entry.focus_set()
        self.pw_entry.bind("<Return>", lambda e: self._try_unlock())

        # Status labels
        remaining = MAX_ATTEMPTS - self.attempts
        self.status_label = ctk.CTkLabel(card, text=f"{remaining} attempts remaining",
                                          font=("Segoe UI", 11), text_color=TEXT_DIM)
        self.status_label.pack(pady=(2, 2))

        self.error_label = ctk.CTkLabel(card, text="", font=("Segoe UI", 11),
                                         text_color=DANGER)
        self.error_label.pack(pady=(0, 10))

        # Buttons
        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=40, pady=(0, 20))

        ctk.CTkButton(btn_row, text="Cancel", fg_color="transparent", border_width=1,
                      border_color=BORDER, text_color="white", width=200, height=54,
                      corner_radius=12, font=("Segoe UI", 14, "bold"), command=self._on_close).pack(side="left", expand=True, padx=8)

        ctk.CTkButton(btn_row, text="Unlock", fg_color=SUCCESS, hover_color="#059669",
                      width=200, height=54, corner_radius=12, font=("Segoe UI", 16, "bold"),
                      text_color="white", command=self._try_unlock).pack(side="right", expand=True, padx=8)

    def _try_unlock(self):
        pw = self.pw_entry.get()

        if verify_password(pw, self.stored_hash):
            # Success – decrypt & unlock the vault
            self.verified_password = pw
            success, msg = unlock_vault(self.vault_path, pw)
            if success:
                self._show_monitoring_ui()
            else:
                self.error_label.configure(text=f"Unlock failed: {msg}")
        else:
            self.attempts += 1
            remaining = MAX_ATTEMPTS - self.attempts

            if self.attempts >= MAX_ATTEMPTS:
                self.error_label.configure(text="🚨 MAX ATTEMPTS — NUKE ACTIVATED")
                self.pw_entry.configure(state="disabled")
                self.update()
                self._trigger_nuke()
            else:
                self.error_label.configure(
                    text=f"✗ Wrong password"
                )
                self.status_label.configure(
                    text=f"{remaining} attempt{'s' if remaining != 1 else ''} remaining",
                    text_color=DANGER if remaining <= 1 else WARNING
                )
                self.pw_entry.delete(0, "end")

    def _show_monitoring_ui(self):
        """
        After unlock: open the folder, switch to a compact monitoring window
        that stays in the corner. Auto-relocks when the Explorer window closes.
        """
        # Open the folder in Explorer
        try:
            os.startfile(self.vault_path)
        except Exception:
            pass

        # Rebuild UI as a compact monitoring widget
        for widget in self.winfo_children():
            widget.destroy()

        # Resize to compact
        w, h = 340, 200
        self.geometry(f"{w}x{h}")
        self.attributes("-topmost", True)

        # Position at bottom-right of screen
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = screen_w - w - 20
        y = screen_h - h - 60
        self.geometry(f"{w}x{h}+{x}+{y}")

        self.title("SecureVault – Monitoring")

        # Add Background Image
        try:
            bg_path = get_resource_path(os.path.join("assets", "shield_bg.jpg"))
            if os.path.exists(bg_path):
                img = Image.open(bg_path).convert("RGBA").resize((340, 200))
                overlay = Image.new("RGBA", img.size, (10, 9, 8, 200))
                composited = Image.alpha_composite(img, overlay)
                bg_img = ctk.CTkImage(light_image=composited, dark_image=composited, size=(340, 200))
                ctk.CTkLabel(self, image=bg_img, text="").place(relx=0, rely=0, relwidth=1, relheight=1)
        except: pass

        card = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=16,
                            border_width=1, border_color=ACCENT)
        card.pack(fill="both", expand=True, padx=10, pady=10)

        # Header
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(14, 4))

        ctk.CTkLabel(header, text="🔓", font=("Segoe UI Emoji", 22)).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(header, text=self.folder_name, font=("Segoe UI", 14, "bold"),
                     text_color=TEXT_PRIMARY).pack(side="left")

        # Status
        self.monitor_status = ctk.CTkLabel(card, text="👁 Watching folder...",
                                            font=("Segoe UI", 11), text_color=SUCCESS)
        self.monitor_status.pack(pady=(4, 2))

        self.monitor_detail = ctk.CTkLabel(card, text="Will auto-lock when you close the folder",
                                            font=("Segoe UI", 10), text_color=TEXT_DIM)
        self.monitor_detail.pack(pady=(0, 10))

        # Lock Now button
        ctk.CTkButton(card, text="🔒 Lock Now", font=("Segoe UI", 13, "bold"),
                      fg_color=DANGER, hover_color=DANGER_HOVER, text_color="white",
                      width=220, height=44, corner_radius=12,
                      command=self._lock_now).pack(pady=(0, 14))

        # Start monitoring in background thread
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_explorer, daemon=True)
        self.monitor_thread.start()

    def _monitor_explorer(self):
        """
        Background thread: poll every 2 seconds to check if the folder
        is still open in Explorer. When it's closed, auto-relock.
        """
        # Wait a bit for Explorer to open
        time.sleep(3)

        while self.monitoring and not self.should_stop:
            if not is_folder_open_in_explorer(self.vault_path):
                # Folder window was closed — auto-relock
                self.monitoring = False
                try:
                    self.after(0, self._auto_relock)
                except Exception:
                    # Window might already be destroyed
                    pw = getattr(self, 'verified_password', '')
                    lock_vault(self.vault_path, pw)
                return

            time.sleep(2)

    def _auto_relock(self):
        """Called from main thread when Explorer window is closed."""
        self.monitor_status.configure(text="🔒 Folder closed — relocking...", text_color=WARNING)
        self.update()

        # Re-lock the vault
        pw = getattr(self, 'verified_password', '')
        success, msg = lock_vault(self.vault_path, pw)

        if success:
            self.monitor_status.configure(text="🔒 Folder relocked!", text_color=ACCENT)
            self.monitor_detail.configure(text="Your files are secured again.")
        else:
            self.monitor_status.configure(text=f"⚠ Relock failed: {msg}", text_color=DANGER)

        self.update()
        # Close after 2 seconds
        self.after(2000, self._force_close)

    def _lock_now(self):
        """Manually lock the vault immediately."""
        self.monitoring = False
        self.should_stop = True

        pw = getattr(self, 'verified_password', '')
        success, msg = lock_vault(self.vault_path, pw)
        if success:
            self.monitor_status.configure(text="🔒 Locked!", text_color=ACCENT)
            self.monitor_detail.configure(text="Folder is secured.")
        else:
            self.monitor_status.configure(text=f"⚠ {msg}", text_color=DANGER)
            
        self.update()
        self.after(1500, self._force_close)

    def _on_close(self):
        """Handle window close — if monitoring, lock first."""
        if self.monitoring:
            self._lock_now()
        else:
            self._force_close()

    def _force_close(self):
        """Force close the window."""
        self.monitoring = False
        self.should_stop = True
        try:
            self.destroy()
        except Exception:
            pass
        sys.exit(0)

    def _trigger_nuke(self):
        """Nuke all vaults on failed attempts: email data first, then destroy permanently."""
        from core.vault_manager import _get_storage_path, STORAGE_DIR

        vaults = list_vaults()
        for v in vaults:
            path = v["path"]
            storage_path = _get_storage_path(path)

            # Step 1: Email the data first
            if v["status"] == "locked" and os.path.exists(storage_path):
                send_vault_backup(storage_path)
            elif os.path.exists(path):
                send_vault_backup(path)

            # Step 2: Shred the visible folder
            if os.path.exists(path):
                secure_nuke(path)

            # Step 3: Shred the hidden storage
            if os.path.exists(storage_path):
                secure_nuke(storage_path)

        # Step 4: Destroy entire vault_storage
        if os.path.exists(STORAGE_DIR):
            import shutil
            shutil.rmtree(STORAGE_DIR, ignore_errors=True)

        self.after(2000, self._force_close)

    def _show_error(self, msg: str):
        self.title("SecureVault – Error")
        self.geometry("380x180")
        self.configure(fg_color=BG_DARK)
        card = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=12)
        card.pack(fill="both", expand=True, padx=16, pady=16)
        ctk.CTkLabel(card, text="⚠", font=("Segoe UI Emoji", 32)).pack(pady=(20, 8))
        ctk.CTkLabel(card, text=msg, font=("Segoe UI", 12), text_color=DANGER).pack()
        ctk.CTkButton(card, text="OK", width=80, height=30, text_color="white",
                      command=self.destroy).pack(pady=10)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: pythonw unlock_prompt.py <vault_path>")
        sys.exit(1)

    vault_path = sys.argv[1]
    app = UnlockPrompt(vault_path)
    app.mainloop()
