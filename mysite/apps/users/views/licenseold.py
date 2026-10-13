# LicenseUtils.py - Production Version - Inside ERP
import os
import base64
import hashlib
from datetime import date
import uuid
from pathlib import Path

SECRET_KEY = "MyDjangoApp"

digit_map_decode = {
    'J': '0', 'I': '1', 'H': '2', 'G': '3', 'F': '4',
    'E': '5', 'D': '6', 'C': '7', 'B': '8', 'A': '9'
}
digit_map_encode = {v: k for k, v in digit_map_decode.items()}

APP_NAME = "AlphaServer"

def get_license_path():
    if os.name == 'nt':
        base = os.getenv("LOCALAPPDATA") or os.path.expanduser("~\\AppData\\Local")
    else:
        base = os.path.expanduser("~/.config")
    path = os.path.join(base, APP_NAME)
    Path(path).mkdir(parents=True, exist_ok=True)
    return os.path.join(path, "license.dat")

LICENSE_FILE = get_license_path()

def get_machine_id():
    try:
        return hex(uuid.getnode())
    except:
        return "0"

def company_to_code(company_name):
    clean_name = "".join(company_name.upper().split())
    raw = (SECRET_KEY + clean_name).encode()
    hash_val = hashlib.sha256(raw).hexdigest()
    num = int(hash_val[:8], 16)
    code = ""
    for _ in range(4):
        code += digit_map_encode[str(num % 10)]
        num //= 10
    return code[::-1]

def decode_license(key):
    try:
        key = key.strip().upper()
        if len(key)!= 19: # 3+2+2+4+2+4+2 = 19 now with K-Z fix it is 19
            # Keep backward compatible with 17 also
            if len(key)!= 17 and len(key)!= 19:
                return None

        # Handle both 17 and 19 length
        if len(key) == 19:
            encoded_month = key[3:5]
            encoded_year = key[7:11]
            encoded_day = key[11:13]
            encoded_company = key[13:17]
        else: # 17 length old
            encoded_month = key[3:5]
            encoded_year = key[7:11]
            encoded_day = key[11:13]
            encoded_company = key[13:17]

        valid_chars = set('ABCDEFGHIJ')
        if not all(c in valid_chars for c in encoded_month+encoded_year+encoded_day+encoded_company):
            return None

        month = ''.join(digit_map_decode[c] for c in encoded_month)
        year = ''.join(digit_map_decode[c] for c in encoded_year)
        day = ''.join(digit_map_decode[c] for c in encoded_day)

        expiry = date(int(year), int(month), int(day))
        return expiry, encoded_company
    except:
        return None

def encrypt(text):
    try:
        machine_id = get_machine_id()
        text_bytes = text.encode()
        key_bytes = (SECRET_KEY + machine_id).encode()
        encrypted = bytes(text_bytes[i] ^ key_bytes[i % len(key_bytes)] for i in range(len(text_bytes)))
        return base64.b64encode(encrypted).decode()
    except:
        return None

def decrypt(encoded_text):
    try:
        machine_id = get_machine_id()
        encrypted_bytes = base64.b64decode(encoded_text)
        key_bytes = (SECRET_KEY + machine_id).encode()
        decrypted = bytes(encrypted_bytes[i] ^ key_bytes[i % len(key_bytes)] for i in range(len(encrypted_bytes)))
        return decrypted.decode()
    except:
        return None

# --- MAIN FUNCTIONS ---

def save_license(key, current_company_name):
    # User-friendly messages only
    decoded = decode_license(key)
    if not decoded:
        return False, "Invalid license key. Please check and try again."

    expiry, code_in_license = decoded
    expected_code = company_to_code(current_company_name)

    if code_in_license!= expected_code:
        # DO NOT show expected/got code
        return False, f"License is not valid for company '{current_company_name}'."

    if expiry < date.today():
        return False, "This license has already expired."

    # Save to file
    encrypted_data = encrypt(f"{expiry}|{current_company_name}")
    if not encrypted_data:
        return False, "Failed to save license."

    try:
        with open(LICENSE_FILE, "w") as f:
            f.write(encrypted_data)
    except Exception:
        return False, "Failed to save license file. No permission."

    # Save in DB if you use CompanyConfiguration
    try:
        from apps.settings.models import CompanyConfiguration
        companyConfig, _ = CompanyConfiguration.objects.get_or_create(id=1)
        companyConfig.license_exp_dt = expiry
        companyConfig.save()
    except Exception:
        pass

    return True, "License activated successfully."

def is_license_valid():
    if not os.path.exists(LICENSE_FILE):
        return False
    try:
        with open(LICENSE_FILE, "r") as f:
            encrypted = f.read().strip()
        if not encrypted:
            return False

        decrypted = decrypt(encrypted)
        if not decrypted or "|" not in decrypted:
            return False

        expiry_str, _ = decrypted.split("|", 1)
        expiry = date.fromisoformat(expiry_str)
        return expiry >= date.today()
    except:
        return False