import smtplib
import shutil
import os
from email.message import EmailMessage
from dotenv import load_dotenv

from core.paths import get_data_path

from core.config_manager import load_config

# Load configuration from encrypted storage
_config = load_config()

DEFAULT_SMTP = {
    "SENDER_EMAIL": "",
    "EMAIL_PASSWORD": "",
    "RECEIVER_EMAIL": "",
    "SMTP_SERVER": "smtp.gmail.com",
    "SMTP_PORT": "587"
}


def send_vault_backup(folder_to_zip: str) -> bool:
    """
    Zip the vault folder and send it as an email attachment via SMTP.
    Returns True on success, False on failure.
    """
    # Load fresh config
    config = load_config()
    
    # Validate environment variables
    sender = config.get("SENDER_EMAIL", DEFAULT_SMTP["SENDER_EMAIL"])
    password = config.get("EMAIL_PASSWORD", DEFAULT_SMTP["EMAIL_PASSWORD"])
    receiver = config.get("RECEIVER_EMAIL", DEFAULT_SMTP["RECEIVER_EMAIL"])
    smtp_server = config.get("SMTP_SERVER", DEFAULT_SMTP["SMTP_SERVER"])
    smtp_port = config.get("SMTP_PORT", DEFAULT_SMTP["SMTP_PORT"])

    if not all([sender, password, receiver]):
        print("[!] SMTP credentials missing. Check your .env file.")
        print("    Required: SENDER_EMAIL, EMAIL_PASSWORD, RECEIVER_EMAIL")
        return False

    if not os.path.exists(folder_to_zip):
        print("[!] Vault folder not found. Nothing to send.")
        return False

    zip_name = "vault_backup"
    zip_file = f"{zip_name}.zip"

    try:
        # Create the zip archive
        shutil.make_archive(zip_name, 'zip', folder_to_zip)

        # Build the email
        msg = EmailMessage()
        msg['Subject'] = "🚨 SECURE VAULT: Unauthorized Access Alert"
        msg['From'] = sender
        msg['To'] = receiver
        msg.set_content(
            "ALERT: 3 failed password attempts detected on SecureVault.\n\n"
            "The vault contents have been zipped and attached to this email.\n"
            "The vault has been permanently destroyed on the host machine.\n\n"
            "Secure your accounts immediately."
        )

        with open(zip_file, 'rb') as f:
            file_data = f.read()
            msg.add_attachment(
                file_data,
                maintype='application',
                subtype='zip',
                filename=zip_file
            )

        # Send via SMTP
        with smtplib.SMTP(smtp_server, int(smtp_port)) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)

        print(f"[✓] Vault backup sent to {receiver}")
        return True

    except smtplib.SMTPAuthenticationError:
        print("[!] SMTP authentication failed. Check your email/password.")
        print("    For Gmail, use an App Password (not your regular password).")
        return False
    except smtplib.SMTPException as e:
        print(f"[!] SMTP error: {e}")
        return False
    except Exception as e:
        print(f"[!] Mail failed: {e}")
        return False
    finally:
        if os.path.exists(zip_file):
            os.remove(zip_file)

def send_otp(otp_code: str) -> bool:
    """
    Send a 6-digit OTP via SMTP for password reset.
    Returns True on success, False on failure.
    """
    config = load_config()
    sender = config.get("SENDER_EMAIL", DEFAULT_SMTP["SENDER_EMAIL"])
    password = config.get("EMAIL_PASSWORD", DEFAULT_SMTP["EMAIL_PASSWORD"])
    receiver = config.get("RECEIVER_EMAIL", DEFAULT_SMTP["RECEIVER_EMAIL"])
    smtp_server = config.get("SMTP_SERVER", DEFAULT_SMTP["SMTP_SERVER"])
    smtp_port = config.get("SMTP_PORT", DEFAULT_SMTP["SMTP_PORT"])

    if not all([sender, password, receiver]):
        print("[!] SMTP credentials missing for OTP.")
        return False

    try:
        msg = EmailMessage()
        msg['Subject'] = "🔒 SecureVault: Password Reset OTP"
        msg['From'] = sender
        msg['To'] = receiver
        msg.set_content(
            f"Your SecureVault Password Reset OTP is:\n\n"
            f"   {otp_code}\n\n"
            f"If you did not request this, please ignore this email."
        )

        with smtplib.SMTP(smtp_server, int(smtp_port)) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)

        print(f"[✓] OTP sent to {receiver}")
        return True

    except Exception as e:
        print(f"[!] OTP Mail failed: {e}")
        return False