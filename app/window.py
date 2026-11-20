import os
import threading
from PyQt6.QtCore import QObject, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QMainWindow, QMenu, QMessageBox,
    QPushButton, QSystemTrayIcon, QVBoxLayout, QWidget,
)
from app.core.dlna_manager import DlnaManager
from app.core.network import is_ufw_blocking
from app.settings.config import (
    ICONS_DIR, LOGO_OFF, LOGO_ON, get_autostart, get_lang,
    get_nosleep, get_thumbs, load_folders, save_folders,
    save_lang, save_nosleep, save_thumbs, set_autostart,
)


class _WorkerBridge(QObject):
    done = pyqtSignal(object, object)


def get_icon(name):
    path = os.path.join(ICONS_DIR, f"{name}.png")
    return QIcon(path) if os.path.exists(path) else QIcon()


class FolderList(QListWidget):
    def __init__(self, cb):
        super().__init__()
        self.cb = cb
        self.setAcceptDrops(True)
        self.setIconSize(QSize(48, 48))
        self.setSpacing(5)

    def dragEnterEvent(self, e):  # pylint: disable=invalid-name
        if e.mimeData().hasUrls():
            e.accept()
        else:
            e.ignore()

    def dragMoveEvent(self, e):  # pylint: disable=invalid-name
        if e.mimeData().hasUrls():
            e.accept()
        else:
            e.ignore()

    def dropEvent(self, e):  # pylint: disable=invalid-name
        fs = load_folders()
        for u in e.mimeData().urls():
            p = u.toLocalFile()
            if os.path.isdir(p) and p not in fs:
                fs.append(p)
        save_folders(fs)
        self.cb()


