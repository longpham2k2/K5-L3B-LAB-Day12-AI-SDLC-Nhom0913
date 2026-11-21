"""Buổi tối — Mở Quán. KHUNG: đi lại, chặn biên, đồng hồ, kho nạp từ file/scenario.

Nhóm viết tiếp (PRD-0 mục F, Quán):
  ĐÃ LÀM (lát 3): khách đến theo lịch, chọn món nấu được, giữ chỗ nguyên liệu, kiên nhẫn,
                  bỏ đi (customer_left), no_dish, vòng đời khách.
  TODO(nhóm, lát 4): interact tại bếp/bàn (cook_started, dish_ready, dish_picked, served),
                     ăn xong trả tiền (paid), boa, uy tín, hết ca (quan_end).
"""

from ..ids import sort_by_id
from .ramp import ramp_velocity

TICK = 60.0


class QuanSim:
    mode = "quan"
    phase = "quan"

    def __init__(self, tuning, scenario, streams, ids, inventory=None):
        t = tuning["quan"]
        self.t = t
        self.menu = tuning["menu"]
        self.rng = streams
        self.ids = ids
        p = scenario.get("player", {})
        self.pos = list(p.get("pos", t["start_pos"]))
        self.vel = [float(c) for c in p.get("vel", [0.0, 0.0])]
        self._tgt = None
        self._ramp_left = 0
        # kho: --inventory HOẶC scenario.stock (cả hai -> cli đã báo mã 2)
        self.stock = dict(inventory if inventory is not None else scenario.get("stock", {}))
        self.hand = scenario.get("hand")
        self.time_left_ticks = scenario.get("time_left_ticks", int(round(t["duration_s"] * 60)))
        self.reputation = scenario.get("reputation", t["reputation_initial"])
        self.stoves = [dict(s, state=s.get("state", "idle"), dish=s.get("dish"),
                            cook_ticks_left=s.get("cook_ticks_left", 0), ready_ticks=s.get("ready_ticks", 0))
                       for s in self._merge(t["stoves"], scenario.get("stoves", []))]
        self.tables = self._merge(t["tables"], scenario.get("tables", []))
        self.initial_time_left_ticks = self.time_left_ticks
        self.elapsed_ticks = 0
        self.random_customers = scenario.get("random_customers", True)
        self.customers = []
        for source in sort_by_id(scenario.get("customers", [])):
            ids.reserve(source["id"])
            customer = self._normalize_customer(source)
            if customer is not None:
                self.customers.append(customer)
        self.money = 0
        self.earned = 0
        self.shift_earned = 0
        self.done = False
        self.reason = None

    @staticmethod
    def _merge(defaults, updates):
        by_id = {d["id"]: dict(d) for d in defaults}
        for u in updates:
            if u["id"] not in by_id:
                from ..errors import BadInput
                raise BadInput(f"id bếp/bàn không tồn tại: {u['id']}")
            by_id[u["id"]].update(u)
        return sort_by_id(list(by_id.values()))

    def snapshot(self) -> dict:
        occupied = {c["table_id"]: c["id"] for c in self.customers}
        available = self._available_stock()
        return {
            "player": {"pos": self.pos},
            "stock": {k: available[k] for k in sorted(available) if available[k] > 0},
            "hand": self.hand,
            "stoves": [{k: s.get(k) for k in ("id", "pos", "state", "dish", "cook_ticks_left", "ready_ticks")}
                       for s in self.stoves],
            "tables": [{"id": tb["id"], "pos": tb["pos"], "customer_id": occupied.get(tb["id"])} for tb in self.tables],
            "customers": sort_by_id(self.customers),
        }

    def step(self, inp):
        events = []
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        self.elapsed_ticks = self.initial_time_left_ticks - self.time_left_ticks
        for customer in sort_by_id(list(self.customers)):
            if customer["state"] == "waiting":
                customer["patience_ticks_left"] = max(0, customer["patience_ticks_left"] - 1)
                if customer["patience_ticks_left"] <= 0:
                    self._remove_customer(customer)
                    self.reputation = max(
                        self.t["reputation_min"],
                        self.reputation + float(self.t["left_reputation_delta"]),
                    )
                    events.append(("customer_left", {
                        "customer_id": customer["id"],
                        "table_id": customer["table_id"],
                        "dish_id": customer.get("dish_id"),
                        "reason": "patience",
                    }))
        events.extend(self._maybe_arrive())
        self._move(inp)
        # TODO(nhóm): tối đa MỘT interact, chọn đối tượng theo (khoảng cách, bếp trước bàn, id).
        if self.time_left_ticks <= 0:
            self.done = True
            self.reason = "time"
            events.append(("quan_end", {"reason": "time", "money": self.money, "earned": self.earned,
                                        "shift_earned": self.shift_earned, "reputation": self.reputation}))
        return events

    def _move(self, inp):
        speed = self.t["walk_speed"]
        mx, mz = inp.move
        self.vel = ramp_velocity(self, (mx * speed, mz * speed), int(self.t.get("ramp_max_ticks", 6)))
        b = self.t["bounds"]
        for i, axis in enumerate(("x", "z")):
            self.pos[i] += self.vel[i] / TICK
            lo, hi = b[axis]
            if self.pos[i] <= lo:
                self.pos[i], self.vel[i] = lo, max(0.0, self.vel[i])
            elif self.pos[i] >= hi:
                self.pos[i], self.vel[i] = hi, min(0.0, self.vel[i])

    def _reserved_total(self):
        total = {}
        for customer in self.customers:
            for item, amount in customer.get("reserved", {}).items():
                total[item] = total.get(item, 0) + amount
        return total

    def _available_stock(self):
        reserved = self._reserved_total()
        available = {}
        for item in set(self.stock) | set(reserved):
            available[item] = max(0, int(self.stock.get(item, 0)) - int(reserved.get(item, 0)))
        return available

    def _cookable_dishes(self):
        available = self._available_stock()
        cookable = []
        for dish_id in sorted(self.menu):
            recipe = self.menu[dish_id].get("recipe", {})
            if all(int(available.get(item, 0)) >= int(amount) for item, amount in recipe.items()):
                cookable.append(dish_id)
        return cookable

    def _reserve_dish(self, dish_id):
        dish = self.menu.get(dish_id)
        if dish is None:
            return None
        available = self._available_stock()
        recipe = dish.get("recipe", {})
        if not all(int(available.get(item, 0)) >= int(amount) for item, amount in recipe.items()):
            return None
        return {item: int(amount) for item, amount in recipe.items()}

    def _normalize_customer(self, source):
        dish_id = source.get("dish_id")
        state = source.get("state", "waiting")
        reserved = dict(source.get("reserved", {}))

        if reserved:
            pass
        elif dish_id:
            reserved = self._reserve_dish(dish_id) or {}
            if not reserved:
                return None
        elif state == "waiting":
            dish_id = self._choose_dish()
            if dish_id is None:
                return None
            reserved = self._reserve_dish(dish_id) or {}

        patience_ticks = source.get("patience_ticks_left")
        if patience_ticks is None:
            patience_ticks = int(round(float(self.t["patience_s"]) * TICK))
        return {
            "id": source["id"],
            "table_id": source["table_id"],
            "dish_id": dish_id,
            "state": state,
            "patience_ticks_left": int(patience_ticks),
            "reserved": reserved,
        }

    def _choose_dish(self):
        cookable = self._cookable_dishes()
        if not cookable:
            return None
        if len(cookable) == 1:
            return cookable[0]
        return self.rng.get("quan_customer_dish").choice(cookable)

    def _remove_customer(self, customer):
        self.customers = [c for c in self.customers if c["id"] != customer["id"]]

    def _maybe_arrive(self):
        if not self.random_customers:
            return []

        first_tick = int(self.t["first_customer_tick"])
        interval_ticks = int(round(float(self.t["customer_interval_s"]) * TICK))
        if self.elapsed_ticks < first_tick:
            return []
        if interval_ticks > 0 and (self.elapsed_ticks - first_tick) % interval_ticks != 0:
            return []

        occupied = {c["table_id"] for c in self.customers}
        free_tables = [table["id"] for table in self.tables if table["id"] not in occupied]
        if not free_tables:
            return []

        table_id = sorted(free_tables)[0]
        customer_id = self.ids.new("C")
        dish_id = self._choose_dish()
        if dish_id is None:
            return [("no_dish", {
                "customer_id": customer_id,
                "table_id": table_id,
            })]

        reserved = self._reserve_dish(dish_id)
        if reserved is None:
            return [("no_dish", {
                "customer_id": customer_id,
                "table_id": table_id,
            })]

        customer = {
            "id": customer_id,
            "table_id": table_id,
            "dish_id": dish_id,
            "state": "waiting",
            "patience_ticks_left": int(round(float(self.t["patience_s"]) * TICK)),
            "reserved": reserved,
        }
        self.customers.append(customer)
        return [("customer_arrived", {
            "customer_id": customer_id,
            "table_id": table_id,
            "dish_id": dish_id,
            "reserved": dict(reserved),
        })]
