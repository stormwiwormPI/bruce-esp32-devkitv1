"""
Bruce WebUI over the USB cable
==============================
Serves Bruce's own web interface from this PC and drives the board over the
USB cable. No WiFi, no access point, no router.

The firmware serves a graphical interface over HTTP. This tool mirrors those
files to disk once, serves them to your browser from localhost, and translates
the interface's API calls into serial commands on COM3:

    WebUI request            ->  serial command
    POST /bruce/cm            ->  the command verbatim  (every Bruce tool)
    GET  /bruce/systeminfo    ->  `settings` + `ls`
    GET  /bruce/listfiles     ->  `ls`
    GET  /bruce/wifi          ->  `wifi add`
    GET  /bruce/reboot        ->  `power reboot`

Because /cm is passed straight through, every Bruce tool (WiFi, IR, RF, BLE,
RFID, scanning) works over the cable exactly as it does over WiFi.

Usage:
    python bruce_cable_ui.py
    python bruce_cable_ui.py --port COM3 --http 8080

Notes:
  * The local port must be 8080. The interface contains
        const IS_DEV = "127.0.0.1:8080" === window.location.host
    and only prefixes its API calls with "/bruce" on that exact host:port.
  * File upload and the built-in editor are unavailable over cable; the
    firmware's serial reader rejects larger files. Those endpoints say so
    instead of failing silently.
"""

from __future__ import annotations

import argparse
import base64
import email
import gzip
import http.client
import json
import re
import sys
import threading
import time
import urllib.parse
import webbrowser
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

try:
    import serial
except ImportError:
    print("pyserial is required:  pip install pyserial", file=sys.stderr)
    raise


DEVICE_PORT = 80
MIRROR_PATHS = ("/index.css", "/index.js", "/theme.css")
MAIN_PAGE = "index.html"
WEBUI_USER = "admin"
WEBUI_PASSWORD = "bruce"
CACHE_DIR = Path(__file__).resolve().parent / "webui_files"

LITTLEFS_TOTAL_KB = 192.0
BRUCE_VERSION = "dev"
PROMPT = "#"

C = {"d": "\033[2m", "g": "\033[32m", "c": "\033[36m",
     "y": "\033[33m", "r": "\033[31m", "b": "\033[1m", "x": "\033[0m"}


def say(msg: str, colour: str = "g") -> None:
    print(f"{C[colour]}{msg}{C['x']}", flush=True)


def decode_body(data: bytes, encoding: str | None) -> bytes:
    """
    The board gzips responses even when asked for `identity`, so every body is
    decoded here and Content-Encoding dropped. Otherwise the browser is handed
    compressed bytes labelled as HTML.
    """
    enc = (encoding or "").lower()
    try:
        if "gzip" in enc:
            return gzip.decompress(data)
        if "deflate" in enc:
            try:
                return zlib.decompress(data)
            except zlib.error:
                return zlib.decompress(data, -zlib.MAX_WBITS)
    except Exception:
        return data
    return data


