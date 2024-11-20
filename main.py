import logging
import os
import subprocess
import sys

from dotenv import load_dotenv
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QApplication, QMenu, QSystemTrayIcon

load_dotenv()

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

OPENVPN_COMMAND = os.environ.get("OPENVPN3_EXECUTABLE_PATH", "openvpn3")
CONFIG_FILE_PATH = os.environ.get("OPENVPN3_CONFIG_FILE_PATH", "config.ovpn")
CHECK_CONNECTION_TIMEOUT = os.environ.get("CHECK_CONNECTION_TIMEOUT", 2000)


class TrayApp:
    def __init__(self):
        self.app = QApplication([])
        self.app.setQuitOnLastWindowClosed(False)
        self.tray_icons = {
            "disabled": QIcon("wifi-grey.png"),
            "enabled": QIcon("wifi.png"),
        }
        self.tray = QSystemTrayIcon()
        self.set_tray_icon("disabled")
        self.tray.setVisible(True)
        self.menu_actions = [
            self.create_menu_action("Connect", self.action_connect),
            self.create_menu_action("Disconnect", self.action_disconnect),
            self.create_menu_action("Exit", self.action_exit),
        ]
        self.menu = QMenu()
        self.current_session_id = None

    def start(self):
        for action in self.menu_actions:
            self.menu.addAction(action)
        self.tray.setContextMenu(self.menu)

        timer = QTimer()
        timer.start(CHECK_CONNECTION_TIMEOUT)
        timer.timeout.connect(self.timer_loop)
        sys.exit(self.app.exec_())

    def timer_loop(self):
        self.check_session()

    def check_session(self):
        if self.ovpn_connection_exists():
            self.set_tray_icon("enabled")
            return

        self.set_tray_icon("disabled")

    def create_menu_action(self, name, callback) -> QAction:
        action = QAction(name)
        action.triggered.connect(callback)
        return action

    def set_tray_icon(self, icon_name: str):
        icon = self.tray_icons.get(icon_name)
        self.tray.setIcon(icon)

    def action_exit(self):
        if self.current_session_id:
            self.action_disconnect()
        sys.exit(self.app.quit())

    def action_connect(self):
        self.ovpn_connect()
        self.check_session()


    def action_disconnect(self):
        self.ovpn_disconnect()
        self.check_session()

    def ovpn_connection_exists(self) -> bool:
        out = self.get_subprocess_output([OPENVPN_COMMAND, "sessions-list"])
        log.debug(out)

        if "Client connected" in out:
            self.set_current_session_id(out)
            return True

        return False

    def ovpn_connect(self):
        log.info("Will try to connect to OpenVPN")
        out = self.get_subprocess_output([
            OPENVPN_COMMAND,
            "session-start",
            "--config",
            CONFIG_FILE_PATH,
        ])
        log.debug(out)

    def ovpn_disconnect(self):
        log.info("Will disconnect from OpenVPN")
        out = self.get_subprocess_output([
            OPENVPN_COMMAND,
            "session-manage",
            "--disconnect",
            "--session-path",
            self.current_session_id,
        ])
        log.debug(out)

    def set_current_session_id(self, ovpn_output):
        lines = ovpn_output.split("\n")
        for line_raw in lines:
            line = line_raw.strip()
            if line.startswith("Path: "):
                self.current_session_id = line.split(":")[-1].strip()

    def get_subprocess_output(self, command):
        out = ""
        try:
            out = subprocess.run(
                command, capture_output=True, check=False,  # noqa: S603
            ).stdout.decode("utf8").strip()
        except Exception:
            log.exception("Subprocess failed")

        return out

if __name__ == "__main__":
    TrayApp().start()
