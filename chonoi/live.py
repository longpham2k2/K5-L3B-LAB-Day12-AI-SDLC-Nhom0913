"""Cửa sổ chơi trực tiếp bằng TRÌNH DUYỆT, chỉ dùng thư viện chuẩn Python.

    python3 -m chonoi.live --mode gather|quan|day [--days 1..5] [--seed N] [--port 8000]

Máy chủ HTTP nhỏ (ThreadingHTTPServer) phục vụ `chonoi/web/index.html` và các API:
    GET  /state   -> snapshot JSON hiện tại + `meta` + `menu_meta` + `shop_meta` + `events` + `stats`
    POST /input   -> {"move": [a, b], "interact": bool, "catch": bool, "pause": bool, "shop_done": bool, "buy": str}
    POST /restart -> chơi lại từ đầu (tùy chọn {"mode": ..., "days": N})
    POST /hold    -> {"hold": bool} (tạm giữ loop nền khi đang xem màn giới thiệu UI)
"""

import argparse
import json
import os
import re
import sys
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .contract import load_contract
from .errors import BadInput
from .inputs import BUTTONS_V11, LiveInputs
from .inventory import read_inventory
from .runner import Session
from .scenario import load_scenario

WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
TICK_S = 1.0 / 60.0
MAX_BODY = 4096
RECENT_EVENTS = 40


