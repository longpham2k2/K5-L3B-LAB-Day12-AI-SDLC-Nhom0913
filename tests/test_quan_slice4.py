"""Lát 4 (quan): nấu, bưng, phục vụ, ăn, trả tiền, boa, uy tín, hết ca, kiểm scenario mức luật.
Hộp đen qua headless_cmd (đọc số từ game.contract.json) + unit test nhiều bàn/bếp cho hòa thứ tự.
Theo PRD-0 mục D, E, F (Quán bước 1–4) — docs/prd/phase-1.md.
"""

import copy
import json
import os
import unittest

from chonoi.ids import IdAllocator
from chonoi.inputs import InputState
from chonoi.rng import Streams
from chonoi.sim.quan import QuanSim

from helpers import Workdir, events, frames, read_jsonl, run_headless, snapshots, write_json

CONTRACT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game.contract.json")
with open(CONTRACT_PATH, encoding="utf-8") as _f:
    TUNING = json.load(_f)["tuning"]

Q = TUNING["quan"]
MENU = TUNING["menu"]
MULT = TUNING["score"]["reputation_multiplier"]
PATIENCE_MAX = int(round(Q["patience_s"] * 60))
EAT_TICKS = int(round(Q["eat_s"] * 60))
STOVE_POS = Q["stoves"][0]["pos"]
TABLE_POS = Q["tables"][0]["pos"]


def run_quan(w, block, ticks, inp=None, inv_file=None, every=1):
    block = dict({"random_customers": False}, **block)
    args = ["--mode", "quan", "--seed", "1", "--ticks", str(ticks),
            "--scenario", write_json(w.path("sc.json"), {"quan": block}),
            "--snapshot-every", str(every), "--out", w.path("o.jsonl")]
    if inp is not None:
        args += ["--inputs", write_json(w.path("in.json"), inp)]
    if inv_file is not None:
        args += ["--inventory", inv_file]
    code, err = run_headless(*args)
    assert code == 0, err
    return read_jsonl(w.path("o.jsonl"))


def snap(rows, tick):
    return {r["tick"]: r for r in snapshots(rows)}[tick]


def press_interact(tick=0):
    return frames({"tick": tick, "interact": True})


def waiting_customer(cid="C1", table_id="T1", dish_id="ca_loc_nuong_trui", **extra):
    c = {"id": cid, "table_id": table_id, "dish_id": dish_id, "state": "waiting", "order_status": "reserved"}
    c.update(extra)
    return c


