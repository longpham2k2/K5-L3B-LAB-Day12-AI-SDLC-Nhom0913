"""Soak headless (TICKET-04 mục 2): python3 -m chonoi.soak --seed 7 --days 10 --out soak.json

Chạy N Ngày trong MỘT tiến trình qua `Session("day")` (cùng lớp sim với headless). Mỗi Ngày gather -> quan -> shop;
kế hoạch D1–D5 lặp ở Ngày 6+; tiền, earned, uy tín, cấp, số Ngày và id cá thể tiếp tục xuyên suốt.
Bot tất định: không điều khiển — mỗi pha chạy tới hết giờ (gather 10.800, quán 10.800, Shop 600 tick).
Ghi soak.json: days, days_completed, crashes, results[{day, earned, reputation, score}] lúc Shop đóng, duration_s.
Không ghi bảng xếp hạng. Mã thoát: 0 khi đạt (days_completed == days, crashes == 0), 1 khi có crash, 2 khi cờ sai.
"""

import argparse
import json
import sys
import time
import traceback

from .contract import load_contract
from .inputs import LiveInputs
from .runner import Session


def soak(seed: int, days: int, tuning=None) -> dict:
    tuning = tuning or load_contract()["tuning"]
    start = time.perf_counter()  # chỉ để báo cáo duration_s, không vào mô phỏng
    results, crashes = [], 0
    sess = None
    try:
        sess = Session("day", tuning, {}, seed, days=days)
        bot = LiveInputs()  # không bấm gì: tất định theo seed
        guard = days * 23_000  # một Ngày không pause tối đa 22.200 tick
        while not sess.done and sess.tick < guard:
            for row in sess.step(bot.advance()):
                if row["type"] == "event" and row["name"] == "shop_end":
                    snap = sess.snapshot()
                    results.append({"day": row["day"], "earned": snap["earned"],
                                    "reputation": snap["reputation"], "score": snap["score"]})
    except Exception:  # crash trong một Ngày: ghi lại, dừng soak
        crashes += 1
        traceback.print_exc(file=sys.stderr)
    return {"days": days, "days_completed": sess.days_completed if sess else 0, "crashes": crashes,
            "results": results, "duration_s": round(time.perf_counter() - start, 3)}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="chonoi.soak")
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--days", type=int, required=True)
    p.add_argument("--out", required=True)
    try:
        a = p.parse_args(argv)
    except SystemExit:
        return 2
    if a.days < 1:
        sys.stderr.write("--days phải >= 1\n")
        return 2
    report = soak(a.seed, a.days)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")
    ok = report["days_completed"] == report["days"] and report["crashes"] == 0
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
