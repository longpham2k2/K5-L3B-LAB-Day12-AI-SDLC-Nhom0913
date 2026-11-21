"""Lát 2 (gather): hái nút, mọc lại, bắt cá, hold_full, hồi bắt, kết thúc ở bước cuối.
Hộp đen qua headless_cmd; theo PRD-0 mục F (Gather, bước 1, 3, 4, 5) — docs/prd/phase-1.md."""

import json
import unittest

from helpers import Workdir, events, frames, read_jsonl, run_headless, snapshots, write_json

with open("game.contract.json", encoding="utf-8") as _f:
    G = json.load(_f)["tuning"]["gather"]
REGROW = int(round(G["regrow_s"] * 60))
CATCH_CD = int(round(G["catch_cooldown_s"] * 60))
CAP = G["hold_capacity"]


def run(w, block, ticks, inp=None, inv_out=None):
    block = dict({"random_fish": False}, **block)
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


def press(button, tick=0):
    return frames({"tick": tick, button: True})


def node(i, kind, x, regrow=0):
    return {"id": i, "kind": kind, "pos": [x, 0], "regrow_ticks": regrow}


def fish(i, kind, x, d):
    return {"id": i, "kind": kind, "pos": [x, d]}


class Gather(unittest.TestCase):
    def test_pick_at_exact_radius_edge(self):
        """Ví dụ mục D: nút đúng mép bán kính hái (2.0 m) vẫn hái được."""
        with Workdir() as w:
            rows = run(w, {"player": {"pos": [20, 0]}, "hold": ["ca_loc", "bong_sung"],
                           "nodes": [node("N1", "bong_dien_dien", 22)], "fish": []}, 3, press("interact"))
            ev = events(rows, "gather")
            self.assertEqual(len(ev), 1)
            self.assertEqual(ev[0]["tick"], 1)
            self.assertEqual(ev[0]["data"], {"node_id": "N1", "kind": "bong_dien_dien", "amount": 1})
            s = snap(rows, 1)
            self.assertEqual(s["hold"], ["ca_loc", "bong_sung", "bong_dien_dien"])
            self.assertEqual(s["nodes"][0]["regrow_ticks"], REGROW)
            self.assertFalse(s["nodes"][0]["ready"])

    def test_outside_radius_nothing(self):
        with Workdir() as w:
            rows = run(w, {"player": {"pos": [20, 0]}, "nodes": [node("N1", "bong_sung", 22.01)]}, 2, press("interact"))
            self.assertEqual(events(rows), [])

    def test_no_pick_underwater(self):
        with Workdir() as w:
            rows = run(w, {"player": {"pos": [20, 1]}, "nodes": [node("N1", "bong_sung", 21)]}, 2, press("interact"))
            self.assertEqual(events(rows, "gather"), [])

    def test_nearest_then_id_and_skip_not_ready(self):
        with Workdir() as w:
            rows = run(w, {"player": {"pos": [20, 0]},
                           "nodes": [node("N1", "bong_sung", 21.5), node("N2", "bong_sung", 21)]}, 2, press("interact"))
            self.assertEqual(events(rows, "gather")[0]["data"]["node_id"], "N2", "gần nhất")
            rows = run(w, {"player": {"pos": [20, 0]},
                           "nodes": [node("N2", "bong_sung", 19), node("N1", "bong_dien_dien", 21)]}, 2, press("interact"))
            self.assertEqual(events(rows, "gather")[0]["data"]["node_id"], "N1", "hòa theo id")
            rows = run(w, {"player": {"pos": [20, 0]},
                           "nodes": [node("N1", "bong_sung", 21, regrow=100), node("N2", "bong_sung", 21.5)]},
                       2, press("interact"))
            self.assertEqual(events(rows, "gather")[0]["data"]["node_id"], "N2", "bỏ nút chưa ready")

    def test_hold_full_keeps_node(self):
        with Workdir() as w:
            rows = run(w, {"player": {"pos": [20, 0]}, "hold": ["ca_loc"] * CAP,
                           "nodes": [node("N1", "bong_sung", 21)]}, 2, press("interact"))
            self.assertEqual([e["name"] for e in events(rows)], ["hold_full"])
            self.assertEqual(events(rows)[0]["data"],
                             {"action": "gather", "node_id": "N1", "required": G["node_yield"], "free": 0})
            s = snap(rows, 1)
            self.assertEqual(s["nodes"][0]["regrow_ticks"], 0)
            self.assertEqual(s["hold_count"], CAP)

    def test_regrown_then_pick_same_step(self):
        with Workdir() as w:
            rows = run(w, {"player": {"pos": [20, 0]}, "nodes": [node("N1", "bong_sung", 21, regrow=3)]}, 4,
                       press("interact", tick=2))
            ev = events(rows)
            self.assertEqual([(e["tick"], e["name"]) for e in ev], [(3, "node_regrown"), (3, "gather")])
            self.assertEqual(ev[0]["data"], {"node_id": "N1"})