class CookingAndReady(unittest.TestCase):
    def test_cook_started_consumes_reserved_and_sorts_items(self):
        dish = "lau_ca_linh_dien_dien"
        cook_ticks = int(round(MENU[dish]["cook_s"] * 60))
        price = MENU[dish]["price"]
        with Workdir() as w:
            block = {
                "player": {"pos": list(STOVE_POS)},
                "stock": {"ca_linh": 3, "bong_dien_dien": 1, "ca_loc": 1},
                "customers": [waiting_customer("C1", "T1", dish, order_tick=0)],
            }
            rows = run_quan(w, block, 2, press_interact(0))
            ev = events(rows, "cook_started")
            self.assertEqual(len(ev), 1)
            self.assertEqual(ev[0]["tick"], 1)
            self.assertEqual(ev[0]["data"], {
                "stove_id": "B1",
                "order_id": "C1",
                "dish_id": dish,
                "items": ["bong_dien_dien", "ca_linh", "ca_linh", "ca_linh"],
                "base_price": price,
            })
            s1 = snap(rows, 1)
            self.assertEqual(s1["stock"], {"ca_loc": 1})
            self.assertEqual(s1["customers"][0]["reserved"], {})
            self.assertEqual(s1["customers"][0]["order_status"], "assigned")
            self.assertEqual(s1["stoves"][0]["state"], "cooking")
            self.assertEqual(s1["stoves"][0]["cook_ticks_left"], cook_ticks)
            self.assertEqual(s1["stoves"][0]["dish"], {"order_id": "C1", "dish_id": dish, "base_price": price})

    def test_cook_priority_oldest_order_tick_then_table_natural_id(self):
        """Unit test nhiều bàn: ưu tiên order_tick nhỏ nhất, hòa thì table_id theo id_key (T2 < T10)."""
        tuning = copy.deepcopy(TUNING)
        tuning["quan"]["tables"] = [
            {"id": "T10", "pos": [12, 2]},
            {"id": "T2", "pos": [14, 2]},
        ]
        scenario = {
            "random_customers": False,
            "player": {"pos": list(STOVE_POS)},
            "stock": {"ca_loc": 3},
            "customers": [
                waiting_customer("C1", "T10", "ca_loc_nuong_trui", order_tick=5),
                waiting_customer("C2", "T2", "ca_loc_nuong_trui", order_tick=5),
                # order_tick nhỏ hơn phải được chọn trước mặc dù table_id không nhỏ hơn? dùng T10 vs T2
            ],
        }
        sim = QuanSim(tuning, scenario, Streams(1), IdAllocator())
        ev = sim.step(InputState((0.0, 0.0), {"interact": True, "catch": False}, {"interact"}))
        self.assertEqual([e[0] for e in ev], ["cook_started"])
        self.assertEqual(ev[0][1]["order_id"], "C2", "cùng order_tick thì bàn T2 trước T10")

        # Kiểm tra order_tick nhỏ hơn thắng bàn id nhỏ hơn
        scenario2 = {
            "random_customers": False,
            "player": {"pos": list(STOVE_POS)},
            "stock": {"ca_loc": 2},
            "customers": [
                waiting_customer("C1", "T10", "ca_loc_nuong_trui", order_tick=3),
                waiting_customer("C2", "T2", "ca_loc_nuong_trui", order_tick=5),
            ],
        }
        sim2 = QuanSim(tuning, scenario2, Streams(1), IdAllocator())
        ev2 = sim2.step(InputState((0.0, 0.0), {"interact": True, "catch": False}, {"interact"}))
        self.assertEqual(ev2[0][1]["order_id"], "C1", "order_tick nhỏ hơn phải được nấu trước")

    def test_dish_ready_sets_ready_ticks_zero_then_increments_next_tick(self):
        dish = "goi_bong_sung"
        cook_ticks = int(round(MENU[dish]["cook_s"] * 60))
        with Workdir() as w:
            block = {
                "player": {"pos": list(STOVE_POS)},
                "stock": {"bong_sung": 2},
                "customers": [waiting_customer("C1", "T1", dish)],
            }
            rows = run_quan(w, block, cook_ticks + 4, press_interact(0))
            ready_ev = events(rows, "dish_ready")
            self.assertEqual(len(ready_ev), 1)
            ready_tick = 1 + cook_ticks
            self.assertEqual(ready_ev[0]["tick"], ready_tick)
            self.assertEqual(ready_ev[0]["data"], {"stove_id": "B1", "order_id": "C1", "dish_id": dish})
            self.assertEqual(snap(rows, ready_tick)["stoves"][0]["state"], "ready")
            self.assertEqual(snap(rows, ready_tick)["stoves"][0]["ready_ticks"], 0)
            self.assertEqual(snap(rows, ready_tick + 1)["stoves"][0]["ready_ticks"], 1)

    def test_dish_ready_and_picked_same_tick(self):
        dish = "ca_loc_nuong_trui"
        price = MENU[dish]["price"]
        with Workdir() as w:
            block = {
                "player": {"pos": list(STOVE_POS)},
                "stock": {},
                "stoves": [{"id": "B1", "state": "cooking", "dish": {"order_id": "C1", "dish_id": dish, "base_price": price},
                            "cook_ticks_left": 1, "ready_ticks": 0}],
                "customers": [waiting_customer("C1", "T1", dish, order_status="assigned", reserved={})],
            }
            rows = run_quan(w, block, 2, press_interact(0))
            ev = events(rows)
            self.assertEqual([(e["tick"], e["name"]) for e in ev], [(1, "dish_ready"), (1, "dish_picked")])
            self.assertEqual(ev[1]["data"], {"stove_id": "B1", "order_id": "C1", "dish_id": dish})
            s1 = snap(rows, 1)
            self.assertEqual(s1["stoves"][0]["state"], "idle")
            self.assertIsNone(s1["stoves"][0]["dish"])
            self.assertEqual(s1["hand"], {"order_id": "C1", "dish_id": dish, "base_price": price})


