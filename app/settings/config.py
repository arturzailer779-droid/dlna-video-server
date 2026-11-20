import os
from pathlib import Path
import subprocess  # nosec B404
import uuid

IS_FLATPAK = os.path.exists("/.flatpak-info")
APP_ID = "io.github.arturzailer779_droid.dlna-video-server"

CONFIG_DIR = os.path.expanduser("~/.dlna_server_1_1")
CONFIG_FILE = os.path.join(CONFIG_DIR, "minidlna.conf")
PID_FILE = os.path.join(CONFIG_DIR, "minidlna.pid")
LOG_FILE = os.path.join(CONFIG_DIR, "minidlna.log")
DB_DIR = os.path.join(CONFIG_DIR, "db")
FOLDERS_FILE = os.path.join(CONFIG_DIR, "folders.txt")
LANG_FILE = os.path.join(CONFIG_DIR, "lang.txt")
NOSLEEP_FILE = os.path.join(CONFIG_DIR, "nosleep.txt")
THUMBS_FILE = os.path.join(CONFIG_DIR, "thumbs.txt")
UUID_FILE = os.path.join(CONFIG_DIR, "uuid.txt")
AUTOSTART_FLAG = os.path.join(CONFIG_DIR, "autostart.txt")

AUTOSTART_DIR = os.path.expanduser("~/.config/autostart")
AUTOSTART_FILE = os.path.join(AUTOSTART_DIR, "dlna-server.desktop")

BASE_DIR = Path(__file__).resolve().parents[2]
ASSET_DIR = str(BASE_DIR / "assets")
LOGO_ON = os.path.join(ASSET_DIR, "logo.png")
LOGO_OFF = os.path.join(ASSET_DIR, "logo_off.png")
ICONS_DIR = os.path.join(ASSET_DIR, "icons")

os.makedirs(CONFIG_DIR, exist_ok=True)
os.makedirs(DB_DIR, exist_ok=True)

def get_server_uuid():
    if os.path.exists(UUID_FILE):
        val = open(UUID_FILE, encoding="utf-8").read().strip()
        if len(val) >= 32:
            return val
    val = str(uuid.uuid4())
    open(UUID_FILE, "w", encoding="utf-8").write(val)
    return val

def load_folders():
    if os.path.exists(FOLDERS_FILE):
        return [x.strip() for x in open(FOLDERS_FILE, encoding="utf-8") if x.strip() and os.path.isdir(x.strip())]
    return []

def save_folders(folders):
    open(FOLDERS_FILE, "w", encoding="utf-8").write("\n".join(folders) + "\n")

def get_lang():
    return open(LANG_FILE, encoding="utf-8").read().strip() if os.path.exists(LANG_FILE) else "ru"

def save_lang(code):
    open(LANG_FILE, "w", encoding="utf-8").write(code)

def get_nosleep():
    return open(NOSLEEP_FILE, encoding="utf-8").read().strip() != "0" if os.path.exists(NOSLEEP_FILE) else True

def save_nosleep(enabled):
    open(NOSLEEP_FILE, "w", encoding="utf-8").write("1" if enabled else "0")

def get_thumbs():
    return open(THUMBS_FILE, encoding="utf-8").read().strip() != "0" if os.path.exists(THUMBS_FILE) else True

def save_thumbs(enabled):
    open(THUMBS_FILE, "w", encoding="utf-8").write("1" if enabled else "0")

def _request_flatpak_autostart(enabled: bool):
    if not os.path.exists("/usr/bin/gdbus"):
        return
    st = "true" if enabled else "false"
    arg = f"{{'reason': <'DLNA server autostart'>, 'autostart': <{st}>, 'background': <{st}>, 'commandline': <['dlna-server', '--autostart']>}}"
    subprocess.Popen(["/usr/bin/gdbus", "call", "--session", "--dest", "org.freedesktop.portal.Desktop", "--object-path", "/org/freedesktop/portal/desktop", "--method", "org.freedesktop.portal.Background.RequestBackground", "", arg], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def get_autostart():
    if IS_FLATPAK:
        return os.path.exists(AUTOSTART_FLAG) and open(AUTOSTART_FLAG, encoding="utf-8").read().strip() == "1"
    return os.path.exists(AUTOSTART_FILE)

def set_autostart(enabled):
    if IS_FLATPAK:
        open(AUTOSTART_FLAG, "w", encoding="utf-8").write("1" if enabled else "0")
        _request_flatpak_autostart(enabled)
        return
    if enabled:
        os.makedirs(AUTOSTART_DIR, exist_ok=True)
        e = "[Desktop Entry]\nType=Application\nName=DLNA SERVER\n"
        e += "Exec=/usr/bin/dlna-server --autostart\nIcon=dlna-server\n"
        e += "Terminal=false\nX-GNOME-Autostart-enabled=true\n"
        open(AUTOSTART_FILE, "w", encoding="utf-8").write(e)
    elif os.path.exists(AUTOSTART_FILE):
        os.remove(AUTOSTART_FILE)
