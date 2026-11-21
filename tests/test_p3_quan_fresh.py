"""AC-P3-03: kho cá thể, hao tươi và giữ chỗ theo id trong Quán."""

import unittest

from chonoi.contract import load_contract
from chonoi.errors import BadInput
from chonoi.ids import IdAllocator
from chonoi.inputs import InputState
from chonoi.rng import Streams
from chonoi.sim.quan import QuanSim


def idle():
    return InputState((0.0, 0.0), {}, set())


def customer(reserved=None):
    row = {
        "id": "C1",
        "table_id": "T1",
        "dish_id": "ca_loc_nuong_trui",
        "order_tick": 0,
    }
    if reserved is not None:
        row["reserved"] = reserved
    return row


class QuanFreshness(unittest.TestCase):
    def setUp(self):
        self.tuning = load_contract()["tuning"]

    def sim(self, stock, customers=()):
        return QuanSim(
            self.tuning,
            {"stock": stock, "customers": list(customers), "random_customers": False},
            Streams(1),
            IdAllocator(),
        )

    def test_auto_reservation_uses_freshest_then_natural_item_id(self):
        sim = self.sim([
            {"id": "I10", "kind": "ca_loc", "fresh": 100},
            {"id": "I2", "kind": "ca_loc", "fresh": 90},
            {"id": "I1", "kind": "ca_loc", "fresh": 100},
        ], [customer()])
        self.assertEqual(sim.customers[0]["reserved"], ["I1"])
        self.assertEqual(sim.snapshot()["stock"][0]["id"], "I10")

    def test_spoiled_event_is_id_sorted_and_keeps_spoiled_stock(self):
        sim = self.sim([
            {"id": "I10", "kind": "ca_loc", "fresh": 30},
            {"id": "I2", "kind": "ca_loc", "fresh": 30},
        ])
        events = sim.step(idle())
        self.assertEqual(events, [
            ("spoiled", {"item_id": "I2", "kind": "ca_loc", "location": "stock"}),
            ("spoiled", {"item_id": "I10", "kind": "ca_loc", "location": "stock"}),
        ])
        self.assertEqual([x["id"] for x in sim.snapshot()["stock"]], ["I10", "I2"])

    def test_held_item_that_spoils_is_released_and_reserved_once_again(self):
        sim = self.sim([
            {"id": "I1", "kind": "ca_loc", "fresh": 30},
            {"id": "I2", "kind": "ca_loc", "fresh": 80},
        ], [customer(["I1"])])
        events = sim.step(idle())
        self.assertEqual(events, [
            ("spoiled", {"item_id": "I1", "kind": "ca_loc", "location": "stock"}),
        ])
        self.assertEqual(sim.customers[0]["reserved"], ["I2"])
        self.assertEqual(sim.customers[0]["order_status"], "reserved")

    def test_rehold_shortage_becomes_unfulfillable_but_customer_keeps_waiting(self):
        sim = self.sim([
            {"id": "I1", "kind": "ca_loc", "fresh": 30},
        ], [customer(["I1"])])
        sim.step(idle())
        row = sim.customers[0]
        self.assertEqual((row["state"], row["order_status"], row["reserved"], row["dish_id"]),
                         ("waiting", "unfulfillable", [], None))
        self.assertEqual(sim.snapshot()["stock"][0]["id"], "I1")

    def test_rejects_spoiled_or_shared_fixture_reservation(self):
        with self.assertRaises(BadInput):
            self.sim([{"id": "I1", "kind": "ca_loc", "fresh": 29}], [customer(["I1"])])
        with self.assertRaises(BadInput):
            self.sim([{"id": "I1", "kind": "ca_loc", "fresh": 100}], [
                customer(["I1"]),
                {"id": "C2", "table_id": "T2", "dish_id": "ca_loc_nuong_trui", "reserved": ["I1"]},
            ])


if __name__ == "__main__":
    unittest.main()
