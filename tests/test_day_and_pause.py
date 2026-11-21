"""Unit + hộp đen test cho AC-P2-06 (`--mode day`) và AC-P2-07 (`pause` ở cả 3 mode).
Theo TICKET-02 mục 4.1–4.5 (docs/prd/phase-2.md) và giao diện §5 (docs/contracts/README.md).
"""

import copy
import json
import os
import unittest

from chonoi.contract import load_contract
from chonoi.inputs import InputPlayer
from chonoi.runner import Session, run
from chonoi.scenario import load_scenario

from helpers import Workdir, events, frames, read_jsonl, run_headless, snapshots, write_json

CONTRACT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game.contract.json")
with open(CONTRACT_PATH, encoding="utf-8") as _f:
    TUNING = json.load(_f)["tuning"]


class _FakeGather:
    mode = "gather"
    phase = "gather"

    def __init__(self, tuning, scenario, streams, ids, *, day=1, active_upgrades=None):
        self.day = day
        self.active_upgrades = dict(active_upgrades or {})
        self.hold = list(scenario.get("hold", []))
        self.time_left_ticks = scenario.get("time_left_ticks", 10)
        self.money = 0
        self.earned = 0
        self.reputation = tuning["quan"]["reputation_initial"]
        self.done = False
        self.reason = None
        self.steps = 0

    def inventory_items(self):
        counts = {}
        for k in self.hold:
            counts[k] = counts.get(k, 0) + 1
        return {k: counts[k] for k in sorted(counts)}

    def snapshot(self):
        return {
            "player": {"pos": [2.0, 0.0], "vel": [0.0, 0.0], "heading_deg": 0.0,
                       "oxygen_ticks": 1800, "oxygen_max_ticks": 1800, "hp": 3, "hp_max": 3,
                       "zero_oxy_ticks": 0, "invuln_ticks": 0, "catch_cd_ticks": 0, "at_surface": True},
            "hold": list(self.hold), "hold_count": len(self.hold), "hold_capacity": 12,
            "nodes": [], "fish": [],
        }

    def step(self, inp):
        self.steps += 1
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        if inp.pressed("interact"):
            self.done = True
            self.reason = "docked"
            return [("gather_end", {"reason": "docked", "inventory": {"items": self.inventory_items()}})]
        if inp.pressed("catch"):
            self.hold = []
            self.done = True
            self.reason = "fainted"
            return [("faint", {"cause": "monster", "lost": [], "hp": 0}),
                    ("gather_end", {"reason": "fainted", "inventory": {"items": {}}})]
        if self.time_left_ticks <= 0:
            self.done = True
            self.reason = "time"
            return [("gather_end", {"reason": "time", "inventory": {"items": self.inventory_items()}})]
        return []


class _FakeQuan:
    mode = "quan"
    phase = "quan"

    def __init__(self, tuning, scenario, streams, ids, inventory=None, *, plan_dishes=None, carry=None):
        self.stock = dict(inventory or {})
        self.plan_dishes = list(plan_dishes or [])
        carry = carry or {}
        self.money = carry.get("money", 0)
        self.earned = carry.get("earned", 0)
        self.reputation = carry.get("reputation", tuning["quan"]["reputation_initial"])
        self.shift_earned = 0
        self.time_left_ticks = scenario.get("time_left_ticks", 5)
        self.done = False
        self.reason = None

    def snapshot(self):
        return {"player": {"pos": [8.0, 5.0], "vel": [0.0, 0.0]}, "stock": dict(self.stock),
                "hand": None, "stoves": [], "tables": [], "customers": []}

    def step(self, inp):
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        if inp.pressed("interact") and self.stock.get("ca_loc", 0) > 0:
            self.stock["ca_loc"] -= 1
            if self.stock["ca_loc"] == 0:
                del self.stock["ca_loc"]
            self.money += 200
            self.earned += 200
            self.shift_earned += 200
            self.reputation = min(5.0, self.reputation + 0.2)
        if self.time_left_ticks <= 0:
            self.done = True
            self.reason = "time"
            return [("quan_end", {"reason": "time", "money": self.money, "earned": self.earned,
                                  "shift_earned": self.shift_earned, "reputation": self.reputation})]
        return []


