import logging
import os
from PyQt6.QtNetwork import QAbstractSocket, QNetworkInterface

log = logging.getLogger(__name__)


def get_net_info():
    try:
        for iface in QNetworkInterface.allInterfaces():
            flags = iface.flags()
            if not (flags & QNetworkInterface.InterfaceFlag.IsUp):
                continue
            if not (flags & QNetworkInterface.InterfaceFlag.IsRunning):
                continue
            if flags & QNetworkInterface.InterfaceFlag.IsLoopBack:
                continue
            name = iface.name()
            if name.startswith(("lo", "tun", "wg", "docker", "br-", "veth", "virbr")):
                continue
            for entry in iface.addressEntries():
                ip = entry.ip()
                if ip.protocol() == QAbstractSocket.NetworkLayerProtocol.IPv4Protocol:
                    return ip.toString(), name
    except Exception as exc:
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