class InteractPriorityAndServe(unittest.TestCase):
    def test_interact_priority_stove_before_table_and_no_fallthrough(self):
        dish = "ca_loc_nuong_trui"
        price = MENU[dish]["price"]
        payload = {"order_id": "C1", "dish_id": dish, "base_price": price}
        # Khoảng cách bằng nhau (= 1.0) tới B1 và T1 -> chọn bếp B1 trước bàn T1
        with Workdir() as w:
            block = {
                "player": {"pos": [5, 5]},
                "stoves": [{"id": "B1", "pos": [4, 5], "state": "ready", "dish": payload, "cook_ticks_left": 0, "ready_ticks": 2}],
                "tables": [{"id": "T1", "pos": [6, 5]}],
                "customers": [waiting_customer("C1", "T1", dish, order_status="assigned", reserved={})],
            }
            rows = run_quan(w, block, 2, press_interact(0))
            self.assertEqual([e["name"] for e in events(rows)], ["dish_picked"])

        # Bếp B1 gần hơn (0.5 m) nhưng idle không nấu được, bàn T1 xa hơn (1.0 m) đang chờ món trên tay
        # -> KHÔNG rơi xuống bàn T1 (bỏ lượt)
        with Workdir() as w:
            block_idle = {
                "player": {"pos": [5, 5]},
                "hand": dict(payload),
                "stoves": [{"id": "B1", "pos": [4.5, 5], "state": "idle"}],
                "tables": [{"id": "T1", "pos": [6, 5]}],
                "customers": [waiting_customer("C1", "T1", dish, order_status="assigned", reserved={})],
            }
            rows = run_quan(w, block_idle, 2, press_interact(0))
            self.assertEqual(events(rows), [], "đối tượng gần nhất không tương tác được thì phải bỏ lượt")

    def test_exact_interact_radius_edge_and_outside(self):
        dish = "ca_loc_nuong_trui"
        price = MENU[dish]["price"]
        r = Q["interact_radius"]
        with Workdir() as w:
            block_edge = {
                "player": {"pos": [TABLE_POS[0] - r, TABLE_POS[1]]},
                "hand": {"order_id": "C1", "dish_id": dish, "base_price": price},
                "customers": [waiting_customer("C1", "T1", dish, order_status="assigned", reserved={})],
            }
            rows = run_quan(w, block_edge, 2, press_interact(0))
            self.assertEqual([e["name"] for e in events(rows)], ["served"])

            block_out = copy.deepcopy(block_edge)
            block_out["player"]["pos"] = [TABLE_POS[0] - r - 0.01, TABLE_POS[1]]
            rows_out = run_quan(w, block_out, 2, press_interact(0))
            self.assertEqual(events(rows_out), [])

    def test_hand_full_blocks_pick_and_wrong_order_blocks_serve(self):
        """Unit test 2 bàn/bếp: tay đầy không bưng bếp ready; tay sai order_id không phục vụ được bàn."""
        tuning = copy.deepcopy(TUNING)
        tuning["quan"]["stoves"] = [{"id": "B1", "pos": [2, 8]}, {"id": "B2", "pos": [5, 8]}]
        tuning["quan"]["tables"] = [{"id": "T1", "pos": [9, 2]}, {"id": "T2", "pos": [12, 2]}]
        dish = "ca_loc_nuong_trui"
        price = MENU[dish]["price"]
        scenario = {
            "random_customers": False,
            "player": {"pos": [5, 8]},
            "hand": {"order_id": "C1", "dish_id": dish, "base_price": price},
            "stoves": [{"id": "B2", "state": "ready", "dish": {"order_id": "C2", "dish_id": dish, "base_price": price},
                        "cook_ticks_left": 0, "ready_ticks": 1}],
            "customers": [
                waiting_customer("C1", "T1", dish, order_status="assigned", reserved={}),
                waiting_customer("C2", "T2", dish, order_status="assigned", reserved={}),
            ],
        }
        sim = QuanSim(tuning, scenario, Streams(1), IdAllocator())
        # Đứng ở B2 khi tay đang giữ C1 -> không bưng được
        ev1 = sim.step(InputState((0.0, 0.0), {"interact": True, "catch": False}, {"interact"}))
        self.assertEqual(ev1, [])
        self.assertEqual(sim.hand["order_id"], "C1")
        self.assertEqual(sim.stoves[1]["state"], "ready")

        # Đứng ở T2 khi tay đang giữ C1 -> không phục vụ được T2
        sim.pos = [12.0, 2.0]
        ev2 = sim.step(InputState((0.0, 0.0), {"interact": True, "catch": False}, {"interact"}))
        self.assertEqual(ev2, [])
        self.assertEqual(sim.hand["order_id"], "C1")

        # Đứng ở T1 -> phục vụ C1, tay trống, rồi quay lại B2 bưng C2
        sim.pos = [9.0, 2.0]
        ev3 = sim.step(InputState((0.0, 0.0), {"interact": True, "catch": False}, {"interact"}))
        self.assertEqual([e[0] for e in ev3], ["served"])
        self.assertIsNone(sim.hand)
        sim.pos = [5.0, 8.0]
        ev4 = sim.step(InputState((0.0, 0.0), {"interact": True, "catch": False}, {"interact"}))
        self.assertEqual([e[0] for e in ev4], ["dish_picked"])
        self.assertEqual(sim.hand["order_id"], "C2")


