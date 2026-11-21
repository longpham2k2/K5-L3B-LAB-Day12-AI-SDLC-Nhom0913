"""Buổi tối — Mở Quán. KHUNG: đi lại, chặn biên, đồng hồ, kho nạp từ file/scenario.

Nhóm viết tiếp (PRD-0 mục F, Quán):
  ĐÃ LÀM (lát 3): khách đến theo lịch, chọn món nấu được, giữ chỗ nguyên liệu, kiên nhẫn,
                  bỏ đi (customer_left), no_dish, vòng đời khách.
  TODO(nhóm, lát 4): interact tại bếp/bàn (cook_started, dish_ready, dish_picked, served),
                     ăn xong trả tiền (paid), boa, uy tín, hết ca (quan_end).
"""

from ..ids import id_key, sort_by_id
from ..errors import BadInput
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
        self.reputation = min(
            float(t["reputation_max"]),
            max(float(t["reputation_min"]), float(scenario.get("reputation", t["reputation_initial"]))),
        )
        self.stoves = [dict(s, state=s.get("state", "idle"), dish=s.get("dish"),
                            cook_ticks_left=s.get("cook_ticks_left", 0), ready_ticks=s.get("ready_ticks", 0))
                       for s in self._merge(t["stoves"], scenario.get("stoves", []))]
        self.tables = self._merge(t["tables"], scenario.get("tables", []))
        self.initial_time_left_ticks = self.time_left_ticks
        self.elapsed_ticks = 0
        self.random_customers = scenario.get("random_customers", True)
        self.customers = []
        sources = scenario.get("customers", [])
        explicit_sources = [source for source in sources if "reserved" in source]
        implicit_sources = [source for source in sources if "reserved" not in source]
        for source in sort_by_id(explicit_sources):
            ids.reserve(source["id"])
            customer = self._normalize_customer(source)
            self.customers.append(customer)
        implicit_sources.sort(key=lambda source: (
            int(source.get("order_tick", 0)),
            id_key(source["table_id"]),
        ))
        for source in implicit_sources:
            ids.reserve(source["id"])
            customer = self._normalize_customer(source)
            self.customers.append(customer)
        reserved_total = self._reserved_total()
        for item, amount in reserved_total.items():
            if amount > int(self.stock.get(item, 0)):
                raise BadInput("tổng giữ chỗ nguyên liệu vượt tồn kho")
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
        return {
            "player": {"pos": self.pos, "vel": self.vel},
            "stock": {k: self.stock[k] for k in sorted(self.stock) if self.stock[k] > 0},
            "hand": self.hand,
            "stoves": [{k: s.get(k) for k in ("id", "pos", "state", "dish", "cook_ticks_left", "ready_ticks")}
                       for s in self.stoves],
            "tables": [{"id": tb["id"], "pos": tb["pos"], "customer_id": occupied.get(tb["id"])} for tb in self.tables],
            "customers": sort_by_id(self.customers),
        }

    def step(self, inp):
        events = []
        # (1) đồng hồ ca, timer nấu/ăn và kiên nhẫn theo PRD
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        self.elapsed_ticks = self.initial_time_left_ticks - self.time_left_ticks
        for customer in sort_by_id(list(self.customers)):
            if customer["state"] == "waiting":
                customer["patience_ticks_left"] = max(0, customer["patience_ticks_left"] - 1)

        # (2) bếp: lát 3 để nguyên trạng; lát 4 hoàn thiện timer nấu/ready

        # (3) di chuyển, tối đa một interact
        self._move(inp)
        # TODO(nhóm): tối đa MỘT interact, chọn đối tượng theo (khoảng cách, bếp trước bàn, id).

        # (4) khách ăn xong/khách hết kiên nhẫn theo id bàn
        for table in sort_by_id(list(self.tables)):
            customer = next((c for c in self.customers if c["table_id"] == table["id"]), None)
            if customer is not None and customer["state"] == "waiting":
                closing = self.time_left_ticks <= 0
                if not closing and customer["patience_ticks_left"] > 0:
                    continue
                self._remove_customer(customer)
                if not closing:
                    self.reputation = max(
                        float(self.t["reputation_min"]),
                        min(float(self.t["reputation_max"]),
                            self.reputation + float(self.t["left_reputation_delta"])),
                    )
                events.append(("customer_left", {
                    "order_id": customer["id"],
                    "table_id": customer["table_id"],
                    "reason": "closing" if closing else "patience",
                    "reputation": self.reputation,
                }))

        # (5) khách mới, chỉ khi ca còn giờ
        if self.time_left_ticks > 0:
            events.extend(self._maybe_arrive())

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
        order_status = source.get("order_status", "reserved")

        if reserved and order_status == "reserved":
            if dish_id is not None and reserved != self.menu[dish_id]["recipe"]:
                raise BadInput("giữ chỗ khác công thức món")
        elif reserved:
            raise BadInput("reserved phải rỗng khi order_status không là reserved")
        elif order_status == "reserved" and dish_id:
            reserved = self._reserve_dish(dish_id) or {}
            if not reserved:
                order_status = "unfulfillable"
                dish_id = None
        elif order_status == "reserved" and state == "waiting":
            dish_id = self._choose_dish()
            if dish_id is None:
                order_status = "unfulfillable"
                dish_id = None
                reserved = {}
            else:
                reserved = self._reserve_dish(dish_id) or {}
                if not reserved:
                    order_status = "unfulfillable"
                    dish_id = None

        patience_ticks = source.get("patience_ticks_left")
        if patience_ticks is None:
            patience_ticks = int(round(float(self.t["patience_s"]) * TICK))
        base_price = source.get("base_price")
        if base_price is None and dish_id in self.menu:
            base_price = self.menu[dish_id]["price"]
        return {
            "id": source["id"],
            "table_id": source["table_id"],
            "dish_id": dish_id,
            "order_tick": int(source.get("order_tick", 0)),
            "state": state,
            "patience_ticks_left": int(patience_ticks),
            "eat_ticks_left": int(source.get("eat_ticks_left", 0)),
            "order_status": order_status,
            "reserved": reserved,
            "base_price": base_price,
            "tip": int(source.get("tip", 0)),
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
        if self.time_left_ticks <= 0:
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

        table_id = sort_by_id([{"id": table_id} for table_id in free_tables])[0]["id"]
        dish_id = self._choose_dish()
        if dish_id is None:
            return [("no_dish", {})]

        reserved = self._reserve_dish(dish_id)
        if reserved is None:
            return [("no_dish", {})]

        customer_id = self.ids.new("C")
        customer = {
            "id": customer_id,
            "table_id": table_id,
            "dish_id": dish_id,
            "order_tick": self.elapsed_ticks,
            "state": "waiting",
            "patience_ticks_left": int(round(float(self.t["patience_s"]) * TICK)),
            "eat_ticks_left": 0,
            "order_status": "reserved",
            "reserved": reserved,
            "base_price": self.menu[dish_id]["price"],
            "tip": 0,
        }
        self.customers.append(customer)
        return [("customer_arrived", {
            "order_id": customer_id,
            "table_id": table_id,
            "dish_id": dish_id,
        })]
