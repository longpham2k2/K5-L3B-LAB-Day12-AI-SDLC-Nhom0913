"""AC-P3-01/02 (v1.2): kho cá thể, độ tươi ở gather, spoiled, bàn giao file. Theo TICKET-03 — docs/prd/phase-3.md."""

import json
import os
import unittest

from helpers import Workdir, events, frames, items, read_jsonl, run_headless, snapshots, write_json

with open("game.contract.json", encoding="utf-8") as _f:
    C = json.load(_f)
G = C["tuning"]["gather"]
GATHER_PER_TICK = C["tuning"]["freshness"]["gather_decay_per_s"] / 60


def run(w, block, ticks, inp=None, inv_out=None):
    block = dict({"random_fish": False, "monsters": []}, **block)
    args = ["--mode", "gather", "--seed", "1", "--ticks", str(ticks),
            "--scenario", write_json(w.path("sc.json"), {"gather": block}),
            "--snapshot-every", "1", "--out", w.path("o.jsonl")]
    if inp is not None:
        args += ["--inputs", write_json(w.path("in.json"), inp)]
    if inv_out:
        args += ["--inventory-out", inv_out]
    code, err = run_headless(*args)
    assert code == 0, err
    return read_jsonl(w.path("o.jsonl"))


def snap(rows, tick):
    return {r["tick"]: r for r in snapshots(rows)}[tick]


class Contract12(unittest.TestCase):
    def test_version_and_freshness_block(self):
        self.assertEqual(C["contract_version"], "1.2")
        self.assertEqual(C["tuning"]["freshness"],
                         {"initial": 100, "gather_decay_per_s": 0.5, "quan_decay_per_s": 0.25, "spoiled_below": 30})

    def test_inventory_file_schema_v12(self):
        bad = [{"items": {"ca_loc": 1}},                                   # kho đếm v1.0–1.1
               {"items": [{"id": "I1", "kind": "ca_map", "fresh": 50}]},   # kind lạ
               {"items": items("ca_loc", "ca_loc", start=1)[:1] * 2},       # id trùng
               {"items": [{"id": "I1", "kind": "ca_loc", "fresh": 100.5}]},  # fresh ngoài miền
               {"items": [{"id": "", "kind": "ca_loc", "fresh": 50}]},     # id rỗng
               {"items": [{"id": "I1", "kind": "ca_loc"}]},                 # thiếu fresh
               {"items": []} | {"x": 1}]
        with Workdir() as w:
            for b in bad:
                p = write_json(w.path("inv.json"), b)
                code, _ = run_headless("--mode", "quan", "--seed", "1", "--ticks", "0", "--inventory", p,
                                       "--out", w.path("q.jsonl"))
                self.assertEqual(code, 2, b)
                self.assertFalse(os.path.exists(w.path("q.jsonl")))

    def test_scenario_hold_must_be_items(self):
        with Workdir() as w:
            for hold in (["ca_loc"], [{"id": "I1", "kind": "ca_loc", "fresh": -1}], items("ca_loc") * 2):
                sc = write_json(w.path("sc.json"), {"gather": {"hold": hold}})
                code, _ = run_headless("--mode", "gather", "--seed", "1", "--ticks", "0", "--scenario", sc,
                                       "--out", w.path("o.jsonl"))
                self.assertEqual(code, 2, hold)


