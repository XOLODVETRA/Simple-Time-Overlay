import sys
import json
import os
import time
from PyQt5 import QtWidgets, QtGui, QtCore
import winreg

CONFIG_FILE = os.path.join(
    os.getenv('APPDATA', os.path.expanduser('~')), "TimeOverlay", "time_overlay_config.json"
)
APP_NAME = "TimeOverlay"

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class SettingsDialog(QtWidgets.QDialog):
    settingsChanged = QtCore.pyqtSignal(dict)

    def __init__(self, parent=None, config=None):
        super().__init__(parent)
        self.setWindowTitle("Time Settings")
        self.config = config or {}

        icon2_path = resource_path("icon2.ico")
        if os.path.exists(icon2_path):
            self.setWindowIcon(QtGui.QIcon(icon2_path))

        self.selected_font = QtGui.QFont("Arial", self.config.get("time_size", 20), QtGui.QFont.Bold)

        self.init_ui()
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)

    def init_ui(self):
        layout = QtWidgets.QFormLayout(self)

        self.spin_x = QtWidgets.QSpinBox()
        self.spin_x.setRange(0, 5000)
        self.spin_x.setValue(self.config.get("time_position", [100, 50])[0])
        layout.addRow("Position X:", self.spin_x)

        self.spin_y = QtWidgets.QSpinBox()
        self.spin_y.setRange(0, 5000)
        self.spin_y.setValue(self.config.get("time_position", [100, 50])[1])
        layout.addRow("Position Y:", self.spin_y)

        self.spin_size = QtWidgets.QSpinBox()
        self.spin_size.setRange(1, 100)
        self.spin_size.setValue(self.config.get("time_size", 20))
        layout.addRow("Text size:", self.spin_size)

        self.font_btn = QtWidgets.QPushButton("Choose Font")
        self.font_btn.clicked.connect(self.choose_font)
        layout.addRow("Font:", self.font_btn)

        self.font_label = QtWidgets.QLabel(f"{self.selected_font.family()}, {self.selected_font.pointSize()}pt")
        layout.addRow("", self.font_label)

        self.color_btn = QtWidgets.QPushButton("Choose Color")
        self.color_btn.clicked.connect(self.choose_color)
        layout.addRow("Text color:", self.color_btn)

        self.color_preview = QtWidgets.QLabel()
        self.color_preview.setFixedSize(40, 20)
        layout.addRow("", self.color_preview)

        self.transp_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.transp_slider.setRange(10, 100)
        transp = int(self.config.get("transparency", 1) * 100)
        self.transp_slider.setValue(transp)
        layout.addRow("Transparency:", self.transp_slider)

        self.transp_label = QtWidgets.QLabel(f"{transp / 100:.2f}")
        layout.addRow("", self.transp_label)
        self.transp_slider.valueChanged.connect(lambda v: self.transp_label.setText(f"{v / 100:.2f}"))

        self.show_time_cb = QtWidgets.QCheckBox("Show time")
        self.show_time_cb.setChecked(self.config.get("show_time", True))
        layout.addRow(self.show_time_cb)

        self.show_seconds_cb = QtWidgets.QCheckBox("Show seconds")
        self.show_seconds_cb.setChecked(self.config.get("show_seconds", True))
        layout.addRow(self.show_seconds_cb)

        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close)
        layout.addRow(btn_box)
        btn_box.rejected.connect(self.reject)

        self.set_color_preview(self.config.get("time_color", [255, 255, 255]))

        self.spin_x.valueChanged.connect(self.emit_settings)
        self.spin_y.valueChanged.connect(self.emit_settings)
        self.spin_size.valueChanged.connect(self.emit_settings)
        self.transp_slider.valueChanged.connect(self.emit_settings)
        self.show_time_cb.stateChanged.connect(self.emit_settings)
        self.show_seconds_cb.stateChanged.connect(self.emit_settings)

    def choose_color(self):
        initial = QtGui.QColor(*self.config.get("time_color", [255, 255, 255]))
        color = QtWidgets.QColorDialog.getColor(initial, self, "Choose text color")
        if color.isValid():
            rgb = [color.red(), color.green(), color.blue()]
            self.set_color_preview(rgb)
            self.emit_settings()

    def set_color_preview(self, rgb):
        r, g, b = rgb
        self.color_preview.setStyleSheet(f"background-color: rgb({r},{g},{b}); border: 1px solid black;")
        self.selected_color = [r, g, b]

    def choose_font(self):
        font, ok = QtWidgets.QFontDialog.getFont(self.selected_font, self, "Choose Font")
        if ok:
            self.selected_font = font
            self.font_label.setText(f"{font.family()}, {font.pointSize()}pt")
            self.spin_size.setValue(font.pointSize())
            self.emit_settings()

    def emit_settings(self):
        new_settings = {
            "time_position": [self.spin_x.value(), self.spin_y.value()],
            "time_size": self.spin_size.value(),
            "time_color": getattr(self, "selected_color", self.config.get("time_color", [255, 255, 255])),
            "transparency": self.transp_slider.value() / 100,
            "show_time": self.show_time_cb.isChecked(),
            "show_seconds": self.show_seconds_cb.isChecked(),
            "font_family": self.selected_font.family(),
            "font_weight": self.selected_font.weight(),
            "font_italic": self.selected_font.italic()
        }
        self.settingsChanged.emit(new_settings)


class OverlayWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.load_config()
        self.init_ui()
        self.apply_window_flags()
        self.update_clock()
        self.show()

    def load_config(self):
        default_config = {
            "time_position": [100, 50],
            "time_color": [255, 255, 255],
            "transparency": 1,
            "time_size": 20,
            "show_time": True,
            "autostart": False,
            "show_seconds": True,
            "font_family": "Arial",
            "font_weight": QtGui.QFont.Bold,
            "font_italic": False
        }
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    self.config = json.load(f)
                    for key in default_config:
                        if key not in self.config:
                            self.config[key] = default_config[key]
            except Exception:
                self.config = default_config
        else:
            self.config = default_config

    def save_config(self):
        config_dir = os.path.dirname(CONFIG_FILE)
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print("Error saving config:", e)

    def apply_window_flags(self):
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.Tool
        )
        self.setWindowOpacity(self.config["transparency"])

        hwnd = self.winId().__int__()
        import ctypes
        ctypes.windll.user32.SetParent(hwnd, -3)

    def init_ui(self):
        self.label = QtWidgets.QLabel(self)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.update_label_style()

        self.setGeometry(
            self.config["time_position"][0],
            self.config["time_position"][1],
            200, 50
        )

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_clock)
        self.timer.start(1000)

        self.create_tray_icon()

    def update_clock(self):
        if not self.config["show_time"]:
            self.label.clear()
            return
        fmt = "%H:%M:%S" if self.config["show_seconds"] else "%H:%M"
        current_time = time.strftime(fmt)
        self.label.setText(current_time)

        metrics = self.label.fontMetrics()
        width = metrics.horizontalAdvance(current_time) + 20
        height = metrics.height() + 10
        self.resize(width, height)
        self.label.resize(width, height)

    def update_label_style(self):
        font = QtGui.QFont(
            self.config.get("font_family", "Arial"),
            self.config.get("time_size", 20),
            self.config.get("font_weight", QtGui.QFont.Bold),
            self.config.get("font_italic", False)
        )
        self.label.setFont(font)
        r, g, b = self.config["time_color"]
        self.label.setStyleSheet(f"color: rgb({r},{g},{b}); background-color: transparent;")

    def create_tray_icon(self):
        self.tray = QtWidgets.QSystemTrayIcon(self)
        icon_path = resource_path("icon.ico")
        if os.path.exists(icon_path):
            icon = QtGui.QIcon(icon_path)
        else:
            icon = QtGui.QIcon.fromTheme("clock")
            if icon.isNull():
                pix = QtGui.QPixmap(64, 64)
                pix.fill(QtGui.QColor("black"))
                painter = QtGui.QPainter(pix)
                painter.setPen(QtGui.QPen(QtGui.QColor("white")))
                painter.setFont(QtGui.QFont("Arial", 32))
                painter.drawText(pix.rect(), QtCore.Qt.AlignCenter, "T")
                painter.end()
                icon = QtGui.QIcon(pix)
        self.tray.setIcon(icon)
        self.tray.setToolTip("Time Overlay")

        self.menu = QtWidgets.QMenu()

        self.settings_action = self.menu.addAction("Time Settings")
        self.settings_action.triggered.connect(self.open_settings)

        self.autostart_action = QtWidgets.QAction("Autostart", checkable=True)
        self.autostart_action.setChecked(self.config.get("autostart", False))
        self.autostart_action.triggered.connect(self.toggle_autostart)
        self.menu.addAction(self.autostart_action)

        self.menu.addSeparator()

        exit_action = self.menu.addAction("Exit")
        exit_action.triggered.connect(self.exit_app)

        self.tray.setContextMenu(self.menu)

        self.tray.activated.connect(self.on_tray_activated)

        self.tray.show()

    def on_tray_activated(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.Trigger:
            self.open_settings()

    def toggle_autostart(self):
        val = self.autostart_action.isChecked()
        self.config["autostart"] = val
        self.save_config()
        self.setup_autostart(val)

    def setup_autostart(self, enable=None):
        if sys.platform != "win32":
            return
        if enable is None:
            enable = self.config.get("autostart", False)
        app_name = APP_NAME
        exe_path = f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'

        try:
            key = winreg.HKEY_CURRENT_USER
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(key, key_path, 0, winreg.KEY_SET_VALUE) as reg_key:
                if enable:
                    winreg.SetValueEx(reg_key, app_name, 0, winreg.REG_SZ, exe_path)
                else:
                    try:
                        winreg.DeleteValue(reg_key, app_name)
                    except FileNotFoundError:
                        pass
        except Exception as e:
            print("Autostart error:", e)

    def open_settings(self):
        dlg = SettingsDialog(self, self.config)
        dlg.settingsChanged.connect(self.apply_settings)
        dlg.exec_()

    def apply_settings(self, new_config):
        self.config.update(new_config)
        self.save_config()
        self.update_label_style()
        self.setWindowOpacity(self.config["transparency"])
        self.move(self.config["time_position"][0], self.config["time_position"][1])
        self.update_clock()

    def exit_app(self):
        self.tray.hide()
        QtWidgets.qApp.quit()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    overlay = OverlayWindow()
    sys.exit(app.exec_())
