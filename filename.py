import sys
import os
import subprocess
import time
import datetime
import urllib.parse
import urllib.request
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

APP_PORT = int(os.environ.get("APP_PORT", "5050"))
BROWSER_PORT = int(os.environ.get("BROWSER_PORT", "5000"))

# If running in a container/headless mode, start the Gradio backend and exit
HEADLESS = os.environ.get("PHANTOM_HEADLESS") == "1" or "--headless" in sys.argv
if HEADLESS:
    port = int(os.environ.get("BACKEND_PORT", str(APP_PORT)))
    req = urllib.request.Request(f"http://localhost:{port}", headers={"User-Agent": "RAAMA"})
    for _ in range(3):
        try:
            with urllib.request.urlopen(req, timeout=1.0):
                print(f"Backend already running on port {port}")
                sys.exit(0)
        except Exception:
            time.sleep(0.25)

    app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")
    if os.path.exists(app_path):
        log_path = os.path.join(os.path.dirname(app_path), "app_log.txt")
        try:
            log_file = open(log_path, "a", encoding="utf-8")
            popen = subprocess.Popen(
                [sys.executable, app_path],
                cwd=os.path.dirname(app_path),
                stdout=log_file,
                stderr=subprocess.STDOUT,
                env={**os.environ, "GRADIO_SERVER_PORT": str(port)},
            )

            # Wait briefly for server to appear
            started = False
            start_time = time.time()
            timeout = 15.0
            while time.time() - start_time < timeout:
                try:
                    with urllib.request.urlopen(req, timeout=1.0):
                        started = True
                        break
                except Exception:
                    time.sleep(0.5)

            if started:
                print(f"app.py started and reachable on port {port}")
                sys.exit(0)
            else:
                print(f"Failed to start app.py on port {port}. See {log_path} for details.")
                sys.exit(1)
        except Exception as e:
            print("Could not auto-start app.py:", e)
            sys.exit(1)
    else:
        print("app.py not found in project folder")
        sys.exit(1)

from PyQt6.QtCore import QUrl, pyqtSignal, QObject, Qt, QSize, QThread
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QToolBar, QLineEdit, QTabWidget,
    QStatusBar, QLabel, QPushButton, QWidget, QVBoxLayout,
    QHBoxLayout, QProgressBar, QTextEdit, QSplitter, QFrame
)
from PyQt6.QtGui import QIcon, QAction, QFont, QTextCursor, QDesktopServices
from PyQt6.QtWebEngineCore import (
    QWebEngineProfile, QWebEngineUrlRequestInterceptor,
    QWebEngineUrlRequestInfo, QWebEnginePage
)
from PyQt6.QtWebEngineWidgets import QWebEngineView


