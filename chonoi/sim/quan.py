"""Buổi tối — Mở Quán (`quan`). KHUNG: đi lại, chặn biên, đồng hồ, kho nạp từ file/scenario.

Nhóm viết tiếp (PRD-0 mục F, Quán):
  ĐÃ LÀM (lát 3 — Huy, test: tests/test_quan_slice3.py): khách đến theo lịch, chọn món
      nấu được theo seed, giữ chỗ nguyên liệu, kiên nhẫn, bỏ đi (customer_left), no_dish.
  ĐÃ LÀM (lát 4 — Duy, test: tests/test_quan_slice4.py):
      - kiểm mâu thuẫn scenario `quan` mức luật (mã thoát 2)
      - bếp (cook_started, dish_ready, ready_ticks), bưng (dish_picked), phục vụ (served)
      - tương tác ưu tiên (khoảng cách, bếp trước bàn, id tự nhiên), không rơi xuống đối tượng sau
      - ăn xong trả tiền (paid), boa (theo tỷ lệ kiên nhẫn), uy tín, đóng ca (closing), quan_end
"""

from decimal import Decimal
import math

from ..errors import BadInput
from ..ids import id_key, sort_by_id
from ..inventory import validate_items
from .ramp import ramp_velocity

TICK = 60.0
STOVE_KEYS = {"id", "pos", "state", "dish", "cook_ticks_left", "ready_ticks"}
TABLE_KEYS = {"id", "pos"}
DISH_KEYS = {"order_id", "dish_id", "base_price"}
CUSTOMER_KEYS = {
    "id", "table_id", "dish_id", "order_tick", "state",
    "patience_ticks_left", "eat_ticks_left", "order_status",
    "reserved", "base_price", "tip",
}
STOVE_STATES = ("idle", "cooking", "ready")
CUSTOMER_STATES = ("waiting", "eating")
ORDER_STATUSES = ("reserved", "assigned", "unfulfillable", "served")


def _is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _is_nonneg_int(v) -> bool:
    return not isinstance(v, bool) and isinstance(v, int) and v >= 0


def _is_pos_int(v) -> bool:
    return not isinstance(v, bool) and isinstance(v, int) and v > 0


def _check_pos(name, pos, bounds):
    if not (isinstance(pos, list) and len(pos) == 2 and all(_is_num(c) for c in pos)):
        raise BadInput(f"{name} phải là [x, z]")
    for c, axis in zip(pos, ("x", "z")):
        lo, hi = bounds[axis]
        if not (lo <= c <= hi):
            raise BadInput(f"{name} nằm ngoài vùng quán ({axis} ∈ [{lo}, {hi}])")
    return [float(pos[0]), float(pos[1])]