class Catch(unittest.TestCase):
    def test_catch_nearest_school_full_yield(self):
        with Workdir() as w:
            rows = run(w, {"player": {"pos": [30, 10]},
                           "fish": [fish("F1", "ca_linh", 31, 10), fish("F2", "ca_loc", 31.5, 10)]}, 2, press("catch"))
            ev = events(rows, "fish_caught")
            self.assertEqual([(e["tick"], e["data"]) for e in ev],
                             [(1, {"fish_id": "F1", "kind": "ca_linh", "yield": G["fish_yield"]["ca_linh"]})])
            s = snap(rows, 1)
            self.assertEqual(s["hold"], ["ca_linh"] * G["fish_yield"]["ca_linh"])
            self.assertEqual([f["id"] for f in s["fish"]], ["F2"], "đàn bị bắt bị xóa")
            self.assertEqual(s["player"]["catch_cd_ticks"], CATCH_CD)

    def test_catch_tie_by_id_and_edge(self):
        with Workdir() as w:
            r = G["catch_radius"]
            rows = run(w, {"player": {"pos": [30, 10]},
                           "fish": [fish("F2", "ca_loc", 30 + r, 10), fish("F1", "ca_loc", 30 - r, 10)]}, 2, press("catch"))
            self.assertEqual(events(rows, "fish_caught")[0]["data"]["fish_id"], "F1")

    def test_cooldown_reuse_from_t_plus_l(self):
        """Cooldown L đặt ở tick t dùng lại từ t+L."""
        school = [fish("F1", "ca_loc", 30, 11), fish("F2", "ca_loc", 30, 9)]
        with Workdir() as w:
            early = frames({"tick": 0, "catch": True}, {"tick": 1, "catch": False}, {"tick": CATCH_CD - 1, "catch": True})
            rows = run(w, {"player": {"pos": [30, 10]}, "fish": school}, CATCH_CD + 2, early)
            self.assertEqual([e["tick"] for e in events(rows, "fish_caught")], [1])
            ok = frames({"tick": 0, "catch": True}, {"tick": 1, "catch": False}, {"tick": CATCH_CD, "catch": True})
            rows = run(w, {"player": {"pos": [30, 10]}, "fish": school}, CATCH_CD + 2, ok)
            self.assertEqual([e["tick"] for e in events(rows, "fish_caught")], [1, 1 + CATCH_CD])

    def test_hold_full_keeps_school_no_cooldown_no_other_school(self):
        with Workdir() as w:
            rows = run(w, {"player": {"pos": [30, 10]}, "hold": ["bong_sung"] * (CAP - 2),
                           "fish": [fish("F1", "ca_linh", 31, 10), fish("F2", "ca_loc", 31.5, 10)]}, 2, press("catch"))
            self.assertEqual([e["name"] for e in events(rows)], ["hold_full"])
            self.assertEqual(events(rows)[0]["data"], {"action": "catch", "fish_id": "F1",
                                                       "required": G["fish_yield"]["ca_linh"], "free": 2})
            s = snap(rows, 1)
            self.assertEqual([f["id"] for f in s["fish"]], ["F1", "F2"])
            self.assertEqual(s["player"]["catch_cd_ticks"], 0)

    def test_no_catch_at_surface_or_out_of_range(self):
        with Workdir() as w:
            rows = run(w, {"player": {"pos": [30, 0.5]}, "fish": [fish("F1", "ca_loc", 30, 1)]}, 2, press("catch"))
            self.assertEqual(events(rows), [])
            rows = run(w, {"player": {"pos": [30, 10]}, "fish": [fish("F1", "ca_loc", 33, 10)]}, 2, press("catch"))
            self.assertEqual(events(rows), [])
            self.assertEqual(snap(rows, 1)["player"]["catch_cd_ticks"], 0, "không có đàn thì không hồi chiêu")


class LastStep(unittest.TestCase):
    def test_pick_on_last_step_goes_to_inventory(self):
        with Workdir() as w:
            inv = w.path("inv.json")
            rows = run(w, {"player": {"pos": [20, 0]}, "nodes": [node("N1", "bong_sung", 21)], "time_left_ticks": 1},
                       5, press("interact"), inv_out=inv)
            self.assertEqual([e["name"] for e in events(rows)], ["gather", "gather_end"])
            self.assertEqual(events(rows, "gather_end")[0]["data"],
                             {"reason": "time", "inventory": {"items": {"bong_sung": 1}}})
            with open(inv, encoding="utf-8") as f:
                self.assertEqual(json.load(f), {"items": {"bong_sung": 1}})

    def test_dock_edge_on_last_step_is_docked(self):
        with Workdir() as w:
            x = G["dock_pos"][0] + G["dock_radius"]
            rows = run(w, {"player": {"pos": [x, 0]}, "time_left_ticks": 1}, 5, press("interact"))
            self.assertEqual(rows[-1]["reason"], "docked")


if __name__ == "__main__":
    unittest.main()
