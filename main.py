import os
import getpass
from core.auth import hash_password, verify_password
from core.mailer import send_vault_backup
from core.shredder import secure_nuke

# Paths
VAULT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vault")
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
HASH_FILE = os.path.join(DATA_DIR, "hash.txt")
LOG_FILE = os.path.join(DATA_DIR, "attempts.log")

MAX_ATTEMPTS = 3


def get_attempts() -> int:
    """Read the current failed attempt count from the log file."""
    if not os.path.exists(LOG_FILE):
        return 0
    try:
        with open(LOG_FILE, "r") as f:
            return int(f.read().strip() or 0)
    except (ValueError, OSError):
        return 0


def update_attempts(count: int):
    """Write the current attempt count to the log file."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(LOG_FILE, "w") as f:
        f.write(str(count))


def setup_password():
    """First-run: prompt user to create a master password."""
    print("=" * 50)
    print("  SECUREVAULT – First Time Setup")
    print("=" * 50)
    print()

    while True:
        password = getpass.getpass("Create master password: ")
        if len(password) < 4:
            print("[!] Password must be at least 4 characters.\n")
            continue

        confirm = getpass.getpass("Confirm master password: ")
        if password != confirm:
            print("[!] Passwords do not match. Try again.\n")
            continue

        # Hash and save
        hashed = hash_password(password)
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(HASH_FILE, "w") as f:
            f.write(hashed)

        # Ensure vault directory exists
        os.makedirs(VAULT_PATH, exist_ok=True)

        print()
        print("[✓] Master password set successfully.")
        print(f"[✓] Vault directory ready at: {VAULT_PATH}")
        print("[i] Place your sensitive files inside the vault/ folder.")
        print()
        return


def trigger_nuke():
    """Execute the nuke sequence: backup via email, then permanent destroy."""
    print()
    print("=" * 50)
    print("  ⚠  SECURITY BREACH – NUKE SEQUENCE ACTIVE  ⚠")
    print("=" * 50)
    print()

    print("[*] Step 1: Sending vault backup via email...")
    email_sent = send_vault_backup(VAULT_PATH)

    if email_sent:
        print("[*] Step 2: Permanently destroying vault...")
        secure_nuke(VAULT_PATH)
    else:
        print("[!] Email failed. Vault NOT deleted (data preservation).")
        print("[!] Fix your .env SMTP settings and re-run to retry.")


def main():
    # Ensure data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)

    # Check if password is set up
    needs_setup = False
    if not os.path.exists(HASH_FILE):
        needs_setup = True
    else:
        with open(HASH_FILE, "r") as f:
            if not f.read().strip():
                needs_setup = True

    if needs_setup:
        setup_password()
        return

    # Load stored hash
    with open(HASH_FILE, "r") as f:
        stored_hash = f.read().strip()

    # Check if already locked out
    attempts = get_attempts()

    if attempts >= MAX_ATTEMPTS:
        print("[!] System already locked from previous failed attempts.")
        trigger_nuke()
        return

    # Prompt for password
    print()
    print("=" * 50)
    print("  SECUREVAULT – Authentication")
    print("=" * 50)
    print()
    remaining = MAX_ATTEMPTS - attempts
    password = getpass.getpass(f"Enter vault password ({remaining} attempt{'s' if remaining != 1 else ''} remaining): ")

    if verify_password(password, stored_hash):
        update_attempts(0)  # Reset on success
        print()
        print("[✓] Access Granted. Welcome back.")
        print(f"[i] Vault location: {VAULT_PATH}")
        print()
    else:
        attempts += 1
        update_attempts(attempts)
        remaining = MAX_ATTEMPTS - attempts
        print()
        print(f"[✗] Access Denied. {remaining} attempt{'s' if remaining != 1 else ''} remaining.")

        if attempts >= MAX_ATTEMPTS:
            print("[!] Maximum attempts reached.")
            trigger_nuke()


if __name__ == "__main__":
    main()