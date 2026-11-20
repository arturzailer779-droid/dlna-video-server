import logging, os, shutil, signal, socket, subprocess, time
from PyQt6.QtDBus import QDBusConnection, QDBusInterface, QDBusReply
from app.core.network import get_net_info
from app.settings.config import (
    CONFIG_DIR, CONFIG_FILE, DB_DIR, IS_FLATPAK, LOG_FILE,
    LOGO_ON, PID_FILE, get_nosleep, get_server_uuid,
    get_thumbs, load_folders,
)

log = logging.getLogger(__name__)
DLNA_PORT = 8208
PGREP_BIN = shutil.which("pgrep") or "/usr/bin/pgrep"
PKILL_BIN = shutil.which("pkill") or "/usr/bin/pkill"
MINIDLNA_BIN = shutil.which("minidlnad") or "/usr/sbin/minidlnad"
INHIBIT_BIN = shutil.which("systemd-inhibit") or "/usr/bin/systemd-inhibit"

class DlnaManager:
    def __init__(self):
        self.last_error = ""
        self._cookie = None

    def _dbus_inhibit(self, enable: bool):
        bus = QDBusConnection.sessionBus()
        if not bus.isConnected():
            return
        ifc = QDBusInterface(
            "org.freedesktop.ScreenSaver",
            "/org/freedesktop/ScreenSaver",
            "org.freedesktop.ScreenSaver",
            bus,
        )
        if not ifc.isValid():
            return
        if enable and self._cookie is None:
            rep = QDBusReply(ifc.call("Inhibit", "DLNA SERVER", "Active"))
            if rep.isValid():
                self._cookie = rep.value()
        elif not enable and self._cookie is not None:
            ifc.call("UnInhibit", self._cookie)
            self._cookie = None

    def _read_pid(self):
        if os.path.exists(PID_FILE):
            try:
                pid = int(open(PID_FILE, encoding="utf-8").read().strip())
                os.kill(pid, 0)
                cmd = open(f"/proc/{pid}/cmdline", "rb").read().decode(errors="ignore")
                if "minidlnad" in cmd:
                    return pid
            except (OSError, ValueError):
                pass
        return None

    def is_running(self):
        if self._read_pid() is not None:
            return True
        r = subprocess.run([PGREP_BIN, "-f", f"minidlnad.*{CONFIG_FILE}"],
                           stdout=subprocess.DEVNULL, check=False)
        return r.returncode == 0

    def stop(self):
        self._dbus_inhibit(False)
        pid = self._read_pid()
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        subprocess.run([PKILL_BIN, "-TERM", "-f", CONFIG_FILE],
                       stderr=subprocess.DEVNULL, check=False)
        for _ in range(3):
            if not self.is_running():
                break
            time.sleep(0.1)
        if self.is_running():
            subprocess.run([PKILL_BIN, "-KILL", "-f", CONFIG_FILE],
                           stderr=subprocess.DEVNULL, check=False)
            time.sleep(0.2)
        if os.path.exists(PID_FILE):
            try:
                os.remove(PID_FILE)
            except OSError:
                pass

    def _read_last_log_error(self):
        if os.path.exists(LOG_FILE):
            try:
                ls = [l.strip() for l in open(LOG_FILE, encoding="utf-8", errors="ignore").readlines()[-5:] if l.strip()]
                if ls:
                    return ls[-1]
            except OSError:
                pass
        return ""

    def start(self, rescan=False):
        self.last_error = ""
        folders = load_folders()
        if not folders:
            self.last_error = "NO_FOLDERS"
            return False
        self.stop()
        _, iface = get_net_info()
        il = f"network_interface={iface}\n" if iface not in ("", "auto", "offline") else ""
        md = "\n".join(f"media_dir={f}" for f in folders)
        host = socket.gethostname()
        sn = f"DLNA SERVER ({host})" if host else "DLNA SERVER"
        th = "yes" if get_thumbs() else "no"
        cfg = (f"port={DLNA_PORT}\n{il}{md}\nfriendly_name={sn}\nuuid={get_server_uuid()}\n"
               f"root_container=B\nicon={LOGO_ON}\ndb_dir={DB_DIR}\nlog_dir={CONFIG_DIR}\ninotify=yes\n"
               f"enable_subtitles=yes\nstrict_dlna=yes\nenable_thumbnail={th}\nthumbnail_width=160\n"
               f"thumbnail_quality=10\nforce_sort_criteria=+upnp:class,+dc:title\nnotify_interval=60\n")
        open(CONFIG_FILE, "w", encoding="utf-8").write(cfg)
        cmd = [MINIDLNA_BIN, "-f", CONFIG_FILE, "-P", PID_FILE, "-S"] + (["-R"] if rescan else [])
        if get_nosleep() and not IS_FLATPAK and os.path.exists(INHIBIT_BIN):
            cmd = [INHIBIT_BIN, "--what=sleep:idle", "--who=DLNA SERVER", "--why=DLNA active"] + cmd
        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        except OSError as exc:
            self.last_error = str(exc)
            return False
        for _ in range(20):
            if self.is_running():
                if get_nosleep() and IS_FLATPAK:
                    self._dbus_inhibit(True)
                return True
            time.sleep(0.1)
        self.last_error = self._read_last_log_error() or "minidlnad failed to start"
        return False

    def status_summary(self, ru=True):
        ip, iface = get_net_info()
        if self.is_running():
            return f"IP: {ip} ({iface})\nПорт: {DLNA_PORT} • Активен" if ru else f"IP: {ip} ({iface})\nPort: {DLNA_PORT} • Active"
        return f"IP: {ip} ({iface})\nПорт: {DLNA_PORT} • Ожидание" if ru else f"IP: {ip} ({iface})\nPort: {DLNA_PORT} • Standby"
