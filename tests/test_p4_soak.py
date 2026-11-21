"""AC-P4-01 (v1.3): manifest bench_cmd/soak_cmd, soak nhiều Ngày, kế hoạch D1–D5 lặp ở Ngày 6+ (TICKET-04 mục 1–2)."""

import json
<<<<<<< HEAD
import shlex
import shutil
=======
>>>>>>> 0922d1960b4b90e34abdb278f79d7c16e27e14d7
import subprocess
import sys
import unittest

from chonoi.contract import load_contract
from chonoi.inputs import LiveInputs
from chonoi.runner import Session
from chonoi.soak import soak

from helpers import ROOT, Workdir, contract_cmd

with open("game.contract.json", encoding="utf-8") as _f:
    C = json.load(_f)
TUNING = load_contract()["tuning"]


def contract_command(name):
    """Giữ manifest chuẩn `python3`, nhưng chạy test được trên Windows không có alias đó."""
    command = shlex.split(C[name])
    if command[0] == "python3" and shutil.which("python3") is None:
        command[0] = sys.executable
    return command


class Manifest13(unittest.TestCase):
    def test_root_has_version_and_commands(self):
        self.assertEqual(C["contract_version"], "1.3")
        self.assertEqual(C["bench_cmd"], "python3 -m chonoi.bench")
        self.assertEqual(C["soak_cmd"], "python3 -m chonoi.soak")


class Soak(unittest.TestCase):
    def test_six_days_wraps_plan_and_completes(self):
        r = soak(7, 6, TUNING)
        self.assertEqual((r["days"], r["days_completed"], r["crashes"]), (6, 6, 0))
        self.assertEqual([x["day"] for x in r["results"]], [1, 2, 3, 4, 5, 6])
        self.assertEqual(set(r["results"][0]), {"day", "earned", "reputation", "score"})

    def test_day6_plan_repeats_day1(self):
        sess = Session("day", TUNING, {}, 1, days=6)
        bot, plans = LiveInputs(), {}
        while not sess.done:
            for row in sess.step(bot.advance()):
                if row["type"] == "event" and row["name"] == "day_plan":
                    plans[row["day"]] = row["data"]
        d1 = TUNING["day_plan"][0]
        self.assertEqual(plans[6], {"dishes": d1["dishes"], "ingredients": d1["ingredients"]})

    def test_deterministic_gameplay_fields(self):
        a, b = soak(3, 2, TUNING), soak(3, 2, TUNING)
        a.pop("duration_s"), b.pop("duration_s")
        self.assertEqual(a, b)

    def test_cli_writes_soak_json(self):
        with Workdir() as w:
            out = w.path("soak.json")
<<<<<<< HEAD
            cmd = contract_command("soak_cmd") + ["--seed", "7", "--days", "1", "--out", out]
=======
            soak_base = contract_cmd("soak_cmd")  # cross-platform: python3 -> sys.executable trên Windows
            cmd = soak_base + ["--seed", "7", "--days", "1", "--out", out]
>>>>>>> 0922d1960b4b90e34abdb278f79d7c16e27e14d7
            p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            with open(out, encoding="utf-8") as f:
                r = json.load(f)
            self.assertEqual(set(r), {"days", "days_completed", "crashes", "results", "duration_s"})
            self.assertEqual((r["days_completed"], r["crashes"]), (1, 0))
<<<<<<< HEAD
            bad = subprocess.run(contract_command("soak_cmd") + ["--seed", "7", "--days", "0", "--out", out],
=======
            bad = subprocess.run(soak_base + ["--seed", "7", "--days", "0", "--out", out],
>>>>>>> 0922d1960b4b90e34abdb278f79d7c16e27e14d7
                                 cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(bad.returncode, 2)


if __name__ == "__main__":
    unittest.main()
