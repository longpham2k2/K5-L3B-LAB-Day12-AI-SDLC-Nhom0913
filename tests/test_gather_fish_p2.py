"""AC-P2-02 (gather v1.1): cá bơi, đổi hướng theo seed, phản xạ mép, sinh cá theo lịch.
Hộp đen qua headless_cmd; theo TICKET-02 mục 1.1 và thứ tự 4.5 — docs/prd/phase-2.md."""

import json
import math
import unittest

from helpers import Workdir, events, frames, read_jsonl, run_headless, snapshots, write_json

with open("game.contract.json", encoding="utf-8") as _f:
    G = json.load(_f)["tuning"]["gather"]
STEP = G["fish_speed"] / 60.0
TURN = G["fish_turn_ticks"]
SPAWN = G["fish_spawn_ticks"]


def run(w, block, ticks, inp=None, seed=1):
    args = ["--mode", "gather", "--seed", str(seed), "--ticks", str(ticks),
            "--scenario", write_json(w.path("sc.json"), {"gather": block}),
            "--snapshot-every", "1", "--out", w.path("o.jsonl")]
    if inp is not None:
        args += ["--inputs", write_json(w.path("in.json"), inp)]
    code, err = run_headless(*args)
    assert code == 0, err
    return read_jsonl(w.path("o.jsonl"))


def fish_at(rows, tick, fid):
    s = {r["tick"]: r for r in snapshots(rows)}[tick]
    return {f["id"]: f for f in s["fish"]}[fid]


def school(fid="F1", kind="ca_linh", pos=(50, 8), heading=0, age=0):
    return {"id": fid, "kind": kind, "pos": list(pos), "heading_deg": heading, "age_ticks": age}


FAR = {"pos": [2, 0]}  # người chơi ở bến, xa mọi đàn


class Swim(unittest.TestCase):
    def test_swims_at_fish_speed_and_counts_age(self):
        with Workdir() as w:
            rows = run(w, {"player": FAR, "fish": [school(heading=0)]}, 60)
            f = fish_at(rows, 60, "F1")
            self.assertAlmostEqual(f["pos"][0], 50 + 60 * STEP, places=2)
            self.assertAlmostEqual(f["pos"][1], 8, places=3)
            self.assertEqual(f["age_ticks"], 60)

    def test_heading_changes_on_swim_step_120_before_moving(self):
        with Workdir() as w:
            rows = run(w, {"player": FAR, "fish": [school(heading=0, age=TURN - 1)]}, 2)
            f = fish_at(rows, 1, "F1")
            self.assertEqual(f["age_ticks"], TURN)
            self.assertNotEqual(f["heading_deg"], 0, "đổi hướng ở bước bơi thứ 120")
            h = math.radians(f["heading_deg"])
            self.assertAlmostEqual(f["pos"][0], 50 + STEP * math.cos(h), places=2, msg="đổi hướng TRƯỚC khi di chuyển")
            rows = run(w, {"player": FAR, "fish": [school(heading=0, age=0)]}, TURN - 1)
            self.assertEqual(fish_at(rows, TURN - 1, "F1")["heading_deg"], 0, "chưa tới bước 120 thì giữ hướng")

    def test_reflect_x_edge_and_flip_heading(self):
        hi = G["fish_x"][1]
        with Workdir() as w:
            rows = run(w, {"player": FAR, "fish": [school(pos=(hi - 0.01, 8), heading=0)]}, 1)
            f = fish_at(rows, 1, "F1")
            self.assertAlmostEqual(f["pos"][0], hi - (STEP - 0.01), places=3)
            self.assertAlmostEqual(f["heading_deg"], 180, places=3)

    def test_reflect_depth_band_of_species(self):
        lo, hi = G["fish_depths"]["ca_linh"]
        with Workdir() as w:
            rows = run(w, {"player": FAR, "fish": [school(pos=(50, hi - 0.01), heading=90)]}, 1)
            f = fish_at(rows, 1, "F1")
            self.assertAlmostEqual(f["pos"][1], hi - (STEP - 0.01), places=3)
            self.assertAlmostEqual(f["heading_deg"], 270, places=3)

    def test_corner_flips_both(self):
        xh = G["fish_x"][1]
        dh = G["fish_depths"]["ca_linh"][1]
        with Workdir() as w:
            rows = run(w, {"player": FAR, "fish": [school(pos=(xh - 0.001, dh - 0.001), heading=45)]}, 1)
            self.assertAlmostEqual(fish_at(rows, 1, "F1")["heading_deg"], 225, places=3)

    def test_random_fish_false_keeps_fixture_still(self):
        with Workdir() as w:
            rows = run(w, {"player": FAR, "random_fish": False, "fish": [school()]}, SPAWN)
            f = fish_at(rows, SPAWN, "F1")
            self.assertEqual(f["pos"], [50, 8])
            self.assertEqual(f["age_ticks"], 0)
            self.assertEqual(events(rows, "fish_spawned"), [])

    def test_catch_uses_position_before_swim(self):
        """Đàn đang bơi ra xa đúng mép bán kính: bắt ở bước này vẫn trúng vì xét vị trí trước khi bơi."""
        r = G["catch_radius"]
        with Workdir() as w:
            rows = run(w, {"player": {"pos": [30 + r, 10]}, "fish": [school(kind="ca_loc", pos=(30, 10), heading=180)]},
                       2, frames({"tick": 0, "catch": True}))
            self.assertEqual([e["data"]["fish_id"] for e in events(rows, "fish_caught")], ["F1"])


class Spawn(unittest.TestCase):
    def test_default_start_has_8_then_spawns_at_360(self):
        with Workdir() as w:
            rows = run(w, {"player": FAR}, SPAWN + 1)
            sp = events(rows, "fish_spawned")
            self.assertEqual([e["tick"] for e in sp], [SPAWN])
            d = sp[0]["data"]
            self.assertEqual(set(d), {"id", "kind", "pos"})
            self.assertEqual(d["id"], "F9")
            self.assertIn(d["pos"][0], G["fish_spawn_x"])
            self.assertIn(d["pos"][1], G["fish_spawn_depths"][d["kind"]])
            s = {r["tick"]: r for r in snapshots(rows)}
            self.assertEqual(len(s[SPAWN - 1]["fish"]), G["fish_initial"])
            new = {f["id"]: f for f in s[SPAWN]["fish"]}["F9"]
            others = [f for f in s[SPAWN]["fish"] if f["id"] != "F9"]
            self.assertTrue(all(math.dist(new["pos"], f["pos"]) > G["fish_spawn_clearance"] for f in others))
            self.assertEqual(new["age_ticks"], 0, "cá mới tham gia từ bước sau")
            self.assertEqual({f["id"]: f for f in s[SPAWN + 1]["fish"]}["F9"]["age_ticks"], 1)

    def test_no_spawn_at_cap(self):
        pts = [(x, d) for x in G["fish_spawn_x"] for d in (5, 10)][:G["fish_max"]]
        full = [school(f"F{i + 1}", "ca_linh", p) for i, p in enumerate(pts)]
        with Workdir() as w:
            rows = run(w, {"player": FAR, "fish": full}, SPAWN)
            self.assertEqual(events(rows, "fish_spawned"), [])

    def test_deterministic_per_seed(self):
        with Workdir() as w:
            a = run(w, {"player": FAR}, SPAWN, seed=5)
            b = run(w, {"player": FAR}, SPAWN, seed=5)
            self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
