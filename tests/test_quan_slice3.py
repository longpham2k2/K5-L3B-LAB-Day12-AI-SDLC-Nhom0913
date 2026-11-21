import unittest

from chonoi.contract import load_contract
from chonoi.errors import BadInput
from chonoi.inputs import LiveInputs
from chonoi.runner import Session

from helpers import items


class QuanSlice3(unittest.TestCase):
    def setUp(self):
        self.tuning = load_contract()["tuning"]

    def test_arrival_reserves_recipe_and_snapshot_shows_available_stock(self):
        scenario = {
            "stock": items("ca_loc"),
            "random_customers": True,
        }
        session = Session("quan", self.tuning, scenario, 1)
        live = LiveInputs()
        for _ in range(119):
            session.step(live.advance())

        rows = session.step(live.advance())
        names = [row["name"] for row in rows]
        self.assertIn("customer_arrived", names)
        customer = session.snapshot()["state"] if False else session.sim.customers[0]
        self.assertEqual(customer["dish_id"], "ca_loc_nuong_trui")
        self.assertEqual(customer["reserved"], ["I1"])
        self.assertEqual(customer["order_status"], "reserved")
        self.assertEqual(customer["order_tick"], 120)
        self.assertEqual(session.snapshot()["stock"][0]["id"], "I1")

    def test_no_dish_when_no_recipe_is_cookable(self):
        session = Session("quan", self.tuning, {"stock": [], "random_customers": True}, 1)
        live = LiveInputs()
        for _ in range(119):
            session.step(live.advance())

        rows = session.step(live.advance())
        self.assertEqual([row["name"] for row in rows], ["no_dish"])
        self.assertEqual(session.sim.customers, [])

    def test_patience_zero_leaves_customer_and_lowers_reputation(self):
        scenario = {
            "stock": items("ca_loc"),
            "random_customers": False,
            "customers": [{
                "id": "C1",
                "table_id": "T1",
                "dish_id": "ca_loc_nuong_trui",
                "patience_ticks_left": 1,
            }],
        }
        session = Session("quan", self.tuning, scenario, 1)
        live = LiveInputs()
        rows = session.step(live.advance())
        self.assertEqual([row["name"] for row in rows], ["customer_left"])
        self.assertEqual(session.sim.customers, [])
        self.assertEqual(session.sim.reputation, 2.5)
        self.assertEqual(session.snapshot()["stock"][0]["id"], "I1")

    def test_fixture_reservation_must_match_recipe_and_stock(self):
        scenario = {
            "stock": items("ca_loc"),
            "random_customers": False,
            "customers": [{
                "id": "C1",
                "table_id": "T1",
                "dish_id": "ca_loc_nuong_trui",
                "reserved": ["I1", "I2"],
            }],
        }
        with self.assertRaises(BadInput):
            Session("quan", self.tuning, scenario, 1)

    def test_no_dish_does_not_allocate_customer_id(self):
        session = Session(
            "quan",
            self.tuning,
                {"stock": [], "random_customers": True},
            1,
        )
        live = LiveInputs()
        for _ in range(119):
            session.step(live.advance())

        rows = session.step(live.advance())
        self.assertEqual([row["name"] for row in rows], ["no_dish"])
        self.assertEqual(session.sim.ids.new("C"), "C1")

    def test_closing_leaves_waiting_customer_before_quan_end(self):
        scenario = {
            "stock": items("ca_loc"),
            "random_customers": False,
            "time_left_ticks": 1,
            "customers": [{
                "id": "C1",
                "table_id": "T1",
                "dish_id": "ca_loc_nuong_trui",
                "patience_ticks_left": 1,
            }],
        }
        session = Session("quan", self.tuning, scenario, 1)
        rows = session.step(LiveInputs().advance())
        self.assertEqual([row["name"] for row in rows], ["customer_left", "quan_end"])
        self.assertEqual(rows[0]["data"]["reason"], "closing")
        self.assertEqual(rows[0]["data"]["reputation"], 3.0)
        self.assertTrue(session.done)
        self.assertEqual(session.sim.customers, [])

    def test_missing_reservation_without_stock_is_unfulfillable(self):
        session = Session(
            "quan",
            self.tuning,
            {
                "stock": [],
                "random_customers": False,
                "customers": [{
                    "id": "C1",
                    "table_id": "T1",
                    "dish_id": "ca_loc_nuong_trui",
                    "order_tick": 5,
                }],
            },
            1,
        )
        customer = session.sim.customers[0]
        self.assertEqual(customer["order_status"], "unfulfillable")
        self.assertEqual(customer["reserved"], [])
        self.assertIsNone(customer["dish_id"])


if __name__ == "__main__":
    unittest.main()
