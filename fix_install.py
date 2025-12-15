import sys
import subprocess
import os

print("--- 🔧 KIT FINDER REPAIR TOOL ---")
print(f"Python Location: {sys.executable}")

# Force install into the current python environment
print("\nAttempting to force install 'streamlit-keyup'...")
try:
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", 
        "streamlit-keyup", 
        "--break-system-packages", 
        "--force-reinstall"
    ])
    print("\n✅ SUCCESS! The tool is installed.")
    print("You can now run: streamlit run extras.py")
except Exception as e:
    print(f"\n❌ FAILED: {e}")