class _FakeShop:
    mode = "shop"
    phase = "shop"

    def __init__(self, tuning, *, stock, carry, upgrades):
        self.stock = dict(stock)
        self.upgrades = upgrades
        self.money = carry.get("money", 0)
        self.earned = carry.get("earned", 0)
        self.reputation = carry.get("reputation", tuning["quan"]["reputation_initial"])
        self.time_left_ticks = tuning["shop"]["max_ticks"]
        self.done = False
        self.reason = None
        self._cfg = tuning["shop"]["upgrades"]

    def snapshot(self):
        return {"stock": dict(self.stock)}

    def step(self, inp):
        evs = []
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        if inp.buy:
            if inp.buy not in self._cfg:
                evs.append(("buy_failed", {"action": inp.buy, "reason": "unknown"}))
            else:
                cur = self.upgrades.get(inp.buy, 0)
                if cur >= len(self._cfg[inp.buy]):
                    evs.append(("buy_failed", {"action": inp.buy, "reason": "max_level"}))
                else:
                    nxt = self._cfg[inp.buy][cur]
                    if self.money < nxt["price"]:
                        evs.append(("buy_failed", {"action": inp.buy, "reason": "funds"}))
                    else:
                        self.money -= nxt["price"]
                        self.upgrades[inp.buy] = cur + 1
                        evs.append(("bought", {"upgrade": inp.buy, "level": cur + 1,
                                               "price": nxt["price"], "money": self.money}))
        if inp.pressed("shop_done"):
            self.done = True
            self.reason = "done"
            evs.append(("shop_end", {"reason": "done"}))
        elif self.time_left_ticks <= 0:
            self.done = True
            self.reason = "time"
            evs.append(("shop_end", {"reason": "time"}))
        return evs


FACTORIES = {"gather": _FakeGather, "quan": _FakeQuan, "shop": _FakeShop}


