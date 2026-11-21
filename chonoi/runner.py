"""Vòng tick (Contract B, mô hình tick + điều phối `--mode day` + `pause`).

Thứ tự ghi: (sự kiện tick 0 nếu là `day`) -> snapshot tick 0 -> với mỗi bước: sự kiện (theo thứ tự xử lý)
rồi snapshot (nếu tới lượt hoặc buổi kết thúc) -> dòng 'end'. Mỗi tick tối đa một snapshot.

`Session` là API bước tick gọn dùng chung cho headless (`run`) và cửa sổ chơi trực tiếp (`chonoi.live`):
cả hai chạy CÙNG một lớp sim, không nhân đôi logic.
"""

import copy
from decimal import Decimal
import inspect
import math

from .errors import BadInput
from .ids import IdAllocator
from .inputs import InputPlayer
from .inventory import write_inventory
from .jsonl import JsonlWriter
from .rng import Streams
from .sim.gather import GatherSim
from .sim.quan import QuanSim
from .sim.shop import ShopSim


def _default_factories():
    return {"gather": GatherSim, "quan": QuanSim, "shop": ShopSim}


def _build_plans(tuning, day_sc):
    plans = {}
    for entry in tuning.get("day_plan", []):
        plans[entry["day"]] = {
            "dishes": dict(entry["dishes"]),
            "ingredients": dict(entry["ingredients"]),
        }
    for entry in day_sc.get("day_plan", []):
        dishes = dict(entry["dishes"])
        ing = {}
        for dish_id, cnt in dishes.items():
            for k, qty in tuning["menu"][dish_id]["recipe"].items():
                ing[k] = ing.get(k, 0) + qty * cnt
        plans[entry["day"]] = {"dishes": dishes, "ingredients": ing}
    return plans


def _build_gather(cls, tuning, g_sc, streams, ids, *, day=None, active_upgrades=None):
    params = inspect.signature(cls.__init__).parameters
    kwargs = {}
    if "day" in params and day is not None:
        kwargs["day"] = day
    if "active_upgrades" in params and active_upgrades is not None:
        kwargs["active_upgrades"] = dict(active_upgrades)
    return cls(tuning, g_sc, streams, ids, **kwargs)


def _build_quan(cls, tuning, q_sc, streams, ids, inventory, *, plan_dishes=None, carry=None):
    if plan_dishes is not None:
        allowed = set(plan_dishes)
        for c in q_sc.get("customers", []):
            if c.get("dish_id") is not None and c["dish_id"] not in allowed:
                raise BadInput(f"customers.{c['id']}: món {c['dish_id']} không nằm trong kế hoạch Ngày")
    params = inspect.signature(cls.__init__).parameters
    kwargs = {"inventory": inventory}
    if "plan_dishes" in params and plan_dishes is not None:
        kwargs["plan_dishes"] = list(plan_dishes)
    if "carry" in params and carry is not None:
        kwargs["carry"] = dict(carry)
    sim = cls(tuning, q_sc, streams, ids, **kwargs)
    if carry is not None and "carry" not in params:
        sim.money = carry.get("money", 0)
        sim.earned = carry.get("earned", 0)
        rep = carry.get("reputation", tuning["quan"]["reputation_initial"])
        if hasattr(sim, "_rep_dec"):
            sim._rep_dec = Decimal(str(rep))
        sim.reputation = float(rep)
    return sim


