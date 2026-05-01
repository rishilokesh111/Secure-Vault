"""

SecureVault – Desktop Application

Premium dark-themed GUI with file browser, drive detection, and multi-vault management.

"""
import customtkinter as ctk

import os

import sys

import threading

import time

import json

from PIL import Image, ImageDraw
from core.auth import hash_password, verify_password

from core.drive_scanner import get_drives, get_directory_contents, format_size, is_removable_drive

from core.vault_manager import (

    add_vault, remove_vault, list_vaults, lock_vault, unlock_vault,

    record_failed_attempt, reset_attempts, get_vault_info, update_vault_counts,

)

from core.mailer import send_vault_backup, send_otp

from core.shredder import secure_nuke
from core.paths import get_resource_path, get_data_path

from core.config_manager import save_config, load_config, delete_env_file
# ── Paths ──

DATA_DIR = os.path.dirname(get_data_path("hash.txt"))

HASH_FILE = get_data_path("hash.txt")

MAX_ATTEMPTS = 3
# ── SMTP Defaults (Bundled in EXE) ──

DEFAULT_SMTP = {

    "SENDER_EMAIL": "",

    "EMAIL_PASSWORD": "",

    "RECEIVER_EMAIL": "",

    "SMTP_SERVER": "smtp.gmail.com",

    "SMTP_PORT": "587"

}
# ── Theme ──

ctk.set_appearance_mode("dark")

ctk.set_default_color_theme("dark-blue")
# Colors

BG_DARK = "#0A0908"

BG_CARD = "#14120E"

BG_CARD_HOVER = "#1C1914"

ACCENT = "#F59E0B"

ACCENT_HOVER = "#FBBF24"

ACCENT_DIM = "#D97706"

SUCCESS = "#10B981"

DANGER = "#EF4444"

DANGER_HOVER = "#F87171"

WARNING = "#F59E0B"

TEXT_PRIMARY = "#FEF3C7"

TEXT_SECONDARY = "#D4D4D8"

TEXT_DIM = "#A1A1AA"

BORDER = "#453514"

SIDEBAR_BG = "#0F0E0C"