class Freshness(unittest.TestCase):
    def test_prd_threshold_example_spoils_on_first_step(self):
        """Ví dụ TICKET-03: fresh đúng 30 -> ươn ở bước đầu (so ngưỡng trước làm tròn)."""
        with Workdir() as w:
            rows = run(w, {"hold": [{"id": "I1", "kind": "ca_linh", "fresh": 30}]}, 1)
            self.assertEqual(events(rows), [{"type": "event", "tick": 1, "phase": "gather", "name": "spoiled",
                                             "data": {"item_id": "I1", "kind": "ca_linh", "location": "hold"}}])

    def test_hold_decays_half_point_per_second_and_spoils_once(self):
        just_above = 30.5  # biểu diễn chính xác: sau đúng 60 bước = 30.0 (chưa ươn), bước 61 < 30
        with Workdir() as w:
            rows = run(w, {"hold": [{"id": "I1", "kind": "ca_loc", "fresh": 80},
                                    {"id": "I2", "kind": "ca_linh", "fresh": just_above}]}, 120)
            self.assertAlmostEqual(snap(rows, 60)["hold"][0]["fresh"], 79.5, delta=0.01)
            self.assertAlmostEqual(snap(rows, 120)["hold"][0]["fresh"], 79.0, delta=0.01)
            sp = events(rows, "spoiled")
            self.assertEqual([(e["tick"], e["data"]["item_id"]) for e in sp], [(61, "I2")], "đúng một lần, đúng tick")
            self.assertAlmostEqual(snap(rows, 60)["hold"][1]["fresh"], 30.0, delta=1e-9)

    def test_simultaneous_spoils_in_id_order_and_clamp_at_zero(self):
        with Workdir() as w:
            rows = run(w, {"hold": [{"id": "I2", "kind": "ca_loc", "fresh": 30},
                                    {"id": "I1", "kind": "ca_linh", "fresh": 30},
                                    {"id": "I3", "kind": "ca_keo", "fresh": 0}]}, 3)
            self.assertEqual([e["data"]["item_id"] for e in events(rows, "spoiled")], ["I1", "I2"])
            self.assertEqual(snap(rows, 3)["hold"][2]["fresh"], 0, "kẹp đáy 0, không phát lại")

    def test_new_item_starts_at_100_and_decays_from_next_step(self):
        with Workdir() as w:
            rows = run(w, {"player": {"pos": [20, 0]}, "hold": items("ca_loc"),
                           "nodes": [{"id": "N1", "kind": "bong_sung", "pos": [21, 0]}]}, 3, frames({"tick": 0, "interact": True}))
            h1 = snap(rows, 1)["hold"]
            self.assertEqual(h1[1], {"id": "I2", "kind": "bong_sung", "fresh": 100}, "id kế tiếp I2, fresh 100")
            self.assertAlmostEqual(snap(rows, 2)["hold"][1]["fresh"], 100 - GATHER_PER_TICK, delta=1e-3)

    def test_monster_hit_lost_items_lifo(self):
        with Workdir() as w:
            hold = items("ca_loc", "bong_sung", "ca_linh", "keo_neo")
            rows = run(w, {"player": {"pos": [61, 24]}, "hold": hold,
                           "monsters": [{"id": "M1", "kind": "ca_sau", "pos": [60, 24],
                                         "waypoints": [[60, 24], [64, 24]]}]}, 1)
            lost = events(rows, "monster_hit")[0]["data"]["lost"]
            self.assertEqual([x["id"] for x in lost], ["I4", "I3"], "nhặt sau mất trước")
            self.assertEqual(set(lost[0]), {"id", "kind", "fresh"})


class Handoff(unittest.TestCase):
    def test_prd_file_handoff_smoke(self):
        """Ví dụ TICKET-03: fresh 100 + interact tick 0 -> cập bến; quán --ticks 0 nhận đúng id/kind/fresh sau lần hao."""
        with Workdir() as w:
            inv = w.path("inv.json")
            rows = run(w, {"hold": [{"id": "I1", "kind": "ca_linh", "fresh": 100}]}, 1,
                       frames({"tick": 0, "interact": True}), inv_out=inv)
            with open(inv, encoding="utf-8") as f:
                saved = json.load(f)
            self.assertEqual(saved["items"][0]["id"], "I1")
            self.assertAlmostEqual(saved["items"][0]["fresh"], 100 - GATHER_PER_TICK, places=9, msg="đủ chính xác")
            end = events(rows, "gather_end")[0]["data"]
            self.assertEqual(end["reason"], "docked")
            self.assertAlmostEqual(end["inventory"]["items"][0]["fresh"], saved["items"][0]["fresh"], delta=0.01)
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "0", "--inventory", inv,
                                     "--out", w.path("q.jsonl"))
            self.assertEqual(code, 0, err)
            stock = snapshots(read_jsonl(w.path("q.jsonl")))[0]["stock"]
            self.assertEqual([(x["id"], x["kind"]) for x in stock], [("I1", "ca_linh")])
            self.assertAlmostEqual(stock[0]["fresh"], saved["items"][0]["fresh"], delta=0.01)

    def test_faint_writes_empty_item_inventory(self):
        with Workdir() as w:
            inv = w.path("inv.json")
            run(w, {"player": {"pos": [50, 10], "oxygen_ticks": 0, "zero_oxy_ticks": 59, "hp": 1},
                    "hold": items("ca_loc", "bong_sung")}, 5, inv_out=inv)
            with open(inv, encoding="utf-8") as f:
                self.assertEqual(json.load(f), {"items": []})


if __name__ == "__main__":
    unittest.main()
