"""AC-P2-03 (gather v1.1): Cá Sấu tuần tra/đuổi/lùi, monster_hit, bất tử, rơi hàng LIFO, ngất do quái.
Theo TICKET-02 mục 1.2 và thứ tự 4.5 — docs/prd/phase-2.md."""

import json
import unittest

from chonoi.contract import load_contract
from chonoi.errors import BadInput
from chonoi.ids import IdAllocator
from chonoi.rng import Streams
from chonoi.sim.gather import GatherSim

from helpers import Workdir, events, items, read_jsonl, run_headless, snapshots, write_json

TUNING = load_contract()["tuning"]
G = TUNING["gather"]
MON = G["monsters"]
SP = MON["species"]["ca_sau"]
PATROL = SP["patrol_speed"] / 60.0
CHASE = SP["chase_speed"] / 60.0


def run(w, block, ticks):
    block = dict({"random_fish": False, "fish": []}, **block)
    code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", str(ticks),
                             "--scenario", write_json(w.path("sc.json"), {"gather": block}),
                             "--snapshot-every", "1", "--out", w.path("o.jsonl"))
    assert code == 0, err
    return read_jsonl(w.path("o.jsonl"))


def snap(rows, tick):
    return {r["tick"]: r for r in snapshots(rows)}[tick]


def mon(rows, tick, mid="M1"):
    return {m["id"]: m for m in snap(rows, tick)["monsters"]}[mid]


def croc(mid="M1", pos=(60, 24), wps=((60, 24), (64, 24)), **kw):
    return dict({"id": mid, "kind": "ca_sau", "pos": list(pos), "waypoints": [list(p) for p in wps]}, **kw)


def sim(day=1, upgrades=None, scenario=None):
    return GatherSim(TUNING, scenario or {}, Streams(1), IdAllocator(), day=day, active_upgrades=upgrades)


def kinds(xs):
    """v1.2 (TICKET-03): kho/giỏ là cá thể {id,kind,fresh} -> so theo loại."""
    return [x["kind"] for x in xs]


class Layout(unittest.TestCase):
    def test_standalone_uses_day1_layout(self):
        with Workdir() as w:
            m = snap(run(w, {}, 0), 0)["monsters"]
            self.assertEqual([x["id"] for x in m], ["M1"])
            self.assertEqual(m[0]["state"], "patrol")
            self.assertEqual(m[0]["target_idx"], 1)
            self.assertEqual(m[0]["pos"], [60, 24])
            self.assertIsNone(m[0]["recoil_dir"])

    def test_m2_from_day_3(self):
        self.assertEqual([m["id"] for m in sim(day=2).monsters], ["M1"])
        self.assertEqual([m["id"] for m in sim(day=3).monsters], ["M1", "M2"])

    def test_active_upgrades_set_max_oxygen_and_hp(self):
        s = sim(upgrades={"oxygen": 1, "hp": 2})
        self.assertEqual(s.oxygen_max, 45 * 60)
        self.assertEqual(s.oxygen_ticks, 45 * 60)
        self.assertEqual(s.hp, 5)
        self.assertEqual(s.snapshot()["player"]["hp_max"], 5)

    def test_bad_monster_fixture_exit_2(self):
        with Workdir() as w:
            out = w.path("o.jsonl")
            for m in (croc(kind="ca_map"), croc(state="recoil"), croc(target_idx=2),
                      croc(wps=((60, 24),)), croc(pos=(60, 5))):
                sc = write_json(w.path("sc.json"), {"gather": {"monsters": [m]}})
                code, _ = run_headless("--mode", "gather", "--seed", "1", "--ticks", "0", "--scenario", sc, "--out", out)
                self.assertEqual(code, 2, m)