class PauseTests(unittest.TestCase):
    def test_pause_freezes_gather_and_unpause_runs_same_tick(self):
        with Workdir() as w:
            inp = write_json(w.path("in.json"), frames(
                {"tick": 0, "move": [0, 1]},
                {"tick": 2, "pause": True, "interact": True},  # vào pause và bỏ qua interact
                {"tick": 3, "pause": False, "catch": True},    # bỏ qua catch khi đang pause
                {"tick": 4, "pause": True},                    # resume + chạy gameplay ngay bước này
                {"tick": 5, "pause": False},
            ))
            with open(inp, encoding="utf-8") as f:
                inp_frames = json.load(f)["frames"]
            run("gather", TUNING, {"player": {"pos": [2, 0]}}, 1,
                inp_frames, 6, w.path("o.jsonl"), 1)
            rows = read_jsonl(w.path("o.jsonl"))
            evs = events(rows)
            self.assertEqual([(e["tick"], e["name"], e["data"]) for e in evs], [
                (3, "paused", {}),
                (5, "resumed", {}),
            ])
            s = {r["tick"]: r for r in snapshots(rows)}
            # tick 3 & 4 đang pause: sim_tick, phase_tick, time_left_ticks đứng yên
            self.assertEqual(s[2]["state"], "playing")
            self.assertEqual(s[2]["sim_tick"], 2)
            self.assertEqual(s[3]["state"], "paused")
            self.assertEqual(s[3]["sim_tick"], 2)
            self.assertEqual(s[3]["phase_tick"], 2)
            self.assertEqual(s[3]["time_left_ticks"], s[2]["time_left_ticks"])
            self.assertEqual(s[4]["state"], "paused")
            self.assertEqual(s[4]["sim_tick"], 2)
            # tick 5: resumed + chạy gameplay ngay bước đó (sim_tick tăng từ 2 -> 3)
            self.assertEqual(s[5]["state"], "playing")
            self.assertEqual(s[5]["sim_tick"], 3)
            self.assertEqual(s[5]["phase_tick"], 3)
            self.assertEqual(s[5]["time_left_ticks"], s[2]["time_left_ticks"] - 1)
            # tick 6: sim_tick = 4
            self.assertEqual(s[6]["sim_tick"], 4)

    def test_pause_in_quan_and_tick_limit_while_paused(self):
        with Workdir() as w:
            fr = frames({"tick": 1, "pause": True}, {"tick": 2, "interact": True})["frames"]
            run("quan", TUNING, {"random_customers": False, "stock": {"ca_loc": 1}}, 1,
                fr, 4, w.path("q.jsonl"), 1)
            rows = read_jsonl(w.path("q.jsonl"))
            end = rows[-1]
            self.assertEqual(end["ticks"], 4)
            self.assertEqual(end["sim_tick"], 1)
            self.assertEqual(end["state"], "paused")
            self.assertEqual(end["reason"], "tick_limit")

    def test_pause_ignores_buy_in_shop(self):
        with Workdir() as w:
            sc = {"day": {"money": 300, "earned": 300}, "gather": {"hold": ["ca_loc"]},
                  "quan": {"time_left_ticks": 1}}
            fr = frames(
                {"tick": 0, "interact": True},   # tick 1: gather_end -> quan (phase_tick 0)
                {"tick": 1, "interact": False},  # tick 2: quan_end -> shop (phase_tick 0)
                {"tick": 2, "pause": True, "buy": "oxygen"},  # tick 3: vào pause, bỏ qua buy
                {"tick": 3, "pause": False, "buy": "oxygen"}, # tick 4: đang pause, bỏ qua buy
                {"tick": 4, "pause": True, "buy": "oxygen"},  # tick 5: resumed + buy cùng bước
                {"tick": 5, "shop_done": True},               # tick 6: shop_end -> days_complete
            )["frames"]
            run("day", TUNING, sc, 1, fr, 20, w.path("d.jsonl"), 1, days=1, sim_factories=FACTORIES)
            rows = read_jsonl(w.path("d.jsonl"))
            bought = events(rows, "bought")
            self.assertEqual(len(bought), 1)
            self.assertEqual(bought[0]["tick"], 5)
            self.assertEqual(bought[0]["day"], 1)
            self.assertEqual(bought[0]["phase"], "shop")