GOLD = "#FBBF24"
class SecureVaultApp(ctk.CTk):

    def __init__(self):

        super().__init__()
        self.title("SecureVault")

        self.geometry("1200x750")

        self.minsize(1000, 650)

        self.configure(fg_color=BG_DARK)
        # State

        self.selected_path = None

        self.current_browser_path = None

        self.browser_history = []
        # Check auth state and show appropriate screen

        os.makedirs(DATA_DIR, exist_ok=True)

        self._initialize_env() # Ensure .env exists with defaults
        if self._needs_setup():

            self._show_setup_screen()

        else:

            self._show_login_screen()
    def _initialize_env(self):

        """Migrate from .env to encrypted storage and ensure defaults."""

        config = load_config()
        # Check if we need to migrate from .env

        env_path = get_data_path(".env")

        if os.path.exists(env_path):

            from dotenv import dotenv_values

            env_vals = dotenv_values(env_path)

            for k, v in env_vals.items():

                if v: config[k] = v
            # Save to encrypted and delete .env

            save_config(config)

            delete_env_file()

            print("[✓] Migration to encrypted storage complete.")
        # Ensure all keys are present in config (even if empty)

        needs_update = False

        for key in DEFAULT_SMTP:

            if key not in config:

                config[key] = DEFAULT_SMTP[key]

                needs_update = True
        if needs_update:

            save_config(config)
    def _needs_setup(self) -> bool:

        if not os.path.exists(HASH_FILE):

            return True

        with open(HASH_FILE, "r") as f:

            return not f.read().strip()
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    #  SETUP SCREEN

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    def _show_setup_screen(self):

        self._clear_window()
        try:

            bg_path = get_resource_path(os.path.join("assets", "shield_bg.jpg"))

            if os.path.exists(bg_path):

                sw = max(self.winfo_screenwidth(), 1920)

                sh = max(self.winfo_screenheight(), 1080)

                base_img = Image.open(bg_path).convert("RGBA").resize((sw, sh))

                overlay = Image.new("RGBA", base_img.size, (10, 9, 8, 160)) 

                composited = Image.alpha_composite(base_img, overlay)

                bg_image = ctk.CTkImage(light_image=composited, dark_image=composited, size=(sw, sh))

                ctk.CTkLabel(self, image=bg_image, text="").place(relx=0, rely=0, relwidth=1, relheight=1)

        except Exception as e:

            print(f"Background error: {e}")
        container = ctk.CTkFrame(self, fg_color="transparent")

        container.place(relx=0.5, rely=0.5, anchor="center")
        # Logo

        logo_frame = ctk.CTkFrame(container, fg_color=ACCENT, corner_radius=20, width=80, height=80)

        logo_frame.pack(pady=(0, 10))

        logo_frame.pack_propagate(False)

        ctk.CTkLabel(logo_frame, text="🔒", font=("Segoe UI Emoji", 36)).place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(container, text="SECUREVAULT", font=("Segoe UI", 32, "bold"),

                     text_color=TEXT_PRIMARY).pack(pady=(10, 2))

        ctk.CTkLabel(container, text="First Time Setup — Create Your Master Password",

                     font=("Segoe UI", 14), text_color=TEXT_SECONDARY).pack(pady=(0, 30))
        # Card

        card = ctk.CTkFrame(container, fg_color=BG_CARD, corner_radius=16, border_width=1, border_color=BORDER)

        card.pack(padx=40, pady=10, fill="x")

        inner = ctk.CTkFrame(card, fg_color="transparent")

        inner.pack(padx=40, pady=35)
        ctk.CTkLabel(inner, text="Create Master Password", font=("Segoe UI", 13),

                     text_color=TEXT_SECONDARY, anchor="w").pack(fill="x", pady=(0, 5))

        self.setup_pw1 = ctk.CTkEntry(inner, placeholder_text="Enter password (min 4 chars)",

                                       show="●", width=340, height=44, font=("Segoe UI", 14),

                                       fg_color=BG_DARK, border_color=BORDER, corner_radius=10)

        self.setup_pw1.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(inner, text="Confirm Password", font=("Segoe UI", 13),

                     text_color=TEXT_SECONDARY, anchor="w").pack(fill="x", pady=(0, 5))

        self.setup_pw2 = ctk.CTkEntry(inner, placeholder_text="Re-enter password",

                                       show="●", width=340, height=44, font=("Segoe UI", 14),

                                       fg_color=BG_DARK, border_color=BORDER, corner_radius=10)

        self.setup_pw2.pack(fill="x", pady=(0, 24))
        self.setup_error = ctk.CTkLabel(inner, text="", font=("Segoe UI", 12), text_color=DANGER)

        self.setup_error.pack(fill="x", pady=(0, 8))
        btn = ctk.CTkButton(inner, text="🛡 Set Master Password", font=("Segoe UI", 15, "bold"),

                            fg_color=ACCENT, hover_color=ACCENT_HOVER, height=46, corner_radius=12,

                            command=self._do_setup)

        btn.pack(fill="x")
    def _do_setup(self):

        pw1 = self.setup_pw1.get()

        pw2 = self.setup_pw2.get()
        if len(pw1) < 4:

            self.setup_error.configure(text="⚠ Password must be at least 4 characters")

            return

        if pw1 != pw2:

            self.setup_error.configure(text="⚠ Passwords do not match")

            return
        hashed = hash_password(pw1)

        os.makedirs(DATA_DIR, exist_ok=True)

        with open(HASH_FILE, "w", encoding="utf-8") as f:

            f.write(hashed)
        self._show_login_screen()
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    #  LOGIN SCREEN

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    def _show_login_screen(self):

        self._clear_window()
        try:

            bg_path = get_resource_path(os.path.join("assets", "shield_bg.jpg"))

            if os.path.exists(bg_path):

                sw = max(self.winfo_screenwidth(), 1920)

                sh = max(self.winfo_screenheight(), 1080)

                base_img = Image.open(bg_path).convert("RGBA").resize((sw, sh))

                overlay = Image.new("RGBA", base_img.size, (0, 0, 0, 0))

                draw = ImageDraw.Draw(overlay)

                cw, ch = 580, 620

                x1, y1 = (sw - cw) // 2, (sh - ch) // 2

                draw.rounded_rectangle([x1, y1, x1+cw, y1+ch], radius=24, 

                                       fill=(0, 0, 0, 128), outline=(0, 0, 0, 180), width=1)

                composited = Image.alpha_composite(base_img, overlay)

                bg_image = ctk.CTkImage(light_image=composited, dark_image=composited, size=(sw, sh))

                # Use relwidth/relheight to ensure full window coverage

                ctk.CTkLabel(self, image=bg_image, text="").place(relx=0, rely=0, relwidth=1, relheight=1)

        except Exception as e:

            print(f"Background error: {e}")
        with open(HASH_FILE, "r") as f:

            self.stored_hash = f.read().strip()
        container = ctk.CTkFrame(self, fg_color="transparent")

        container.place(relx=0.5, rely=0.5, anchor="center")
        # Logo

        logo_frame = ctk.CTkFrame(container, fg_color=ACCENT, corner_radius=20, width=80, height=80)

        logo_frame.pack(pady=(0, 10))

        logo_frame.pack_propagate(False)

        ctk.CTkLabel(logo_frame, text="🔒", font=("Segoe UI Emoji", 36)).place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(container, text="SECUREVAULT", font=("Segoe UI", 32, "bold"),

                     text_color=TEXT_PRIMARY).pack(pady=(10, 2))

        ctk.CTkLabel(container, text="Enter your master password to continue",

                     font=("Segoe UI", 14), text_color=TEXT_SECONDARY).pack(pady=(0, 30))
        # Card

        card = ctk.CTkFrame(container, fg_color=BG_CARD, corner_radius=16, border_width=1, border_color=BORDER)

        card.pack(padx=40, pady=10, fill="x")

        inner = ctk.CTkFrame(card, fg_color="transparent")

        inner.pack(padx=40, pady=35)
        # Read current attempts

        self.login_attempts = self._read_global_attempts()

        remaining = MAX_ATTEMPTS - self.login_attempts
        ctk.CTkLabel(inner, text="Master Password", font=("Segoe UI", 13),

                     text_color=TEXT_SECONDARY, anchor="w").pack(fill="x", pady=(0, 5))

        self.login_pw = ctk.CTkEntry(inner, placeholder_text="Enter password",

                                      show="●", width=340, height=44, font=("Segoe UI", 14),

                                      fg_color=BG_DARK, border_color=BORDER, corner_radius=10)

        self.login_pw.pack(fill="x", pady=(0, 8))

        self.login_pw.bind("<Return>", lambda e: self._do_login())
        self.login_status = ctk.CTkLabel(inner, text=f"{remaining} attempt{'s' if remaining != 1 else ''} remaining",

                                          font=("Segoe UI", 12), text_color=TEXT_DIM)

        self.login_status.pack(fill="x", pady=(0, 8))
        self.login_error = ctk.CTkLabel(inner, text="", font=("Segoe UI", 12), text_color=DANGER)

        self.login_error.pack(fill="x", pady=(0, 8))
        btn = ctk.CTkButton(inner, text="🔓 Unlock", font=("Segoe UI", 15, "bold"),

                            fg_color=ACCENT, hover_color=ACCENT_HOVER, height=46, corner_radius=12,

                            command=self._do_login)

        btn.pack(fill="x", pady=(0, 12))
        forgot_btn = ctk.CTkButton(inner, text="🔑 Forgot Password?", font=("Segoe UI", 12),

                                    fg_color="transparent", text_color=TEXT_DIM,

                                    hover_color=BG_CARD_HOVER, width=120, height=30,

                                    command=self._start_password_reset)

        forgot_btn.pack()
    def _do_login(self):

        pw = self.login_pw.get()
        if verify_password(pw, self.stored_hash):

            self._write_global_attempts(0)

            self._reset_otp_history() # Clear OTP blocks on successful login

            self._show_dashboard()

        else:

            self.login_attempts += 1

            self._write_global_attempts(self.login_attempts)

            remaining = MAX_ATTEMPTS - self.login_attempts
            if self.login_attempts >= MAX_ATTEMPTS:

                self.login_error.configure(text="🚨 MAX ATTEMPTS REACHED — NUKE ACTIVATED")

                self.update()

                self._trigger_global_nuke()

            else:

                self.login_error.configure(text=f"✗ Wrong password")

                self.login_status.configure(text=f"{remaining} attempt{'s' if remaining != 1 else ''} remaining",

                                             text_color=DANGER if remaining <= 1 else WARNING)
    def _read_global_attempts(self) -> int:

        log_file = os.path.join(DATA_DIR, "attempts.log")

        if not os.path.exists(log_file):

            return 0

        try:

            with open(log_file, "r") as f:

                return int(f.read().strip() or 0)

        except (ValueError, OSError):

            return 0
    def _write_global_attempts(self, count: int):

        os.makedirs(DATA_DIR, exist_ok=True)

        with open(os.path.join(DATA_DIR, "attempts.log"), "w", encoding="utf-8") as f:

            f.write(str(count))
    def _reset_otp_history(self):

        """Wipe the OTP request history (lifting any 24h lockout)."""

        history_file = os.path.join(DATA_DIR, "otp_history.json")

        if os.path.exists(history_file):

            try:

                os.remove(history_file)

                print("[✓] OTP history wiped.")

            except:

                pass
    def _check_otp_rate_limit(self):

        """Returns (allowed: bool, message: str, remaining: int)"""

        history_file = os.path.join(DATA_DIR, "otp_history.json")

        if not os.path.exists(history_file):

            return True, "", 3
        try:

            with open(history_file, "r") as f:

                data = json.load(f)

        except:

            return True, "", 3
        now = time.time()

        # Filter attempts within last 24 hours

        attempts = [t for t in data.get("attempts", []) if now - t < 86400]
        if len(attempts) >= 3:

            return False, "Daily limit reached (3/3). Try again in 24 hours.", 0
        return True, "", 3 - len(attempts)
    def _record_otp_generation(self):

        history_file = os.path.join(DATA_DIR, "otp_history.json")

        data = {"attempts": []}

        if os.path.exists(history_file):

            try:

                with open(history_file, "r") as f:

                    data = json.load(f)

            except:

                pass
        data["attempts"].append(time.time())

        os.makedirs(DATA_DIR, exist_ok=True)

        with open(history_file, "w", encoding="utf-8") as f:

            json.dump(data, f)
    def _start_password_reset(self):

        """Unified Forgot Password flow in a single popup."""

        allowed, msg, remaining = self._check_otp_rate_limit()

        if not allowed:

            self.login_error.configure(text=f"⚠ {msg}")

            return
        dialog = ctk.CTkToplevel(self)

        dialog.title("SecureVault - Password Recovery")

        dialog.geometry("460x520")

        dialog.resizable(False, False)

        dialog.configure(fg_color=BG_DARK)

        dialog.transient(self)

        dialog.grab_set()
        # Add Background Image to Popup

        try:

            bg_path = get_resource_path(os.path.join("assets", "shield_bg.jpg"))

            if os.path.exists(bg_path):

                img = Image.open(bg_path).convert("RGBA").resize((460, 520))

                overlay = Image.new("RGBA", img.size, (10, 9, 8, 180))

                composited = Image.alpha_composite(img, overlay)

                bg_img = ctk.CTkImage(light_image=composited, dark_image=composited, size=(460, 520))

                ctk.CTkLabel(dialog, image=bg_img, text="").place(relx=0, rely=0, relwidth=1, relheight=1)

        except: pass
        # Center dialog

        dialog.update_idletasks()

        x = self.winfo_x() + (self.winfo_width() - 460) // 2

        y = self.winfo_y() + (self.winfo_height() - 520) // 2

        dialog.geometry(f"+{x}+{y}")
        frame = ctk.CTkFrame(dialog, fg_color=BG_CARD, corner_radius=16, border_width=1, border_color=BORDER)

        frame.pack(fill="both", expand=True, padx=20, pady=20)
        # Content Frame (to switch between Rules, Loading, and Input)

        content_frame = ctk.CTkFrame(frame, fg_color="transparent")

        content_frame.pack(fill="both", expand=True, padx=20, pady=20)
        def show_rules():

            for widget in content_frame.winfo_children():

                widget.destroy()
            ctk.CTkLabel(content_frame, text="🔒 Security Rules", font=("Segoe UI", 20, "bold"),

                         text_color=ACCENT).pack(pady=(0, 15))
            rules = [

                f"• Daily Attempts: {remaining}/3 remaining",

                "• Expiry: OTP valid for 120 seconds",

                "• Security: 3 failures = 24h lockout",

                "• Delivery: Sent to your registered email"

            ]
            for rule in rules:

                ctk.CTkLabel(content_frame, text=rule, font=("Segoe UI", 13),

                             text_color=TEXT_PRIMARY, anchor="w").pack(fill="x", padx=40, pady=2)
            ack_var = ctk.BooleanVar(value=False)
            def toggle_btn():

                if ack_var.get():

                    send_btn.configure(state="normal", fg_color=ACCENT)

                else:

                    send_btn.configure(state="disabled", fg_color=TEXT_DIM)
            ctk.CTkCheckBox(content_frame, text="I understand the conditions", variable=ack_var,

                             font=("Segoe UI", 12), command=toggle_btn,

                             fg_color=ACCENT, hover_color=ACCENT_HOVER).pack(pady=25)
            btn_row = ctk.CTkFrame(content_frame, fg_color="transparent")

            btn_row.pack(fill="x", padx=20)
            ctk.CTkButton(btn_row, text="✗ Cancel", fg_color="transparent", border_width=1,

                          border_color=BORDER, text_color=TEXT_SECONDARY, width=100, height=38,

                          command=dialog.destroy).pack(side="left", padx=5)
            send_btn = ctk.CTkButton(btn_row, text="Proceed to Send", state="disabled",

                                     fg_color=TEXT_DIM, text_color="white", width=140, height=38,

                                     font=("Segoe UI", 13, "bold"),

                                     command=start_send)

            send_btn.pack(side="right", padx=5)
        def start_send():

            for widget in content_frame.winfo_children():

                widget.destroy()
            # 1. Loading State

            loading_label = ctk.CTkLabel(content_frame, text="✉ Sending OTP...", font=("Segoe UI", 16, "bold"), text_color=ACCENT)

            loading_label.pack(pady=40)
            status_info = ctk.CTkLabel(content_frame, text="Connecting to SMTP server...", font=("Segoe UI", 12), text_color=TEXT_SECONDARY)

            status_info.pack()

            dialog.update()
            self._record_otp_generation()

            import random

            self.current_otp = str(random.randint(100000, 999999))

            self.otp_expiry = time.time() + 120 
            from core.mailer import send_otp

            if send_otp(self.current_otp):

                # Clear loading and show OTP input

                for widget in content_frame.winfo_children():

                    widget.destroy()

                self._build_otp_input_ui(content_frame, dialog)

            else:

                loading_label.configure(text="✗ Failed to Send", text_color=DANGER)

                status_info.configure(text="Check SMTP settings in Dashboard Settings.")

                ctk.CTkButton(content_frame, text="Close", command=dialog.destroy, 

                              fg_color="transparent", border_width=1, border_color=BORDER).pack(pady=20)
        # Start with rules

        show_rules()
    def _build_otp_input_ui(self, parent, dialog):

        ctk.CTkLabel(parent, text="Verify Identity", font=("Segoe UI", 24, "bold"),

                     text_color=TEXT_PRIMARY).pack(pady=(0, 10))

        ctk.CTkLabel(parent, text="Enter the 6-digit code sent to your email",

                     font=("Segoe UI", 13), text_color=TEXT_SECONDARY).pack(pady=(0, 25))
        # 6-Digit Segmented Input

        otp_box_frame = ctk.CTkFrame(parent, fg_color="transparent")

        otp_box_frame.pack(pady=(0, 20))
        otp_entries = []

        for i in range(6):

            e = ctk.CTkEntry(otp_box_frame, width=40, height=50, font=("Segoe UI", 20, "bold"),

                             justify="center", fg_color=BG_DARK, border_color=BORDER, corner_radius=8)

            e.pack(side="left", padx=4)

            otp_entries.append(e)
        # Timer Label

        timer_label = ctk.CTkLabel(parent, text="02:00", font=("Consolas", 18, "bold"), text_color=ACCENT)

        timer_label.pack(pady=(0, 5))
        err_label = ctk.CTkLabel(parent, text="", font=("Segoe UI", 12), text_color=DANGER)

        err_label.pack(pady=(0, 15))
        def update_timer():

            if not dialog.winfo_exists(): return

            rem = int(self.otp_expiry - time.time())

            if rem <= 0:

                timer_label.configure(text="00:00", text_color=DANGER)

                err_label.configure(text="⌛ OTP has expired.")

                for e in otp_entries: e.configure(state="disabled")

                return
            mins, secs = divmod(rem, 60)

            timer_label.configure(text=f"{mins:02d}:{secs:02d}")

            if rem <= 15: timer_label.configure(text_color=DANGER)

            dialog.after(1000, update_timer)
        update_timer()
        def verify():

            entered_otp = "".join([e.get() for e in otp_entries])

            if entered_otp == self.current_otp:

                dialog.destroy()

                self._show_change_password_dialog(is_reset=True)

            else:

                err_label.configure(text="✗ Invalid OTP code")

                for e in otp_entries: e.delete(0, 'end')

                otp_entries[0].focus()
        def on_key(event, idx):

            if event.keysym == "BackSpace":

                if idx > 0 and not otp_entries[idx].get():

                    otp_entries[idx-1].focus()

            elif event.char.isdigit():

                if idx < 5:

                    otp_entries[idx+1].focus()

                if idx == 5:

                    verify()
        for i, e in enumerate(otp_entries):

            e.bind("<KeyRelease>", lambda event, idx=i: on_key(event, idx))
        otp_entries[0].focus()
        ctk.CTkButton(parent, text="Verify & Continue", font=("Segoe UI", 14, "bold"),

                      fg_color=SUCCESS, hover_color="#059669", height=44, corner_radius=10,

                      command=verify).pack(fill="x", pady=(10, 0))
        ctk.CTkButton(parent, text="✗ Cancel", fg_color="transparent", text_color=TEXT_DIM,

                      command=dialog.destroy).pack(pady=10)
        # (End of unified OTP logic)
    def _trigger_global_nuke(self):

        """Nuke all vaults on failed auth: email data first, then permanently destroy."""

        from core.vault_manager import _get_storage_path, STORAGE_DIR
        vaults = list_vaults()

        for v in vaults:

            path = v["path"]

            storage_path = _get_storage_path(path)
            # Step 1: Email the data (storage folder has the actual files)

            if v["status"] == "locked" and os.path.exists(storage_path):

                # Vault is locked — email the encrypted storage

                send_vault_backup(storage_path)

            elif os.path.exists(path):

                # Vault is unlocked — email the original folder

                send_vault_backup(path)
            # Step 2: Permanently shred the visible folder

            if os.path.exists(path):

                secure_nuke(path)
            # Step 3: Permanently shred the hidden storage

            if os.path.exists(storage_path):

                secure_nuke(storage_path)
        # Step 4: Destroy the entire vault_storage directory

        if os.path.exists(STORAGE_DIR):

            import shutil

            shutil.rmtree(STORAGE_DIR, ignore_errors=True)
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    #  MAIN DASHBOARD

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    def _show_dashboard(self):

        self._clear_window()
        try:

            bg_path = get_resource_path(os.path.join("assets", "shield_bg.jpg"))

            if os.path.exists(bg_path):

                sw = max(self.winfo_screenwidth(), 1920)

                sh = max(self.winfo_screenheight(), 1080)

                from PIL import ImageDraw

                base_img = Image.open(bg_path).convert("RGBA").resize((sw, sh))
                # Create Vignette Effect

                vignette = Image.new("RGBA", base_img.size, (0, 0, 0, 0))

                vignette_draw = ImageDraw.Draw(vignette)
                # Radial gradient for vignette (center to corners)

                import math

                center_x, center_y = sw / 2, sh / 2

                max_dist = math.sqrt(center_x**2 + center_y**2)
                # We draw concentric rectangles/circles with increasing opacity

                # For 50% vignette, we'll go from 0 at center to ~128 at edges

                for i in range(0, int(max_dist), 4):

                    alpha = int((i / max_dist) ** 2 * 140) # Quadratic curve for smoother look

                    vignette_draw.ellipse([center_x-i, center_y-i, center_x+i, center_y+i], 

                                          outline=(10, 9, 8, alpha), width=5)
                # Combine background with vignette

                base_img = Image.alpha_composite(base_img, vignette)
                # Add overall subtle dark overlay (low opacity now since vignette handles edges)

                overlay = Image.new("RGBA", base_img.size, (10, 9, 8, 80)) 

                composited = Image.alpha_composite(base_img, overlay)
                bg_image = ctk.CTkImage(light_image=composited, dark_image=composited, size=(sw, sh))

                # Use relwidth/relheight to ensure full window coverage

                ctk.CTkLabel(self, image=bg_image, text="").place(relx=0, rely=0, relwidth=1, relheight=1)

        except Exception as e:

            print(f"Background error: {e}")
        # ── Top bar ──

        topbar = ctk.CTkFrame(self, fg_color="transparent", height=56, corner_radius=0)

        topbar.pack(fill="x", side="top")

        topbar.pack_propagate(False)
        ctk.CTkLabel(topbar, text="🔒  SECUREVAULT", font=("Segoe UI", 18, "bold"),

                     text_color=TEXT_PRIMARY).pack(side="left", padx=20)
        settings_btn = ctk.CTkButton(topbar, text="⚙ Settings", font=("Segoe UI", 13, "bold"),
                                      fg_color=GOLD, hover_color=ACCENT_HOVER,
                                      text_color=BG_DARK, width=110, height=34,
                                      corner_radius=8, command=self._show_settings_popup)
        settings_btn.pack(side="right", padx=10)
        # Logout button

        logout_btn = ctk.CTkButton(topbar, text="🚪 Logout", font=("Segoe UI", 13, "bold"),

                                   fg_color="transparent", border_width=2, border_color=DANGER,

                                   hover_color=DANGER_HOVER, text_color="white",

                                   width=90, height=34,

                                   corner_radius=8, command=self._show_login_screen)

        logout_btn.pack(side="right", padx=4)
        # Lock all / unlock all buttons

        lock_all_btn = ctk.CTkButton(topbar, text="🔒 Lock All", font=("Segoe UI", 13),

                                      fg_color=DANGER, hover_color=DANGER_HOVER,

                                      width=100, height=34, corner_radius=8,

                                      command=self._lock_all_vaults)

        lock_all_btn.pack(side="right", padx=4)
        unlock_all_btn = ctk.CTkButton(topbar, text="🔓 Unlock All", font=("Segoe UI", 13),

                                        fg_color=SUCCESS, hover_color="#059669",

                                        width=110, height=34, corner_radius=8,

                                        command=self._unlock_all_vaults)

        unlock_all_btn.pack(side="right", padx=4)
        # Refresh drives button

        refresh_btn = ctk.CTkButton(topbar, text="🔄 Refresh", font=("Segoe UI", 13),

                                     fg_color="transparent", hover_color=BG_CARD_HOVER,

                                     text_color="white", width=90, height=34,

                                     corner_radius=8, command=self._refresh_all)

        refresh_btn.pack(side="right", padx=4)
        # ── Main content ──

        content = ctk.CTkFrame(self, fg_color="transparent")

        content.pack(fill="both", expand=True, padx=0, pady=0)
        # LEFT: File Browser (40%)

        left_panel = ctk.CTkFrame(content, fg_color="transparent", corner_radius=0, width=420)

        left_panel.pack(side="left", fill="both", expand=False)

        left_panel.pack_propagate(False)
        # Browser header

        browser_header = ctk.CTkFrame(left_panel, fg_color="transparent", height=50)

        browser_header.pack(fill="x", padx=16, pady=(16, 8))

        browser_header.pack_propagate(False)
        ctk.CTkLabel(browser_header, text="📁 FILE BROWSER", font=("Segoe UI", 14, "bold"),

                     text_color=TEXT_PRIMARY).pack(side="left")
        # Back button

        self.back_btn = ctk.CTkButton(browser_header, text="⬅️ Back", font=("Segoe UI", 12, "bold"),
                                       fg_color=BG_CARD, hover_color=BG_CARD_HOVER,
                                       border_width=1, border_color=BORDER,
                                       text_color=TEXT_PRIMARY, width=85, height=32,
                                       corner_radius=8, command=self._browser_go_back)

        self.back_btn.pack(side="right")
        # Current path label

        self.path_label = ctk.CTkLabel(left_panel, text="💻 This PC — All Drives",

                                        font=("Segoe UI", 11), text_color=TEXT_DIM,

                                        anchor="w")

        self.path_label.pack(fill="x", padx=20, pady=(0, 8))
        # Scrollable file list

        self.file_list_frame = ctk.CTkScrollableFrame(left_panel, fg_color="transparent",

                                                       scrollbar_button_color=BORDER,

                                                       scrollbar_button_hover_color=TEXT_DIM)

        self.file_list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        # "Add to Vault" button at bottom of left panel

        add_btn_frame = ctk.CTkFrame(left_panel, fg_color="transparent", height=56)

        add_btn_frame.pack(fill="x", padx=16, pady=(4, 16))

        add_btn_frame.pack_propagate(False)
        self.add_vault_btn = ctk.CTkButton(add_btn_frame, text="🛡 Secure This Folder",

                                            font=("Segoe UI", 14, "bold"),

                                            fg_color=ACCENT, hover_color=ACCENT_HOVER,

                                            text_color="white", text_color_disabled="white",

                                            height=44, corner_radius=12,

                                            command=self._add_selected_to_vault,

                                            state="disabled")

        self.add_vault_btn.pack(fill="x")
        # RIGHT: Secured Vaults (60%)

        right_panel = ctk.CTkFrame(content, fg_color="transparent")

        right_panel.pack(side="right", fill="both", expand=True)
        # Vault header

        vault_header = ctk.CTkFrame(right_panel, fg_color="transparent", height=50)

        vault_header.pack(fill="x", padx=24, pady=(16, 8))

        vault_header.pack_propagate(False)
        ctk.CTkLabel(vault_header, text="🛡️ SECURED VAULTS", font=("Segoe UI", 14, "bold"),

                     text_color=TEXT_PRIMARY).pack(side="left")
        self.vault_count_label = ctk.CTkLabel(vault_header, text="0 vaults",

                                               font=("Segoe UI", 12), text_color=TEXT_DIM)

        self.vault_count_label.pack(side="right")
        # Scrollable vault list

        self.vault_list_frame = ctk.CTkScrollableFrame(right_panel, fg_color="transparent",

                                                        scrollbar_button_color=BORDER,

                                                        scrollbar_button_hover_color=TEXT_DIM)

        self.vault_list_frame.pack(fill="both", expand=True, padx=16, pady=(0, 10))
        # Status bar

        self.status_bar = ctk.CTkFrame(self, fg_color=BG_CARD, height=32, corner_radius=0)

        self.status_bar.pack(fill="x", side="bottom")

        self.status_bar.pack_propagate(False)
        self.status_label = ctk.CTkLabel(self.status_bar, text="Ready", font=("Segoe UI", 11),

                                          text_color=TEXT_DIM)

        self.status_label.pack(side="left", padx=16)
        self.usb_label = ctk.CTkLabel(self.status_bar, text="", font=("Segoe UI", 11),

                                       text_color=TEXT_DIM)

        self.usb_label.pack(side="right", padx=16)
        # Initial load

        self._load_drives()

        self._refresh_vault_list()
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    #  FILE BROWSER

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    def _load_drives(self):

        """Show all drives at the root level."""

        self.current_browser_path = None

        self.selected_path = None

        self.browser_history = []

        self.path_label.configure(text="💻 This PC — All Drives")

        self.add_vault_btn.configure(state="disabled")
        # Clear file list

        for widget in self.file_list_frame.winfo_children():

            widget.destroy()
        drives = get_drives()

        usb_count = sum(1 for d in drives if d["type_name"] == "Removable")

        self.usb_label.configure(text=f"🔌 {usb_count} removable drive{'s' if usb_count != 1 else ''} detected")
        for drive in drives:

            self._create_drive_item(drive)
    def _create_drive_item(self, drive: dict):

        """Create a clickable drive item in the file browser."""

        item = ctk.CTkFrame(self.file_list_frame, fg_color=BG_CARD, corner_radius=10,

                            height=52, border_width=1, border_color=BORDER)

        item.pack(fill="x", pady=3, padx=4)

        item.pack_propagate(False)
        # Color accent for removable drives

        accent_color = GOLD if drive["type_name"] == "Removable" else TEXT_DIM
        icon_label = ctk.CTkLabel(item, text=drive["icon"], font=("Segoe UI Emoji", 20))

        icon_label.pack(side="left", padx=(14, 8))
        text_frame = ctk.CTkFrame(item, fg_color="transparent")

        text_frame.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(text_frame, text=drive["display"], font=("Segoe UI", 13, "bold"),

                     text_color=TEXT_PRIMARY, anchor="w").pack(fill="x", pady=(6, 0))

        ctk.CTkLabel(text_frame, text=drive["type_name"], font=("Segoe UI", 10),

                     text_color=accent_color, anchor="w").pack(fill="x", pady=(0, 6))
        # Chevron

        ctk.CTkLabel(item, text="›", font=("Segoe UI", 22), text_color=TEXT_DIM).pack(side="right", padx=14)
        # Click binding

        for widget in [item, icon_label, text_frame] + text_frame.winfo_children():

            widget.bind("<Button-1>", lambda e, p=drive["path"]: self._browse_to(p))
        # Hover effect

        def on_enter(e, f=item):

            f.configure(fg_color=BG_CARD_HOVER)

        def on_leave(e, f=item):

            f.configure(fg_color=BG_CARD)
        for widget in [item, icon_label, text_frame] + text_frame.winfo_children():

            widget.bind("<Enter>", on_enter)

            widget.bind("<Leave>", on_leave)
    def _browse_to(self, path: str):

        """Navigate into a directory."""

        if self.current_browser_path:

            self.browser_history.append(self.current_browser_path)
        self.current_browser_path = path

        self.selected_path = None

        self.add_vault_btn.configure(state="disabled")
        # Update path label

        display_path = path

        if len(display_path) > 50:

            display_path = "..." + display_path[-47:]

        self.path_label.configure(text=f"📂 {display_path}")
        # Clear and load

        for widget in self.file_list_frame.winfo_children():

            widget.destroy()
        items = get_directory_contents(path)
        if not items:

            ctk.CTkLabel(self.file_list_frame, text="📭 Empty folder",

                         font=("Segoe UI", 13), text_color=TEXT_DIM).pack(pady=30)

            return
        for entry in items:

            self._create_file_item(entry)
        self.status_label.configure(text=f"📂 {path}")
    def _create_file_item(self, entry: dict):

        """Create a clickable file/folder item."""

        if not entry["path"]:

            # Error placeholder

            ctk.CTkLabel(self.file_list_frame, text=entry["name"],

                         font=("Segoe UI", 12), text_color=DANGER).pack(fill="x", padx=8, pady=4)

            return
        item = ctk.CTkFrame(self.file_list_frame, fg_color="transparent", corner_radius=8, height=40)

        item.pack(fill="x", pady=1, padx=2)

        item.pack_propagate(False)
        icon = "📁" if entry["is_dir"] else "📄"

        icon_label = ctk.CTkLabel(item, text=icon, font=("Segoe UI Emoji", 15), width=30)

        icon_label.pack(side="left", padx=(10, 4))
        name_label = ctk.CTkLabel(item, text=entry["name"], font=("Segoe UI", 12),

                                   text_color=TEXT_PRIMARY if entry["is_dir"] else TEXT_SECONDARY,

                                   anchor="w")

        name_label.pack(side="left", fill="x", expand=True)
        if not entry["is_dir"]:

            size_label = ctk.CTkLabel(item, text=format_size(entry["size"]),

                                       font=("Segoe UI", 10), text_color=TEXT_DIM)

            size_label.pack(side="right", padx=10)
        if entry["is_dir"]:

            # Double-click to navigate, single-click to select

            chevron = ctk.CTkLabel(item, text="›", font=("Segoe UI", 18), text_color=TEXT_DIM)

            chevron.pack(side="right", padx=10)
            def on_click(e, p=entry["path"], f=item):

                self._select_folder(p, f)
            def on_dbl(e, p=entry["path"]):

                self._browse_to(p)
            for w in [item, icon_label, name_label, chevron]:

                w.bind("<Button-1>", on_click)

                w.bind("<Double-Button-1>", on_dbl)

        else:

            for w in [item, icon_label, name_label]:

                w.bind("<Button-1>", lambda e: None)
        # Hover effect

        def on_enter(e, f=item):

            f.configure(fg_color=BG_CARD)

        def on_leave(e, f=item):

            if self.selected_path != entry.get("path"):

                f.configure(fg_color="transparent")
        for w in [item, icon_label, name_label]:

            w.bind("<Enter>", on_enter)

            w.bind("<Leave>", on_leave)
    def _select_folder(self, path: str, frame: ctk.CTkFrame):

        """Select a folder for vault operations."""

        # Deselect all

        for widget in self.file_list_frame.winfo_children():

            if isinstance(widget, ctk.CTkFrame):

                widget.configure(fg_color="transparent")
        # Select this one

        frame.configure(fg_color=ACCENT_DIM)

        self.selected_path = path

        self.add_vault_btn.configure(state="normal")

        self.status_label.configure(text=f"Selected: {path}")
    def _browser_go_back(self):

        """Navigate back in browser history."""

        if self.browser_history:

            prev = self.browser_history.pop()

            self.current_browser_path = None  # Prevent double append

            self._browse_to(prev)

            if self.browser_history:

                self.browser_history.pop()  # Remove the one we just added

        else:

            self._load_drives()
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    #  VAULT MANAGEMENT

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    def _add_selected_to_vault(self):

        """Add the selected folder to secured vaults."""

        if not self.selected_path:

            return
        success, msg = add_vault(self.selected_path)

        if success:

            self.status_label.configure(text=f"✓ {msg}")

            self._refresh_vault_list()

        else:

            self.status_label.configure(text=f"✗ {msg}")
    def _refresh_vault_list(self):

        """Refresh the vault list display."""

        for widget in self.vault_list_frame.winfo_children():

            widget.destroy()
        vaults = list_vaults()

        self.vault_count_label.configure(text=f"{len(vaults)} vault{'s' if len(vaults) != 1 else ''}")
        if not vaults:

            # Empty state

            empty_frame = ctk.CTkFrame(self.vault_list_frame, fg_color="transparent")

            empty_frame.pack(expand=True, pady=60)

            ctk.CTkLabel(empty_frame, text="🛡️", font=("Segoe UI Emoji", 48)).pack()

            ctk.CTkLabel(empty_frame, text="No Secured Vaults Yet", font=("Segoe UI", 16, "bold"),

                         text_color=TEXT_SECONDARY).pack(pady=(10, 4))

            ctk.CTkLabel(empty_frame, text="Browse files on the left and select\na folder to secure it.",

                         font=("Segoe UI", 12), text_color=TEXT_DIM, justify="center").pack()

            return
        for vault in vaults:

            self._create_vault_card(vault)
    def _create_vault_card(self, vault: dict):

        """Create a vault card with status and controls."""

        is_locked = vault["status"] == "locked"

        exists = vault["exists"]
        card = ctk.CTkFrame(self.vault_list_frame, fg_color=BG_CARD, corner_radius=12,

                            border_width=1, border_color=ACCENT_DIM if is_locked else BORDER)

        card.pack(fill="x", pady=5, padx=4)
        inner = ctk.CTkFrame(card, fg_color="transparent")

        inner.pack(fill="x", padx=16, pady=12)
        # Top row: icon + name + status

        top = ctk.CTkFrame(inner, fg_color="transparent")

        top.pack(fill="x")
        status_icon = "🔒" if is_locked else "🔓"

        status_color = ACCENT if is_locked else SUCCESS
        ctk.CTkLabel(top, text=status_icon, font=("Segoe UI Emoji", 22)).pack(side="left", padx=(0, 8))
        name_frame = ctk.CTkFrame(top, fg_color="transparent")

        name_frame.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(name_frame, text=vault["name"], font=("Segoe UI", 14, "bold"),

                     text_color=TEXT_PRIMARY, anchor="w").pack(fill="x")
        # Path info

        path_display = vault["path"]

        if len(path_display) > 45:

            path_display = "..." + path_display[-42:]

        ctk.CTkLabel(name_frame, text=path_display, font=("Segoe UI", 10),

                     text_color=TEXT_DIM, anchor="w").pack(fill="x")
        # Status badge

        status_text = "LOCKED" if is_locked else "UNLOCKED"

        badge = ctk.CTkLabel(top, text=f" {status_text} ", font=("Segoe UI", 10, "bold"),

                              text_color=BG_DARK, fg_color=status_color, corner_radius=6,

                              width=80, height=24)

        badge.pack(side="right", padx=4)
        if not exists:

            ctk.CTkLabel(top, text="⚠ Missing", font=("Segoe UI", 10),

                         text_color=WARNING).pack(side="right", padx=4)
        # Bottom row: details + buttons

        bottom = ctk.CTkFrame(inner, fg_color="transparent")

        bottom.pack(fill="x", pady=(10, 0))
        # Info

        info_text = f"📄 {vault['file_count']} files · 📁 {vault['dir_count']} folders"

        if vault["drive"]:

            info_text += f" · 💾 {vault['drive']}"

        ctk.CTkLabel(bottom, text=info_text, font=("Segoe UI", 10),

                     text_color=TEXT_DIM).pack(side="left")
        # Action buttons

        btn_frame = ctk.CTkFrame(bottom, fg_color="transparent")

        btn_frame.pack(side="right")
        # Remove button

        remove_btn = ctk.CTkButton(btn_frame, text="🗑", font=("Segoe UI Emoji", 14),

                                    fg_color="transparent", hover_color=DANGER,

                                    width=34, height=34, corner_radius=8,

                                    command=lambda p=vault["path"]: self._remove_vault(p))

        remove_btn.pack(side="right", padx=2)
        # Lock/Unlock toggle button

        if is_locked:

            toggle_btn = ctk.CTkButton(btn_frame, text="🔓 Unlock", font=("Segoe UI", 12),

                                        fg_color=SUCCESS, hover_color="#059669",

                                        width=90, height=34, corner_radius=8,

                                        command=lambda p=vault["path"]: self._unlock_vault(p))

        else:

            toggle_btn = ctk.CTkButton(btn_frame, text="🔒 Lock", font=("Segoe UI", 12),

                                        fg_color=ACCENT, hover_color=ACCENT_HOVER,

                                        width=80, height=34, corner_radius=8,

                                        command=lambda p=vault["path"]: self._lock_vault(p))

        toggle_btn.pack(side="right", padx=2)
    def _lock_vault(self, path: str):

        """Prompt for password then lock vault."""

        self._show_password_prompt(

            title="🔒 Lock Vault",

            subtitle=f"Enter password to lock:\n{os.path.basename(path)}",

            on_success=lambda pw: self._do_lock_vault(path, pw)

        )
    def _do_lock_vault(self, path: str, password: str):

        """Actually lock after password verified."""

        success, msg = lock_vault(path, password)

        self.status_label.configure(text=msg)

        self._refresh_vault_list()
    def _unlock_vault(self, path: str):

        """Show password prompt before unlocking a vault."""

        self._show_password_prompt(

            title="🔓 Unlock Vault",

            subtitle=f"Enter password to unlock:\n{os.path.basename(path)}",

            on_success=lambda pw: self._do_unlock_vault(path, pw)

        )
    def _do_unlock_vault(self, path: str, password: str):

        """Actually unlock after password verified, then monitor for auto-relock."""

        success, msg = unlock_vault(path, password)

        self.status_label.configure(text=msg)

        self._refresh_vault_list()
        if success:

            # Open the folder in Explorer

            try:

                os.startfile(path)

            except Exception:

                pass
            # Start background relock monitor

            self.status_label.configure(text=f"👁 Watching: {os.path.basename(path)} — will auto-lock on close")

            monitor = threading.Thread(

                target=self._monitor_and_relock, args=(path, password), daemon=True

            )

            monitor.start()
    def _show_password_prompt(self, title: str, subtitle: str, on_success: callable):

        """Show a password dialog. Verifies against master password. 3 failures = nuke.

        on_success receives the verified password as argument: on_success(password)"""

        dialog = ctk.CTkToplevel(self)

        dialog.title("Password Required")

        dialog.geometry("420x280")

        dialog.configure(fg_color=BG_DARK)

        dialog.transient(self)

        dialog.grab_set()

        dialog.resizable(False, False)
        dialog.update_idletasks()

        x = self.winfo_x() + (self.winfo_width() - 420) // 2

        y = self.winfo_y() + (self.winfo_height() - 280) // 2

        dialog.geometry(f"+{x}+{y}")
        # Add Background Image

        try:

            bg_path = get_resource_path(os.path.join("assets", "shield_bg.jpg"))

            if os.path.exists(bg_path):

                img = Image.open(bg_path).convert("RGBA").resize((420, 280))

                overlay = Image.new("RGBA", img.size, (10, 9, 8, 180))

                composited = Image.alpha_composite(img, overlay)

                bg_img = ctk.CTkImage(light_image=composited, dark_image=composited, size=(420, 280))

                ctk.CTkLabel(dialog, image=bg_img, text="").place(relx=0, rely=0, relwidth=1, relheight=1)

        except: pass
        frame = ctk.CTkFrame(dialog, fg_color=BG_CARD, corner_radius=12)

        frame.pack(fill="both", expand=True, padx=16, pady=16)
        ctk.CTkLabel(frame, text=title, font=("Segoe UI", 18, "bold"),

                     text_color=TEXT_PRIMARY).pack(pady=(20, 4))

        ctk.CTkLabel(frame, text=subtitle, font=("Segoe UI", 11),

                     text_color=TEXT_SECONDARY, justify="center").pack(pady=(0, 16))
        pw_entry = ctk.CTkEntry(frame, placeholder_text="Enter master password",

                                 show="●", width=300, height=42, font=("Segoe UI", 14),

                                 fg_color=BG_DARK, border_color=BORDER, corner_radius=10)

        pw_entry.pack(pady=(0, 8))

        pw_entry.focus_set()
        error_label = ctk.CTkLabel(frame, text="", font=("Segoe UI", 11), text_color=DANGER)

        error_label.pack(pady=(0, 10))
        # Load stored hash

        with open(HASH_FILE, "r") as f:

            stored_hash = f.read().strip()
        attempts_tracker = {"count": 0}
        def try_unlock():

            pw = pw_entry.get()

            if verify_password(pw, stored_hash):

                dialog.destroy()

                on_success(pw)  # Pass verified password to callback

            else:

                attempts_tracker["count"] += 1

                remaining = MAX_ATTEMPTS - attempts_tracker["count"]

                if attempts_tracker["count"] >= MAX_ATTEMPTS:

                    dialog.destroy()

                    self.status_label.configure(text="🚨 MAX ATTEMPTS — NUKE ACTIVATED")

                    self.update()

                    self._trigger_global_nuke()

                else:

                    error_label.configure(

                        text=f"✗ Wrong password — {remaining} attempt{'s' if remaining != 1 else ''} left"

                    )

                    pw_entry.delete(0, "end")
        pw_entry.bind("<Return>", lambda e: try_unlock())
        btn_row = ctk.CTkFrame(frame, fg_color="transparent")

        btn_row.pack(fill="x", padx=30, pady=(0, 16))
        ctk.CTkButton(btn_row, text="✗ Cancel", fg_color="transparent", border_width=1,

                      border_color=BORDER, text_color=TEXT_SECONDARY, width=120, height=38,

                      corner_radius=8, command=dialog.destroy).pack(side="left", expand=True, padx=4)
        ctk.CTkButton(btn_row, text="🔓 Unlock", fg_color=SUCCESS, hover_color="#059669",

                      width=120, height=38, corner_radius=8, font=("Segoe UI", 13, "bold"),

                      command=try_unlock).pack(side="right", expand=True, padx=4)
    def _monitor_and_relock(self, path: str, password: str = ""):

        """Background thread: monitor if the folder is still open in Explorer, relock when closed."""

        import subprocess as sp
        norm_path = os.path.normpath(path).replace("\\", "/").lower()
        # Wait for Explorer to open

        time.sleep(3)
        while True:

            try:

                result = sp.run(

                    ["powershell", "-NoProfile", "-Command",

                     '(New-Object -ComObject Shell.Application).Windows() | ForEach-Object { $_.LocationURL }'],

                    capture_output=True, text=True, timeout=5,

                    creationflags=0x08000000

                )

                folder_open = False

                for line in result.stdout.strip().splitlines():

                    explorer_path = line.strip().replace("file:///", "").replace("%20", " ").lower().rstrip("/")

                    if explorer_path == norm_path:

                        folder_open = True

                        break
                if not folder_open:

                    # Folder was closed — relock

                    lock_vault(path, password)

                    try:

                        self.after(0, lambda: self._on_auto_relock(path))

                    except Exception:

                        pass

                    return
            except Exception:

                pass
            time.sleep(2)
    def _on_auto_relock(self, path: str):

        """Called on main thread when auto-relock completes."""

        self.status_label.configure(text=f"🔒 Auto-locked: {os.path.basename(path)}")

        self._refresh_vault_list()
    def _remove_vault(self, path: str):

        """Remove a vault after confirmation."""

        dialog = ctk.CTkToplevel(self)

        dialog.title("Remove Vault")

        dialog.geometry("420x200")

        dialog.configure(fg_color=BG_DARK)

        dialog.transient(self)

        dialog.grab_set()

        dialog.resizable(False, False)
        # Center on parent

        dialog.update_idletasks()

        x = self.winfo_x() + (self.winfo_width() - 420) // 2

        y = self.winfo_y() + (self.winfo_height() - 200) // 2

        dialog.geometry(f"+{x}+{y}")
        # Add Background Image

        try:

            bg_path = get_resource_path(os.path.join("assets", "shield_bg.jpg"))

            if os.path.exists(bg_path):

                img = Image.open(bg_path).convert("RGBA").resize((420, 200))

                overlay = Image.new("RGBA", img.size, (10, 9, 8, 180))

                composited = Image.alpha_composite(img, overlay)

                bg_img = ctk.CTkImage(light_image=composited, dark_image=composited, size=(420, 200))

                ctk.CTkLabel(dialog, image=bg_img, text="").place(relx=0, rely=0, relwidth=1, relheight=1)

        except: pass
        frame = ctk.CTkFrame(dialog, fg_color=BG_CARD, corner_radius=12)

        frame.pack(fill="both", expand=True, padx=16, pady=16)
        ctk.CTkLabel(frame, text="⚠ Remove Vault?", font=("Segoe UI", 16, "bold"),

                     text_color=WARNING).pack(pady=(20, 8))

        ctk.CTkLabel(frame, text=f"Remove protection from:\n{os.path.basename(path)}",

                     font=("Segoe UI", 12), text_color=TEXT_SECONDARY, justify="center").pack(pady=(0, 4))

        ctk.CTkLabel(frame, text="(The folder will NOT be deleted)",

                     font=("Segoe UI", 10), text_color=TEXT_DIM).pack(pady=(0, 16))
        btn_row = ctk.CTkFrame(frame, fg_color="transparent")

        btn_row.pack(fill="x", padx=20, pady=(0, 16))
        ctk.CTkButton(btn_row, text="✗ Cancel", fg_color="transparent", border_width=1,

                      border_color=BORDER, text_color=TEXT_SECONDARY, width=120, height=36,

                      corner_radius=8, command=dialog.destroy).pack(side="left", expand=True, padx=4)
        ctk.CTkButton(btn_row, text="Remove", fg_color=DANGER, hover_color=DANGER_HOVER,

                      width=120, height=36, corner_radius=8,

                      command=lambda: self._do_remove_vault(path, dialog)).pack(side="right", expand=True, padx=4)
    def _do_remove_vault(self, path: str, dialog):

        dialog.destroy()

        success, msg = remove_vault(path)

        self.status_label.configure(text=msg)

        self._refresh_vault_list()
    def _lock_all_vaults(self):

        """Prompt for password once, then lock all unlocked vaults."""

        vaults = list_vaults()

        unlocked = [v for v in vaults if v["status"] == "unlocked"]

        if not unlocked:

            self.status_label.configure(text="No unlocked vaults to lock")

            return
        def do_lock_all(pw):

            count = 0

            for v in unlocked:

                lock_vault(v["path"], pw)

                count += 1

            self.status_label.configure(text=f"🔒 Locked {count} vault{'s' if count != 1 else ''}")

            self._refresh_vault_list()
        self._show_password_prompt(

            title="🔒 Lock All Vaults",

            subtitle=f"Enter password to lock {len(unlocked)} vault{'s' if len(unlocked) != 1 else ''}",

            on_success=do_lock_all

        )
    def _unlock_all_vaults(self):

        """Prompt for password once, then unlock all locked vaults."""

        vaults = list_vaults()

        locked = [v for v in vaults if v["status"] == "locked"]

        if not locked:

            self.status_label.configure(text="No locked vaults to unlock")

            return
        def do_unlock_all(pw):

            count = 0

            for v in locked:

                unlock_vault(v["path"], pw)

                count += 1

            self.status_label.configure(text=f"🔓 Unlocked {count} vault{'s' if count != 1 else ''}")

            self._refresh_vault_list()
        self._show_password_prompt(

            title="🔓 Unlock All Vaults",

            subtitle=f"Enter password to unlock {len(locked)} vault{'s' if len(locked) != 1 else ''}",

            on_success=do_unlock_all

        )
    def _refresh_all(self):

        """Refresh both file browser and vault list."""

        if self.current_browser_path:

            self._browse_to(self.current_browser_path)

    def _refresh_all(self):
        """Refresh both file browser and vault list."""
        if self.current_browser_path:
            self._browse_to(self.current_browser_path)
        else:
            self._load_drives()
        self._refresh_vault_list()
        self.status_label.configure(text="🔄 Refreshed")

    # ══════════════════════════════════════════════════
    #  SETTINGS POPUP
    # ══════════════════════════════════════════════════

    def _show_settings_popup(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("SecureVault — Settings")
        dialog.geometry("550x650")
        dialog.configure(fg_color=BG_DARK)
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 550) // 2
        y = self.winfo_y() + (self.winfo_height() - 650) // 2
        dialog.geometry(f"+{x}+{y}")

        # Add Background Image
        try:
            bg_path = get_resource_path(os.path.join("assets", "shield_bg.jpg"))
            if os.path.exists(bg_path):
                img = Image.open(bg_path).convert("RGBA").resize((550, 650))
                overlay = Image.new("RGBA", img.size, (10, 9, 8, 200))
                composited = Image.alpha_composite(img, overlay)
                bg_img = ctk.CTkImage(light_image=composited, dark_image=composited, size=(550, 650))
                ctk.CTkLabel(dialog, image=bg_img, text="").place(relx=0, rely=0, relwidth=1, relheight=1)
        except: pass

        # Main Layout: Fixed Footer First, then Scrollable Content
        footer_frame = ctk.CTkFrame(dialog, fg_color=BG_DARK, height=80, corner_radius=0)
        footer_frame.pack(fill="x", side="bottom")

        content_frame = ctk.CTkScrollableFrame(dialog, fg_color="transparent", width=510, height=520)
        content_frame.pack(fill="both", expand=True, padx=10, pady=(10, 0))

        # Dedicated Status Label for Popup
        popup_status = ctk.CTkLabel(footer_frame, text="", font=("Segoe UI", 11))
        popup_status.pack(pady=(5, 0))

        btn_row = ctk.CTkFrame(footer_frame, fg_color="transparent")
        btn_row.pack(pady=10)

        # --- Settings Header ---
        ctk.CTkLabel(content_frame, text="⚙ Settings", font=("Segoe UI", 20, "bold"),
                     text_color=TEXT_PRIMARY).pack(pady=(10, 20))

        # --- Security Section ---
        ctk.CTkLabel(content_frame, text="🔐 Security", font=("Segoe UI", 14, "bold"),
                     text_color=ACCENT).pack(anchor="w", padx=28, pady=(10, 5))

        sec_frame = ctk.CTkFrame(content_frame, fg_color=BG_DARK, corner_radius=10)
        sec_frame.pack(fill="x", padx=20, pady=(0, 20))

        ctk.CTkLabel(sec_frame, text="Update your master password.",
                     font=("Segoe UI", 11), text_color=TEXT_DIM).pack(side="left", padx=15, pady=15)

        ctk.CTkButton(sec_frame, text="Change Password", font=("Segoe UI", 11, "bold"),
                       fg_color=DANGER, hover_color=DANGER_HOVER, width=120, height=32,
                       command=lambda: [dialog.destroy(), self._show_change_password_dialog()]).pack(side="right", padx=15)

        # --- SMTP Settings ---
        smtp_container = ctk.CTkFrame(content_frame, fg_color="transparent")
        smtp_container.pack(fill="x", padx=28)

        header_row = ctk.CTkFrame(smtp_container, fg_color="transparent")
        header_row.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(header_row, text="📧 SMTP Configuration", font=("Segoe UI", 13, "bold"),
                     text_color=ACCENT).pack(side="left")

        config_values = load_config()
        fields = {}
        entries = []
        pw_entry_ref = [None]

        def toggle_edit():
            is_disabled = fields["SENDER_EMAIL"].cget("state") == "disabled"
            new_state = "normal" if is_disabled else "disabled"

            for entry in entries:
                entry.configure(state=new_state, border_color=ACCENT if is_disabled else BORDER)

            edit_btn.configure(text="🔒 Lock" if is_disabled else "✏️ Edit",
                               fg_color=ACCENT_DIM if is_disabled else BG_DARK)
            save_btn.configure(state="normal" if is_disabled else "disabled")
            test_btn.configure(state="normal" if is_disabled else "disabled")

            if is_disabled:
                popup_status.configure(text="Editing Enabled - Don't forget to save!", text_color=ACCENT)
            else:
                popup_status.configure(text="")

        def toggle_password_visibility():
            if pw_entry_ref[0]:
                current_show = pw_entry_ref[0].cget("show")
                pw_entry_ref[0].configure(show="" if current_show == "●" else "●")
                eye_btn.configure(text="👁" if current_show == "" else "🙈")

        edit_btn = ctk.CTkButton(header_row, text="✏️ Edit", font=("Segoe UI", 11),
                                 width=70, height=26, fg_color=BG_DARK, border_width=1,
                                 border_color=BORDER, corner_radius=6, command=toggle_edit)
        edit_btn.pack(side="right")

        for label, key, is_pw in [
            ("Sender Email", "SENDER_EMAIL", False),
            ("Email Password", "EMAIL_PASSWORD", True),
            ("Receiver Email", "RECEIVER_EMAIL", False),
            ("SMTP Server", "SMTP_SERVER", False),
            ("SMTP Port", "SMTP_PORT", False),
        ]:
            row = ctk.CTkFrame(smtp_container, fg_color="transparent")
            row.pack(fill="x", pady=2)

            label_row = ctk.CTkFrame(row, fg_color="transparent")
            label_row.pack(fill="x")

            ctk.CTkLabel(label_row, text=label, font=("Segoe UI", 11),
                         text_color=TEXT_SECONDARY).pack(side="left")

            if is_pw:
                eye_btn = ctk.CTkButton(label_row, text="👁", width=30, height=20, 
                                        fg_color="transparent", text_color=TEXT_DIM,
                                        hover_color=BG_CARD_HOVER, command=toggle_password_visibility)
                eye_btn.pack(side="right")

            entry = ctk.CTkEntry(smtp_container, font=("Segoe UI", 12),
                                  fg_color=BG_DARK, border_color=BORDER, corner_radius=8,
                                  height=36, show="●" if is_pw else "", state="disabled")
            entry.pack(fill="x", pady=(0, 8))

            if is_pw: pw_entry_ref[0] = entry

            val = config_values.get(key) or DEFAULT_SMTP.get(key, "")
            if val:
                entry.configure(state="normal")
                entry.insert(0, val)
                entry.configure(state="disabled")

            fields[key] = entry
            entries.append(entry)

        def save_smtp():
            try:
                new_config = {k: fields[k].get() for k in DEFAULT_SMTP}
                if save_config(new_config):
                    popup_status.configure(text="✓ SMTP settings encrypted and saved", text_color=SUCCESS)
                    self.status_label.configure(text="✓ SMTP Configuration Updated", text_color=SUCCESS)
                    toggle_edit()
                else: raise Exception("Encryption failed")
            except Exception as e:
                popup_status.configure(text=f"✗ Error: {e}", text_color=DANGER)

        def test_smtp():
            save_smtp()
            popup_status.configure(text="⏳ Testing SMTP connection...", text_color=ACCENT)
            def run_test():
                from core.mailer import send_otp
                import random
                otp = str(random.randint(1000, 9999))
                if send_otp(f"TEST-{otp}"):
                    popup_status.configure(text=f"✓ Test OTP sent to {fields['RECEIVER_EMAIL'].get()}", text_color=SUCCESS)
                else: popup_status.configure(text="✗ SMTP Test Failed. Check credentials.", text_color=DANGER)
            threading.Thread(target=run_test, daemon=True).start()

        test_btn = ctk.CTkButton(btn_row, text="⚡ Save & Test", fg_color=SUCCESS, hover_color="#059669",
                                 width=150, height=44, corner_radius=10, font=("Segoe UI", 12, "bold"),
                                 state="disabled", command=test_smtp)
        test_btn.pack(side="left", padx=10)

        save_btn = ctk.CTkButton(btn_row, text="💾 Save Only", fg_color=ACCENT, hover_color=ACCENT_HOVER,
                                 width=150, height=44, corner_radius=10, font=("Segoe UI", 12, "bold"),
                                 state="disabled", command=save_smtp)
        save_btn.pack(side="right", padx=10)

        ctk.CTkButton(footer_frame, text="Close", fg_color="transparent", border_width=1, border_color=BORDER,
                      text_color=TEXT_SECONDARY, width=100, height=32, command=dialog.destroy).pack(pady=(0, 10))

    def _show_change_password_dialog(self, is_reset=False):
        """Show dialog to change master password."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Change Master Password")
        dialog.geometry("480x520" if not is_reset else "480x420")
        dialog.resizable(False, False)
        dialog.configure(fg_color=BG_DARK)
        dialog.transient(self)
        dialog.grab_set()

        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 480) // 2
        y = self.winfo_y() + (self.winfo_height() - 520) // 2
        dialog.geometry(f"+{x}+{y}")

        try:
            bg_path = get_resource_path(os.path.join("assets", "shield_bg.jpg"))
            if os.path.exists(bg_path):
                img = Image.open(bg_path).convert("RGBA").resize((480, 520))
                overlay = Image.new("RGBA", img.size, (10, 9, 8, 180))
                composited = Image.alpha_composite(img, overlay)
                bg_img = ctk.CTkImage(light_image=composited, dark_image=composited, size=(480, 520))
                ctk.CTkLabel(dialog, image=bg_img, text="").place(relx=0, rely=0, relwidth=1, relheight=1)
        except: pass

        frame = ctk.CTkFrame(dialog, fg_color=BG_CARD, corner_radius=16, border_width=1, border_color=BORDER)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(frame, text="🔐 Reset Password" if is_reset else "🔐 Change Password", 
                     font=("Segoe UI", 20, "bold"), text_color=ACCENT).pack(pady=(20, 15))

        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=30)

        if not is_reset:
            ctk.CTkLabel(inner, text="Current Password", font=("Segoe UI", 12), text_color=TEXT_SECONDARY).pack(anchor="w")
            curr_pw = ctk.CTkEntry(inner, show="●", height=40, fg_color=BG_DARK, border_color=BORDER)
            curr_pw.pack(fill="x", pady=(2, 12))

        ctk.CTkLabel(inner, text="New Password", font=("Segoe UI", 12), text_color=TEXT_SECONDARY).pack(anchor="w")
        new_pw = ctk.CTkEntry(inner, show="●", height=40, fg_color=BG_DARK, border_color=BORDER)
        new_pw.pack(fill="x", pady=(2, 12))

        ctk.CTkLabel(inner, text="Confirm New Password", font=("Segoe UI", 12), text_color=TEXT_SECONDARY).pack(anchor="w")
        conf_pw = ctk.CTkEntry(inner, show="●", height=40, fg_color=BG_DARK, border_color=BORDER)
        conf_pw.pack(fill="x", pady=(2, 12))

        err_label = ctk.CTkLabel(inner, text="", font=("Segoe UI", 12), text_color=DANGER)
        err_label.pack(pady=5)

        def attempt_change():
            if not is_reset:
                if not verify_password(curr_pw.get(), self.stored_hash):
                    err_label.configure(text="✗ Current password incorrect")
                    return

            n1, n2 = new_pw.get(), conf_pw.get()
            if len(n1) < 4:
                err_label.configure(text="⚠ Password too short (min 4 chars)")
                return
            if n1 != n2:
                err_label.configure(text="✗ Passwords do not match")
                return

            new_hash = hash_password(n1)
            with open(HASH_FILE, "w", encoding="utf-8") as f: f.write(new_hash)
            self.stored_hash = new_hash
            self._reset_otp_history()
            dialog.destroy()
            if is_reset:
                self._show_login_screen()
                self.login_error.configure(text="✓ Password reset successful!", text_color=SUCCESS)
            else: self.status_label.configure(text="✓ Master password updated")

        ctk.CTkButton(inner, text="Update Password", font=("Segoe UI", 15, "bold"),
                      fg_color=SUCCESS, hover_color="#059669", height=46, corner_radius=12,
                      command=attempt_change).pack(fill="x", pady=10)

    # ══════════════════════════════════════════════════
    #  UTILITIES
    # ══════════════════════════════════════════════════

    def _clear_window(self):
        """Remove all widgets from the window."""
        for widget in self.winfo_children():
            widget.destroy()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--unlock":
        if len(sys.argv) < 3: sys.exit(1)
        from unlock_prompt import UnlockPrompt
        UnlockPrompt(sys.argv[2]).mainloop()
    else:
        SecureVaultApp().mainloop()