class Session:
    """Một lượt chơi (hỗ trợ `gather`, `quan`, `shop` (nội bộ/test), `day` và `pause`): bước từng tick, lấy snapshot / dòng end."""

    def __init__(self, mode, tuning, scenario, seed, inventory=None, *, days=1, sim_factories=None):
        self.mode = mode
        self.tuning = tuning
        self.scenario = scenario or {}
        self.streams = Streams(seed)
        self.ids = IdAllocator()
        self.factories = dict(_default_factories())
        if sim_factories:
            self.factories.update(sim_factories)

        self.tick = 0
        self.sim_tick = 0
        self.phase_tick = 0
        self.paused = False
        self.done = False
        self.reason = None

        if mode == "day":
            self.days_total = days
            self.day = 1
            self.days_completed = 0
            day_sc = self.scenario.get("day", {})
            self.money = int(day_sc.get("money", 0))
            self.earned = int(day_sc.get("earned", 0))
            self.reputation = float(day_sc.get("reputation", tuning["quan"]["reputation_initial"]))
            self.upgrades = {k: int(v) for k, v in day_sc.get("upgrades", {}).items() if v > 0}
            self.active_upgrades = dict(self.upgrades)
            self.plans = _build_plans(tuning, day_sc)
            self.sim = self._make_gather(first_day=True)
        else:
            self.days_total = 1
            self.day = None
            self.days_completed = 0
            if mode == "gather":
                self.sim = _build_gather(self.factories["gather"], tuning, self.scenario, self.streams, self.ids)
            elif mode == "shop":
                carry = self.scenario.get("carry", {"money": 0, "earned": 0,
                                                    "reputation": tuning["quan"]["reputation_initial"]})
                self.sim = self.factories["shop"](tuning, stock=dict(self.scenario.get("stock", {})),
                                                  carry=dict(carry), upgrades=dict(self.scenario.get("upgrades", {})))
            else:
                self.sim = _build_quan(self.factories["quan"], tuning, self.scenario, self.streams, self.ids, inventory)

    def _gather_scenario_for_day(self, first_day: bool) -> dict:
        g_sc = copy.deepcopy(self.scenario.get("gather", {}))
        if not first_day:
            g_sc.pop("hold", None)
            if isinstance(g_sc.get("player"), dict):
                for k in ("oxygen_ticks", "hp", "zero_oxy_ticks"):
                    g_sc["player"].pop(k, None)
        return g_sc

    def _make_gather(self, first_day: bool):
        g_sc = self._gather_scenario_for_day(first_day)
        return _build_gather(self.factories["gather"], self.tuning, g_sc, self.streams, self.ids,
                             day=self.day, active_upgrades=self.active_upgrades)

    def _wrap_event(self, phase: str, name: str, data: dict, *, tick: int = None, day: int = None) -> dict:
        row = {
            "type": "event",
            "tick": self.tick if tick is None else tick,
            "phase": phase,
            "name": name,
            "data": data,
        }
        if self.mode == "day":
            row["day"] = self.day if day is None else day
        return row

    def init_events(self) -> list:
        """Sự kiện đầu ngày tại tick 0 cho `--mode day`."""
        if self.mode != "day":
            return []
        plan = self.plans[self.day]
        return [
            self._wrap_event("gather", "day_start", {}, tick=0, day=self.day),
            self._wrap_event("gather", "day_plan", {
                "dishes": dict(plan["dishes"]),
                "ingredients": dict(plan["ingredients"]),
            }, tick=0, day=self.day),
            self._wrap_event("gather", "phase_start", {}, tick=0, day=self.day),
        ]

    def _totals(self):
        if self.mode == "day":
            return self.money, self.earned, self.reputation
        return self.sim.money, self.sim.earned, self.sim.reputation

    def _state_str(self) -> str:
        if self.paused:
            return "paused"
        return "finished" if self.done else "playing"

    def snapshot(self) -> dict:
        money, earned, rep = self._totals()
        mult = self.tuning["score"]["reputation_multiplier"]
        s = {
            "type": "snapshot",
            "tick": self.tick,
            "sim_tick": self.sim_tick,
            "mode": self.mode,
            "phase": self.sim.phase,
            "phase_tick": self.phase_tick,
            "state": self._state_str(),
            "time_left_ticks": self.sim.time_left_ticks,
            "money": money,
            "earned": earned,
            "reputation": rep,
            "score": earned + mult * math.floor(rep),
        }
        if self.mode == "day":
            plan = self.plans[self.day]
            s.update({
                "day": self.day,
                "day_plan": {"dishes": dict(plan["dishes"]), "ingredients": dict(plan["ingredients"])},
                "upgrades": dict(self.upgrades),
                "active_upgrades": dict(self.active_upgrades),
            })
        s.update(self.sim.snapshot())
        return s

    def step(self, inp) -> list:
        """Chạy một bước với `inp` (chonoi.inputs.InputState); trả các dòng event."""
        if self.done:
            return []
        pre_events = []
        if inp.pressed("pause"):
            if not self.paused:
                self.paused = True
                self.tick += 1
                return [self._wrap_event(self.sim.phase, "paused", {})]
            self.paused = False
            pre_events.append(self._wrap_event(self.sim.phase, "resumed", {}, tick=self.tick + 1))
        elif self.paused:
            self.tick += 1
            return []

        old_phase = self.sim.phase
        old_day = self.day
        self.tick += 1
        self.sim_tick += 1
        self.phase_tick += 1

        raw_events = self.sim.step(inp)
        rows = pre_events + [
            self._wrap_event(old_phase, name, data, day=old_day) for name, data in raw_events
        ]

        if self.mode != "day":
            if self.sim.done:
                self.done = True
                self.reason = self.sim.reason
            return rows

        if old_phase in ("quan", "shop"):
            self.money = self.sim.money
            self.earned = self.sim.earned
            self.reputation = self.sim.reputation
            if old_phase == "shop":
                self.upgrades = dict(self.sim.upgrades)

        if self.sim.done:
            self.phase_tick = 0
            if old_phase == "gather":
                inv = self.sim.inventory_items()
                q_sc = copy.deepcopy(self.scenario.get("quan", {}))
                plan = self.plans[self.day]
                carry = {"money": self.money, "earned": self.earned, "reputation": self.reputation}
                self.sim = _build_quan(self.factories["quan"], self.tuning, q_sc, self.streams, self.ids,
                                       inv, plan_dishes=list(plan["dishes"]), carry=carry)
                rows.append(self._wrap_event("quan", "phase_start", {}))
            elif old_phase == "quan":
                leftover = {k: v for k, v in self.sim.stock.items() if v > 0}
                carry = {"money": self.money, "earned": self.earned, "reputation": self.reputation}
                self.sim = self.factories["shop"](self.tuning, stock=leftover, carry=carry, upgrades=dict(self.upgrades))
                rows.append(self._wrap_event("shop", "phase_start", {}))
            elif old_phase == "shop":
                self.days_completed += 1
                if self.days_completed >= self.days_total:
                    self.done = True
                    self.reason = "days_complete"
                else:
                    self.day += 1
                    self.active_upgrades = dict(self.upgrades)
                    self.sim = self._make_gather(first_day=False)
                    plan = self.plans[self.day]
                    rows.append(self._wrap_event("gather", "day_start", {}))
                    rows.append(self._wrap_event("gather", "day_plan", {
                        "dishes": dict(plan["dishes"]),
                        "ingredients": dict(plan["ingredients"]),
                    }))
                    rows.append(self._wrap_event("gather", "phase_start", {}))
        return rows

    def end_row(self) -> dict:
        money, earned, rep = self._totals()
        mult = self.tuning["score"]["reputation_multiplier"]
        row = {
            "type": "end",
            "ticks": self.tick,
            "sim_tick": self.sim_tick,
            "mode": self.mode,
            "state": self._state_str(),
            "reason": self.reason if self.done else "tick_limit",
            "money": money,
            "earned": earned,
            "reputation": rep,
            "score": earned + mult * math.floor(rep),
        }
        if self.mode == "day":
            row["days_completed"] = self.days_completed
        return row

    def write_inventory_if_done(self, inventory_out):
        """File kho: ghi MỘT lần khi có gather_end; chưa kết thúc thì giữ nguyên file đích."""
        if self.mode == "gather" and self.done and inventory_out:
            write_inventory(inventory_out, self.sim.inventory_items())


def run(mode, tuning, scenario, seed, frames, ticks, out_path, snapshot_every,
        inventory=None, inventory_out=None, *, days=1, sim_factories=None):
    sess = Session(mode, tuning, scenario, seed, inventory, days=days, sim_factories=sim_factories)
    player = InputPlayer(frames)
    w = JsonlWriter(out_path)
    try:
        for row in sess.init_events():
            w.write(row)
        w.write(sess.snapshot())  # tick 0: sau khi dựng scenario, trước mọi input
        last_snapped = 0
        while sess.tick < ticks and not sess.done:
            phase_before = sess.sim.phase
            inp = player.advance(sess.tick)  # bước k đọc input có tick == k
            for row in sess.step(inp):
                w.write(row)
            # PRD: snapshot đổi pha ghi pha mới với phase_tick:0; tối đa 1 snapshot/tick
            if sess.tick % snapshot_every == 0 or sess.done or sess.sim.phase != phase_before:
                w.write(sess.snapshot())
                last_snapped = sess.tick
        if last_snapped != sess.tick:
            w.write(sess.snapshot())
        w.write(sess.end_row())
    finally:
        w.close()
    sess.write_inventory_if_done(inventory_out)
    return sess.sim
