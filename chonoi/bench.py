"""Benchmark có render trên trình duyệt thật (TICKET-04 mục 1):

    python3 -m chonoi.bench --seed 42 --duration 30 --out bench.json

Mở cảnh sáng chuẩn (`LiveGame("gather", tuning, {}, seed)`) ở viewport 1280×720 qua Playwright,
làm nóng `--warmup` giây (mặc định 3 s) rồi đo `--duration` giây khung hình `requestAnimationFrame`.
Xuất 5 trường: avg_fps, p1_low_fps, frames, measured_s, load_ms.
Mã thoát: 0 khi đạt, 1 khi không khởi chạy được trình duyệt thật, 2 khi tham số sai.
"""

import argparse
import json
import math
import os
import shutil
import sys
import time

from .contract import load_contract
from .live import LiveGame, LiveServer

VIEWPORT = {"width": 1280, "height": 720}


def compute_metrics(dts_ms, load_ms: float) -> dict:
    """Tính 5 chỉ số benchmark theo đúng định nghĩa TICKET-04 mục 1."""
    clean = [float(d) for d in dts_ms if d > 0]
    if not clean:
        raise ValueError("không thu được khung hình hợp lệ nào trong khoảng đo")
    frames = len(clean)
    measured_s = sum(clean) / 1000.0
    avg_fps = frames / measured_s
    slow_count = max(1, math.ceil(0.01 * frames))
    slowest = sorted(clean, reverse=True)[:slow_count]
    avg_slow_s = (sum(slowest) / len(slowest)) / 1000.0
    p1_low_fps = 1.0 / avg_slow_s
    return {
        "avg_fps": round(avg_fps, 2),
        "p1_low_fps": round(p1_low_fps, 2),
        "frames": frames,
        "measured_s": round(measured_s, 3),
        "load_ms": round(float(load_ms), 1),
    }


def _launch_browser(playwright):
    """Khởi chạy Chromium của Playwright hoặc Chrome/Edge có sẵn trên hệ thống."""
    errors = []
    exe_override = os.environ.get("CHONOI_BROWSER_EXE")
    candidates = []
    if exe_override:
        candidates.append({"executable_path": exe_override})
    candidates.append({})  # Chromium mặc định của Playwright nếu đã cài
    for channel in ("chrome", "msedge", "chromium"):
        candidates.append({"channel": channel})
    for cmd in ("google-chrome", "chromium", "chromium-browser", "chrome", "msedge"):
        found = shutil.which(cmd)
        if found:
            candidates.append({"executable_path": found})

    for opts in candidates:
        try:
            return playwright.chromium.launch(headless=True, **opts)
        except Exception as e:
            errors.append(f"{opts or 'default'}: {e}")
    raise RuntimeError("Không khởi chạy được trình duyệt cho benchmark.\n" + "\n".join(errors[-3:]))


_MEASURE_JS = """({ warmupMs, durationMs }) => new Promise((resolve) => {
  const dts = [];
  let warmEnd = null;
  let measStart = null;
  let prev = null;
  function step(now) {
    if (warmEnd === null) warmEnd = now + warmupMs;
    if (now >= warmEnd) {
      if (prev === null) {
        prev = now;
        measStart = now;
      } else {
        const dt = now - prev;
        if (dt > 0) dts.push(dt);
        prev = now;
        if (now - measStart >= durationMs) {
          resolve(dts);
          return;
        }
      }
    }
    requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
})"""


def run_bench(seed: int, duration: float, warmup: float = 3.0, tuning=None) -> dict:
    """Chạy benchmark cảnh sáng chuẩn 1280×720 trên trình duyệt thật."""
    tuning = tuning or load_contract()["tuning"]
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        raise RuntimeError(f"Thiếu thư viện playwright để chạy benchmark trình duyệt: {e}") from e

    server = LiveServer(LiveGame("gather", tuning, {}, seed, days=1), host="127.0.0.1", port=0)
    t0 = time.perf_counter()
    server.start()
    browser = None
    try:
        with sync_playwright() as p:
            browser = _launch_browser(p)
            page = browser.new_page(viewport=VIEWPORT)
            page.set_default_timeout(max(30000, int((warmup + duration + 20) * 1000)))
            page.goto(server.url, wait_until="domcontentloaded")
            page.wait_for_function(
                "() => typeof window.__chonoi_has_snap === 'function' && window.__chonoi_has_snap() && (window.__chonoi_frames || 0) >= 1"
            )
            load_ms = (time.perf_counter() - t0) * 1000.0
            dts_ms = page.evaluate(_MEASURE_JS, {"warmupMs": warmup * 1000.0, "durationMs": duration * 1000.0})
            browser.close()
            browser = None
    finally:
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass
        server.stop()
    return compute_metrics(dts_ms, load_ms)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="chonoi.bench")
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--duration", type=float, required=True)
    p.add_argument("--warmup", type=float, default=3.0)
    p.add_argument("--out", required=True)
    try:
        a = p.parse_args(argv)
    except SystemExit:
        return 2
    if a.duration <= 0 or a.warmup < 0:
        sys.stderr.write("--duration phải > 0 và --warmup phải >= 0\n")
        return 2
    try:
        report = run_bench(a.seed, a.duration, warmup=a.warmup)
    except Exception as e:
        sys.stderr.write(f"lỗi benchmark trình duyệt: {e}\n")
        return 1
    out_dir = os.path.dirname(os.path.abspath(a.out))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
