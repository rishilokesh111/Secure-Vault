import subprocess
import os
import sys

def build():
    print("Starting SecureVault EXE Build...")
    
    # Entry point
    script = "app.py"
    
    # Assets to include
    # Syntax: "source;destination" (Windows)
    assets = "assets;assets"
    
    # Build command
    cmd = [
        "python", "-m", "PyInstaller",
        "--noconsole",
        "--onefile",
        f"--add-data={assets}",
        "--name=SecureVault",
        "--hidden-import=customtkinter",
        script
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True)
        print("\nBuild Successful!")
        print("Your EXE is in the 'dist' folder.")
    except subprocess.CalledProcessError as e:
        print(f"\nBuild Failed: {e}")

if __name__ == "__main__":
    build()