# ── Cohesive Startpage HTML ──────────────────────────────────────────
STARTPAGE_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Phantom Privacy Browser</title>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <style>
    body{background:#071025;color:#e6eef8;font-family:Inter,Segoe UI,Helvetica,Arial;margin:0;}
    .wrap{max-width:980px;margin:48px auto;padding:28px;background:linear-gradient(180deg,rgba(255,255,255,0.02),rgba(255,255,255,0.01));border-radius:16px;border:1px solid rgba(255,255,255,0.03)}
    h1{font-weight:800;font-size:28px;margin:0 0 6px;color:#f8fafc}
    p.lead{color:#94a3b8;margin:6px 0 18px}
    .cards{display:flex;gap:12px;flex-wrap:wrap}
    .card{flex:1 1 220px;padding:14px;border-radius:12px;background:rgba(255,255,255,0.01);border:1px solid rgba(255,255,255,0.03)}
    .card h3{margin:0 0 6px;font-size:14px;color:#cfe7ff}
    .home-actions{margin-top:18px;display:flex;gap:10px}
    .btn{background:#0ea5e9;color:#042033;padding:8px 14px;border-radius:10px;text-decoration:none;font-weight:700}
    .link{color:#93c5fd;text-decoration:none}
    .small{font-size:13px;color:#9aa9bd}
    .search-wrap { width: min(820px, 100%); margin: 24px auto 18px; }
    .search-box {
      display: flex; align-items: center; gap: 10px; width: 100%;
      background: rgba(15,23,42,0.92); border: 1px solid rgba(148,163,184,0.2);
      border-radius: 18px; padding: 10px 12px 10px 16px; box-shadow: 0 18px 48px rgba(15,23,42,0.45);
    }
    .search-box input {
      flex: 1; border: none; background: transparent; color: #f8fafc; font-size: 18px; padding: 10px 0; outline: none;
    }
    .search-box input::placeholder { color: #64748b; }
    .search-box button {
      border: none; border-radius: 12px; background: linear-gradient(135deg, #38bdf8, #8b5cf6); color: #03131f;
      font-weight: 800; padding: 12px 20px; cursor: pointer; font-size: 15px;
    }
  </style>
</head>
<body>
  <div class="wrap">
    <h1>RAAMA Privacy Browser</h1>
    <p class="lead">Private, in-memory browsing with a built-in AI assistant.
    Use the Copilot panel to access the AI Studio (local service).</p>

    <div class="search-wrap">
      <form class="search-box" action="https://duckduckgo.com/" method="get" target="_blank">
        <input type="text" name="q" placeholder="Search the web or enter a URL..." aria-label="Search" />
        <button type="submit">Search</button>
      </form>
    </div>

    <div class="home-actions" style="justify-content:center;">
      <a class="btn" href="http://localhost:5050/chat/">Open AI Studio</a>
      <a class="link" href="https://duckduckgo.com" target="_blank">Search (DuckDuckGo)</a>
    </div>
    <p class="small" style="margin-top:14px;text-align:center">Tip: If the AI Studio is not reachable, toggle the Copilot panel to retry.</p>
  </div>
</body>
</html>
"""


def start_local_browser_server(port: int = BROWSER_PORT):
    """Serve the browser landing page on a dedicated local port for the desktop browser app."""
    try:
        with urllib.request.urlopen(f"http://localhost:{port}", timeout=1.0):
            print(f"RAAMA browser already running at http://localhost:{port}")
            return
    except Exception:
        pass

    class BrowserRequestHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            body = STARTPAGE_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            return

    server = ThreadingHTTPServer(("0.0.0.0", port), BrowserRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"RAAMA browser server started at http://localhost:{port}")
    print(f"LAN URL: http://10.57.162.222:{port}/")
    return server


# Start the browser landing page server so the browser app is assigned to 5000.
start_local_browser_server()


# ── Network Interceptor ───────────────────────────────────────────────
class InterceptorSignals(QObject):
    url_blocked = pyqtSignal(str)
    url_upgraded = pyqtSignal(str)


class PrivacyUrlInterceptor(QWebEngineUrlRequestInterceptor):
    TRACKER_DOMAINS = {
        "doubleclick.net", "google-analytics.com", "googlesyndication.com",
        "adservice.google.com", "googleadservices.com", "facebook.com/tr",
        "connect.facebook.net", "analytics.twitter.com", "scorecardresearch.com",
        "adnxs.com", "criteo.com", "criteo.net", "amazon-adsystem.com",
        "outbrain.com", "taboola.com", "pubmatic.com", "rubiconproject.com",
        "moatads.com", "quantserve.com", "hotjar.com", "segment.io",
        "segment.com", "mixpanel.com", "chartbeat.com", "omtrdc.net",
        "bluekai.com", "ads-twitter.com", "adsymptotic.com", "casalemedia.com",
        "openx.net", "yieldmanager.com", "smartadserver.com", "zedo.com",
        "adroll.com", "buysellads.com", "exponential.com"
    }

    TRACKER_KEYWORDS = [
        "/ad/", "/ads/", "/pixel.gif", "analytics.js", "gtm.js",
        "telemetry", "track.js", "tracker.js", "/collect?"
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.signals = InterceptorSignals()
        self.blocked_count = 0
        self.upgraded_count = 0

    def interceptRequest(self, info: QWebEngineUrlRequestInfo):
        url = info.requestUrl()
        scheme = url.scheme().lower()
        host = url.host().lower()
        url_str = url.toString().lower()

        # Automatic HTTPS upgrade (exclude localhost / app.py)
        if scheme == "http" and host not in ("localhost", "127.0.0.1", ""):
            upgraded_url = QUrl(url)
            upgraded_url.setScheme("https")
            info.redirectUrl(upgraded_url)
            self.upgraded_count += 1
            self.signals.url_upgraded.emit(url.toString())
            return

        should_block = False
        if any(domain in host for domain in self.TRACKER_DOMAINS):
            should_block = True
        elif any(keyword in url_str for keyword in self.TRACKER_KEYWORDS):
            should_block = True

        if should_block:
            info.block(True)
            self.blocked_count += 1
            self.signals.url_blocked.emit(host or url_str)


class PrivacyWebPage(QWebEnginePage):
    def __init__(self, profile: QWebEngineProfile, parent=None):
        super().__init__(profile, parent)


# ── AI Copilot Sidebar Widget ─────────────────────────────────────────
class RaamaAssistantPanel(QWidget):
    """Seamless right-docked AI Assistant panel hosting app.py."""

    def __init__(self, main_window, port: int, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.port = port
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Unified Header Bar matching browser chrome with status + controls
        header = QWidget(self)
        header.setFixedHeight(38)
        header.setStyleSheet("""
            QWidget {
                background: #0f172a;
                border-bottom: 1px solid #1e293b;
                border-left: 1px solid #1e293b;
            }
        """)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(12, 0, 8, 0)
        h_layout.setSpacing(6)

        title = QLabel("🤖 RAAMA Copilot", self)
        title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        title.setStyleSheet("color: #38bdf8; border: none; background: transparent;")

        badge = QLabel("HF AI", self)
        badge.setStyleSheet("""
            color: #818cf8;
            background: rgba(129, 140, 248, 0.12);
            border: 1px solid rgba(129, 140, 248, 0.25);
            border-radius: 4px;
            padding: 1px 5px;
            font-size: 10px;
            font-weight: 600;
        """)

        # Status indicator and actions
        self.copilot_status = QLabel("🔴 Disconnected", self)
        self.copilot_status.setStyleSheet("color:#f97316; font-size:12px; padding:0 6px;")

        btn_check = QPushButton("Check", self)
        btn_check.setToolTip("Check Copilot status and reload if available")
        btn_check.setFixedSize(46, 24)
        btn_check.clicked.connect(self.check_backend)

        btn_reload = QPushButton("🔄", self)
        btn_reload.setToolTip("Reload AI Chat")
        btn_reload.setFixedSize(26, 24)
        btn_reload.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reload.setStyleSheet("""
            QPushButton { background: transparent; color: #94a3b8; border: none; border-radius: 4px; font-size: 11px; }
            QPushButton:hover { background: #1e293b; color: #f8fafc; }
        """)
        btn_reload.clicked.connect(self.reload_assistant)

        btn_tab = QPushButton("↗️", self)
        btn_tab.setToolTip("Open in New Tab")
        btn_tab.setFixedSize(26, 24)
        btn_tab.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_tab.setStyleSheet("""
            QPushButton { background: transparent; color: #94a3b8; border: none; border-radius: 4px; font-size: 11px; }
            QPushButton:hover { background: #1e293b; color: #f8fafc; }
        """)
        btn_tab.clicked.connect(self.open_in_new_tab)

        btn_ext = QPushButton("🌐", self)
        btn_ext.setToolTip("Open AI Studio in external browser")
        btn_ext.setFixedSize(26, 24)
        btn_ext.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(f"http://localhost:{self.port}")))

        btn_close = QPushButton("✕", self)
        btn_close.setToolTip("Hide Copilot Sidebar")
        btn_close.setFixedSize(26, 24)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton { background: transparent; color: #64748b; border: none; border-radius: 4px; font-size: 11px; font-weight: bold; }
            QPushButton:hover { background: #1e293b; color: #f87171; }
        """)
        btn_close.clicked.connect(self.main_window.toggle_assistant_panel)

        h_layout.addWidget(title)
        h_layout.addWidget(badge)
        h_layout.addStretch()
        h_layout.addWidget(self.copilot_status)
        h_layout.addWidget(btn_check)
        h_layout.addWidget(btn_reload)
        h_layout.addWidget(btn_tab)
        h_layout.addWidget(btn_ext)
        h_layout.addWidget(btn_close)
        layout.addWidget(header)

        # Embedded WebEngineView for app.py (lazy load)
        self.web_view = QWebEngineView(self)
        self.web_view.setStyleSheet("background: #070913;")
        # Defer loading until status is checked
        if self.check_backend():
            self.web_view.load(QUrl(f"http://localhost:{self.port}"))
        layout.addWidget(self.web_view)

    def reload_assistant(self):
        if self.check_backend():
            self.web_view.reload()
        else:
            # indicate disconnected
            self.copilot_status.setText("🔴 Disconnected")

    def open_in_new_tab(self):
        self.main_window.add_new_tab(QUrl(f"http://localhost:{self.port}"), title="🤖 RAAMA Copilot")

    def check_backend(self) -> bool:
        """Quickly probe the local AI Studio and update status label.
        Returns True if reachable.
        """
        try:
            req = urllib.request.Request(f"http://localhost:{self.port}", headers={"User-Agent": "RAAMA"})
            with urllib.request.urlopen(req, timeout=1.0):
                self.copilot_status.setText("🟢 Connected")
                self.copilot_status.setStyleSheet("color:#10b981; font-size:12px; padding:0 6px;")
                return True
        except Exception:
            self.copilot_status.setText("🔴 Disconnected")
            self.copilot_status.setStyleSheet("color:#f97316; font-size:12px; padding:0 6px;")
            return False


# ── Main Browser Window ───────────────────────────────────────────────
class RaamaPrivacyBrowserWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RAAMA Privacy Browser")
        self.resize(1380, 860)

        # Use fixed backend port 5050 and dedicated browser port 5000
        self.backend_port = APP_PORT
        self.browser_port = BROWSER_PORT
        self.ensure_app_py_running()

        # In-Memory Profile
        self.profile = QWebEngineProfile(self)
        self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.NoCache)
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies)
        self.profile.setCachePath("")
        self.profile.setPersistentStoragePath("")

        # Network Interceptor
        self.interceptor = PrivacyUrlInterceptor(self)
        self.interceptor.signals.url_blocked.connect(self.on_url_blocked)
        self.interceptor.signals.url_upgraded.connect(self.on_url_upgraded)
        self.profile.setUrlRequestInterceptor(self.interceptor)

        # UI Setup
        self.init_ui()
        self.add_new_tab(is_home=True)

    def ensure_app_py_running(self):
        # Try a few quick attempts to connect to the backend first
        req = urllib.request.Request(f"http://localhost:{self.backend_port}", headers={"User-Agent": "RAAMA"})
        for _ in range(3):
            try:
                with urllib.request.urlopen(req, timeout=1.0):
                    return
            except Exception:
                time.sleep(0.25)

        app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")
        if os.path.exists(app_path):
            log_path = os.path.join(os.path.dirname(app_path), "app_log.txt")
            try:
                # Start app.py and capture logs so failures are visible
                log_file = open(log_path, "a", encoding="utf-8")
                popen = subprocess.Popen(
                    [sys.executable, app_path],
                    cwd=os.path.dirname(app_path),
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    creationflags=(subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0),
                    env={**os.environ, "GRADIO_SERVER_PORT": str(self.backend_port)}
                )

                # Wait for server to come up (polling)
                started = False
                start_time = time.time()
                timeout = 12.0
                while time.time() - start_time < timeout:
                    try:
                        with urllib.request.urlopen(req, timeout=1.0):
                            started = True
                            break
                    except Exception:
                        time.sleep(0.5)

                if not started:
                    print(f"app.py did not become reachable within {timeout} seconds. See {log_path} for details. Using port {self.backend_port}.")

            except Exception as e:
                print("Could not auto-start app.py:", e)

    def init_ui(self):
        self.splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.setCentralWidget(self.splitter)

        # Tabs
        self.tabs = QTabWidget(self)
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.on_tab_changed)

        # New Tab (+)
        self.add_tab_btn = QPushButton("+", self)
        self.add_tab_btn.setFixedSize(28, 28)
        self.add_tab_btn.setToolTip("Open New Private Tab")
        self.add_tab_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_tab_btn.setStyleSheet("""
            QPushButton {
                background: #1e293b;
                color: #94a3b8;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 15px;
            }
            QPushButton:hover { background: #334155; color: #f8fafc; }
        """)
        self.add_tab_btn.clicked.connect(lambda: self.add_new_tab())
        self.tabs.setCornerWidget(self.add_tab_btn, Qt.Corner.TopRightCorner)

        self.splitter.addWidget(self.tabs)

        # Assistant Sidebar Panel (Collapsed by default for a clean browser experience)
        self.assistant_panel = RaamaAssistantPanel(self, self.backend_port, self)
        self.assistant_panel.setMinimumWidth(360)
        self.assistant_panel.setMaximumWidth(520)
        self.splitter.addWidget(self.assistant_panel)

        # Set default proportions & hide sidebar initially
        self.splitter.setSizes([1000, 380])
        self.assistant_panel.setVisible(False)

        # ── Navigation Toolbar ────────────────────────────────────────
        toolbar = QToolBar("Navigation", self)
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(16, 16))
        toolbar.setFixedHeight(44)
        self.addToolBar(toolbar)

        # Sleek Brand Label on top left
        self.brand_label = QLabel(" 🛡️ RAAMA ", self)
        self.brand_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.brand_label.setStyleSheet("color: #38bdf8; padding: 0 8px 0 4px;")
        toolbar.addWidget(self.brand_label)

        # Nav Buttons
        self.new_tab_action = QAction("＋", self)
        self.new_tab_action.setToolTip("New Tab")
        self.new_tab_action.triggered.connect(lambda: self.add_new_tab())
        toolbar.addAction(self.new_tab_action)

        self.back_action = QAction("◀", self)
        self.back_action.setToolTip("Back")
        self.back_action.triggered.connect(self.navigate_back)
        toolbar.addAction(self.back_action)

        self.forward_action = QAction("▶", self)
        self.forward_action.setToolTip("Forward")
        self.forward_action.triggered.connect(self.navigate_forward)
        toolbar.addAction(self.forward_action)

        self.reload_action = QAction("🔄", self)
        self.reload_action.setToolTip("Reload Page")
        self.reload_action.triggered.connect(self.reload_page)
        toolbar.addAction(self.reload_action)

        self.home_action = QAction("🏠", self)
        self.home_action.setToolTip("Incognito Home")
        self.home_action.triggered.connect(self.navigate_home)
        toolbar.addAction(self.home_action)

        toolbar.addSeparator()

        # Modern Address Bar
        self.address_bar = QLineEdit(self)
        self.address_bar.setPlaceholderText("Search with DuckDuckGo or enter URL...")
        self.address_bar.returnPressed.connect(self.navigate_to_url)
        self.address_bar.setStyleSheet("""
            QLineEdit {
                background: #0b1120;
                color: #f8fafc;
                border: 1px solid #1e293b;
                border-radius: 8px;
                padding: 6px 14px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #38bdf8;
                background: #0d1527;
            }
        """)
        toolbar.addWidget(self.address_bar)

        # Native-looking Copilot Pill on the right
        self.assistant_toggle_btn = QPushButton("🤖 Copilot", self)
        self.assistant_toggle_btn.setToolTip("Toggle RAAMA AI Copilot Sidebar")
        self.assistant_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_assistant_btn_style(is_active=False)
        self.assistant_toggle_btn.clicked.connect(self.toggle_assistant_panel)
        toolbar.addWidget(self.assistant_toggle_btn)

        # ── Status Bar ────────────────────────────────────────────────
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setMaximumWidth(120)
        self.progress_bar.setFixedHeight(10)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #1e293b;
                border-radius: 5px;
                background-color: #0b1120;
            }
            QProgressBar::chunk {
                background-color: #38bdf8;
                border-radius: 4px;
            }
        """)
        self.status_bar.addPermanentWidget(self.progress_bar)

        self.shield_label = QLabel("🛡️ Blocked: 0 | 🔒 HTTPS Upgraded: 0", self)
        self.shield_label.setStyleSheet("color: #64748b; font-size: 11px; padding: 0 8px;")
        self.status_bar.addPermanentWidget(self.shield_label)

        # ── Global Stylesheet ─────────────────────────────────────────
        self.setStyleSheet("""
            QMainWindow { background: #090d16; }
            QToolBar {
                background: #0f172a;
                border-bottom: 1px solid #1e293b;
                padding: 3px 8px;
                spacing: 4px;
            }
            QToolBar QToolButton {
                background: transparent;
                color: #94a3b8;
                border-radius: 6px;
                padding: 4px 6px;
                font-size: 12px;
            }
            QToolBar QToolButton:hover {
                background: #1e293b;
                color: #f8fafc;
            }
            QToolBar QToolButton:disabled {
                color: #475569;
            }
            QTabWidget::pane {
                border: none;
                background: #090d16;
            }
            QTabBar::tab {
                background: #0f172a;
                color: #94a3b8;
                padding: 7px 16px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 2px;
                min-width: 130px;
                max-width: 220px;
                font-size: 12px;
                border: 1px solid transparent;
            }
            QTabBar::tab:selected {
                background: #090d16;
                color: #38bdf8;
                border-top: 2px solid #38bdf8;
            }
            QTabBar::tab:hover:!selected {
                background: #1e293b;
                color: #f8fafc;
            }
            QStatusBar {
                background: #0f172a;
                color: #94a3b8;
                border-top: 1px solid #1e293b;
                font-size: 11px;
            }
            QSplitter::handle {
                background: #1e293b;
                width: 1px;
            }
        """)

    def update_assistant_btn_style(self, is_active: bool):
        if is_active:
            self.assistant_toggle_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(56, 189, 248, 0.15);
                    color: #38bdf8;
                    border: 1px solid #38bdf8;
                    border-radius: 8px;
                    font-weight: 600;
                    padding: 5px 14px;
                    font-size: 12px;
                    margin-left: 6px;
                }
                QPushButton:hover {
                    background: rgba(56, 189, 248, 0.25);
                }
            """)
        else:
            self.assistant_toggle_btn.setStyleSheet("""
                QPushButton {
                    background: #1e293b;
                    color: #cbd5e1;
                    border: 1px solid #334155;
                    border-radius: 8px;
                    font-weight: 600;
                    padding: 5px 14px;
                    font-size: 12px;
                    margin-left: 6px;
                }
                QPushButton:hover {
                    background: #334155;
                    color: #38bdf8;
                    border-color: #38bdf8;
                }
            """)

    def toggle_assistant_panel(self):
        """Show or hide the assistant sidebar cleanly."""
        new_state = not self.assistant_panel.isVisible()
        self.assistant_panel.setVisible(new_state)
        self.update_assistant_btn_style(is_active=new_state)
        if new_state:
            self.assistant_panel.web_view.load(QUrl(f"http://localhost:{self.backend_port}"))

    def current_view(self) -> QWebEngineView:
        return self.tabs.currentWidget()

    def find_free_port(self, start: int = 5050, max_try: int = 32) -> int:
        """Find a free localhost port starting at `start` and probing upwards.
        Returns the first available port found or an OS-assigned ephemeral port.
        """
        for p in range(start, start + max_try):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                s.bind(("127.0.0.1", p))
                s.close()
                return p
            except OSError:
                s.close()
                continue

        # Fallback: ask OS for an ephemeral port
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        return port

    def add_new_tab(self, qurl: QUrl = None, title: str = "New Tab", is_home: bool = False):
        view = QWebEngineView(self)
        page = PrivacyWebPage(self.profile, view)
        view.setPage(page)

        view.titleChanged.connect(lambda t: self.update_tab_title(view, t))
        view.iconChanged.connect(lambda icon: self.update_tab_icon(view, icon))
        view.urlChanged.connect(lambda u: self.update_url_bar(view, u))
        view.loadProgress.connect(lambda p: self.update_load_progress(view, p))
        view.loadStarted.connect(lambda: self.on_load_started(view))
        view.loadFinished.connect(lambda ok: self.on_load_finished(view, ok))

        index = self.tabs.addTab(view, title)
        self.tabs.setCurrentIndex(index)

        if is_home or qurl is None:
            view.load(QUrl(f"http://localhost:{self.browser_port}"))
        else:
            view.load(qurl)

    def close_tab(self, index: int):
        if self.tabs.count() > 1:
            view = self.tabs.widget(index)
            self.tabs.removeTab(index)
            view.deleteLater()
        else:
            view = self.current_view()
            if view:
                view.setHtml(STARTPAGE_HTML, QUrl("about:blank"))

    def on_tab_changed(self, index: int):
        view = self.current_view()
        if view:
            self.update_url_bar(view, view.url())
            self.update_nav_buttons(view)

    def update_tab_title(self, view: QWebEngineView, title: str):
        index = self.tabs.indexOf(view)
        if index != -1:
            display_title = title if len(title) <= 20 else title[:18] + "..."
            self.tabs.setTabText(index, display_title or "Private Tab")

    def update_tab_icon(self, view: QWebEngineView, icon: QIcon):
        index = self.tabs.indexOf(view)
        if index != -1:
            self.tabs.setTabIcon(index, icon)

    def update_url_bar(self, view: QWebEngineView, url: QUrl):
        if view == self.current_view():
            url_str = url.toString()
            if url_str == "about:blank":
                self.address_bar.setText("")
            else:
                self.address_bar.setText(url_str)

    def update_load_progress(self, view: QWebEngineView, progress: int):
        if view == self.current_view():
            self.progress_bar.setValue(progress)
            if progress >= 100:
                self.progress_bar.hide()
            else:
                self.progress_bar.show()

    def on_load_started(self, view: QWebEngineView):
        if view == self.current_view():
            self.status_bar.showMessage("Loading securely...")
            self.progress_bar.setValue(10)
            self.progress_bar.show()

    def on_load_finished(self, view: QWebEngineView, success: bool):
        if view == self.current_view():
            if success:
                self.status_bar.showMessage("Page loaded securely.", 2500)
            else:
                self.status_bar.showMessage("Page load interrupted.", 2500)
            self.progress_bar.hide()
            self.update_nav_buttons(view)

    def update_nav_buttons(self, view: QWebEngineView):
        if view:
            self.back_action.setEnabled(view.history().canGoBack())
            self.forward_action.setEnabled(view.history().canGoForward())

    def navigate_back(self):
        view = self.current_view()
        if view:
            view.back()

    def navigate_forward(self):
        view = self.current_view()
        if view:
            view.forward()

    def reload_page(self):
        view = self.current_view()
        if view:
            view.reload()

    def navigate_home(self):
        view = self.current_view()
        if view:
            view.load(QUrl(f"http://localhost:{self.browser_port}"))

    def navigate_to_url(self):
        text = self.address_bar.text().strip()
        if not text:
            return

        if text.startswith("http://") or text.startswith("https://") or text.startswith("file://") or text.startswith("about:"):
            url = QUrl(text)
        elif "." in text and " " not in text:
            url = QUrl("https://" + text)
        else:
            encoded_query = urllib.parse.quote(text)
            url = QUrl(f"https://duckduckgo.com/?q={encoded_query}")

        view = self.current_view()
        if view:
            view.load(url)

    def on_url_blocked(self, target: str):
        self.update_shield_label()
        self.status_bar.showMessage(f"🛡️ Blocked tracker: {target[:40]}", 2000)

    def on_url_upgraded(self, target: str):
        self.update_shield_label()

    def update_shield_label(self):
        blocked = self.interceptor.blocked_count
        upgraded = self.interceptor.upgraded_count
        self.shield_label.setText(f"🛡️ Blocked: {blocked} | 🔒 HTTPS Upgraded: {upgraded}")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("RAAMA Privacy Browser")
    app.setOrganizationName("RAAMA")

    window = RaamaPrivacyBrowserWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