# --------------------------------------------------------------------------- #
#  Serial backend
# --------------------------------------------------------------------------- #
class SerialBoard:
    """Talks to the board over COM3 using its serial command console."""

    def __init__(self, port: str, baud: int = 115200):
        self.port = port
        self.baud = baud
        self.ser: serial.Serial | None = None
        self.lock = threading.Lock()
        self.nav_lock = threading.Lock()
        self.nav_queue: list[str] = []
        self.latest_frame: bytes = empty_frame()
        self._last_getscreen_ts: float = 0.0
        self._stop_poller = threading.Event()
        self._poller_thread: threading.Thread | None = None
        self._use_bin_dump: bool = True

    def open(self) -> None:
        self.ser = serial.Serial(self.port, self.baud, timeout=0.05)
        say(f"opened {self.port} @ {self.baud} baud", "d")

    def _reopen_locked(self) -> bool:
        try:
            if self.ser:
                try:
                    self.ser.close()
                except Exception:
                    pass
            time.sleep(0.15)
            self.ser = serial.Serial(self.port, self.baud, timeout=0.05)
            return True
        except Exception:
            return False

    def start_poller(self) -> None:
        if self._poller_thread is not None and self._poller_thread.is_alive():
            return
        self._stop_poller.clear()
        self._poller_thread = threading.Thread(
            target=self._poller_loop, name="ScreenPoller", daemon=True
        )
        self._poller_thread.start()

    def _poller_loop(self) -> None:
        while not self._stop_poller.is_set():
            try:
                # 1. Always drain queued navigation commands immediately
                cmds: list[str] = []
                with self.nav_lock:
                    if self.nav_queue:
                        cmds = self.nav_queue[:]
                        self.nav_queue.clear()
                for cmd in cmds:
                    self._exec_nav(cmd)

                # 2. Poll screen when Navigator is active (or we have no frame yet)
                now = time.time()
                if now - self._last_getscreen_ts < 3.0 or self.latest_frame == empty_frame():
                    frame = self._poll_screen_once()
                    if frame and frame[0] == 0xAA and len(frame) > 10:
                        self.latest_frame = frame
                    time.sleep(0.005)
                else:
                    time.sleep(0.02)
            except Exception:
                time.sleep(0.1)

    def enqueue_nav(self, cmd: str) -> None:
        with self.nav_lock:
            # Cap queue length so holding a key never builds up lag
            if len(self.nav_queue) < 6:
                self.nav_queue.append(cmd)

    def _exec_nav(self, command: str) -> None:
        with self.lock:
            try:
                if not self.ser or not self.ser.is_open:
                    if not self._reopen_locked():
                        return
                if self.ser.in_waiting:
                    self.ser.read(self.ser.in_waiting)
                self.ser.write((command + "\r\n").encode())
                deadline = time.time() + 0.35
                buf = b""
                while time.time() < deadline:
                    waiting = self.ser.in_waiting
                    chunk = self.ser.read(waiting or 256)
                    if chunk:
                        buf += chunk
                        if b"\n#" in buf or buf.rstrip().endswith(b"#"):
                            break
            except Exception:
                self._reopen_locked()

    def _poll_screen_once(self) -> bytes | None:
        with self.lock:
            try:
                if not self.ser or not self.ser.is_open:
                    if not self._reopen_locked():
                        return None
                if self.ser.in_waiting:
                    self.ser.read(self.ser.in_waiting)

                if self._use_bin_dump:
                    self.ser.write(b"display bin\r\n")
                    raw = b""
                    deadline = time.time() + 0.45
                    while time.time() < deadline:
                        waiting = self.ser.in_waiting
                        chunk = self.ser.read(waiting or 512)
                        if chunk:
                            raw += chunk
                            if b"Display command accept:" in raw:
                                self._use_bin_dump = False
                                break
                            idx = raw.find(b"BIN:")
                            if idx != -1 and len(raw) >= idx + 6:
                                length = (raw[idx + 4] << 8) | raw[idx + 5]
                                end_pos = idx + 6 + length
                                if len(raw) >= end_pos:
                                    payload = raw[idx + 6 : end_pos]
                                    # Drain trailing prompt bytes if already in buffer
                                    if self.ser.in_waiting:
                                        self.ser.read(self.ser.in_waiting)
                                    if payload and payload[0] == 0xAA:
                                        return payload
                                    return None
                    if self._use_bin_dump:
                        return None

                # Fallback to ASCII hex 'display dump'
                if self.ser.in_waiting:
                    self.ser.read(self.ser.in_waiting)
                self.ser.write(b"display dump\r\n")
                buf = ""
                deadline = time.time() + 0.8
                while time.time() < deadline:
                    waiting = self.ser.in_waiting
                    d = self.ser.read(waiting or 512)
                    if d:
                        buf += d.decode("utf-8", errors="replace")
                        if "[End of Dump]" in buf:
                            break
                m = re.search(r"Binary Dump:(.*?)\[End of Dump\]", buf, re.S)
                if not m:
                    return None
                hex_tokens = re.findall(r"\b[0-9A-Fa-f]{2}\b", m.group(1))
                if not hex_tokens:
                    return None
                data = bytes(int(tok, 16) for tok in hex_tokens)
                return data if data and data[0] == 0xAA else None
            except Exception:
                self._reopen_locked()
                return None

    def reset(self) -> None:
        """ESP32 auto-reset: EN is on RTS, GPIO0 is on DTR.

        DTR must stay high; pulling it low forces the ROM bootloader and the
        firmware never runs.
        """
        self.ser.dtr = False
        self.ser.rts = False
        time.sleep(0.15)
        self.ser.rts = True
        time.sleep(0.20)
        self.ser.rts = False

    def drain(self, seconds: float = 20.0) -> None:
        end = time.time() + seconds
        while time.time() < end:
            try:
                if not self.ser.in_waiting:
                    time.sleep(0.05)
                    continue
                self.ser.read(4096)
            except Exception:
                break

    def wait_until_ready(self, timeout: float = 25.0) -> bool:
        """
        Reset the board and read its boot log until the console prompt or main
        menu stage appears, showing progress meanwhile.
        """
        self.reset()
        start = time.time()
        seen = ""
        last_probe = 0.0
        while time.time() - start < timeout:
            try:
                if self.ser.in_waiting:
                    seen += self.ser.read(self.ser.in_waiting).decode(
                        "utf-8", errors="replace")
                    if ("first-mainMenu" in seen
                            or any(l.strip() == PROMPT or l.lstrip().startswith(PROMPT + " ")
                                   for l in seen.splitlines())):
                        time.sleep(0.25)
                        if self.ser.in_waiting:
                            self.ser.read(self.ser.in_waiting)
                        self._clear_line()
                        say("board ready", "g")
                        return True
                now = time.time()
                if "setup-end" in seen and now - last_probe > 0.8:
                    self.ser.write(b"\r\n")
                    last_probe = now
            except Exception:
                break

            elapsed = int(time.time() - start)
            dots = "." * (elapsed % 4)
            sys.stdout.write(f"\r    booting{dots}  {elapsed:>2}s / {timeout:.0f}s   ")
            sys.stdout.flush()
            time.sleep(0.25)

        self._clear_line()
        return False

    @staticmethod
    def _clear_line() -> None:
        sys.stdout.write("\r" + " " * 56 + "\r")
        sys.stdout.flush()

    def run(self, command: str, timeout: float = 20.0) -> str:
        """Send one command and read until the console prints its '#' prompt."""
        with self.lock:
            try:
                if not self.ser or not self.ser.is_open:
                    self._reopen_locked()
                while self.ser.in_waiting:
                    self.ser.read(4096)
                self.ser.write((command + "\r\n").encode())

                buf, deadline = "", time.time() + timeout
                while time.time() < deadline:
                    waiting = self.ser.in_waiting
                    d = self.ser.read(waiting or 512)
                    if d:
                        buf += d.decode("utf-8", errors="replace")
                        if any(l.strip() == PROMPT or l.lstrip().startswith(PROMPT + " ")
                               for l in buf.splitlines()):
                            return self._clean(buf, command)
                return self._clean(buf, command)
            except Exception:
                self._reopen_locked()
                return ""

    @staticmethod
    def _clean(buf: str, command: str) -> str:
        kept = []
        for line in buf.splitlines():
            s = line.rstrip()
            if s.strip() in (PROMPT, f"COMMAND: {command}"):
                continue
            if s.lstrip().startswith(PROMPT + " "):
                continue
            kept.append(s)
        return "\n".join(kept).strip()

    # ------------------------------------------------------------- endpoints
    def systeminfo(self) -> dict:
        raw = self.run("settings", 20)
        used = sum(int(m) for m in re.findall(r"^\S+\t(\d+)$", self.run("ls", 15), re.M))
        used_kb = used / 1024.0
        return {
            "BRUCE_VERSION": BRUCE_VERSION,
            "SD": {"free": "0 B", "used": "0 B", "total": "0 B"},
            "LittleFS": {
                "free": f"{max(0.0, LITTLEFS_TOTAL_KB - used_kb):.2f} kB",
                "used": f"{used_kb:.2f} kB",
                "total": f"{LITTLEFS_TOTAL_KB:.2f} kB",
            },
        }

    def listfiles(self, fs: str, folder: str) -> str:
        """The interface expects 'Fi:/path:size' for files, 'Fo:/path' for dirs."""
        raw = self.run("ls", 15)
        out = []
        for line in raw.splitlines():
            m = re.match(r"^(.+?)\t(\d+)$", line.rstrip())
            if not m:
                continue
            name, size = m.group(1).strip(), m.group(2)
            path = folder.rstrip("/") + "/" + name
            out.append(f"Fo:{path}" if name.endswith("/") else f"Fi:{path}:{size}")
        return "\n".join(out)

    def getscreen(self) -> bytes:
        """Return the latest cached binary TFT frame immediately for 60Hz polling."""
        self._last_getscreen_ts = time.time()
        return self.latest_frame

    def close(self) -> None:
        self._stop_poller.set()
        if self.ser:
            try:
                self.ser.close()
            except Exception:
                pass