class TipPaymentAndReputation(unittest.TestCase):
    def test_tip_at_exact_ratio_and_below_ratio(self):
        dish = "ca_loc_nuong_trui"
        price = MENU[dish]["price"]
        expected_tip = int(price * Q["tip_rate"])
        half = int(round(PATIENCE_MAX * Q["tip_min_patience_ratio"]))

        # Sau bước 1, patience_ticks_left = half + 1 - 1 = half (đúng bằng 50%) -> được boa
        with Workdir() as w:
            block = {
                "player": {"pos": list(TABLE_POS)},
                "hand": {"order_id": "C1", "dish_id": dish, "base_price": price},
                "customers": [waiting_customer("C1", "T1", dish, order_status="assigned", reserved={},
                                               patience_ticks_left=half + 1)],
            }
            rows = run_quan(w, block, EAT_TICKS + 3, press_interact(0))
            served = events(rows, "served")[0]
            self.assertEqual(served["tick"], 1)
            self.assertEqual(served["data"], {
                "order_id": "C1", "table_id": "T1", "dish_id": dish,
                "patience_ticks_left": half, "base_price": price, "tip": expected_tip,
            })
            # Đang ăn thì chưa cộng tiền và uy tín chưa đổi
            s1 = snap(rows, 1)
            self.assertEqual(s1["money"], 0)
            self.assertEqual(s1["reputation"], Q["reputation_initial"])
            self.assertEqual(s1["customers"][0]["state"], "eating")
            self.assertEqual(s1["customers"][0]["order_status"], "served")
            self.assertEqual(s1["customers"][0]["eat_ticks_left"], EAT_TICKS)

            paid = events(rows, "paid")[0]
            pay_tick = 1 + EAT_TICKS
            self.assertEqual(paid["tick"], pay_tick)
            self.assertEqual(paid["data"], {
                "order_id": "C1", "table_id": "T1",
                "base_price": price, "tip": expected_tip, "amount": price + expected_tip,
                "reason": "finished_eating",
            })
            sp = snap(rows, pay_tick)
            self.assertEqual(sp["money"], price + expected_tip)
            self.assertEqual(sp["earned"], price + expected_tip)
            self.assertAlmostEqual(sp["reputation"], Q["reputation_initial"] + Q["tip_reputation"], places=3)
            self.assertEqual(sp["score"], (price + expected_tip) + MULT * 3)
            self.assertEqual(sp["customers"], [])
            self.assertIsNone(sp["tables"][0]["customer_id"])

        # Dưới ngưỡng 50% (patience_ticks_left ban đầu = half -> sau bước 1 còn half - 1) -> boa = 0, không tăng uy tín
        with Workdir() as w:
            block["customers"][0]["patience_ticks_left"] = half
            rows = run_quan(w, block, EAT_TICKS + 3, press_interact(0))
            self.assertEqual(events(rows, "served")[0]["data"]["tip"], 0)
            self.assertEqual(events(rows, "paid")[0]["data"]["amount"], price)
            sp = snap(rows, 1 + EAT_TICKS)
            self.assertEqual(sp["reputation"], Q["reputation_initial"])
            self.assertEqual(sp["score"], price + MULT * 3)

    def test_serve_at_zero_patience_tick_still_valid(self):
        dish = "ca_loc_nuong_trui"
        price = MENU[dish]["price"]
        with Workdir() as w:
            block = {
                "player": {"pos": list(TABLE_POS)},
                "hand": {"order_id": "C1", "dish_id": dish, "base_price": price},
                "customers": [waiting_customer("C1", "T1", dish, order_status="assigned", reserved={},
                                               patience_ticks_left=1)],
            }
            rows = run_quan(w, block, EAT_TICKS + 2, press_interact(0))
            served = events(rows, "served")[0]
            self.assertEqual(served["data"]["patience_ticks_left"], 0)
            self.assertEqual(served["data"]["tip"], 0)
            self.assertEqual(events(rows, "customer_left"), [])
            self.assertEqual(events(rows, "paid")[0]["data"]["reason"], "finished_eating")

    def test_reputation_clamps_and_no_float_drift(self):
        dish = "ca_loc_nuong_trui"
        price = MENU[dish]["price"]
        with Workdir() as w:
            block = {
                "reputation": Q["reputation_max"] - 0.1,
                "customers": [{
                    "id": "C1", "table_id": "T1", "dish_id": dish,
                    "state": "eating", "order_status": "served",
                    "eat_ticks_left": 1, "base_price": price, "tip": 12,
                }],
            }
            rows = run_quan(w, block, 2)
            self.assertEqual(snap(rows, 1)["reputation"], Q["reputation_max"])

        # Kiểm 5 lần cộng +0.2 từ 1.0 phải ra đúng 2.0 (floor == 2, không bị 1.9999999999999998)
        tuning = copy.deepcopy(TUNING)
        tuning["quan"]["tables"] = [{"id": f"T{i}", "pos": [i, 2]} for i in range(1, 6)]
        scenario = {
            "random_customers": False,
            "reputation": 1.0,
            "customers": [{
                "id": f"C{i}", "table_id": f"T{i}", "dish_id": dish,
                "state": "eating", "order_status": "served",
                "eat_ticks_left": 1, "base_price": price, "tip": 12,
            } for i in range(1, 6)],
        }
        sim = QuanSim(tuning, scenario, Streams(1), IdAllocator())
        sim.step(InputState((0.0, 0.0), {"interact": False, "catch": False}, set()))
        self.assertEqual(sim.reputation, 2.0)


