#!/usr/bin/env python3
import os, sys, time
from PyQt6.QtWidgets import QApplication
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from app.settings.config import CONFIG_DIR
from app.window import MainWindow

SERVER_NAME = os.path.join(CONFIG_DIR, "instance.sock")

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    sock = QLocalSocket()
    sock.connectToServer(SERVER_NAME)
    if sock.waitForConnected(300):
        sock.write(b"SHOW")
        sock.waitForBytesWritten(300)
        sock.disconnectFromServer()
        sys.exit(0)

    QLocalServer.removeServer(SERVER_NAME)
    srv = QLocalServer()
    srv.listen(SERVER_NAME)

    minimized = "--autostart" in sys.argv
    if minimized:
        time.sleep(3)
    win = MainWindow(start_minimized=minimized)

    def on_new_conn():
        conn = srv.nextPendingConnection()
        if conn:
            def wake():
                win.showNormal()
                win.raise_()
                win.activateWindow()
            conn.readyRead.connect(wake)

    srv.newConnection.connect(on_new_conn)
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