class DayFlowTests(unittest.TestCase):
    def test_day_two_days_upgrades_active_next_day_and_hold_reset(self):
        with Workdir() as w:
            sc = {
                "day": {"money": 50, "earned": 50},
                "gather": {"hold": ["ca_loc"]},
                "quan": {"time_left_ticks": 2},
            }
            # Ngày 1: tick 0 interact (đóng gather -> quan), tick 2 interact (bán cá +200 -> money=250),
            # tick 2 hết giờ quan -> shop, tick 3 mua oxygen cấp 1 (-200 -> 50) + shop_done -> sang Ngày 2!
            # Ngày 2: tick 4 catch (ngất -> kho rỗng), tick 6 hết giờ quan -> shop, tick 7 shop_done -> days_complete!
            fr = frames(
                {"tick": 0, "interact": True},                 # step 0 (tick 1): gather_end(docked) -> phase_start(quan)
                {"tick": 1, "interact": False},                # step 1 (tick 2): quan tick 1
                {"tick": 2, "interact": True},                 # step 2 (tick 3): quan bán (+200, rep 3.2) + quan_end -> phase_start(shop)
                {"tick": 3, "buy": "oxygen", "shop_done": True},  # step 3 (tick 4): bought -> shop_end(done) -> Day 2 day_start/day_plan/phase_start
                {"tick": 4, "interact": False, "shop_done": False, "catch": True}, # step 4 (tick 5): Day 2 faint -> gather_end(fainted) -> phase_start(quan)
                {"tick": 5, "catch": False},                   # step 5 (tick 6): Day 2 quan tick 1
                {"tick": 6},                                   # step 6 (tick 7): Day 2 quan_end -> phase_start(shop)
                {"tick": 7, "shop_done": True},                # step 7 (tick 8): Day 2 shop_end(done) -> days_complete
            )["frames"]
            run("day", TUNING, sc, 1, fr, 30, w.path("d.jsonl"), 1, days=2, sim_factories=FACTORIES)
            rows = read_jsonl(w.path("d.jsonl"))

            # Kiểm tra event tick 0 của Ngày 1
            t0_evs = [e for e in events(rows) if e["tick"] == 0]
            self.assertEqual([(e["name"], e["day"], e["phase"]) for e in t0_evs], [
                ("day_start", 1, "gather"),
                ("day_plan", 1, "gather"),
                ("phase_start", 1, "gather"),
            ])
            self.assertEqual(t0_evs[1]["data"], TUNING["day_plan"][0] | {} if False else {
                "dishes": TUNING["day_plan"][0]["dishes"],
                "ingredients": TUNING["day_plan"][0]["ingredients"],
            })

            s = {r["tick"]: r for r in snapshots(rows)}
            # tick 0: gather Ngày 1
            self.assertEqual(s[0]["day"], 1)
            self.assertEqual(s[0]["phase"], "gather")
            self.assertEqual(s[0]["phase_tick"], 0)
            self.assertEqual(s[0]["money"], 50)
            self.assertEqual(s[0]["upgrades"], {})
            self.assertEqual(s[0]["active_upgrades"], {})
            # tick 1: gather_end (phase cũ) -> phase_start(quan), snapshot đổi sang quan phase_tick=0
            self.assertEqual(s[1]["phase"], "quan")
            self.assertEqual(s[1]["phase_tick"], 0)
            # tick 3: bought sẽ ở tick 4; sau tick 3 sang shop
            self.assertEqual(s[3]["phase"], "shop")
            self.assertEqual(s[3]["phase_tick"], 0)
            self.assertEqual(s[3]["money"], 250)
            self.assertEqual(s[3]["earned"], 250)
            self.assertAlmostEqual(s[3]["reputation"], 3.2)
            # tick 4: buy("oxygen") + shop_done -> bought, shop_end (day 1, shop) rồi Day 2 day_start/day_plan/phase_start (day 2, gather)
            t4_evs = [(e["name"], e["day"], e["phase"]) for e in events(rows) if e["tick"] == 4]
            self.assertEqual(t4_evs, [
                ("bought", 1, "shop"),
                ("shop_end", 1, "shop"),
                ("day_start", 2, "gather"),
                ("day_plan", 2, "gather"),
                ("phase_start", 2, "gather"),
            ])
            self.assertEqual(s[4]["day"], 2)
            self.assertEqual(s[4]["phase"], "gather")
            self.assertEqual(s[4]["phase_tick"], 0)
            self.assertEqual(s[4]["money"], 50)
            self.assertEqual(s[4]["earned"], 250)
            self.assertEqual(s[4]["upgrades"], {"oxygen": 1})
            self.assertEqual(s[4]["active_upgrades"], {"oxygen": 1})

            # Dòng end
            end = rows[-1]
            self.assertEqual(end["type"], "end")
            self.assertEqual(end["mode"], "day")
            self.assertEqual(end["reason"], "days_complete")
            self.assertEqual(end["days_completed"], 2)
            self.assertEqual(end["money"], 50)
            self.assertEqual(end["earned"], 250)
            self.assertAlmostEqual(end["reputation"], 3.2)
            self.assertEqual(end["score"], 250 + 300)

    def test_active_upgrades_stays_empty_during_same_day_shop(self):
        with Workdir() as w:
            sc = {"day": {"money": 300, "earned": 300}, "gather": {"hold": ["ca_loc"]},
                  "quan": {"time_left_ticks": 1}}
            fr = frames(
                {"tick": 0, "interact": True},  # -> quan
                {"tick": 1, "interact": False}, # -> shop
                {"tick": 2, "buy": "hp"},       # mua hp cấp 1 trong Shop (chưa đóng Shop)
            )["frames"]
            run("day", TUNING, sc, 1, fr, 3, w.path("d.jsonl"), 1, days=2, sim_factories=FACTORIES)
            s3 = {r["tick"]: r for r in snapshots(read_jsonl(w.path("d.jsonl")))}[3]
            self.assertEqual(s3["phase"], "shop")
            self.assertEqual(s3["upgrades"], {"hp": 1})
            self.assertEqual(s3["active_upgrades"], {}, "chỉ sang Ngày mới mới áp active_upgrades")

    def test_day_deterministic_bytes_real_sims(self):
        """Chạy --mode day trên GatherSim/QuanSim thật tới bước giữa gather phải tất định từng byte."""
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {"day": {"money": 100, "earned": 100},
                                                "gather": {"random_fish": False}})
            inp = write_json(w.path("in.json"), frames({"tick": 0, "move": [0, 1]}, {"tick": 5, "pause": True},
                                                       {"tick": 7, "pause": True}))
            for i in (1, 2):
                code, err = run_headless("--mode", "day", "--days", "1", "--seed", "9", "--ticks", "12",
                                         "--scenario", sc, "--inputs", inp, "--out", w.path(f"d{i}.jsonl"))
                self.assertEqual(code, 0, err)
            with open(w.path("d1.jsonl"), "rb") as a, open(w.path("d2.jsonl"), "rb") as b:
                self.assertEqual(a.read(), b.read())

    def test_phase_change_writes_snapshot_with_phase_tick_zero(self):
        with Workdir() as w:
            sc = {"day": {}, "quan": {"time_left_ticks": 2}}
            fr = frames(
                {"tick": 0, "interact": True},                 # step 0 -> tick 1: gather -> quan
                {"tick": 1, "interact": False},                # step 1 -> tick 2: quan tick 1 (kỳ vọng không ghi snapshot)
                {"tick": 3, "shop_done": True},                # step 2 -> tick 3: quan -> shop; step 3 -> tick 4: shop -> gather(Ngày 2)
                {"tick": 4, "shop_done": False},               # step 4 -> tick 5: gather Ngày 2 tick 1 (không ghi snapshot)
                {"tick": 5, "interact": True},                 # step 5 -> tick 6: gather -> quan (Ngày 2)
                {"tick": 6, "interact": False},                # step 6 -> tick 7: quan tick 1 (không ghi snapshot)
                {"tick": 8, "shop_done": True},                # step 7 -> tick 8: quan -> shop; step 8 -> tick 9: days_complete
            )["frames"]
            run("day", TUNING, sc, 1, fr, 15, w.path("d.jsonl"), 1000, days=2, sim_factories=FACTORIES)
            snaps = snapshots(read_jsonl(w.path("d.jsonl")))
            snap_ticks = [r["tick"] for r in snaps]
            self.assertEqual(len(snap_ticks), len(set(snap_ticks)), "mỗi tick tối đa 1 snapshot")
            self.assertEqual(snap_ticks, [0, 1, 3, 4, 6, 8, 9])
            s = {r["tick"]: r for r in snaps}
            self.assertEqual((s[1]["day"], s[1]["phase"], s[1]["phase_tick"]), (1, "quan", 0))
            self.assertEqual((s[3]["day"], s[3]["phase"], s[3]["phase_tick"]), (1, "shop", 0))
            self.assertEqual((s[4]["day"], s[4]["phase"], s[4]["phase_tick"]), (2, "gather", 0))
            self.assertEqual((s[6]["day"], s[6]["phase"], s[6]["phase_tick"]), (2, "quan", 0))
            self.assertEqual((s[8]["day"], s[8]["phase"], s[8]["phase_tick"]), (2, "shop", 0))


