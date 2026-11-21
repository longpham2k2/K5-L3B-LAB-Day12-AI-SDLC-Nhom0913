"""Lát 1 (gather): oxy, ngạt, Máu, ngất, dive/surface, giỏ LIFO khi ngất.
Hộp đen qua headless_cmd; mỗi test trích đúng câu trong PRD-0 mục F (Gather, bước 2)."""

import json
import unittest

from helpers import Workdir, events, frames, items, read_jsonl, run_headless, snapshots, write_json


def tuning_gather():
    with open("game.contract.json", encoding="utf-8") as f:
        return json.load(f)["tuning"]["gather"]


G = tuning_gather()
OXY_MAX = int(round(G["oxygen_max_s"] * 60))


def run(w, block, ticks, inp=None, every=1, inv_out=None):
    args = ["--mode", "gather", "--seed", "1", "--ticks", str(ticks),
            "--scenario", write_json(w.path("sc.json"), {"gather": block}),
            "--snapshot-every", str(every), "--out", w.path("o.jsonl")]
    if inp is not None:
        args += ["--inputs", write_json(w.path("in.json"), inp)]
    if inv_out:
        args += ["--inventory-out", inv_out]
    code, err = run_headless(*args)
    assert code == 0, err
    return read_jsonl(w.path("o.jsonl"))


def snap_at(rows, tick):
    return {r["tick"]: r for r in snapshots(rows)}[tick]


def kinds(xs):
    """v1.2 (TICKET-03): kho/giỏ là cá thể {id,kind,fresh} -> so theo loại."""
    return [x["kind"] for x in xs]


class Oxygen(unittest.TestCase):
    def test_underwater_drains_one_per_tick(self):
        with Workdir() as w:
            rows = run(w, {"player": {"pos": [50, 10]}, "random_fish": False}, 10)
            self.assertEqual(snap_at(rows, 10)["player"]["oxygen_ticks"], OXY_MAX - 10)
            self.assertFalse(snap_at(rows, 10)["player"]["at_surface"])

    def test_surface_refills_and_clamps(self):
        with Workdir() as w:
            rows = run(w, {"player": {"pos": [50, 0], "oxygen_ticks": 100}, "random_fish": False}, 10)
            self.assertEqual(snap_at(rows, 5)["player"]["oxygen_ticks"], 100 + 5 * G["oxygen_refill_per_tick"])
            rows = run(w, {"player": {"pos": [50, 0], "oxygen_ticks": OXY_MAX - 1}, "random_fish": False}, 3)
            self.assertEqual(snap_at(rows, 1)["player"]["oxygen_ticks"], OXY_MAX)

    def test_surface_edge_counts_as_surface(self):
        """Mặt nước là d <= surface_depth (tính cả đúng mép)."""
        with Workdir() as w:
            rows = run(w, {"player": {"pos": [50, G["surface_depth"]], "oxygen_ticks": 10}, "random_fish": False}, 1)
            self.assertEqual(snap_at(rows, 1)["player"]["oxygen_ticks"], 10 + G["oxygen_refill_per_tick"])

    def test_oxygen_empty_once_when_hitting_zero(self):
        with Workdir() as w:
            rows = run(w, {"player": {"pos": [50, 10], "oxygen_ticks": 5}, "random_fish": False}, 20)
            ev = events(rows, "oxygen_empty")
            self.assertEqual(len(ev), 1)
            self.assertEqual(ev[0]["tick"], 5)
            self.assertEqual(ev[0]["data"], {"oxygen_ticks": 0})
            self.assertEqual(snap_at(rows, 5)["player"]["zero_oxy_ticks"], 1, "kể cả bước vừa chạm 0")


