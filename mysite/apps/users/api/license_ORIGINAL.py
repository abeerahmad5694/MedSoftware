


# LicenseUtils.py - FIXED PERMISSION VERSION
import os
import base64
import hashlib
from datetime import date
import uuid
from pathlib import Path
import platform
import sys
SECRET_KEY = "MyDjangoApp"

digit_map_decode = {
    'J': '0', 'I': '1', 'H': '2', 'G': '3', 'F': '4',
    'E': '5', 'D': '6', 'C': '7', 'B': '8', 'A': '9'
}
digit_map_encode = {v:k for k,v in digit_map_decode.items()}

APP_NAME = "AlphaServer"

# def get_license_path():
#     # Try 1: LOCALAPPDATA
#     try:
#         base = os.getenv("LOCALAPPDATA")
#         if not base:
#             base = os.path.join(os.path.expanduser("~"), "AppData", "Local")

#         path = Path(base) / APP_NAME
#         path.mkdir(parents=True, exist_ok=True)
#         test_file = path / "license.dat"
#         # Test if writable
#         return str(test_file)
#     except Exception as e:
#         print(f"License path primary failed: {e}")
#         # Fallback 2: Save in project folder
#         try:
#             fallback_path = Path(__file__).resolve().parent / "license.dat"
#             print(f"Using fallback path: {fallback_path}")
#             return str(fallback_path)
#         except Exception as e2:
#             print(f"Fallback also failed: {e2}")
#             return os.path.join(os.getcwd(), "license.dat")



def get_license_path():
    # --- Priority 1: Windows Local AppData ---
    try:
        if os.name == 'nt' or platform.system() == 'Windows':
            base = os.getenv("LOCALAPPDATA")
            if not base:
                base = os.path.join(os.path.expanduser("~"), "AppData", "Local")
            
            path = Path(base) / APP_NAME
            path.mkdir(parents=True, exist_ok=True)
            
            # Check writable
            test_file = path / "license.dat"
            # Try to touch file to test permission
            if not test_file.exists():
                test_file.touch(exist_ok=True)
            
            print(f"[LICENSE] Using Windows path: {test_file}")
            return str(test_file)
    except Exception as e:
        print(f"License Windows path failed: {e}")

    # --- Priority 2: Project root where manage.py and config.ini are ---
    # This will work for PythonAnywhere / Linux / Docker
    try:
        # Start from current file and go up until we find manage.py
        current = Path(__file__).resolve()
        for parent in current.parents:
            if (parent / "manage.py").exists() and (parent / "config.ini").exists():
                fallback = parent / "license.dat"
                print(f"[LICENSE] Using project root: {fallback}")
                return str(fallback)
            # Also check one level up (your structure is mysite/apps/...)
            if (parent / "mysite" / "manage.py").exists():
                fallback = parent / "mysite" / "license.dat"
                print(f"[LICENSE] Using mysite folder: {fallback}")
                return str(fallback)
    except Exception as e:
        print(f"Project root search failed: {e}")

    # --- Priority 3: Absolute fallback beside this file ---
    try:
        fallback_path = Path(__file__).resolve().parent.parent.parent.parent / "license.dat"
        print(f"[LICENSE] Using final fallback: {fallback_path}")
        return str(fallback_path)
    except:
        return os.path.join(os.getcwd(), "license.dat")


LICENSE_FILE = get_license_path()
print(f"[LICENSE] Using file: {LICENSE_FILE}")

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
        if len(key) not in (17, 19):
            return None

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
    except Exception as e:
        print(f"decode_license failed: {e}")
        return None

def encrypt(text):
    try:
        machine_id = get_machine_id()
        text_bytes = text.encode()
        key_bytes = (SECRET_KEY + machine_id).encode()
        encrypted = bytes(text_bytes[i] ^ key_bytes[i % len(key_bytes)] for i in range(len(text_bytes)))
        return base64.b64encode(encrypted).decode()
    except Exception as e:
        print(f"encrypt failed: {e}")
        return None

def decrypt(encoded_text):
    try:
        machine_id = get_machine_id()
        encrypted_bytes = base64.b64decode(encoded_text)
        key_bytes = (SECRET_KEY + machine_id).encode()
        decrypted = bytes(encrypted_bytes[i] ^ key_bytes[i % len(key_bytes)] for i in range(len(encrypted_bytes)))
        return decrypted.decode()
    except Exception as e:
        print(f"decrypt failed: {e}")
        return None