class DayCliAndScenarioValidation(unittest.TestCase):
    def test_days_flag_and_inventory_flags_exit_2(self):
        with Workdir() as w:
            out = w.path("o.jsonl")
            inv = write_json(w.path("inv.json"), {"items": {"ca_loc": 1}})
            for args in (
                ("--mode", "gather", "--days", "1", "--seed", "1", "--ticks", "0", "--out", out),
                ("--mode", "quan", "--days", "2", "--seed", "1", "--ticks", "0", "--out", out),
                ("--mode", "day", "--days", "0", "--seed", "1", "--ticks", "0", "--out", out),
                ("--mode", "day", "--days", "6", "--seed", "1", "--ticks", "0", "--out", out),
                ("--mode", "day", "--inventory", inv, "--seed", "1", "--ticks", "0", "--out", out),
                ("--mode", "day", "--inventory-out", w.path("x.json"), "--seed", "1", "--ticks", "0", "--out", out),
            ):
                code, _ = run_headless(*args)
                self.assertEqual(code, 2, args)
                self.assertFalse(os.path.exists(out))

    def test_day_scenario_validation_rules(self):
        with Workdir() as w:
            out = w.path("o.jsonl")
            # Hợp lệ: dùng day.upgrades cấp 1 cho oxygen/hp -> gather.player.hp = 4 hợp lệ, day_plan tự tính ingredients
            good = write_json(w.path("good.json"), {
                "day": {
                    "money": 100, "earned": 200, "upgrades": {"oxygen": 1, "hp": 1},
                    "day_plan": [{"day": 1, "dishes": {"ca_loc_nuong_trui": 2}}],
                },
                "gather": {"player": {"hp": 4, "oxygen_ticks": 2700}},
            })
            code, err = run_headless("--mode", "day", "--days", "1", "--seed", "1", "--ticks", "0",
                                     "--scenario", good, "--out", out)
            self.assertEqual(code, 0, err)
            s0 = snapshots(read_jsonl(out))[0]
            self.assertEqual(s0["day_plan"], {"dishes": {"ca_loc_nuong_trui": 2}, "ingredients": {"ca_loc": 2}})
            self.assertEqual(s0["upgrades"], {"oxygen": 1, "hp": 1})
            self.assertEqual(s0["active_upgrades"], {"oxygen": 1, "hp": 1})

            # Các scenario lỗi -> mã 2
            bad_blocks = [
                {"quan": {"stock": {"ca_loc": 1}}},
                {"quan": {"reputation": 4.0}},
                {"day": {"money": 100}},  # thiếu earned
                {"day": {"money": 200, "earned": 100}},  # money > earned
                {"day": {"money": 0, "earned": 0, "upgrades": {"weapon": 1}}},  # nâng cấp chưa bật
                {"day": {"money": 0, "earned": 0, "upgrades": {"hp": 9}}},  # quá max level
                {"day": {"money": 0, "earned": 0, "day_plan": [{"day": 1, "dishes": {"ca_loc_nuong_trui": 1}, "ingredients": {"ca_loc": 9}}]}},
                {"day": {"money": 0, "earned": 0}, "gather": {"player": {"hp": 4}}},  # vượt hp cơ sở khi chưa nâng cấp
            ]
            bad_out = w.path("bad.jsonl")
            for idx, blk in enumerate(bad_blocks):
                sc = write_json(w.path(f"bad_{idx}.json"), blk)
                c, _ = run_headless("--mode", "day", "--days", "1", "--seed", "1", "--ticks", "0",
                                    "--scenario", sc, "--out", bad_out)
                self.assertEqual(c, 2, f"case {idx} phải thoát mã 2: {blk}")
                self.assertFalse(os.path.exists(bad_out))


if __name__ == "__main__":
    unittest.main()