class ClosingShift(unittest.TestCase):
    def test_closing_pays_just_served_customer(self):
        dish = "ca_loc_nuong_trui"
        price = MENU[dish]["price"]
        with Workdir() as w:
            block = {
                "time_left_ticks": 1,
                "player": {"pos": list(TABLE_POS)},
                "hand": {"order_id": "C1", "dish_id": dish, "base_price": price},
                "customers": [waiting_customer("C1", "T1", dish, order_status="assigned", reserved={})],
            }
            rows = run_quan(w, block, 10, press_interact(0))
            ev = events(rows)
            self.assertEqual([e["name"] for e in ev], ["served", "paid", "quan_end"])
            self.assertEqual(ev[1]["data"]["reason"], "closing")
            self.assertEqual(ev[1]["data"]["amount"], price + int(price * Q["tip_rate"]))
            self.assertEqual(ev[2]["data"]["reason"], "time")
            self.assertEqual(rows[-1]["reason"], "time")

    def test_closing_eating_finished_vs_still_eating(self):
        dish = "ca_loc_nuong_trui"
        price = MENU[dish]["price"]
        with Workdir() as w:
            block_done = {
                "time_left_ticks": 1,
                "customers": [{
                    "id": "C1", "table_id": "T1", "dish_id": dish,
                    "state": "eating", "order_status": "served",
                    "eat_ticks_left": 1, "base_price": price, "tip": 0,
                }],
            }
            rows_done = run_quan(w, block_done, 5)
            self.assertEqual([e["name"] for e in events(rows_done)], ["paid", "quan_end"])
            self.assertEqual(events(rows_done, "paid")[0]["data"]["reason"], "finished_eating")

            block_eating = copy.deepcopy(block_done)
            block_eating["customers"][0]["eat_ticks_left"] = 50
            rows_eating = run_quan(w, block_eating, 5)
            self.assertEqual([e["name"] for e in events(rows_eating)], ["paid", "quan_end"])
            self.assertEqual(events(rows_eating, "paid")[0]["data"]["reason"], "closing")

    def test_closing_waiting_customer_leaves_no_rep_loss_and_cleans_up(self):
        dish = "ca_loc_nuong_trui"
        price = MENU[dish]["price"]
        # Khách đang nấu trên bếp
        with Workdir() as w:
            block = {
                "time_left_ticks": 1,
                "stoves": [{"id": "B1", "state": "cooking",
                            "dish": {"order_id": "C1", "dish_id": dish, "base_price": price},
                            "cook_ticks_left": 100, "ready_ticks": 0}],
                "customers": [waiting_customer("C1", "T1", dish, order_status="assigned", reserved={})],
            }
            rows = run_quan(w, block, 5)
            ev = events(rows)
            self.assertEqual([e["name"] for e in ev], ["customer_left", "quan_end"])
            self.assertEqual(ev[0]["data"], {
                "order_id": "C1", "table_id": "T1", "reason": "closing", "reputation": Q["reputation_initial"],
            })
            s1 = snap(rows, 1)
            self.assertEqual(s1["stoves"][0]["state"], "idle")
            self.assertIsNone(s1["stoves"][0]["dish"])
            self.assertEqual(s1["customers"], [])

        # Khách có món trên tay
        with Workdir() as w:
            block_hand = {
                "time_left_ticks": 1,
                "hand": {"order_id": "C1", "dish_id": dish, "base_price": price},
                "customers": [waiting_customer("C1", "T1", dish, order_status="assigned", reserved={})],
            }
            rows = run_quan(w, block_hand, 5)
            self.assertEqual([e["name"] for e in events(rows)], ["customer_left", "quan_end"])
            self.assertIsNone(snap(rows, 1)["hand"])


