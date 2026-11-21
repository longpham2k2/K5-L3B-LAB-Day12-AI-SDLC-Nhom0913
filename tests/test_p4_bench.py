"""AC-P4-02 (v1.3): benchmark có render 1280x720 (seed 42, 5 trường JSON, p1_low_fps, lỗi rõ khi thiếu trình duyệt)."""

import importlib.util
import io
import json
import os
import subprocess
import unittest
from contextlib import redirect_stderr
from unittest import mock

from chonoi.bench import compute_metrics, main as bench_main
from helpers import ROOT, Workdir, contract_cmd

with open(os.path.join(ROOT, "game.contract.json"), encoding="utf-8") as _f:
    C = json.load(_f)


class BenchMathAndErrors(unittest.TestCase):
    def test_contract_bench_cmd_and_exact_metrics_formula(self):
        self.assertEqual(C["contract_version"], "1.3")
        self.assertEqual(C["bench_cmd"], "python3 -m chonoi.bench")

        # 200 khung: 198 khung 10 ms + 2 khung chậm nhất 50 ms -> ceil(0.01*200)=2 khung chậm -> p1_low = 20 fps
        dts = [10.0] * 198 + [50.0, 50.0]
        m = compute_metrics(dts, load_ms=1234.5)
        self.assertEqual(set(m), {"avg_fps", "p1_low_fps", "frames", "measured_s", "load_ms"})
        self.assertEqual(m["frames"], 200)
        self.assertEqual(m["measured_s"], 2.08)
        self.assertAlmostEqual(m["avg_fps"], round(200 / 2.08, 2), places=2)
        self.assertEqual(m["p1_low_fps"], 20.0)
        self.assertEqual(m["load_ms"], 1234.5)

        # 50 khung: max(1, ceil(0.01*50)) = 1 khung chậm nhất 100 ms -> p1_low = 10 fps
        m2 = compute_metrics([10.0] * 49 + [100.0], load_ms=500.0)
        self.assertEqual(m2["frames"], 50)
        self.assertEqual(m2["p1_low_fps"], 10.0)

    def test_bad_flags_exit_2_and_missing_browser_exit_1(self):
        with Workdir() as w:
            out = w.path("bench.json")
            buf = io.StringIO()
            with redirect_stderr(buf):
                self.assertEqual(bench_main(["--seed", "42", "--duration", "0", "--out", out]), 2)
                self.assertEqual(bench_main(["--seed", "42", "--duration", "1", "--warmup", "-0.5", "--out", out]), 2)
                self.assertEqual(bench_main(["--seed", "42"]), 2)
            err = io.StringIO()
            with redirect_stderr(err), mock.patch("chonoi.bench._launch_browser", side_effect=RuntimeError("không tìm thấy trình duyệt")):
                rc = bench_main(["--seed", "42", "--duration", "0.5", "--warmup", "0", "--out", out])
            self.assertEqual(rc, 1)
            self.assertIn("trình duyệt", err.getvalue())
            self.assertFalse(os.path.exists(out))


# Bench thật cần Playwright + Chromium (không thuộc thư viện chuẩn). Máy không cài thì BỎ QUA thay vì làm đỏ main;
# cài: python3 -m pip install playwright && python3 -m playwright install chromium (xem README, mục Benchmark).
@unittest.skipUnless(importlib.util.find_spec("playwright"), "cần playwright: pip install playwright && playwright install chromium")
class BenchBrowserCli(unittest.TestCase):
    def test_real_browser_bench_cli_writes_five_fields(self):
        with Workdir() as w:
            out = w.path("bench.json")
            cmd = contract_cmd("bench_cmd") + [
                "--seed", "42", "--duration", "0.6", "--warmup", "0.2", "--out", out
            ]
            p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=45)
            self.assertEqual(p.returncode, 0, p.stderr)
            with open(out, encoding="utf-8") as f:
                r = json.load(f)
            self.assertEqual(set(r), {"avg_fps", "p1_low_fps", "frames", "measured_s", "load_ms"})
            self.assertIsInstance(r["frames"], int)
            self.assertGreater(r["frames"], 0)
            self.assertGreater(r["measured_s"], 0.3)
            self.assertGreater(r["load_ms"], 0)
            self.assertGreater(r["avg_fps"], 0)
            self.assertGreater(r["p1_low_fps"], 0)
            self.assertLessEqual(r["p1_low_fps"], r["avg_fps"])


if __name__ == "__main__":
    unittest.main()