# --------------------------------------------------------------------------- #
#  Mirroring
# --------------------------------------------------------------------------- #
def fetch_main_page(ip: str) -> bytes | None:
    """
    The board only serves the real interface to an authenticated session, so log
    in and capture it. Over the cable there is no session concept, so we serve
    this cached copy.
    """
    try:
        conn = http.client.HTTPConnection(ip, DEVICE_PORT, timeout=20)
        body = urllib.parse.urlencode({"username": WEBUI_USER,
                                        "password": WEBUI_PASSWORD}).encode()
        conn.request("POST", "/login", body=body, headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept-Encoding": "identity", "Connection": "close"})
        r = conn.getresponse()
        r.read()
        cookie = (r.getheader("Set-Cookie") or "").split(";")[0]
        conn.close()
        if not cookie:
            return None

        conn = http.client.HTTPConnection(ip, DEVICE_PORT, timeout=20)
        conn.request("GET", "/", headers={"Cookie": cookie,
                                           "Accept-Encoding": "identity",
                                           "Connection": "close"})
        r = conn.getresponse()
        data = decode_body(r.read(), r.getheader("Content-Encoding"))
        conn.close()
        return data if r.status == 200 else None
    except Exception:
        return None


def build_mirror(ip: str, force: bool = False) -> bool:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    for path in MIRROR_PATHS:
        dest = CACHE_DIR / path.lstrip("/")
        if dest.exists() and not force:
            continue
        try:
            conn = http.client.HTTPConnection(ip, DEVICE_PORT, timeout=20)
            conn.request("GET", path, headers={"Accept-Encoding": "identity",
                                               "Connection": "close"})
            r = conn.getresponse()
            dest.write_bytes(decode_body(r.read(), r.getheader("Content-Encoding")))
            conn.close()
            say(f"  {path}  ({dest.stat().st_size:,} B)", "c")
        except Exception:
            say(f"  could not fetch {path}", "y")

    main = CACHE_DIR / MAIN_PAGE
    if force or not main.exists():
        data = fetch_main_page(ip)
        if data:
            main.write_bytes(data)
            say(f"  / ({MAIN_PAGE}, {len(data):,} B)", "c")
        else:
            say(f"  could not capture the interface page - is the password "
                f"still '{WEBUI_PASSWORD}'?", "y")
    return (CACHE_DIR / MAIN_PAGE).exists()


# --------------------------------------------------------------------------- #
#  HTTP server
# --------------------------------------------------------------------------- #
def inject_banner(html: bytes) -> bytes:
    """
    Kept as a hook for local tweaks. This project ships no banner - see the
    README, which explains that the board has no display fitted.
    """
    return html


# --------------------------------------------------------------------------- #
#  Virtual framebuffer
# --------------------------------------------------------------------------- #
# The interface's "Navigator" tab draws the device's TFT into a <canvas> by
# parsing /getscreen with this record format (see index.js):
#
#   0xAA | len:int8 | type:int8 | payload
#
# type 99  canvas header   -> w:int16, h:int16, rotation:int8   (len = 8)
# type 0   fill background -> fg:int16                           (len = 5)
# type 14  centred text    -> x:int16, y:int16, size:int8,
#                            fg:int16, text                      (len = 9+len(text))
#
# Colours are RGB565. `len` is the whole record size in bytes, and the reader
# derives field widths from it, so it must be exact.
SCREEN_W, SCREEN_H = 240, 320

RGB565 = {
    "black": 0x0000, "white": 0xFFFF, "grey": 0x8410,
    "green": 0x07E0, "darkgreen": 0x03E0, "amber": 0xFD20,
    "red": 0xF800, "magenta": 0xF81F, "blue": 0x001F,
    "cyan": 0x07FF, "yellow": 0xFFE0,
}


def _rec(rtype: int, payload: bytes) -> bytes:
    """len is the WHOLE record size: 0xAA + len + type + payload."""
    return bytes([0xAA, len(payload) + 3, rtype]) + payload


def empty_frame(w: int = SCREEN_W, h: int = SCREEN_H) -> bytes:
    """A correctly formed but blank fallback frame."""
    out = bytearray()
    out += bytes([0xAA, 8, 99]) + w.to_bytes(2, "big") + h.to_bytes(2, "big") + bytes([0])
    out += _rec(0, RGB565["black"].to_bytes(2, "big"))
    return bytes(out)


def build_frame(lines: list[tuple[str, int, str]]) -> bytes:
    """Render a few lines of text as the board's TFT framebuffer format."""
    out = bytearray()

    # canvas header: len must be 8 (1 type + 2 + 2 + 1 + ... per the reader)
    out += bytes([0xAA, 8, 99]) + SCREEN_W.to_bytes(2, "big") \
        + SCREEN_H.to_bytes(2, "big") + bytes([0])

    # black background: 1 type + 2 fg = 3 payload bytes
    out += _rec(0, RGB565["black"].to_bytes(2, "big"))

    # title
    out += _text(SCREEN_W // 2, 24, 3, RGB565["green"], "BRUCE")
    out += _text(SCREEN_W // 2, 52, 1, RGB565["grey"], "PREDATORY FIRMWARE")

    y = 90
    for text, size, colour in lines:
        out += _text(SCREEN_W // 2, y, size, RGB565[colour], text)
        y += 8 * size + 6

    return bytes(out)


def _text(x: int, y: int, size: int, colour: int, text: str) -> bytes:
    # The reader treats every field except 'txt'/'file'/'rotation'/'fs' as
    # int16 - including 'size'. The string length is derived from the record
    # size (g - 11), so _rec computes the exact byte count.
    payload = (x.to_bytes(2, "big") + y.to_bytes(2, "big")
               + size.to_bytes(2, "big") + colour.to_bytes(2, "big")
               + text.encode("utf-8"))
    return _rec(14, payload)


def rewrite_set_cookie(value: str) -> str:
    """
    The board scopes its session cookie to its own address. A browser refuses
    that for localhost, so drop the Domain attribute and let it bind locally.
    """
    parts = [p.strip() for p in value.split(";")]
    return "; ".join([parts[0]] + [p for p in parts[1:]
                                   if not p.lower().startswith("domain=")])


def upload_file_to_board(board: SerialBoard, filepath: str, data: bytes) -> bool:
    """Uploads binary or text data in 256-byte base64 chunks over serial."""
    chunk_size = 256
    if not filepath.startswith("/"):
        filepath = "/" + filepath
    if len(data) == 0:
        board.run(f'writeb64 "{filepath}" w ', 5)
        return True
    first = True
    for offset in range(0, len(data), chunk_size):
        chunk = data[offset : offset + chunk_size]
        b64 = base64.b64encode(chunk).decode("ascii")
        mode = "w" if first else "a"
        board.run(f'writeb64 "{filepath}" {mode} {b64}', 10)
        first = False
    return True


class Handler(BaseHTTPRequestHandler):
    server_version = "BruceCableUI/1.0"
    protocol_version = "HTTP/1.1"

    def _nav_lines(self) -> list[tuple[str, int, str]]:
        """Content the Navigator tab draws on the virtual screen."""
        rows = [("No display fitted", 1, "amber"),
                ("", 1, "grey"),
                ("This panel is drawn on", 1, "grey"),
                ("your PC, not on the board", 1, "grey"),
                ("", 1, "grey"),
                ("Fit an ILI9341 / ST7789", 1, "cyan"),
                ("TFT and rebuild with", 1, "cyan"),
                ("HAS_SCREEN to use a", 1, "cyan"),
                ("real screen instead", 1, "cyan"),
                ("", 1, "grey")]
        try:
            fs = self.server.board.systeminfo()["LittleFS"]  # type: ignore[attr-defined]
            rows.append(("LittleFS", 1, "green"))
            rows.append((f"{fs['used']} / {fs['total']}", 1, "white"))
        except Exception:
            pass
        return rows

    def do_GET(self) -> None:
        path = urlsplit(self.path).path

        if path in MIRROR_PATHS:
            local = CACHE_DIR / path.lstrip("/")
            if local.exists():
                ctype = {".css": "text/css", ".js": "application/javascript"}.get(
                    local.suffix, "application/octet-stream")
                self._send(200, local.read_bytes(), {"Content-Type": ctype})
                return

        if path in ("/", "/index.html", "/login", "/favicon.ico"):
            page = CACHE_DIR / MAIN_PAGE
            if page.exists():
                self._send(200, inject_banner(page.read_bytes()),
                           {"Content-Type": "text/html; charset=utf-8"})
                return
            self._send(500, b"The interface has not been mirrored yet.\r\n"
                            b"Connect the board to your network once and run:\r\n"
                            b"  python bruce_cable_ui.py --mirror\r\n",
                       {"Content-Type": "text/plain"})
            return

        board: SerialBoard = self.server.board  # type: ignore[attr-defined]
        q = urllib.parse.parse_qs(urlsplit(self.path).query)
        try:
            if path == "/bruce/systeminfo":
                self._send(200, json.dumps(board.systeminfo()).encode(),
                           {"Content-Type": "application/json"})
            elif path == "/bruce/listfiles":
                fs = (q.get("fs") or ["LittleFS"])[0]
                folder = (q.get("folder") or ["/"])[0]
                self._send(200, board.listfiles(fs, folder).encode(),
                           {"Content-Type": "text/plain"})
            elif path == "/bruce/reboot":
                self._send(200, board.run("power reboot", 8).encode(),
                           {"Content-Type": "text/plain"})
            elif path == "/bruce/wifi":
                usr = (q.get("usr") or [""])[0]
                pwd = (q.get("pwd") or [""])[0]
                self._send(200, board.run(f'wifi add "{usr}" "{pwd}"', 18).encode(),
                           {"Content-Type": "text/plain"})
            elif path in ("/bruce/getscreen", "/getscreen"):
                self._send(200, board.getscreen(),
                           {"Content-Type": "application/octet-stream"})
            elif path == "/bruce/file":
                action = (q.get("action") or [""])[0]
                name = (q.get("name") or [""])[0]
                if name and not name.startswith("/"):
                    name = "/" + name
                if action == "delete":
                    board.run(f'rm "{name}"', 10)
                    self._send(200, b"OK", {"Content-Type": "text/plain"})
                elif action == "create":
                    board.run(f'mkdir "{name}"', 10)
                    self._send(200, b"OK", {"Content-Type": "text/plain"})
                elif action == "createfile":
                    board.run(f'writeb64 "{name}" w ', 10)
                    self._send(200, b"OK", {"Content-Type": "text/plain"})
                elif action == "edit":
                    content = board.run(f'cat "{name}"', 15)
                    self._send(200, content.encode("utf-8"), {"Content-Type": "text/plain"})
                else:
                    self._send(400, b"Unknown file action", {"Content-Type": "text/plain"})
            elif path.startswith("/bruce/"):
                self._send(400, f"{path} has no serial equivalent.\r\n"
                                .encode(), {"Content-Type": "text/plain"})
            else:
                self._send(404, b"Not found", {"Content-Type": "text/plain"})
        except Exception as exc:
            self._send(502, f"serial backend error: {exc}".encode(),
                       {"Content-Type": "text/plain"})

    @staticmethod
    def _parse_fields(content_type: str | None, body: bytes) -> dict[str, str]:
        text = body.decode("utf-8", errors="replace")
        if "multipart/form-data" in (content_type or "").lower() or "Content-Disposition:" in text:
            out: dict[str, str] = {}
            for m in re.finditer(
                r'Content-Disposition:\s*form-data;\s*name="([^"]+)"\r?\n\r?\n(.*?)\r?\n--',
                text,
                re.S,
            ):
                out[m.group(1)] = m.group(2)
            return out
        return {k: v[0] for k, v in urllib.parse.parse_qs(text).items() if v}

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        ctype = self.headers.get("Content-Type")
        path = urlsplit(self.path).path
        board: SerialBoard = self.server.board  # type: ignore[attr-defined]
        try:
            if path == "/bruce/cm":
                fields = self._parse_fields(ctype, body)
                cmd = fields.get("cmnd", "").strip()
                if cmd.lower().startswith("nav "):
                    board.enqueue_nav(cmd)
                    self._send(200, b"OK", {"Content-Type": "text/plain"})
                else:
                    self._send(200, board.run(cmd, 30).encode(),
                               {"Content-Type": "text/plain"})
            elif path == "/bruce/upload":
                msg = email.message_from_bytes(b"Content-Type: " + (ctype or "").encode() + b"\r\n\r\n" + body)
                folder = "/"
                filename = ""
                file_data = b""
                if msg.is_multipart():
                    for part in msg.get_payload():
                        cd = part.get("Content-Disposition", "")
                        if 'name="folder"' in cd:
                            folder = part.get_payload(decode=True).decode("utf-8", errors="replace").strip()
                        elif 'name="file"' in cd:
                            filename = part.get_filename() or "uploaded_file"
                            file_data = part.get_payload(decode=True) or b""
                if not filename:
                    m = re.search(rb'filename="([^"]+)"\r?\n\r?\n(.*?)\r?\n--', body, re.S)
                    if m:
                        filename = m.group(1).decode("utf-8", errors="replace")
                        file_data = m.group(2)
                target_path = (folder.rstrip("/") + "/" + filename.lstrip("/")).replace("//", "/")
                if target_path and target_path != "/":
                    upload_file_to_board(board, target_path, file_data)
                    self._send(200, b"OK", {"Content-Type": "text/plain"})
                else:
                    self._send(400, b"No file provided", {"Content-Type": "text/plain"})
            elif path == "/bruce/rename":
                fields = self._parse_fields(ctype, body)
                old = fields.get("filePath", "")
                new = fields.get("fileName", "")
                self._send(200, board.run(f'storage rename "{old}" "{new}"', 18).encode(),
                           {"Content-Type": "text/plain"})
            elif path == "/bruce/edit":
                fields = self._parse_fields(ctype, body)
                fpath = fields.get("filePath") or fields.get("fileName") or ""
                content = fields.get("content") or fields.get("fileContent") or ""
                if fpath:
                    if not fpath.startswith("/"):
                        fpath = "/" + fpath
                    upload_file_to_board(board, fpath, content.encode("utf-8"))
                    self._send(200, b"OK", {"Content-Type": "text/plain"})
                else:
                    self._send(400, b"Missing filePath", {"Content-Type": "text/plain"})
            else:
                self._send(404, b"Not found", {"Content-Type": "text/plain"})
        except Exception as exc:
            self._send(502, f"serial backend error: {exc}".encode(),
                       {"Content-Type": "text/plain"})

    def _send(self, status: int, data: bytes, headers: dict[str, str],
              multi: list[tuple[str, str]] | None = None) -> None:
        self.send_response(status)
        for k, v in headers.items():
            self.send_header(k, v)
        for k, v in (multi or []):
            self.send_header(k, v)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def log_message(self, fmt: str, *args) -> None:
        if self.path.startswith("/bruce/getscreen"):
            return
        sys.stderr.write(f"{C['d']}  {self.command} {self.path} -> {fmt % args}{C['x']}\n")


def auto_detect_port() -> str:
    try:
        import serial.tools.list_ports
        ports = list(serial.tools.list_ports.comports())
        for p in ports:
            hwid = (p.hwid or "").upper()
            desc = (p.description or "").lower()
            if "VID:PID=" in hwid or any(k in desc for k in ("cp210", "ch34", "ftdi", "uart", "usb", "serial")):
                return p.device
        for p in ports:
            dev = p.device
            if sys.platform.startswith("linux") and ("/dev/ttyUSB" in dev or "/dev/ttyACM" in dev):
                return dev
            if sys.platform == "darwin" and ("/dev/cu.usbserial" in dev or "/dev/cu.SLAB" in dev or "/dev/cu.wch" in dev):
                return dev
            if sys.platform.startswith("win") and dev.startswith("COM"):
                return dev
        if ports:
            return ports[0].device
    except Exception:
        pass
    if sys.platform.startswith("win"):
        return "COM3"
    elif sys.platform == "darwin":
        return "/dev/cu.usbserial-0001"
    else:
        return "/dev/ttyUSB0"


# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(description="Bruce WebUI over the USB cable")
    ap.add_argument("--port", default=None, help="serial port of the board (auto-detected if omitted)")
    ap.add_argument("--http", type=int, default=8080, help="local web port")
    ap.add_argument("--device", help="board IP, used only when mirroring")
    ap.add_argument("--mirror", action="store_true",
                    help="refresh the cached interface files, then exit")
    ap.add_argument("--no-open", action="store_true")
    args = ap.parse_args()

    if args.mirror:
        ip = args.device or "192.168.1.204"
        say(f"mirroring from {ip} ...", "b")
        ok = build_mirror(ip, force=True)
        say("done" if ok else "interface page could not be captured", "g" if ok else "r")
        sys.exit(0 if ok else 1)

    port = args.port or auto_detect_port()
    try:
        board = SerialBoard(port)
        board.open()
    except Exception as exc:
        say(f"Cannot open {port}: {exc}", "r")
        if sys.platform.startswith("linux") and "permission" in str(exc).lower():
            say("  Permission denied accessing serial port.", "y")
            say("  Run this command to add yourself to dialout group, then log out & in:", "y")
            say("    sudo usermod -a -G dialout $USER", "b")
        else:
            say("  If the board is not detected or missing USB drivers:", "y")
            say("    CP210x: https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers", "b")
            say("    CH340:  https://www.wch-ic.com/downloads/CH341SER_EXE.html", "b")
            say("  Make sure your micro-USB cable is a data cable (not charge-only).", "d")
        say("Close any serial monitor (Arduino IDE, PuTTY, screen) first.", "d")
        sys.exit(1)

    say("resetting the board...", "d")
    if not board.wait_until_ready(timeout=25.0):
        say("the board did not report ready - continuing anyway", "y")
        board.drain(3)

    board.start_poller()
    try:
        board.run(f"date set {int(time.time())}")
    except Exception:
        pass

    if not (CACHE_DIR / MAIN_PAGE).exists():
        say("No cached interface found.", "y")
        say("With the board briefly on your WiFi, run:", "d")
        say("  python bruce_cable_ui.py --mirror", "b")
        sys.exit(1)

    httpd = ThreadingHTTPServer(("127.0.0.1", args.http), Handler)
    httpd.board = board  # type: ignore[attr-defined]
    url = f"http://127.0.0.1:{args.http}/"

    if not args.no_open:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()

    say("")
    say("  ==========================================================", "g")
    say("   Bruce is running. Interface is open in your browser.", "b")
    say(f"    {url}", "b")
    say("  ==========================================================", "g")
    say("")
    say("  Open the Navigator tab for the menu and nav buttons.", "d")
    say(f"  interface files : {CACHE_DIR}", "d")
    say(f"  board           : {args.port} @ 115200 baud", "d")
    say("  file manager & editor are enabled over cable", "g")
    say("")
    say("  Keep this window open. Ctrl+C to stop.", "d")
    say("")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        say("\nstopped", "y")
        board.close()


if __name__ == "__main__":
    main()