class FullCycleAndScenarioValidation(unittest.TestCase):
    def test_full_cycle_from_inventory_and_byte_determinism(self):
        dish = "goi_bong_sung"
        price = MENU[dish]["price"]
        tip = int(price * Q["tip_rate"])
        cook_ticks = int(round(MENU[dish]["cook_s"] * 60))
        with Workdir() as w:
            inv = write_json(w.path("inv.json"), {"items": {"bong_sung": 2}})
            block = {
                "random_customers": False,
                "player": {"pos": list(STOVE_POS)},
                "stoves": [{"id": "B1", "pos": [2, 8]}],
                "tables": [{"id": "T1", "pos": [2, 6]}],  # cách bếp 2 m -> 0.5 s đi bộ
                "customers": [waiting_customer("C1", "T1", dish)],
            }
            sc = write_json(w.path("sc.json"), {"quan": block})
            pick_tick = 1 + cook_ticks
            walk_start = pick_tick + 1
            serve_tick = walk_start + 35  # 6 tick tăng tốc + 30 tick ~ 2 m
            inp = write_json(w.path("in.json"), frames(
                {"tick": 0, "interact": True},
                {"tick": 1, "interact": False},
                {"tick": pick_tick, "interact": True},
                {"tick": pick_tick + 1, "interact": False, "move": [0, -1]},
                {"tick": serve_tick - 1, "move": [0, 0]},
                {"tick": serve_tick, "interact": True},
                {"tick": serve_tick + 1, "interact": False},
            ))
            total_ticks = serve_tick + 1 + EAT_TICKS + 5
            for i in (1, 2):
                code, err = run_headless("--mode", "quan", "--seed", "7", "--ticks", str(total_ticks),
                                         "--scenario", sc, "--inputs", inp, "--inventory", inv,
                                         "--snapshot-every", "10", "--out", w.path(f"o{i}.jsonl"))
                self.assertEqual(code, 0, err)
            with open(w.path("o1.jsonl"), "rb") as a, open(w.path("o2.jsonl"), "rb") as b:
                self.assertEqual(a.read(), b.read())
            rows = read_jsonl(w.path("o1.jsonl"))
            self.assertEqual([e["name"] for e in events(rows)],
                             ["cook_started", "dish_ready", "dish_picked", "served", "paid"])
            end = rows[-1]
            self.assertEqual(end["money"], price + tip)
            self.assertEqual(end["earned"], price + tip)
            self.assertAlmostEqual(end["reputation"], Q["reputation_initial"] + Q["tip_reputation"], places=3)
            self.assertEqual(end["score"], (price + tip) + MULT * 3)

    def test_auto_reserve_when_omitted_and_invalid_scenarios_exit_2(self):
        dish = "ca_loc_nuong_trui"
        price = MENU[dish]["price"]
        with Workdir() as w:
            # Bỏ qua reserved ở đơn reserved khi kho đủ -> tự cấp đúng công thức
            rows = run_quan(w, {
                "stock": {"ca_loc": 1},
                "customers": [{"id": "C1", "table_id": "T1", "dish_id": dish}],
            }, 0)
            self.assertEqual(snapshots(rows)[0]["customers"][0]["reserved"], {"ca_loc": 1})

            bad_cases = [
                # Giữ chỗ tường minh vượt tồn kho
                {"stock": {}, "customers": [waiting_customer("C1", "T1", dish, reserved={"ca_loc": 1})]},
                # Giữ sai công thức
                {"stock": {"ca_loc": 2}, "customers": [waiting_customer("C1", "T1", dish, reserved={"ca_loc": 2})]},
                # assigned nhưng không có món ở bếp hoặc tay
                {"customers": [waiting_customer("C1", "T1", dish, order_status="assigned", reserved={})]},
                # Cùng order_id ở cả bếp và tay
                {
                    "hand": {"order_id": "C1", "dish_id": dish, "base_price": price},
                    "stoves": [{"id": "B1", "state": "ready", "dish": {"order_id": "C1", "dish_id": dish, "base_price": price}}],
                    "customers": [waiting_customer("C1", "T1", dish, order_status="assigned", reserved={})],
                },
                # Món ở bếp không khớp món khách gọi
                {
                    "stoves": [{"id": "B1", "state": "cooking", "cook_ticks_left": 10,
                                "dish": {"order_id": "C1", "dish_id": "goi_bong_sung", "base_price": 40}}],
                    "customers": [waiting_customer("C1", "T1", dish, order_status="assigned", reserved={})],
                },
                # Khách eating thiếu base_price/tip hoặc eat_ticks_left <= 0 hoặc order_status != served
                {"customers": [{"id": "C1", "table_id": "T1", "dish_id": dish, "state": "eating",
                                "order_status": "served", "eat_ticks_left": 10}]},
                {"customers": [{"id": "C1", "table_id": "T1", "dish_id": dish, "state": "eating",
                                "order_status": "served", "eat_ticks_left": 0, "base_price": price, "tip": 0}]},
                {"customers": [{"id": "C1", "table_id": "T1", "dish_id": dish, "state": "eating",
                                "order_status": "assigned", "eat_ticks_left": 10, "base_price": price, "tip": 0}]},
                # Món lạ hoặc uy tín ngoài miền
                {"customers": [waiting_customer("C1", "T1", "mon_la", reserved={})]},
                {"reputation": Q["reputation_max"] + 0.1},
            ]
            out = w.path("bad.jsonl")
            for idx, block in enumerate(bad_cases):
                sc = write_json(w.path(f"bad_{idx}.json"), {"quan": block})
                code, _ = run_headless("--mode", "quan", "--seed", "1", "--ticks", "0", "--scenario", sc, "--out", out)
                self.assertEqual(code, 2, f"case {idx} phải thoát mã 2: {block}")
                self.assertFalse(os.path.exists(out), f"case {idx} không được tạo file out")


