"""Test cửa sổ chơi trực tiếp (chonoi.live). Chỉ dành cho starter Python: nhóm đổi ngôn ngữ thì xóa file này."""

import json
import time
import unittest
import urllib.error
import urllib.request

from chonoi.contract import load_contract
from chonoi.live import LiveGame, LiveServer

from helpers import items


def _get(url):
    with urllib.request.urlopen(url, timeout=5) as r:
        return r.status, r.read()


def _post(url, obj):
    req = urllib.request.Request(url, data=json.dumps(obj).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status
    except urllib.error.HTTPError as e:
        e.close()
        return e.code


class LiveServerTest(unittest.TestCase):
    def test_state_input_and_clean_stop(self):
        tuning = load_contract()["tuning"]
        server = LiveServer(LiveGame("gather", tuning, {}, 1), port=0)  # cổng ngẫu nhiên
        server.start()
        try:
            base = f"http://127.0.0.1:{server.port}"
            code, body = _get(base + "/state")
            self.assertEqual(code, 200)
            st = json.loads(body)
            self.assertIn("tick", st)
            self.assertEqual(st["mode"], "gather")
            self.assertEqual(st["player"]["pos"], [2, 0])
            self.assertEqual(_post(base + "/input", {"move": [1, 0], "interact": False, "catch": False}), 200)
            self.assertEqual(_post(base + "/input", {"move": [5, 0]}), 400)
            code, html = _get(base + "/")
            self.assertEqual(code, 200)
            self.assertIn(b"<canvas", html)
            deadline = time.time() + 3
            while time.time() < deadline:
                st2 = json.loads(_get(base + "/state")[1])
                if st2["tick"] > st["tick"] + 3 and st2["player"]["pos"][0] > st["player"]["pos"][0]:
                    break
                time.sleep(0.05)
            self.assertGreater(st2["tick"], st["tick"], "mô phỏng phải chạy nền")
            self.assertGreater(st2["player"]["pos"][0], st["player"]["pos"][0], "input phải tác động tới sim")
        finally:
            server.stop()
        self.assertFalse(server.game._thread.is_alive())
        self.assertFalse(server._thread.is_alive())

    def test_quan_hud_state_and_html_fields(self):
        tuning = load_contract()["tuning"]
        scenario = {
            "random_customers": False,
            # v1.2 (TICKET-03): kho cá thể & reserved mảng id
            "stock": items("ca_loc", "ca_loc", "bong_sung", "bong_sung"),
            "stoves": [{"id": "B1", "state": "cooking", "cook_ticks_left": 120,
                        "dish": {"order_id": "C1", "dish_id": "ca_loc_nuong_trui", "base_price": 60}}],
            "customers": [
                {"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "order_status": "assigned", "reserved": []},
            ],
        }
        server = LiveServer(LiveGame("quan", tuning, scenario, 1), port=0)
        server.start()
        try:
            base = f"http://127.0.0.1:{server.port}"
            code, body = _get(base + "/state")
            self.assertEqual(code, 200)
            st = json.loads(body)
            self.assertEqual(st["mode"], "quan")
            self.assertEqual(st["stoves"][0]["dish"]["dish_id"], "ca_loc_nuong_trui")
            self.assertIsInstance(st["stock"], list)
            self.assertEqual(st["stock"][0]["id"], "I1")
            code, html = _get(base + "/")
            self.assertEqual(code, 200)
            html_str = html.decode("utf-8")
            self.assertIn("st.dish.dish_id", html_str)
            self.assertIn("c.reserved", html_str)
            self.assertIn("Kho khả dụng", html_str)
            for marker in ("Thủy quái!", "Hết hơi!", "Tạm dừng", "Chợ Nâng Cấp", "Tổng kết hành trình"):
                self.assertIn(marker, html_str)
        finally:
            server.stop()

    def test_day_mode_pause_hold_and_shop_inputs(self):
        tuning = load_contract()["tuning"]
        scenario = {"day": {"money": 300, "earned": 300}, "gather": {"hold": items("ca_loc")},
                    "quan": {"time_left_ticks": 1}}
        server = LiveServer(LiveGame("day", tuning, scenario, 1, days=1), port=0)
        server.start()
        try:
            base = f"http://127.0.0.1:{server.port}"
            st0 = json.loads(_get(base + "/state")[1])
            self.assertEqual(st0["mode"], "day")
            self.assertEqual(st0["day"], 1)
            self.assertIn("day_plan", st0)
            self.assertIn("shop_meta", st0)
            # Hold background loop (for intro overlays)
            self.assertEqual(_post(base + "/hold", {"hold": True}), 200)
            st_h1 = json.loads(_get(base + "/state")[1])
            time.sleep(0.08)
            st_h2 = json.loads(_get(base + "/state")[1])
            self.assertEqual(st_h1["tick"], st_h2["tick"])
            self.assertEqual(_post(base + "/hold", {"hold": False}), 200)
            # Pause / resume / buy / shop_done accepted
            self.assertEqual(_post(base + "/input", {"pause": True}), 200)
            self.assertEqual(_post(base + "/input", {"pause": False}), 200)
            self.assertEqual(_post(base + "/input", {"buy": "oxygen", "shop_done": False}), 200)
            self.assertEqual(_post(base + "/input", {"buy": ""}), 400)
        finally:
            server.stop()

    def test_day_hold_on_start_until_restart(self):
        tuning = load_contract()["tuning"]
        server = LiveServer(LiveGame("day", tuning, {}, 1, days=1, hold_on_start=True), port=0)
        server.start()
        try:
            base = f"http://127.0.0.1:{server.port}"
            time.sleep(0.06)
            st0 = json.loads(_get(base + "/state")[1])
            self.assertTrue(st0["ui_hold"])
            self.assertEqual(st0["tick"], 0)
            self.assertEqual(_post(base + "/restart", {}), 200)
            st1 = json.loads(_get(base + "/state")[1])
            self.assertFalse(st1["ui_hold"])
        finally:
            server.stop()

    def test_gather_freshness_state_and_hud_markers(self):
        tuning = load_contract()["tuning"]
        sc = {
            "hold": items("ca_loc", fresh=29.5) + items("bong_sung", fresh=95, start=2),
            "random_fish": False,
            "monsters": [],
        }
        server = LiveServer(LiveGame("gather", tuning, sc, 1), port=0)
        server.start()
        try:
            base = f"http://127.0.0.1:{server.port}"
            st = json.loads(_get(base + "/state")[1])
            self.assertEqual(st["freshness_meta"]["spoiled_below"], 30)
            self.assertEqual([(x["id"], x["kind"]) for x in st["hold"]], [("I1", "ca_loc"), ("I2", "bong_sung")])
            self.assertLess(st["hold"][0]["fresh"], 30)
            self.assertGreater(st["hold"][1]["fresh"], 90)
            html_str = _get(base + "/")[1].decode("utf-8")
            for marker in ("freshness_meta", "isSpoiled", "formatFreshList", "ươn", "Hết món"):
                self.assertIn(marker, html_str)
        finally:
            server.stop()

    def test_phase4_three_alerts_and_high_contrast_markers(self):
        tuning = load_contract()["tuning"]
        # Cảnh 1: Gather với oxy < 25% và Cá Sấu M1 gần người chơi
        g_sc = {
            "player": {"pos": [10, 12], "oxygen_ticks": 180},
            "random_fish": False,
            "monsters": [{"id": "M1", "kind": "ca_sau", "pos": [12, 12],
                          "waypoints": [[8, 12], [20, 12]], "state": "chase"}],
        }
        srv_g = LiveServer(LiveGame("gather", tuning, g_sc, 1), port=0)
        srv_g.start()
        try:
            base = f"http://127.0.0.1:{srv_g.port}"
            st = json.loads(_get(base + "/state")[1])
            self.assertGreater(st["player"]["oxygen_ticks"], 0)
            self.assertLess(st["player"]["oxygen_ticks"] / st["player"]["oxygen_max_ticks"], 0.25)
            self.assertEqual(st["monsters"][0]["state"], "chase")
            html_str = _get(base + "/")[1].decode("utf-8")
            for marker in ("Thủy quái!", "Oxy sắp hết!", "Hết hơi!", "Sắp giận!", "sắp giận!",
                           "highContrast", "setHighContrast", "Tương phản", "body.hc"):
                self.assertIn(marker, html_str)
        finally:
            srv_g.stop()

        # Cảnh 2: Quán có khách patience < 25%
        q_sc = {
            "random_customers": False,
            "stock": items("ca_loc", "ca_loc"),
            "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui",
                           "order_status": "reserved", "reserved": ["I1"], "patience_ticks_left": 300}],
        }
        srv_q = LiveServer(LiveGame("quan", tuning, q_sc, 1), port=0)
        srv_q.start()
        try:
            st_q = json.loads(_get(f"http://127.0.0.1:{srv_q.port}/state")[1])
            pat_max = st_q["meta"]["patience_s"] * 60
            self.assertLess(st_q["customers"][0]["patience_ticks_left"] / pat_max, 0.25)
        finally:
            srv_q.stop()


if __name__ == "__main__":
    unittest.main()