class QuanSim:
    mode = "quan"
    phase = "quan"

    def __init__(self, tuning, scenario, streams, ids, inventory=None, *, plan_dishes=None, carry=None):
        t = tuning["quan"]
        self.t = t
        self.menu = tuning["menu"]
        self.plan_dishes = self._init_plan_dishes(plan_dishes)
        self.rng = streams
        self.ids = ids
        p = scenario.get("player", {})
        self.pos = [float(c) for c in p.get("pos", t["start_pos"])]
        self.vel = [float(c) for c in p.get("vel", [0.0, 0.0])]
        self._tgt = None
        self._ramp_left = 0

        # kho: --inventory HOẶC scenario.stock (cả hai -> cli đã báo mã 2)
        raw_stock = inventory if inventory is not None else scenario.get("stock", {})
        self.stock = {k: v for k, v in raw_stock.items() if v > 0}

        self.phase_tick = 0
        self.time_left_ticks = scenario.get("time_left_ticks", int(round(t["duration_s"] * 60)))
        rc = scenario.get("random_customers", True)
        if not isinstance(rc, bool):
            raise BadInput("random_customers phải là boolean")
        self.random_customers = rc

        carried = self._init_carry(carry)
        if carried is None:
            money, earned = 0, 0
            rep = scenario.get("reputation", t["reputation_initial"])
        else:
            money, earned, rep = carried
        if not _is_num(rep) or not (t["reputation_min"] <= rep <= t["reputation_max"]):
            raise BadInput("reputation nằm ngoài [reputation_min, reputation_max]")
        self._rep_dec = Decimal(str(rep))
        self.reputation = float(self._rep_dec)

        bounds = t["bounds"]
        self.stoves = self._init_stoves(self._merge(t["stoves"], scenario.get("stoves", []), STOVE_KEYS, bounds))
        self.tables = self._init_tables(self._merge(t["tables"], scenario.get("tables", []), TABLE_KEYS, bounds))
        self.hand = self._validate_dish("quan.hand", scenario.get("hand")) if scenario.get("hand") is not None else None
        self.customers = self._init_customers(scenario.get("customers", []))
        self._validate_cross_state()

        for e in self.customers:
            ids.reserve(e["id"])
        self.money = money
        self.earned = earned
        self.shift_earned = 0
        self.done = False
        self.reason = None

    def _init_plan_dishes(self, plan_dishes):
        """Danh sách món của ngày: lọc menu trước khi xét kho khả dụng."""
        if plan_dishes is None:
            return None
        if not isinstance(plan_dishes, list) or not all(isinstance(d, str) for d in plan_dishes):
            raise BadInput("plan_dishes phải là mảng id món")
        if len(set(plan_dishes)) != len(plan_dishes):
            raise BadInput("plan_dishes không được lặp id món")
        unknown = sorted(set(plan_dishes) - set(self.menu))
        if unknown:
            raise BadInput(f"plan_dishes có món không có trong menu: {unknown}")
        return frozenset(plan_dishes)

    def _init_carry(self, carry):
        """Trạng thái xuyên Ngày do DaySim bàn giao; None nghĩa là ca độc lập."""
        if carry is None:
            return None
        if not isinstance(carry, dict) or set(carry) != {"money", "earned", "reputation"}:
            raise BadInput("carry phải có đúng money, earned, reputation")
        money, earned, rep = carry["money"], carry["earned"], carry["reputation"]
        if not _is_nonneg_int(money) or not _is_nonneg_int(earned) or money > earned:
            raise BadInput("carry cần 0 <= money <= earned (số nguyên)")
        if not _is_num(rep):
            raise BadInput("carry.reputation phải là số hữu hạn")
        return money, earned, rep

    @staticmethod
    def _merge(defaults, updates, allowed_keys, bounds):
        by_id = {}
        for d in defaults:
            item = dict(d)
            item["pos"] = [float(c) for c in d["pos"]]
            by_id[d["id"]] = item
        for u in updates:
            uid = u["id"]
            if uid not in by_id:
                raise BadInput(f"id bếp/bàn không tồn tại: {uid}")
            extra = set(u) - allowed_keys
            if extra:
                raise BadInput(f"trường lạ ở bếp/bàn {uid}: {sorted(extra)}")
            merged = dict(by_id[uid])
            merged.update(u)
            merged["pos"] = _check_pos(f"{uid}.pos", merged["pos"], bounds)
            by_id[uid] = merged
        return sort_by_id(list(by_id.values()))

    def _validate_dish(self, name, d):
        if not isinstance(d, dict) or set(d) != DISH_KEYS:
            raise BadInput(f"{name}: payload món phải có đúng {sorted(DISH_KEYS)}")
        if not isinstance(d["order_id"], str) or not d["order_id"]:
            raise BadInput(f"{name}.order_id phải là chuỗi khác rỗng")
        if d["dish_id"] not in self.menu:
            raise BadInput(f"{name}.dish_id không có trong menu: {d['dish_id']!r}")
        if not _is_pos_int(d["base_price"]):
            raise BadInput(f"{name}.base_price phải là số nguyên dương")
        return {"order_id": d["order_id"], "dish_id": d["dish_id"], "base_price": d["base_price"]}

    def _init_stoves(self, merged):
        stoves = []
        for s in merged:
            state = s.get("state", "idle")
            if state not in STOVE_STATES:
                raise BadInput(f"stoves.{s['id']}.state không hợp lệ: {state!r}")
            raw_dish = s.get("dish")
            dish = self._validate_dish(f"stoves.{s['id']}.dish", raw_dish) if raw_dish is not None else None
            cook_left = s.get("cook_ticks_left", 0)
            ready_ticks = s.get("ready_ticks", 0)
            if not _is_nonneg_int(cook_left) or not _is_nonneg_int(ready_ticks):
                raise BadInput(f"stoves.{s['id']}: bộ đếm phải là số nguyên không âm")
            if state == "idle":
                if dish is not None or cook_left != 0 or ready_ticks != 0:
                    raise BadInput(f"stoves.{s['id']}: bếp idle không được có món hoặc timer dương")
            elif state == "cooking":
                if dish is None or cook_left <= 0 or ready_ticks != 0:
                    raise BadInput(f"stoves.{s['id']}: bếp cooking cần món, cook_ticks_left > 0 và ready_ticks = 0")
            else:  # ready
                if dish is None or cook_left != 0:
                    raise BadInput(f"stoves.{s['id']}: bếp ready cần món và cook_ticks_left = 0")
            stoves.append({
                "id": s["id"],
                "pos": s["pos"],
                "state": state,
                "dish": dish,
                "cook_ticks_left": cook_left,
                "ready_ticks": ready_ticks,
            })
        return stoves

    @staticmethod
    def _init_tables(merged):
        return [{"id": tb["id"], "pos": tb["pos"]} for tb in merged]

    def _init_customers(self, raw_customers):
        patience_max = int(round(self.t["patience_s"] * TICK))
        customers = []
        for c in raw_customers:
            cid = c["id"]
            extra = set(c) - CUSTOMER_KEYS
            if extra:
                raise BadInput(f"customers.{cid}: trường lạ {sorted(extra)}")
            order_status = c.get("order_status", "reserved")
            if order_status not in ORDER_STATUSES:
                raise BadInput(f"customers.{cid}.order_status không hợp lệ: {order_status!r}")
            dish_id = c.get("dish_id")
            if order_status == "unfulfillable":
                if dish_id is not None and (not isinstance(dish_id, str) or dish_id not in self.menu):
                    raise BadInput(f"customers.{cid}: dish_id không hợp lệ: {dish_id!r}")
            else:
                if not isinstance(dish_id, str) or dish_id not in self.menu:
                    raise BadInput(f"customers.{cid}: dish_id không hợp lệ: {dish_id!r}")
            state = c.get("state", "waiting")
            if state not in CUSTOMER_STATES:
                raise BadInput(f"customers.{cid}: state không hợp lệ: {state!r}")
            order_tick = c.get("order_tick", 0)
            if not _is_nonneg_int(order_tick):
                raise BadInput(f"customers.{cid}.order_tick phải là số nguyên không âm")

            if state == "eating":
                if order_status != "served":
                    raise BadInput(f"customers.{cid}: khách eating phải có order_status = 'served'")
                eat_left = c.get("eat_ticks_left", 0)
                if not _is_pos_int(eat_left):
                    raise BadInput(f"customers.{cid}: khách eating phải có eat_ticks_left > 0")
                pat_left = c.get("patience_ticks_left", 0)
                if not _is_nonneg_int(pat_left) or pat_left > patience_max:
                    raise BadInput(f"customers.{cid}.patience_ticks_left không hợp lệ")
                bp, tip = c.get("base_price"), c.get("tip")
                if not _is_pos_int(bp) or not _is_nonneg_int(tip):
                    raise BadInput(f"customers.{cid}: khách eating phải khai base_price > 0 và tip >= 0")
                reserved = validate_items(c["reserved"]) if "reserved" in c else {}
                if reserved:
                    raise BadInput(f"customers.{cid}: khách eating không được còn reserved")
            else:  # waiting
                if order_status == "served":
                    raise BadInput(f"customers.{cid}: khách waiting không thể có order_status = 'served'")
                eat_left = c.get("eat_ticks_left", 0)
                if eat_left != 0:
                    raise BadInput(f"customers.{cid}: khách waiting phải có eat_ticks_left = 0")
                pat_left = c.get("patience_ticks_left", patience_max)
                if not _is_nonneg_int(pat_left) or pat_left > patience_max:
                    raise BadInput(f"customers.{cid}.patience_ticks_left phải trong [0, {patience_max}]")
                bp, tip = c.get("base_price"), c.get("tip")
                # Giá chốt khi bắt đầu nấu (F-Quán bước 3) -> đơn assigned được khai base_price (khớp món, kiểm ở
                # _validate_cross_state). Boa chỉ chốt lúc phục vụ -> khách chưa ăn chỉ được tip vắng/null/0.
                if bp is not None and (order_status != "assigned" or not _is_pos_int(bp)):
                    raise BadInput(f"customers.{cid}: chỉ đơn assigned mới được khai base_price (số nguyên dương)")
                if tip not in (None, 0) or isinstance(tip, bool):
                    raise BadInput(f"customers.{cid}: khách waiting chưa được chốt boa")
                if "reserved" in c:
                    reserved = validate_items(c["reserved"])
                    if order_status == "reserved":
                        recipe = {k: v for k, v in self.menu[dish_id]["recipe"].items() if v > 0}
                        if reserved != recipe:
                            raise BadInput(f"customers.{cid}: reserved không khớp công thức món {dish_id}")
                    elif reserved:
                        raise BadInput(f"customers.{cid}: đơn {order_status} phải có reserved rỗng")
                else:
                    reserved = None if order_status == "reserved" else {}

            customers.append({
                "id": cid,
                "table_id": c["table_id"],
                "dish_id": dish_id,
                "order_tick": order_tick,
                "state": state,
                "patience_ticks_left": pat_left,
                "eat_ticks_left": eat_left,
                "order_status": order_status,
                "reserved": reserved,
                "base_price": bp,
                "tip": tip,
            })

        # Kiểm tổng giữ chỗ tường minh, rồi cấp phát tự động cho đơn reserved khuyết (thiếu kho -> unfulfillable theo Clarify #2)
        used_reserved = {}
        for c in customers:
            if c["reserved"]:
                for k, qty in c["reserved"].items():
                    used_reserved[k] = used_reserved.get(k, 0) + qty
        for k, qty in used_reserved.items():
            if qty > self.stock.get(k, 0):
                raise BadInput(f"tổng giữ chỗ nguyên liệu {k} ({qty}) vượt tồn kho ({self.stock.get(k, 0)})")

        for c in sorted(customers, key=lambda x: (x["order_tick"], id_key(x["table_id"]))):
            if c["reserved"] is None:
                recipe = {k: v for k, v in self.menu[c["dish_id"]]["recipe"].items() if v > 0}
                if all(used_reserved.get(k, 0) + qty <= self.stock.get(k, 0) for k, qty in recipe.items()):
                    for k, qty in recipe.items():
                        used_reserved[k] = used_reserved.get(k, 0) + qty
                    c["reserved"] = recipe
                else:
                    c["order_status"] = "unfulfillable"
                    c["reserved"] = {}
                    c["dish_id"] = None

        return customers

    def _validate_cross_state(self):
        dishes_by_order = {}
        for s in self.stoves:
            if s["dish"] is not None:
                oid = s["dish"]["order_id"]
                if oid in dishes_by_order:
                    raise BadInput(f"nhiều vị trí giữ cùng đơn {oid}")
                dishes_by_order[oid] = s["dish"]
        if self.hand is not None:
            oid = self.hand["order_id"]
            if oid in dishes_by_order:
                raise BadInput(f"bếp và tay giữ cùng đơn {oid}")
            dishes_by_order[oid] = self.hand

        by_id = {c["id"]: c for c in self.customers}
        for oid, dish in dishes_by_order.items():
            if oid not in by_id:
                raise BadInput(f"món trên bếp/tay tham chiếu khách không tồn tại: {oid}")
            c = by_id[oid]
            if c["state"] != "waiting" or c["order_status"] != "assigned":
                raise BadInput(f"đơn {oid} có món nhưng trạng thái không phải waiting/assigned")
            if dish["dish_id"] != c["dish_id"]:
                raise BadInput(f"món {dish['dish_id']} không khớp món khách {oid} gọi ({c['dish_id']})")
            if c["base_price"] is not None and c["base_price"] != dish["base_price"]:
                raise BadInput(f"đơn {oid}: base_price {c['base_price']} khác giá món đã chốt {dish['base_price']}")

        for c in self.customers:
            has_dish = c["id"] in dishes_by_order
            if c["order_status"] == "assigned" and not has_dish:
                raise BadInput(f"đơn assigned {c['id']} thiếu món ở bếp hoặc tay")
            if c["order_status"] != "assigned" and has_dish:
                raise BadInput(f"đơn {c['order_status']} {c['id']} không được có món ở bếp/tay")

    def snapshot(self) -> dict:
        """Snapshot buổi tối theo PRD-0 mục D/E: stock giữ tồn vật lý (gồm phần khách giữ)."""
        occupied = {c["table_id"]: c["id"] for c in self.customers}
        return {
            "player": {"pos": list(self.pos), "vel": list(self.vel)},
            "stock": {k: self.stock[k] for k in sorted(self.stock) if self.stock[k] > 0},
            "hand": dict(self.hand) if self.hand is not None else None,
            "stoves": [
                {
                    "id": s["id"],
                    "pos": list(s["pos"]),
                    "state": s["state"],
                    "dish": dict(s["dish"]) if s["dish"] is not None else None,
                    "cook_ticks_left": s["cook_ticks_left"],
                    "ready_ticks": s["ready_ticks"],
                }
                for s in sort_by_id(self.stoves)
            ],
            "tables": [
                {"id": tb["id"], "pos": list(tb["pos"]), "customer_id": occupied.get(tb["id"])}
                for tb in sort_by_id(self.tables)
            ],
            "customers": [
                {
                    "id": c["id"],
                    "table_id": c["table_id"],
                    "dish_id": c["dish_id"],
                    "order_tick": c["order_tick"],
                    "state": c["state"],
                    "patience_ticks_left": c["patience_ticks_left"],
                    "eat_ticks_left": c["eat_ticks_left"],
                    "order_status": c["order_status"],
                    "reserved": {k: c["reserved"][k] for k in sorted(c["reserved"])},
                    "base_price": c["base_price"],
                    "tip": c["tip"],
                }
                for c in sort_by_id(self.customers)
            ],
        }

    # --- một bước theo PRD-0 mục F (Quán bước 1–5) -----------------------------
    def step(self, inp):
        events = []
        # 1. Tăng đồng hồ, giảm timer ca, nấu, ăn và kiên nhẫn; chỉ tăng ready_ticks cho món ready đầu bước
        self._step_timers()
        # 2. Xét bếp theo id: món nấu xong chuyển ready với ready_ticks = 0
        self._step_stoves_ready(events)
        # 3. Di chuyển rồi xét tối đa một interact theo (khoảng cách, bếp trước bàn, id)
        self._move(inp)
        if inp.pressed("interact"):
            self._step_interact(events)
        # 4. Khách ăn xong trả tiền; còn giờ -> khách rời / khách mới; hết giờ -> đóng ca + quan_end
        self._step_eating_paid(events)
        if self.time_left_ticks > 0:
            self._step_patience_leave(events)
            self._step_spawn_customers(events)
        else:
            self._step_closing(events)
        return events

    def _step_timers(self):
        self.phase_tick += 1
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        for s in self.stoves:
            if s["state"] == "ready":
                s["ready_ticks"] += 1
            elif s["state"] == "cooking":
                s["cook_ticks_left"] = max(0, s["cook_ticks_left"] - 1)
        for c in self.customers:
            if c["state"] == "eating":
                c["eat_ticks_left"] = max(0, c["eat_ticks_left"] - 1)
            else:
                c["patience_ticks_left"] = max(0, c["patience_ticks_left"] - 1)

    def _step_stoves_ready(self, events):
        for s in sort_by_id(self.stoves):
            if s["state"] == "cooking" and s["cook_ticks_left"] == 0:
                s["state"] = "ready"
                s["ready_ticks"] = 0
                events.append(("dish_ready", {
                    "stove_id": s["id"],
                    "order_id": s["dish"]["order_id"],
                    "dish_id": s["dish"]["dish_id"],
                }))

    def _step_interact(self, events):
        radius = self.t["interact_radius"]
        candidates = []
        for s in self.stoves:
            d = math.dist(self.pos, s["pos"])
            if d <= radius:
                candidates.append((d, 0, id_key(s["id"]), "stove", s))
        for tb in self.tables:
            d = math.dist(self.pos, tb["pos"])
            if d <= radius:
                candidates.append((d, 1, id_key(tb["id"]), "table", tb))
        if not candidates:
            return
        _, _, _, kind, target = min(candidates, key=lambda item: (item[0], item[1], item[2]))
        if kind == "stove":
            self._interact_stove(target, events)
        else:
            self._interact_table(target, events)

    def _interact_stove(self, stove, events):
        if stove["state"] == "idle":
            waiting = [c for c in self.customers if c["state"] == "waiting" and c["order_status"] == "reserved"]
            if not waiting:
                return
            c = min(waiting, key=lambda x: (x["order_tick"], id_key(x["table_id"])))
            items = []
            for k in sorted(c["reserved"]):
                qty = c["reserved"][k]
                self.stock[k] -= qty
                if self.stock[k] <= 0:
                    del self.stock[k]
                items.extend([k] * qty)
            c["reserved"] = {}
            c["order_status"] = "assigned"
            dish_cfg = self.menu[c["dish_id"]]
            base_price = dish_cfg["price"]
            stove["state"] = "cooking"
            stove["dish"] = {"order_id": c["id"], "dish_id": c["dish_id"], "base_price": base_price}
            stove["cook_ticks_left"] = int(round(dish_cfg["cook_s"] * TICK))
            stove["ready_ticks"] = 0
            events.append(("cook_started", {
                "stove_id": stove["id"],
                "order_id": c["id"],
                "dish_id": c["dish_id"],
                "items": items,
                "base_price": base_price,
            }))
        elif stove["state"] == "ready":
            if self.hand is not None:
                return
            dish = dict(stove["dish"])
            self.hand = dish
            stove["state"] = "idle"
            stove["dish"] = None
            stove["cook_ticks_left"] = 0
            stove["ready_ticks"] = 0
            events.append(("dish_picked", {
                "stove_id": stove["id"],
                "order_id": dish["order_id"],
                "dish_id": dish["dish_id"],
            }))

    def _interact_table(self, table, events):
        if self.hand is None:
            return
        c = next((x for x in self.customers if x["table_id"] == table["id"]), None)
        if c is None or c["state"] != "waiting":
            return
        if self.hand["order_id"] != c["id"] or self.hand["dish_id"] != c["dish_id"]:
            return
        base_price = self.hand["base_price"]
        self.hand = None
        patience_max = int(round(self.t["patience_s"] * TICK))
        if Decimal(c["patience_ticks_left"]) >= Decimal(patience_max) * Decimal(str(self.t["tip_min_patience_ratio"])):
            tip = math.floor(Decimal(base_price) * Decimal(str(self.t["tip_rate"])))
        else:
            tip = 0
        c["state"] = "eating"
        c["order_status"] = "served"
        c["eat_ticks_left"] = int(round(self.t["eat_s"] * TICK))
        c["base_price"] = base_price
        c["tip"] = tip
        events.append(("served", {
            "order_id": c["id"],
            "table_id": c["table_id"],
            "dish_id": c["dish_id"],
            "patience_ticks_left": c["patience_ticks_left"],
            "base_price": base_price,
            "tip": tip,
        }))

    def _step_eating_paid(self, events):
        for c in sort_by_id(list(self.customers), key=lambda x: x["table_id"]):
            if c["state"] == "eating" and c["eat_ticks_left"] == 0:
                self._collect_payment(c, "finished_eating", events)

    def _step_closing(self, events):
        for c in sort_by_id(list(self.customers), key=lambda x: x["table_id"]):
            if c["state"] == "eating":
                self._collect_payment(c, "closing", events)
            else:
                self._cleanup_customer_order(c)
                events.append(("customer_left", {
                    "order_id": c["id"],
                    "table_id": c["table_id"],
                    "reason": "closing",
                    "reputation": self.reputation,
                }))
                self.customers.remove(c)
        self.done = True
        self.reason = "time"
        events.append(("quan_end", {
            "reason": "time",
            "money": self.money,
            "earned": self.earned,
            "shift_earned": self.shift_earned,
            "reputation": self.reputation,
        }))

    def _collect_payment(self, c, reason, events):
        base_price = c["base_price"]
        tip = c["tip"]
        amount = base_price + tip
        self.money += amount
        self.earned += amount
        self.shift_earned += amount
        if tip > 0:
            self._add_reputation(self.t["tip_reputation"])
        events.append(("paid", {
            "order_id": c["id"],
            "table_id": c["table_id"],
            "base_price": base_price,
            "tip": tip,
            "amount": amount,
            "reason": reason,
        }))
        self.customers.remove(c)

    def _cleanup_customer_order(self, c):
        """Nhả phần giữ thô; bỏ món của đơn đang nấu, ready hoặc trên tay (nguyên liệu đã dùng không hoàn lại)."""
        c["reserved"] = {}
        for s in self.stoves:
            if s["dish"] is not None and s["dish"]["order_id"] == c["id"]:
                s["state"] = "idle"
                s["dish"] = None
                s["cook_ticks_left"] = 0
                s["ready_ticks"] = 0
        if self.hand is not None and self.hand["order_id"] == c["id"]:
            self.hand = None

    def _add_reputation(self, delta):
        lo = Decimal(str(self.t["reputation_min"]))
        hi = Decimal(str(self.t["reputation_max"]))
        self._rep_dec = max(lo, min(hi, self._rep_dec + Decimal(str(delta))))
        self.reputation = float(self._rep_dec)

    # --- Lát 3 (Huy): khách đến theo lịch, giữ chỗ, hết kiên nhẫn -------------
    def _reserved_total(self) -> dict:
        total = {}
        for c in self.customers:
            for item, amount in c.get("reserved", {}).items():
                total[item] = total.get(item, 0) + amount
        return total

    def _available_stock(self) -> dict:
        reserved = self._reserved_total()
        available = {}
        for item in set(self.stock) | set(reserved):
            avail = int(self.stock.get(item, 0)) - int(reserved.get(item, 0))
            if avail > 0:
                available[item] = avail
        return available

    def _cookable_dishes(self) -> list:
        available = self._available_stock()
        cookable = []
        for dish_id in sorted(self.menu):
            if self.plan_dishes is not None and dish_id not in self.plan_dishes:
                continue
            recipe = self.menu[dish_id].get("recipe", {})
            if all(int(available.get(item, 0)) >= int(amount) for item, amount in recipe.items()):
                cookable.append(dish_id)
        return cookable

    def _choose_dish(self):
        cookable = self._cookable_dishes()
        if not cookable:
            return None
        if len(cookable) == 1:
            return cookable[0]
        return self.rng.get("quan_customer_dish").choice(cookable)

    def _step_patience_leave(self, events):
        for c in sort_by_id(list(self.customers), key=lambda x: x["table_id"]):
            if c["state"] == "waiting" and c["patience_ticks_left"] <= 0:
                self._cleanup_customer_order(c)
                self._add_reputation(self.t["left_reputation_delta"])
                events.append(("customer_left", {
                    "order_id": c["id"],
                    "table_id": c["table_id"],
                    "reason": "patience",
                    "reputation": self.reputation,
                }))
                self.customers.remove(c)

    def _step_spawn_customers(self, events):
        if not self.random_customers:
            return
        first_tick = int(self.t["first_customer_tick"])
        interval_ticks = int(round(float(self.t["customer_interval_s"]) * TICK))
        if self.phase_tick < first_tick:
            return
        if interval_ticks > 0 and (self.phase_tick - first_tick) % interval_ticks != 0:
            return

        occupied = {c["table_id"] for c in self.customers}
        free_tables = [tb for tb in sort_by_id(self.tables) if tb["id"] not in occupied]
        if not free_tables:
            return
        table_id = free_tables[0]["id"]

        dish_id = self._choose_dish()
        if dish_id is None:
            events.append(("no_dish", {}))
            return

        cid = self.ids.new("C")
        recipe = {k: int(v) for k, v in self.menu[dish_id]["recipe"].items() if v > 0}
        patience_max = int(round(float(self.t["patience_s"]) * TICK))
        customer = {
            "id": cid,
            "table_id": table_id,
            "dish_id": dish_id,
            "order_tick": self.phase_tick,
            "state": "waiting",
            "patience_ticks_left": patience_max,
            "eat_ticks_left": 0,
            "order_status": "reserved",
            "reserved": recipe,
            "base_price": None,
            "tip": None,
        }
        self.customers.append(customer)
        events.append(("customer_arrived", {
            "order_id": cid,
            "table_id": table_id,
            "dish_id": dish_id,
        }))

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