class AssignedFixturePrice(unittest.TestCase):
    """PRD-0 mục F-Quán bước 3: giá chốt khi bắt đầu nấu, nên đơn `assigned` trong fixture được khai `base_price`
    (khớp payload món). Trước đây bị mã 2 nhầm. Boa chỉ chốt lúc phục vụ -> khách chưa ăn không được có tip > 0."""

    COOKING = {"id": "B1", "state": "cooking", "cook_ticks_left": 10,
               "dish": {"order_id": "C1", "dish_id": "ca_loc_nuong_trui", "base_price": 60}}

    def _code(self, w, customer):
        block = {"stock": {}, "random_customers": False, "stoves": [self.COOKING], "customers": [customer]}
        sc = write_json(w.path("sc.json"), {"quan": block})
        return run_headless("--mode", "quan", "--seed", "1", "--ticks", "0", "--scenario", sc,
                            "--out", w.path("o.jsonl"))[0]

    def test_assigned_customer_may_declare_matching_base_price(self):
        base = {"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "order_status": "assigned"}
        with Workdir() as w:
            self.assertEqual(self._code(w, dict(base, base_price=60)), 0)
            self.assertEqual(self._code(w, dict(base, base_price=60, tip=0)), 0)
            self.assertEqual(self._code(w, dict(base, base_price=61)), 2, "giá khác payload món trên bếp")
            self.assertEqual(self._code(w, dict(base, base_price=60, tip=12)), 2, "boa chưa chốt khi chưa phục vụ")


if __name__ == "__main__":
    unittest.main()
