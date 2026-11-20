#!/usr/bin/env python3
import sys, time
from PyQt6.QtWidgets import QApplication
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from app.window import MainWindow

SERVER_NAME = "dlna_server_single_instance_lock"

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Проверяем, не запущена ли уже программа
    sock = QLocalSocket()
    sock.connectToServer(SERVER_NAME)
    if sock.waitForConnected(200):
        sock.write(b"SHOW")
        sock.waitForBytesWritten(200)
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
            conn.readyRead.connect(lambda: (win.showNormal(), win.activateWindow(), win.raise_()))

    srv.newConnection.connect(on_new_conn)
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
