import logging
import os
import shutil
import subprocess  # nosec B404

log = logging.getLogger(__name__)
IP_BIN = shutil.which("ip") or "/usr/sbin/ip"


def get_net_info():
    try:
        out = subprocess.check_output(
            [IP_BIN, "-o", "-4", "addr", "show", "up"], text=True)  # nosec B603
        cands = []
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 4:
                iface, ip_addr = parts[1], parts[3].split("/")[0]
                if not iface.startswith(("lo", "tun", "wg", "docker", "br-", "veth", "virbr")):
                    cands.append((iface, ip_addr))
        rt = subprocess.check_output(
            [IP_BIN, "-4", "route", "show", "default"], text=True)  # nosec B603
        for iface, ip_addr in cands:
            if f"dev {iface}" in rt:
                return ip_addr, iface
        if cands:
            return cands[0][1], cands[0][0]
    except (OSError, subprocess.CalledProcessError) as exc:
        log.debug("Net lookup error: %s", exc)
    return "127.0.0.1", "offline"


def is_ufw_blocking():
    try:
        if os.path.exists("/etc/ufw/ufw.conf"):
            with open("/etc/ufw/ufw.conf", encoding="utf-8") as fh:
                if "ENABLED=yes" in fh.read():
                    rules = ""
                    for f in ("/etc/ufw/user.rules", "/lib/ufw/user.rules"):
                        if os.path.exists(f):
                            rules += open(f, encoding="utf-8", errors="ignore").read()
                    return "8208" not in rules or "1900" not in rules
    except OSError as exc:
        log.debug("UFW check error: %s", exc)
    return False