class MainWindow(QMainWindow):
    def __init__(self, start_minimized=False):
        super().__init__()
        self.dlna = DlnaManager()
        self._op_lock = threading.Lock()
        self._busy = False
        self._bridge = _WorkerBridge()
        self._bridge.done.connect(self._finish_async)
        self.old_pos = None
        self.setWindowTitle("DLNA SERVER")
        self.setWindowIcon(QIcon(LOGO_ON))
        self.setFixedSize(880, 820)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        qss = os.path.join(os.path.dirname(__file__), "ui/styles.qss")
        with open(qss, encoding="utf-8") as fh:
            self.setStyleSheet(fh.read())
        wrap = QWidget(self)
        self.setCentralWidget(wrap)
        outer = QVBoxLayout(wrap)
        outer.setContentsMargins(0, 17, 0, 0)
        root = QFrame()
        root.setObjectName("MainFrame")
        outer.addWidget(root)
        ml = QVBoxLayout(root)
        ml.setContentsMargins(3, 3, 3, 3)
        ml.setSpacing(0)
        ml.addWidget(self._build_header())
        ml.addWidget(self._build_body(), 1)
        ml.addWidget(self._build_footer())
        self._setup_tray()
        self.reload_list()
        self.upd()
        if not self.dlna.is_running() and load_folders():
            self._run_async(self.dlna.start)
        self.tmr = QTimer(self)
        self.tmr.timeout.connect(self.upd)
        self.tmr.start(3000)
        if not start_minimized:
            self.show()

    def _run_async(self, fn, on_done=None):
        if self._busy:
            return
        self._busy = True
        self.main_btn.setEnabled(False)

        def worker():
            res = None
            try:
                with self._op_lock:
                    res = fn()
            finally:
                self._busy = False
                self._bridge.done.emit(res, on_done)
        threading.Thread(target=worker, daemon=True).start()

    def _finish_async(self, res, on_done):
        self.main_btn.setEnabled(True)
        self.upd()
        if on_done:
            on_done(res)

    def _build_header(self):
        hdr = QFrame()
        hdr.setObjectName("TopHeader")
        hdr.setFixedHeight(174)
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(12, 8, 14, 8)
        hl.setSpacing(14)
        left = QVBoxLayout()
        self.lang_btn = QPushButton(get_lang().upper())
        self.lang_btn.setObjectName("WinCtrlBtn")
        self.lang_btn.setFixedSize(54, 42)
        self.lang_btn.clicked.connect(self.toggle_lang)
        self.help_btn = QPushButton("?")
        self.help_btn.setObjectName("WinCtrlBtn")
        self.help_btn.setFixedSize(54, 42)
        self.help_btn.clicked.connect(self.show_help)
        left.addWidget(self.lang_btn)
        left.addWidget(self.help_btn)
        left.addStretch()
        hl.addLayout(left)
        hl.addSpacing(28)
        logo = QLabel()
        logo.setPixmap(
            QPixmap(LOGO_ON).scaled(
                132,
                132,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))
        hl.addWidget(logo)
        hl.addStretch(1)
        tb = QVBoxLayout()
        tb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tb.setSpacing(2)
        t1 = QLabel("DLNA SERVER")
        t1.setObjectName("HeaderTitle")
        t1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t2 = QLabel("MEDIA SHARING")
        t2.setObjectName("HeaderSubtitle")
        t2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tb.addWidget(t1)
        tb.addWidget(t2)
        hl.addLayout(tb)
        hl.addStretch(1)
        rb = QVBoxLayout()
        wb = QHBoxLayout()
        wb.addStretch()
        bm = QPushButton("—")
        bm.setObjectName("WinCtrlBtn")
        bm.setFixedSize(36, 30)
        bm.clicked.connect(self.showMinimized)
        bc = QPushButton("✕")
        bc.setObjectName("WinCloseBtn")
        bc.setFixedSize(36, 30)
        bc.clicked.connect(self.hide)
        wb.addWidget(bm)
        wb.addWidget(bc)
        rb.addLayout(wb)
        rb.addStretch()
        self.badge = QLabel("●  В эфире")
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.badge.setFixedSize(165, 38)
        rb.addWidget(self.badge)
        hl.addLayout(rb)
        return hdr

    def _build_body(self):
        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(28, 24, 28, 22)
        bl.setSpacing(15)
        self.section_label = QLabel("ПАПКИ МЕДИАТЕКИ")
        self.section_label.setObjectName("SectionLabel")
        bl.addWidget(self.section_label)
        well = QFrame()
        well.setObjectName("ListWell")
        well.setMinimumHeight(240)
        wl = QVBoxLayout(well)
        wl.setContentsMargins(9, 9, 9, 9)
        self.lw = FolderList(self.on_chg)
        self.lw.setObjectName("FolderList")
        wl.addWidget(self.lw)
        bl.addWidget(well, 1)
        actions = QHBoxLayout()
        actions.setSpacing(14)
        self.b_add = QPushButton("Добавить папку")
        self.b_add.setObjectName("MetalActionBtn")
        self.b_add.setIcon(get_icon("plus"))
        self.b_add.clicked.connect(self.add_f)
        self.b_del = QPushButton("Удалить")
        self.b_del.setObjectName("MetalActionBtn")
        self.b_del.setIcon(get_icon("cross"))
        self.b_del.clicked.connect(self.del_f)
        self.b_ref = QPushButton("Обновить")
        self.b_ref.setObjectName("MetalActionBtn")
        self.b_ref.setIcon(get_icon("refresh"))
        self.b_ref.clicked.connect(self.ref_f)
        for btn in (self.b_add, self.b_del, self.b_ref):
            btn.setMinimumHeight(66)
        btn.setIconSize(QSize(42, 42))
        actions.addWidget(btn)
        bl.addLayout(actions)
        return body

    def _build_footer(self):
        wrap_f = QWidget()
        wl = QVBoxLayout(wrap_f)
        wl.setContentsMargins(28, 0, 28, 18)
        wl.setSpacing(12)
        ir = QHBoxLayout()
        ir.setSpacing(10)
        self.net_lbl = QLabel()
        self.net_lbl.setObjectName("InfoPill")
        self.net_lbl.setMinimumHeight(58)
        self.net_lbl.setWordWrap(True)
        ir.addWidget(self.net_lbl, 3)
        self.slp_btn = QPushButton()
        self.slp_btn.setObjectName("InfoPillButton")
        self.slp_btn.setIcon(get_icon("shield"))
        self.slp_btn.setIconSize(QSize(30, 30))
        self.slp_btn.setMinimumHeight(58)
        self.slp_btn.clicked.connect(self.toggle_sleep)
        ir.addWidget(self.slp_btn, 2)
        self.thm_btn = QPushButton()
        self.thm_btn.setObjectName("InfoPillButton")
        self.thm_btn.setIcon(get_icon("thumbs"))
        self.thm_btn.setIconSize(QSize(30, 30))
        self.thm_btn.setMinimumHeight(58)
        self.thm_btn.clicked.connect(self.toggle_thumbs)
        ir.addWidget(self.thm_btn, 2)
        self.aut_btn = QPushButton()
        self.aut_btn.setObjectName("InfoPillButton")
        self.aut_btn.setIcon(get_icon("refresh"))
        self.aut_btn.setIconSize(QSize(26, 26))
        self.aut_btn.setMinimumHeight(58)
        self.aut_btn.clicked.connect(self.toggle_autostart)
        ir.addWidget(self.aut_btn, 2)
        wl.addLayout(ir)
        self.main_btn = QPushButton()
        self.main_btn.setObjectName("MainAction")
        self.main_btn.setMinimumHeight(82)
        self.main_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.main_btn.clicked.connect(self.tog)
        wl.addWidget(self.main_btn)
        box = QWidget()
        box_l = QVBoxLayout(box)
        box_l.setContentsMargins(0, 0, 0, 0)
        box_l.setSpacing(0)
        box_l.addWidget(wrap_f)
        ftr = QFrame()
        ftr.setObjectName("BottomBar")
        ftr.setFixedHeight(58)
        fl = QHBoxLayout(ftr)
        fl.setContentsMargins(20, 6, 18, 6)
        ic = QLabel()
        ic.setPixmap(get_icon("info").pixmap(34, 34))
        fl.addWidget(ic)
        self.st_lbl = QLabel()
        self.st_lbl.setObjectName("StatusText")
        fl.addWidget(self.st_lbl, 1)
        self.signal_lbl = QLabel("▂ ▅ ▇")
        self.signal_lbl.setObjectName("Signal")
        fl.addWidget(self.signal_lbl)
        box_l.addWidget(ftr)
        return box

    def _setup_tray(self):
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(QIcon(LOGO_ON))
        m = QMenu()
        m.addAction("Открыть", lambda: (self.showNormal(), self.activateWindow()))
        m.addAction("Выход", self.quit_app)
        self.tray.setContextMenu(m)
        self.tray.show()

    def toggle_lang(self):
        save_lang("en" if get_lang() == "ru" else "ru")
        self.upd()

    def toggle_sleep(self):
        save_nosleep(not get_nosleep())
        if self.dlna.is_running():
            self._run_async(self.dlna.start)
        else:
            self.upd()

    def toggle_thumbs(self):
        save_thumbs(not get_thumbs())
        if self.dlna.is_running():
            self._run_async(lambda: self.dlna.start(rescan=get_thumbs()))
        else:
            self.upd()

    def toggle_autostart(self):
        set_autostart(not get_autostart())
        self.upd()

    def show_help(self):
        ru = get_lang() == "ru"
        QMessageBox.information(
            self,
            "Справка" if ru else "Help",
            "DLNA SERVER v1.5\nЛокальный медиасервер."
            if ru else "DLNA SERVER v1.5\nLocal media server."
        )

    def mousePressEvent(self, e):  # pylint: disable=invalid-name
        if e.button() == Qt.MouseButton.LeftButton and e.position().y() <= 174:
            wh = self.windowHandle()
            if wh and wh.startSystemMove():
                return
            self.old_pos = e.globalPosition().toPoint()

    def mouseMoveEvent(self, e):  # pylint: disable=invalid-name
        if self.old_pos:
            delta = e.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = e.globalPosition().toPoint()

    def mouseReleaseEvent(self, _e):  # pylint: disable=invalid-name
        self.old_pos = None

    def reload_list(self):
        self.lw.clear()
        for f in load_folders():
            low = f.lower()
            ico = "folder_music" if "музык" in low or "music" in low else (
                "folder_photo" if "фото" in low or "photo" in low else "folder_video")
            it = QListWidgetItem(get_icon(ico), f)
            it.setData(Qt.ItemDataRole.UserRole, f)
            self.lw.addItem(it)

    def on_chg(self):
        self.reload_list()
        if self.dlna.is_running():
            self._run_async(self.dlna.start)
        else:
            self.upd()

    def add_f(self):
        dlg = QFileDialog(self, "Выберите папку")
        dlg.setFileMode(QFileDialog.FileMode.Directory)
        dlg.setOption(QFileDialog.Option.ShowDirsOnly, True)
        dlg.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        if dlg.exec():
            fs = load_folders()
            for f in dlg.selectedFiles():
                if os.path.isdir(f) and f not in fs:
                    fs.append(f)
            save_folders(fs)
            self.on_chg()

    def del_f(self):
        it = self.lw.currentItem()
        if it:
            save_folders([x for x in load_folders() if x != it.data(Qt.ItemDataRole.UserRole)])
        self.on_chg()

    def ref_f(self):
        if load_folders():
            self._run_async(
                lambda: self.dlna.start(
                    rescan=True), lambda _: QMessageBox.information(
                    self, "Готово", "Медиатека обновлена!"))

    def tog(self):
        ru = get_lang() == "ru"
        if self.dlna.is_running():
            self._run_async(self.dlna.stop)
        elif load_folders():
            self._run_async(
                self.dlna.start,
                lambda ok: None if ok else QMessageBox.critical(
                    self,
                    "Ошибка" if ru else "Error",
                    self.dlna.last_error))
        else:
            QMessageBox.warning(self, "Нет папок" if ru else "No Folders",
                                "Сначала добавьте папку!" if ru else "Add a folder first!")

    def quit_app(self):
        self.dlna.stop()
        self.tray.hide()
        QApplication.quit()

    def upd(self):
        ru = get_lang() == "ru"
        run = self.dlna.is_running()
        self.lang_btn.setText(get_lang().upper())
        self.section_label.setText("ПАПКИ МЕДИАТЕКИ" if ru else "MEDIA LIBRARY FOLDERS")
        self.b_add.setText("Добавить папку" if ru else "Add Folder")
        self.b_del.setText("Удалить" if ru else "Remove")
        self.b_ref.setText("Обновить" if ru else "Refresh")
        self.net_lbl.setText("🌐  " + self.dlna.status_summary(ru))
        self.slp_btn.setText(("Анти-сон: Вкл" if get_nosleep() else "Анти-сон: Выкл")
                             if ru else ("Anti-Sleep: On" if get_nosleep() else "Anti-Sleep: Off"))
        self.thm_btn.setText(("Миниатюры: Вкл" if get_thumbs() else "Миниатюры: Выкл")
                             if ru else ("Thumbnails: On" if get_thumbs() else "Thumbnails: Off"))
        self.aut_btn.setText(("Автозапуск: Вкл" if get_autostart() else "Автозапуск: Выкл")
                             if ru else ("Autostart: On" if get_autostart() else "Autostart: Off"))
        if run:
            self.tray.setIcon(QIcon(LOGO_ON))
            self.badge.setText("●  В эфире" if ru else "●  ON AIR")
            self.badge.setStyleSheet(
                "background: #15803D; color: #4ADE80; border: 2px solid #22C55E; "
                "border-radius: 15px; font-weight: bold; font-size: 14px;"
            )
            self.main_btn.setText("Остановить сервер" if ru else "Stop Server")
            self.main_btn.setProperty("running", True)
            if is_ufw_blocking():
                msg = (
                    "⚠ Включён UFW: порты 1900/udp и 8208/tcp!" if ru
                    else "⚠ UFW active: allow 1900/udp & 8208/tcp!"
                )
            else:
                msg = (
                    "DLNA SERVER запущен. Доступен для ТВ и мобильных." if ru
                    else "DLNA SERVER is running for TV & mobile devices."
                )
            self.st_lbl.setText(msg)
        else:
            self.tray.setIcon(QIcon(LOGO_OFF))
            self.badge.setText("●  Остановлен" if ru else "●  STOPPED")
            self.badge.setStyleSheet(
                "background: #991B1B; color: #FCA5A5; border: 2px solid #EF4444; "
                "border-radius: 15px; font-weight: bold; font-size: 14px;"
            )
            self.main_btn.setText("Запустить сервер" if ru else "Start Server")
            self.main_btn.setProperty("running", False)
            self.st_lbl.setText("Раздача остановлена." if ru else "Streaming is stopped.")
        self.main_btn.style().unpolish(self.main_btn)
        self.main_btn.style().polish(self.main_btn)
