# license_encrypt.py - FIXED PATH VERSION
from cryptography.fernet import Fernet
import pathlib

# This gets folder where this script is: E:\...\apps\users\api\
CURRENT_DIR = pathlib.Path(__file__).parent
TARGET_FILE = CURRENT_DIR / "license.py"

print(f"Target: {TARGET_FILE}")

# Backup first
backup = CURRENT_DIR / "license_ORIGINAL.py"
if not backup.exists():
    backup.write_text(TARGET_FILE.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"Backup created: {backup}")

# Generate key
key = Fernet.generate_key()
print(f"YOUR KEY: {key.decode()} - SAVE IT IN SAFE PLACE")

f = Fernet(key)
original_code = TARGET_FILE.read_text(encoding="utf-8")
encrypted = f.encrypt(original_code.encode())

# New protected file - will be written to same location
loader = f'''# Protected LicenseUtils - Auto Decrypted at Runtime
from cryptography.fernet import Fernet

_key = {key}
_data = {encrypted}

def _load():
    f = Fernet(_key)
    code = f.decrypt(_data).decode()
    exec(code, globals())

_load()
del _load
del _key
del _data
'''

TARGET_FILE.write_text(loader, encoding="utf-8")
print("Done! license.py is now encrypted but still works 100%")