def save_license(key, current_company_name):
    decoded = decode_license(key)
    if not decoded:
        return False, "Invalid license key. Please check and try again."

    expiry, code_in_license = decoded
    expected_code = company_to_code(current_company_name)

    if code_in_license!= expected_code:
        return False, f"License is not valid for company '{current_company_name}'."

    if expiry < date.today():
        return False, "This license has already expired."

    encrypted_data = encrypt(f"{expiry}|{current_company_name}")
    if not encrypted_data:
        return False, "Failed to encrypt license."

    try:
        # Ensure folder exists
        Path(LICENSE_FILE).parent.mkdir(parents=True, exist_ok=True)

        # If file exists, remove read-only attribute
        if os.path.exists(LICENSE_FILE):
            try:
                os.chmod(LICENSE_FILE, 0o777)
            except:
                pass

        with open(LICENSE_FILE, "w") as f:
            f.write(encrypted_data)

        print(f"License saved to: {LICENSE_FILE}")

    except PermissionError as pe:
        print(f"PERMISSION ERROR DETAILS: {pe} | File: {LICENSE_FILE}")
        # Try fallback location immediately
        try:
            fallback = Path(os.getcwd()) / "license.dat"
            with open(fallback, "w") as f:
                f.write(encrypted_data)
            print(f"Saved to fallback: {fallback}")
            return True, "License activated successfully."
        except Exception as e2:
            print(f"Fallback save failed: {e2}")
            return False, f"Permission denied. Please run as Administrator or delete folder: {Path(LICENSE_FILE).parent}"

    except Exception as e:
        print(f"save_license file error: {e}")
        return False, "Failed to save license file."

    try:
        from apps.configuration.models import Company
        companyConfig = Company.objects.get(id=1)
        companyConfig.license_expiry = expiry
        companyConfig.save()
    except Exception as e:
        print(f"DB save skipped: {e}")
        pass

    return True, "License activated successfully."


from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages



def is_license_valid():
    if not os.path.exists(LICENSE_FILE):
        # Check fallback
        fallback = Path(os.getcwd()) / "license.dat"
        if not fallback.exists():
            return False

    # Try primary, then fallback
    for path_to_check in [LICENSE_FILE, str(Path(os.getcwd()) / "license.dat")]:
        try:
            if not os.path.exists(path_to_check):
                continue
            with open(path_to_check, "r") as f:
                encrypted = f.read().strip()
            if not encrypted:
                continue
            decrypted = decrypt(encrypted)
            if not decrypted or "|" not in decrypted:
                continue
            expiry_str, _ = decrypted.split("|", 1)
            expiry = date.fromisoformat(expiry_str)
            return expiry >= date.today()
        except Exception as e:
            print(f"is_license_valid check failed for {path_to_check}: {e}")
            continue
    return False