class LiveGame:
    """Một lượt chơi + luồng nền bước 60 tick/s. Mọi truy cập trạng thái đi qua khóa."""

    def __init__(self, mode, tuning, scenario, seed, inventory=None, inventory_out=None, *, days=1, hold_on_start=False):
        self._args = (mode, tuning, scenario, seed, inventory)
        self._days = days
        self._hold_on_start = hold_on_start
        self.mode = mode
        self.tuning = tuning
        self.inventory_out = inventory_out
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None
        self._reset()

    def _reset(self):
        self.session = Session(*self._args, days=self._days)
        self.inputs = LiveInputs()
        self.events = list(self.session.init_events())
        self._saved = False
        self.error = None
        self.ui_hold = bool(self._hold_on_start)
        self._stats = {
            "day_served": 0,
            "day_left": 0,
            "day_tips": 0,
            "day_earned": 0,
            "day_rep_start": self.session.snapshot().get("reputation", self.tuning["quan"]["reputation_initial"]),
            "dishes_sold": {},
        }

    # --- luồng nền ----------------------------------------------------------------
    def start(self):
        self._thread = threading.Thread(target=self._loop, name="chonoi-sim", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _loop(self):
        nxt = time.perf_counter()
        while not self._stop.is_set():
            nxt += TICK_S
            with self._lock:
                try:
                    self._tick_once()
                except Exception:  # luật của nhóm lỗi: báo ra terminal + client, dừng bước (restart để chơi lại)
                    self.error = traceback.format_exc()
                    sys.stderr.write(self.error)
                    self.session.done = True
                    self.session.reason = "error"
            delay = nxt - time.perf_counter()
            if delay > 0:
                self._stop.wait(delay)
            elif delay < -0.25:  # chạy chậm quá thì bỏ bù, tránh chạy dồn
                nxt = time.perf_counter()

    def _update_stats(self, row):
        name = row["name"]
        data = row.get("data", {})
        if name == "day_start":
            self._stats["day_served"] = 0
            self._stats["day_left"] = 0
            self._stats["day_tips"] = 0
            self._stats["day_earned"] = 0
            self._stats["day_rep_start"] = self.session.snapshot().get("reputation", 3.0)
        elif name == "served":
            self._stats["day_served"] += 1
            dish = data.get("dish_id")
            if dish:
                sold = self._stats["dishes_sold"]
                sold[dish] = sold.get(dish, 0) + 1
        elif name == "paid":
            self._stats["day_tips"] += data.get("tip", 0)
            self._stats["day_earned"] += data.get("amount", 0)
        elif name == "customer_left" and data.get("reason") == "patience":
            self._stats["day_left"] += 1

    def _tick_once(self):
        s = self.session
        if s.done or self.ui_hold:
            return
        for row in s.step(self.inputs.advance()):
            self.events.append(row)
            self._update_stats(row)
        del self.events[:-RECENT_EVENTS]
        if s.done and not self._saved:
            self._saved = True
            if self.inventory_out:
                try:
                    s.write_inventory_if_done(self.inventory_out)
                except OSError as e:
                    sys.stderr.write(f"lỗi ghi kho: {e}\n")

    # --- API cho handler -----------------------------------------------------------
    def state_json(self) -> bytes:
        with self._lock:
            snap = self.session.snapshot()
            phase = snap.get("phase", self.mode)
            snap["meta"] = self.tuning.get(phase, {})
            snap["menu_meta"] = self.tuning["menu"]
            snap["shop_meta"] = self.tuning["shop"]
            snap["freshness_meta"] = self.tuning.get("freshness", {})
            snap["events"] = list(self.events)
            snap["stats"] = dict(self._stats)
            snap["ui_hold"] = self.ui_hold
            snap["finished"] = self.session.done
            snap["reason"] = self.session.reason if self.session.done else None
            snap["error"] = self.error
            return json.dumps(snap, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    def set_input(self, body: dict):
        move = body.get("move")
        if move is not None:
            ok = (isinstance(move, list) and len(move) == 2 and
                  all(isinstance(c, (int, float)) and not isinstance(c, bool) and abs(c) <= 1 for c in move))
            if not ok:
                raise ValueError("move phải là [a, b] trong [-1, 1]")
        buttons = {}
        for b in BUTTONS_V11:
            if b in body:
                if not isinstance(body[b], bool):
                    raise ValueError(f"{b} phải là boolean")
                buttons[b] = body[b]
        buy = body.get("buy")
        if buy is not None and (not isinstance(buy, str) or not buy):
            raise ValueError("buy phải là chuỗi khác rỗng")
        with self._lock:
            self.inputs.set(move, buy=buy, **buttons)

    def set_hold(self, hold: bool):
        with self._lock:
            self.ui_hold = bool(hold)

    def restart(self, body: dict = None):
        with self._lock:
            if body:
                if "mode" in body and body["mode"] in ("gather", "quan", "day"):
                    new_mode = body["mode"]
                    if new_mode != self.mode:
                        self.mode = new_mode
                        self._args = (new_mode, self.tuning, {}, self._args[3], None)
                if "days" in body and isinstance(body["days"], int) and 1 <= body["days"] <= 5:
                    self._days = body["days"]
            self._hold_on_start = False
            self._reset()


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    game: LiveGame = None  # gán trên lớp con trong make_server

    def log_message(self, fmt, *args):  # yên lặng
        pass

    def _send(self, code, body: bytes, ctype="application/json; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/state":
            self._send(200, self.game.state_json())
        elif path in ("/sprites.js", "/art.js") or (path.startswith("/assets/") and re.fullmatch(r"/assets/[a-z0-9_]+\.png", path)):
            # tài sản tĩnh của cửa sổ chơi; tên chỉ gồm [a-z0-9_] -> không thể đi ra ngoài thư mục web
            ctype = "text/javascript; charset=utf-8" if path.endswith(".js") else "image/png"
            try:
                with open(os.path.join(WEB_DIR, *path.lstrip("/").split("/")), "rb") as f:
                    self._send(200, f.read(), ctype)
            except OSError:
                self._send(404, b'{"error":"khong co"}')
        elif path in ("/", "/index.html"):
            try:
                with open(os.path.join(WEB_DIR, "index.html"), "rb") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            except OSError:
                self._send(404, b'{"error":"thieu index.html"}')
        else:
            self._send(404, b'{"error":"khong co"}')

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = -1
        if n < 0 or n > MAX_BODY:
            self._send(400, b'{"error":"body sai"}')
            return
        raw = self.rfile.read(n) if n else b""
        try:
            if path == "/input":
                body = json.loads(raw.decode("utf-8") or "{}")
                if not isinstance(body, dict):
                    raise ValueError("body phải là object")
                self.game.set_input(body)
            elif path == "/hold":
                body = json.loads(raw.decode("utf-8") or "{}")
                if not isinstance(body, dict) or not isinstance(body.get("hold"), bool):
                    raise ValueError("hold phải là boolean")
                self.game.set_hold(body["hold"])
            elif path == "/restart":
                body = json.loads(raw.decode("utf-8") or "{}") if raw else {}
                if not isinstance(body, dict):
                    raise ValueError("body phải là object")
                self.game.restart(body)
            else:
                self._send(404, b'{"error":"khong co"}')
                return
        except (ValueError, UnicodeDecodeError) as e:
            self._send(400, json.dumps({"error": str(e)}).encode("utf-8"))
            return
        self._send(200, b'{"ok":true}')


class LiveServer:
    """Máy chủ + mô phỏng. port=0 -> cổng ngẫu nhiên (đọc `.port`)."""

    def __init__(self, game: LiveGame, host="127.0.0.1", port=8000):
        handler = type("Handler", (_Handler,), {"game": game})
        self.game = game
        self.httpd = ThreadingHTTPServer((host, port), handler)
        self.httpd.daemon_threads = True
        self.host = host
        self.port = self.httpd.server_address[1]
        self._thread = None

    @property
    def url(self):
        return f"http://{self.host}:{self.port}/"

    def start(self):
        self.game.start()
        self._thread = threading.Thread(target=self.httpd.serve_forever, name="chonoi-http", daemon=True)
        self._thread.start()

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        if self._thread:
            self._thread.join(timeout=2)
        self.game.stop()


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="chonoi.live", description="Chơi trực tiếp trên trình duyệt (starter).")
    p.add_argument("--mode", required=True, choices=["gather", "quan", "day"])
    p.add_argument("--days", type=int)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--port", type=int, default=8000, help="0 = cổng ngẫu nhiên")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--scenario")
    p.add_argument("--inventory", help="chỉ với quan: nạp kho từ file")
    p.add_argument("--inventory-out", dest="inventory_out", help="chỉ với gather: ghi kho khi kết thúc buổi")
    a = p.parse_args(argv)
    try:
        if a.days is not None and a.mode != "day":
            raise BadInput("--days chỉ dùng với --mode day")
        days = a.days if a.days is not None else 1
        if a.mode == "day" and not (1 <= days <= 5):
            raise BadInput("--days phải trong [1, 5]")
        if a.inventory and a.mode != "quan":
            raise BadInput("--inventory chỉ dùng với quan")
        if a.inventory_out and a.mode != "gather":
            raise BadInput("--inventory-out chỉ dùng với gather")
        tuning = load_contract()["tuning"]
        scenario = load_scenario(a.scenario, a.mode, tuning)
        inventory = read_inventory(a.inventory) if a.inventory else None
        if inventory is not None and "stock" in scenario:
            raise BadInput("vừa có quan.stock vừa có --inventory")
        game = LiveGame(
            a.mode, tuning, scenario, a.seed, inventory, a.inventory_out,
            days=days, hold_on_start=(a.mode == "day"),
        )
        server = LiveServer(game, a.host, a.port)
    except BadInput as e:
        sys.stderr.write(f"đầu vào sai: {e}\n")
        return 2
    except OSError as e:
        sys.stderr.write(f"không mở được cổng {a.port}: {e}\n")
        return 1
    server.start()
    print(f"Mở trình duyệt tại {server.url}  (chế độ {a.mode}, seed {a.seed}). Ctrl+C để dừng.", flush=True)
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
