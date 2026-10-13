import configparser
import os
import subprocess
import sys
import time
import threading
from pathlib import Path

# ---------------------------------------------------------------------------
# Locate config.ini beside the exe (or beside launcher.py in dev)
# ---------------------------------------------------------------------------
if getattr(sys, 'frozen', False):
    _ROOT = Path(sys.executable).resolve().parent
else:
    _ROOT = Path(__file__).resolve().parent

_CONFIG_FILE = _ROOT / 'config.ini'

cfg = configparser.ConfigParser(interpolation=None)
cfg.read(str(_CONFIG_FILE), encoding='utf-8')

SERVER_HOST = cfg.get('server', 'host', fallback='0.0.0.0')
SERVER_PORT = int(cfg.get('server', 'port', fallback='5000'))

# For the browser we always open localhost even if the server binds to 0.0.0.0
BROWSER_HOST = '127.0.0.1' if SERVER_HOST in ('0.0.0.0', '') else SERVER_HOST
APP_URL = f'http://{BROWSER_HOST}:{SERVER_PORT}/'

# ---------------------------------------------------------------------------
# Ensure Django can find the project when running as a frozen exe
# ---------------------------------------------------------------------------
if getattr(sys, 'frozen', False):
    # In Nuitka --standalone the source is in _internal; add project root
    _internal = Path(sys.executable).resolve().parent
    sys.path.insert(0, str(_internal))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')

# ---------------------------------------------------------------------------
# Start Waitress in a daemon thread
# ---------------------------------------------------------------------------
def start_server():
    from waitress import serve
    from mysite.wsgi import application
    print(f'[Launcher] Starting Waitress on {SERVER_HOST}:{SERVER_PORT} ...')
    serve(
        application,
        host=SERVER_HOST,
        port=SERVER_PORT,
        threads=8,
        channel_timeout=120,
    )

server_thread = threading.Thread(target=start_server, daemon=True)
server_thread.start()

# ---------------------------------------------------------------------------
# Wait until the server is actually answering requests
# ---------------------------------------------------------------------------
def wait_for_server(url: str, timeout: int = 30):
    import urllib.request
    import urllib.error
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except Exception:
            time.sleep(0.3)
    return False

print(f'[Launcher] Waiting for server at {APP_URL} ...')
if not wait_for_server(APP_URL):
    print(f'[Launcher] ERROR: Server did not respond within 30 s at {APP_URL}')
    sys.exit(1)

print(f'[Launcher] Server is up. Opening browser ...')

# ---------------------------------------------------------------------------
# Open Chrome / Edge in kiosk mode
# ---------------------------------------------------------------------------
KIOSK_FLAGS = [
    '--kiosk',
    '--kiosk-printing',
    '--incognito',
    '--disable-pinch',
    '--overscroll-history-navigation=0',
    APP_URL,
]

def find_browser():
    """Return path to Chrome or Edge exe, or None if neither is found."""
    chrome_paths = [
        os.path.expandvars(r'%ProgramFiles%\Google\Chrome\Application\chrome.exe'),
        os.path.expandvars(r'%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe'),
        os.path.expandvars(r'%LocalAppData%\Google\Chrome\Application\chrome.exe'),
    ]
    edge_paths = [
        os.path.expandvars(r'%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe'),
        os.path.expandvars(r'%ProgramFiles%\Microsoft\Edge\Application\msedge.exe'),
    ]
    for p in chrome_paths:
        if os.path.isfile(p):
            return p, 'Chrome'
    for p in edge_paths:
        if os.path.isfile(p):
            return p, 'Edge'
    return None, None

browser_exe, browser_name = find_browser()

if browser_exe:
    print(f'[Launcher] Launching {browser_name} in kiosk mode → {APP_URL}')
    subprocess.Popen([browser_exe] + KIOSK_FLAGS)
else:
    print('[Launcher] ERROR: Neither Chrome nor Edge was found.')
    print('           Please install Chrome or Edge and try again.')
    print(f'           Or open a browser manually and go to: {APP_URL}')

# ---------------------------------------------------------------------------
# Keep the launcher (and therefore Waitress) alive until the user closes it
# ---------------------------------------------------------------------------
print('[Launcher] Server running. Press Ctrl+C to stop.')
try:
    server_thread.join()
except KeyboardInterrupt:
    print('[Launcher] Shutting down.')
