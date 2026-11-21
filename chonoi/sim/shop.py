"""Shop Phase 2: mua nâng cấp giữa hai Ngày.

Shop chỉ sửa ``money`` và ``upgrades`` đã mua. DaySim sẽ sao các cấp đó sang
``active_upgrades`` khi dựng Ngày kế tiếp, nên việc mua không đổi lượt lặn
đang diễn ra.
"""

from fractions import Fraction
import math

from .. import items as it
from ..errors import BadInput
from ..inventory import validate_item_list


def _nonneg_int(value) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value >= 0


def _finite_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


class ShopSim:
    """Mô phỏng Shop độc lập, theo giao diện Phase 2 §5."""

    mode = "shop"
    phase = "shop"

    def __init__(self, tuning, *, stock, carry, upgrades):
        self.t = tuning["shop"]
        raw_stock = [
            {**x, "fresh": float(x["fresh"])} if isinstance(x, dict) and isinstance(x.get("fresh"), Fraction) else x
            for x in stock
        ] if isinstance(stock, list) else stock
        validate_item_list(raw_stock, name="shop.stock")
        self.stock = [it.make(x["id"], x["kind"], x["fresh"]) for x in stock]
        self.upgrade_defs = self._validate_upgrade_defs(self.t.get("upgrades"))
        self.money, self.earned, self.reputation = self._validate_carry(carry, tuning["quan"])
        self.upgrades = self._validate_upgrades(upgrades)

        max_ticks = self.t.get("max_ticks")
        if not _nonneg_int(max_ticks) or max_ticks <= 0:
            raise BadInput("shop.max_ticks phải là số nguyên dương")
        self.time_left_ticks = max_ticks
        self.done = False
        self.reason = None

    @staticmethod
    def _validate_carry(carry, quan):
        if not isinstance(carry, dict) or set(carry) != {"money", "earned", "reputation"}:
            raise BadInput("carry phải có đúng money, earned, reputation")
        money, earned, reputation = carry["money"], carry["earned"], carry["reputation"]
        if not _nonneg_int(money) or not _nonneg_int(earned) or money > earned:
            raise BadInput("carry cần 0 <= money <= earned (số nguyên)")
        if not _finite_number(reputation) or not (quan["reputation_min"] <= reputation <= quan["reputation_max"]):
            raise BadInput("carry.reputation nằm ngoài miền hợp lệ")
        return money, earned, float(reputation)

    @staticmethod
    def _validate_upgrade_defs(raw):
        if not isinstance(raw, dict) or not raw:
            raise BadInput("shop.upgrades phải là object không rỗng")
        validated = {}
        for name, levels in raw.items():
            if not isinstance(name, str) or not name or not isinstance(levels, list) or not levels:
                raise BadInput("mỗi shop.upgrades.<id> phải là mảng cấp không rỗng")
            parsed = []
            for index, level in enumerate(levels, start=1):
                if not isinstance(level, dict):
                    raise BadInput(f"shop.upgrades.{name}[{index - 1}] phải là object")
                number, price = level.get("level"), level.get("price")
                if number != index or not _nonneg_int(price) or price <= 0:
                    raise BadInput(f"shop.upgrades.{name}[{index - 1}] có level/price không hợp lệ")
                parsed.append(dict(level))
            validated[name] = parsed
        return validated

    def _validate_upgrades(self, upgrades):
        if not isinstance(upgrades, dict):
            raise BadInput("upgrades phải là object")
        unknown = sorted(set(upgrades) - set(self.upgrade_defs))
        if unknown:
            raise BadInput(f"upgrades có id không hỗ trợ: {unknown}")
        result = {}
        for name, level in upgrades.items():
            if not _nonneg_int(level) or level > len(self.upgrade_defs[name]):
                raise BadInput(f"upgrades.{name} có cấp không hợp lệ")
            if level:
                result[name] = level
        return result

    def snapshot(self) -> dict:
        return {
            "stock": it.dump(self.stock),
            "upgrades": {name: self.upgrades[name] for name in sorted(self.upgrades)},
        }

    def step(self, inp):
        """Mua trước ``shop_done``; lần mua ở tick cuối vẫn được tính."""
        if self.done:
            return []
        events = []
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        if inp.buy is not None:
            self._buy(inp.buy, events)
        if inp.pressed("shop_done"):
            self._finish("done", events)
        elif self.time_left_ticks == 0:
            self._finish("time", events)
        return events

    def _buy(self, action, events):
        if action not in self.upgrade_defs:
            events.append(("buy_failed", {"action": action, "reason": "unknown"}))
            return
        current = self.upgrades.get(action, 0)
        levels = self.upgrade_defs[action]
        if current >= len(levels):
            events.append(("buy_failed", {"action": action, "reason": "max_level"}))
            return
        next_level = levels[current]
        price = next_level["price"]
        if self.money < price:
            events.append(("buy_failed", {"action": action, "reason": "funds"}))
            return
        self.money -= price
        self.upgrades[action] = next_level["level"]
        events.append(("bought", {
            "upgrade": action,
            "level": next_level["level"],
            "price": price,
            "money": self.money,
        }))

    def _finish(self, reason, events):
        self.done = True
        self.reason = reason
        events.append(("shop_end", {"reason": reason}))