class Choke(unittest.TestCase):
    def test_first_choke_at_t_plus_59(self):
        with Workdir() as w:
            rows = run(w, {"player": {"pos": [50, 10], "oxygen_ticks": 5}, "random_fish": False}, 130)
            ch = events(rows, "choke")
            self.assertEqual([e["tick"] for e in ch], [5 + 59, 5 + 59 + 60])
            self.assertEqual([e["data"] for e in ch], [{"hp": 2}, {"hp": 1}])
            self.assertEqual(snap_at(rows, 64)["player"]["zero_oxy_ticks"], 0)
            self.assertEqual(snap_at(rows, 64)["player"]["hp"], 2)

    def test_surfacing_on_choke_step_avoids_choke(self):
        sd = G["surface_depth"]
        with Workdir() as w:
            block = {"player": {"pos": [50, sd + 0.02], "vel": [0, -G["swim_speed"]], "oxygen_ticks": 0,
                                "zero_oxy_ticks": 59}, "random_fish": False}
            rows = run(w, block, 3, inp=frames({"tick": 0, "move": [0, -1]}))
            self.assertEqual(events(rows, "choke"), [])
            p = snap_at(rows, 1)["player"]
            self.assertEqual(p["hp"], G["hp_max"])
            self.assertEqual(p["zero_oxy_ticks"], 0)
            self.assertEqual(p["oxygen_ticks"], G["oxygen_refill_per_tick"])
            self.assertEqual([e["tick"] for e in events(rows, "surface")], [1])


class Faint(unittest.TestCase):
    def test_faint_drops_hold_lifo_and_ends_with_empty_inventory(self):
        with Workdir() as w:
            inv = w.path("inv.json")
            block = {"player": {"pos": [50, 10], "oxygen_ticks": 0, "zero_oxy_ticks": 59, "hp": 1},
                     "hold": items("ca_loc", "bong_sung", "ca_linh"), "random_fish": False}
            rows = run(w, block, 100, inv_out=inv)
            names = [e["name"] for e in events(rows)]
            self.assertEqual(names, ["choke", "faint", "gather_end"])
            ev = {e["name"]: e for e in events(rows)}
            self.assertEqual(ev["choke"]["data"], {"hp": 0})
            f = ev["faint"]["data"]
            self.assertEqual((f["cause"], f["hp"], kinds(f["lost"])), ("choke", 0, ["ca_linh", "bong_sung", "ca_loc"]))
            self.assertEqual([x["id"] for x in f["lost"]], ["I3", "I2", "I1"], "LIFO theo thứ tự vào giỏ")
            self.assertEqual(ev["gather_end"]["data"], {"reason": "fainted", "inventory": {"items": []}})
            self.assertTrue(all(e["tick"] == 1 for e in events(rows)))
            self.assertEqual(rows[-1]["reason"], "fainted")
            last = snapshots(rows)[-1]
            self.assertEqual(last["hold"], [])
            self.assertEqual(last["state"], "finished")
            with open(inv, encoding="utf-8") as f:
                self.assertEqual(json.load(f), {"items": []})


class DiveSurface(unittest.TestCase):
    def test_dive_event_with_pos_after_move(self):
        sd = G["surface_depth"]
        with Workdir() as w:
            block = {"player": {"pos": [50, sd], "vel": [0, G["swim_speed"]]}, "random_fish": False}
            rows = run(w, block, 5, inp=frames({"tick": 0, "move": [0, 1]}))
            dv = events(rows, "dive")
            self.assertEqual(len(dv), 1)
            self.assertEqual(dv[0]["tick"], 1)
            self.assertAlmostEqual(dv[0]["data"]["pos"][1], sd + G["swim_speed"] / 60, places=3)
            self.assertEqual(events(rows, "surface"), [])

    def test_no_event_without_crossing(self):
        with Workdir() as w:
            rows = run(w, {"player": {"pos": [50, 10]}, "random_fish": False}, 30,
                       inp=frames({"tick": 0, "move": [1, 0]}))
            self.assertEqual(events(rows, "dive") + events(rows, "surface"), [])


if __name__ == "__main__":
    unittest.main()
