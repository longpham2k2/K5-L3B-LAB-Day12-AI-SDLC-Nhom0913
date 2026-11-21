"""AC-P2-04/05: quán v1.1 và Shop theo giao diện dành cho day."""

import copy
import unittest

from chonoi.contract import load_contract
from chonoi.errors import BadInput
from chonoi.ids import IdAllocator
from chonoi.inputs import InputState
from chonoi.rng import Streams
from chonoi.runner import Session
from chonoi.sim.quan import QuanSim
from chonoi.sim.shop import ShopSim


def inp(*, buy=None, done=False):
    return InputState((0.0, 0.0), {}, {"shop_done"} if done else set(), buy=buy)


class QuanV11(unittest.TestCase):
    def setUp(self):
        self.tuning = load_contract()["tuning"]

    def test_room_has_two_stoves_four_tables_and_six_dishes(self):
        sim = QuanSim(
            self.tuning,
            {"random_customers": False},
            Streams(1),
            IdAllocator(),
            plan_dishes=["ca_keo_nuong"],
            carry={"money": 70, "earned": 150, "reputation": 3.2},
        )
        snap = sim.snapshot()
        self.assertEqual([s["id"] for s in snap["stoves"]], ["B1", "B2"])
        self.assertEqual([t["id"] for t in snap["tables"]], ["T1", "T2", "T3", "T4"])
        self.assertEqual(len(self.tuning["menu"]), 6)
        self.assertEqual((sim.money, sim.earned, sim.shift_earned, sim.reputation), (70, 150, 0, 3.2))

    def test_day_plan_filters_before_available_stock(self):
        sim = QuanSim(
            self.tuning,
            {"stock": {"ca_loc": 1, "ca_keo": 2}},
            Streams(2),
            IdAllocator(),
            plan_dishes=["ca_keo_nuong"],
        )
        for _ in range(119):
            sim.step(inp())
        events = sim.step(inp())
        self.assertEqual(events, [("customer_arrived", {
            "order_id": "C1", "table_id": "T1", "dish_id": "ca_keo_nuong",
        })])
        self.assertEqual(sim.customers[0]["reserved"], {"ca_keo": 2})

    def test_bad_plan_or_carry_is_rejected(self):
        with self.assertRaises(BadInput):
            QuanSim(self.tuning, {}, Streams(1), IdAllocator(), plan_dishes=["mon_khong_co"])
        with self.assertRaises(BadInput):
            QuanSim(self.tuning, {}, Streams(1), IdAllocator(), carry={"money": 10, "earned": 0, "reputation": 3})


class Shop(unittest.TestCase):
    def setUp(self):
        self.tuning = load_contract()["tuning"]

    def shop(self, money=0, upgrades=None, tuning=None):
        return ShopSim(
            tuning or self.tuning,
            stock={"ca_loc": 1},
            carry={"money": money, "earned": money, "reputation": 3.0},
            upgrades={} if upgrades is None else upgrades,
        )

    def test_buy_exact_funds_then_done_keeps_earned_and_stock(self):
        sim = self.shop(money=200)
        self.assertEqual(sim.step(inp(buy="oxygen", done=True)), [
            ("bought", {"upgrade": "oxygen", "level": 1, "price": 200, "money": 0}),
            ("shop_end", {"reason": "done"}),
        ])
        self.assertTrue(sim.done)
        self.assertEqual(sim.reason, "done")
        self.assertEqual((sim.money, sim.earned, sim.upgrades), (0, 200, {"oxygen": 1}))
        self.assertEqual(sim.snapshot()["stock"], {"ca_loc": 1})

    def test_funds_max_level_and_unknown_leave_state_unchanged(self):
        poor = self.shop(money=199)
        self.assertEqual(poor.step(inp(buy="oxygen")), [
            ("buy_failed", {"action": "oxygen", "reason": "funds"}),
        ])
        self.assertEqual((poor.money, poor.upgrades), (199, {}))

        maxed = self.shop(money=1_100, upgrades={"oxygen": 2})
        self.assertEqual(maxed.step(inp(buy="oxygen")), [
            ("buy_failed", {"action": "oxygen", "reason": "max_level"}),
        ])
        self.assertEqual(maxed.step(inp(buy="khong_co")), [
            ("buy_failed", {"action": "khong_co", "reason": "unknown"}),
        ])
        self.assertEqual((maxed.money, maxed.upgrades), (1_100, {"oxygen": 2}))

    def test_time_closes_after_max_ticks_and_session_builds_shop(self):
        tuning = copy.deepcopy(self.tuning)
        tuning["shop"]["max_ticks"] = 1
        session = Session("shop", tuning, {"stock": {"bong_sung": 2}, "carry": {
            "money": 0, "earned": 0, "reputation": 3.0,
        }, "upgrades": {}}, 1)
        self.assertEqual(session.step(inp()), [{
            "type": "event", "tick": 1, "phase": "shop", "name": "shop_end", "data": {"reason": "time"},
        }])
        self.assertTrue(session.done)
        self.assertEqual(session.snapshot()["stock"], {"bong_sung": 2})


if __name__ == "__main__":
    unittest.main()
