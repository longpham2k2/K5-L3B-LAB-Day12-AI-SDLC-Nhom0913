import unittest

from chonoi.contract import load_contract
from chonoi.inputs import LiveInputs
from chonoi.runner import Session


class QuanSlice3(unittest.TestCase):
    def setUp(self):
        self.tuning = load_contract()["tuning"]

    def test_arrival_reserves_recipe_and_snapshot_shows_available_stock(self):
        scenario = {
            "stock": {"ca_loc": 1},
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
        self.assertEqual(customer["reserved"], {"ca_loc": 1})
        self.assertEqual(session.snapshot()["stock"], {})

    def test_no_dish_when_no_recipe_is_cookable(self):
        session = Session("quan", self.tuning, {"stock": {}, "random_customers": True}, 1)
        live = LiveInputs()
        for _ in range(119):
            session.step(live.advance())

        rows = session.step(live.advance())
        self.assertEqual([row["name"] for row in rows], ["no_dish"])
        self.assertEqual(session.sim.customers, [])

    def test_patience_zero_leaves_customer_and_lowers_reputation(self):
        scenario = {
            "stock": {"ca_loc": 1},
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
        self.assertEqual(session.snapshot()["stock"], {"ca_loc": 1})


if __name__ == "__main__":
    unittest.main()