class Movement(unittest.TestCase):
    def test_patrol_speed_and_switch_target_on_arrival(self):
        with Workdir() as w:
            rows = run(w, {"player": {"pos": [2, 0]}}, 245)
            self.assertAlmostEqual(mon(rows, 60)["pos"][0], 60 + 60 * PATROL, places=3)
            self.assertEqual(mon(rows, 240)["pos"], [64, 24])
            self.assertEqual(mon(rows, 240)["target_idx"], 0, "đến nơi thì đổi mục tiêu cho bước sau")
            self.assertLess(mon(rows, 241)["pos"][0], 64)

    def test_chase_when_player_deep_and_close(self):
        with Workdir() as w:
            rows = run(w, {"player": {"pos": [55, 24]}}, 2)
            m = mon(rows, 1)
            self.assertEqual(m["state"], "chase")
            self.assertAlmostEqual(m["pos"][0], 60 - CHASE, places=3)

    def test_no_chase_when_player_shallow(self):
        with Workdir() as w:
            rows = run(w, {"player": {"pos": [60, 9.9]}, "monsters": [croc(pos=(60, 10))]}, 2)
            self.assertEqual(mon(rows, 1)["state"], "patrol")
            self.assertEqual(events(rows, "monster_hit"), [], "người chơi d < 10 không bị chạm")

    def test_chase_back_to_patrol_when_far(self):
        with Workdir() as w:
            rows = run(w, {"player": {"pos": [40, 24]}, "monsters": [croc(state="chase")]}, 2)
            self.assertEqual(mon(rows, 1)["state"], "patrol")

    def test_clamped_to_species_depth(self):
        with Workdir() as w:
            rows = run(w, {"player": {"pos": [60, 10]}, "monsters": [croc(pos=(60, 11), state="chase")]}, 120)
            self.assertGreaterEqual(min(mon(rows, t)["pos"][1] for t in range(1, 120)), SP["depths"][0])


class Hit(unittest.TestCase):
    def test_hit_loses_hp_drops_half_lifo_and_sets_invuln_and_recoil(self):
        hold = items("ca_loc", "bong_sung", "ca_linh", "keo_neo", "ca_keo")
        with Workdir() as w:
            rows = run(w, {"player": {"pos": [61, 24]}, "hold": hold}, 62)
            hit = events(rows, "monster_hit")
            self.assertEqual(len(hit), 1)
            self.assertEqual(hit[0]["tick"], 1)
            d = hit[0]["data"]
            self.assertEqual(d["monster_id"], "M1")
            self.assertEqual(d["hp"], G["hp_max"] - 1)
            self.assertEqual([x["id"] for x in d["lost"]], ["I5", "I4"], "floor(5/2) = 2, nhặt sau mất trước")
            self.assertEqual(kinds(d["lost"]), ["ca_keo", "keo_neo"])
            self.assertEqual(d["pos"], [61, 24])
            s1 = snap(rows, 1)
            self.assertEqual([x["id"] for x in s1["hold"]], ["I1", "I2", "I3"])
            self.assertEqual(s1["player"]["invuln_ticks"], MON["invuln_ticks"])
            m = mon(rows, 1)
            self.assertEqual((m["state"], m["state_ticks_left"]), ("recoil", SP["recoil_ticks"]))
            self.assertEqual(m["recoil_dir"], [-1.0, 0.0], "lùi theo hướng xa người chơi")
            x1 = m["pos"][0]
            self.assertAlmostEqual(mon(rows, 2)["pos"][0], x1 - SP["recoil_dist"] / SP["recoil_ticks"], places=3,
                                   msg="lùi từ bước sau")
            self.assertEqual(mon(rows, 60)["state"], "recoil")
            self.assertEqual(mon(rows, 61)["state"], "patrol")
            self.assertIsNone(mon(rows, 61)["recoil_dir"])

    def test_no_hit_while_invulnerable_and_no_recoil(self):
        with Workdir() as w:
            rows = run(w, {"player": {"pos": [61, 24], "invuln_ticks": 50}}, 2)
            self.assertEqual(events(rows, "monster_hit"), [])
            self.assertNotEqual(mon(rows, 1)["state"], "recoil")

    def test_one_hit_per_step_nearest_then_id(self):
        both = [croc("M2", pos=(62, 24)), croc("M1", pos=(60, 24), wps=((60, 24), (56, 24)))]
        with Workdir() as w:
            rows = run(w, {"player": {"pos": [61, 24]}, "monsters": both}, 1)
            self.assertEqual([e["data"]["monster_id"] for e in events(rows, "monster_hit")], ["M1"])

    def test_faint_by_monster(self):
        with Workdir() as w:
            rows = run(w, {"player": {"pos": [61, 24], "hp": 1}, "hold": items("ca_loc", "bong_sung", "ca_linh")}, 5)
            ev = events(rows)
            self.assertEqual([e["name"] for e in ev], ["monster_hit", "faint", "gather_end"])
            self.assertEqual(kinds(ev[0]["data"]["lost"]), ["ca_linh"])
            f = ev[1]["data"]
            self.assertEqual((f["cause"], f["hp"], [x["id"] for x in f["lost"]]), ("monster", 0, ["I2", "I1"]))
            self.assertEqual(ev[2]["data"], {"reason": "fainted", "inventory": {"items": []}})


if __name__ == "__main__":
    unittest.main()