def validate_license(view_func=None, redirect_to='dashboard'):
    """
    Usage:
      @validate_license
      def sale_page(request): ...

      @validate_license(redirect_to='company_config')
      def purchase_page(request): ...

      # or in views 
      from apps.users.api.license import is_license_valid
      success = is_license_valid()
      if not success:
        return redirect('dashboard') 


    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            if not is_license_valid():
                messages.error(request, "License expired or not activated. Please activate license.")
                return redirect(redirect_to)
            return func(request, *args, **kwargs)
        return wrapper
    
    # Support both @validate_license and @validate_license(redirect_to='...')
    if view_func is None:
        return decorator
    else:
        return decorator(view_func)



# # LicenseUtils.py - Production Version - Inside ERP
# import os
# import base64
# import hashlib
# from datetime import date
# import uuid
# from pathlib import Path

# SECRET_KEY = "MyDjangoApp"

# digit_map_decode = {
#     'J': '0', 'I': '1', 'H': '2', 'G': '3', 'F': '4',
#     'E': '5', 'D': '6', 'C': '7', 'B': '8', 'A': '9'
# }
# digit_map_encode = {v: k for k, v in digit_map_decode.items()}

# APP_NAME = "AlphaServer"

# def get_license_path():
#     base = os.getenv("LOCALAPPDATA") or os.path.expanduser("~\\AppData\\Local")
#     path = os.path.join(base, APP_NAME)
#     Path(path).mkdir(parents=True, exist_ok=True)
#     return os.path.join(path, "license.dat")

# LICENSE_FILE = get_license_path()

# def get_machine_id():
#     try:
#         return hex(uuid.getnode())
#     except:
#         return "0"

# def company_to_code(company_name):
#     clean_name = "".join(company_name.upper().split())
#     raw = (SECRET_KEY + clean_name).encode()
#     hash_val = hashlib.sha256(raw).hexdigest()
#     num = int(hash_val[:8], 16)
#     code = ""
#     for _ in range(4):
#         code += digit_map_encode[str(num % 10)]
#         num //= 10
#     return code[::-1]

# def decode_license(key):
#     try:
#         key = key.strip().upper()
#         if len(key)!= 19: # 3+2+2+4+2+4+2 = 19 now with K-Z fix it is 19
#             # Keep backward compatible with 17 also
#             if len(key)!= 17 and len(key)!= 19:
#                 return None

#         # Handle both 17 and 19 length
#         if len(key) == 19:
#             encoded_month = key[3:5]
#             encoded_year = key[7:11]
#             encoded_day = key[11:13]
#             encoded_company = key[13:17]
#         else: # 17 length old
#             encoded_month = key[3:5]
#             encoded_year = key[7:11]
#             encoded_day = key[11:13]
#             encoded_company = key[13:17]

#         valid_chars = set('ABCDEFGHIJ')
#         if not all(c in valid_chars for c in encoded_month+encoded_year+encoded_day+encoded_company):
#             return None

#         month = ''.join(digit_map_decode[c] for c in encoded_month)
#         year = ''.join(digit_map_decode[c] for c in encoded_year)
#         day = ''.join(digit_map_decode[c] for c in encoded_day)

#         expiry = date(int(year), int(month), int(day))
#         return expiry, encoded_company
#     except:
#         return None

# def encrypt(text):
#     try:
#         machine_id = get_machine_id()
#         text_bytes = text.encode()
#         key_bytes = (SECRET_KEY + machine_id).encode()
#         encrypted = bytes(text_bytes[i] ^ key_bytes[i % len(key_bytes)] for i in range(len(text_bytes)))
#         return base64.b64encode(encrypted).decode()
#     except:
#         return None

# def decrypt(encoded_text):
#     try:
#         machine_id = get_machine_id()
#         encrypted_bytes = base64.b64decode(encoded_text)
#         key_bytes = (SECRET_KEY + machine_id).encode()
#         decrypted = bytes(encrypted_bytes[i] ^ key_bytes[i % len(key_bytes)] for i in range(len(encrypted_bytes)))
#         return decrypted.decode()
#     except:
#         return None

# # --- MAIN FUNCTIONS ---

# def save_license(key, current_company_name):
#     # User-friendly messages only
#     decoded = decode_license(key)
#     if not decoded:
#         return False, "Invalid license key. Please check and try again."

#     expiry, code_in_license = decoded
#     expected_code = company_to_code(current_company_name)

#     if code_in_license!= expected_code:
#         # DO NOT show expected/got code
#         return False, f"License is not valid for company '{current_company_name}'."

#     if expiry < date.today():
#         return False, "This license has already expired."

#     # Save to file
#     encrypted_data = encrypt(f"{expiry}|{current_company_name}")
#     if not encrypted_data:
#         return False, "Failed to save license."

#     try:
#         with open(LICENSE_FILE, "w") as f:
#             f.write(encrypted_data)
#     except Exception:
#         return False, "Failed to save license file. No permission."

#     # Save in DB if you use CompanyConfiguration
#     try:
#         from apps.configuration.models import Company
#         companyConfig = Company.objects.get(id=1)
#         companyConfig.license_expiry = expiry
#         companyConfig.save()
#     except Exception:
#         pass

#     return True, "License activated successfully."

# def is_license_valid():
#     if not os.path.exists(LICENSE_FILE):
#         return False
#     try:
#         with open(LICENSE_FILE, "r") as f:
#             encrypted = f.read().strip()
#         if not encrypted:
#             return False

#         decrypted = decrypt(encrypted)
#         if not decrypted or "|" not in decrypted:
#             return False

#         expiry_str, _ = decrypted.split("|", 1)
#         expiry = date.fromisoformat(expiry_str)
#         return expiry >= date.today()
#     except:
#         return False