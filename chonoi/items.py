"""Cá thể nguyên liệu v1.2 (TICKET-03 mục 1): {id, kind, fresh}. Dùng chung cho gather, quán, Shop, day.

Biểu diễn trong sim: dict {"id": str, "kind": str, "fresh": Fraction}. Fraction cho phép so ngưỡng 30 và floor giá
CHÍNH XÁC (không sai số thực). Chỉ đổi sang float khi xuất (snapshot/event/file kho) bằng `dump`/`dump_one`.

    from chonoi import items as it
    hold = it.load(scenario.get("hold", []))           # fixture -> nội bộ
    it.new(ids, "ca_linh")                              # cá thể mới, fresh 100, id I<n> kế tiếp
    spoiled = it.decay(hold, it.per_tick(t, "gather"))  # hao 1 tick; trả cá thể vừa ươn (theo id)
    it.usable(x, t) / it.is_spoiled(x, t)               # ươn khi fresh < spoiled_below
    it.pick_freshest(pool, "ca_linh", 3, t)             # tươi nhất, hòa theo id, bỏ hàng ươn
    snapshot["hold"] = it.dump(hold)                    # nội bộ -> JSON (thứ tự giữ nguyên)
"""

from fractions import Fraction

from .ids import id_key

TICK_HZ = 60
DEFAULT_FRESHNESS = {"initial": 100, "gather_decay_per_s": 0.5, "quan_decay_per_s": 0.25, "spoiled_below": 30}


def frac(v) -> Fraction:
    """Số JSON -> Fraction đúng giá trị thập phân đã ghi (97.5 -> 195/2, 0.1 -> 1/10)."""
    if isinstance(v, Fraction):
        return v
    if isinstance(v, int):
        return Fraction(v)
    return Fraction(repr(float(v)))


def cfg(tuning) -> dict:
    return tuning.get("freshness", DEFAULT_FRESHNESS)


def per_tick(tuning, where: str) -> Fraction:
    """Lượng hao mỗi tick: where = "gather" (0.5/s -> 1/120) hoặc "quan" (0.25/s -> 1/240)."""
    return frac(cfg(tuning)[f"{where}_decay_per_s"]) / TICK_HZ


def threshold(tuning) -> Fraction:
    return frac(cfg(tuning)["spoiled_below"])


def is_spoiled(item, tuning) -> bool:
    return item["fresh"] < threshold(tuning)


def usable(item, tuning) -> bool:
    return not is_spoiled(item, tuning)


def make(item_id: str, kind: str, fresh) -> dict:
    return {"id": item_id, "kind": kind, "fresh": frac(fresh)}


def new(ids, kind: str, tuning=None) -> dict:
    """Cá thể mới lúc bắt/hái: id I<n> kế tiếp (xuyên pha/Ngày vì IdAllocator dùng chung), fresh = initial."""
    initial = cfg(tuning or {})["initial"]
    return make(ids.new("I"), kind, initial)


def load(raw_list) -> list:
    """Mảng cá thể đã kiểm schema (scenario/file kho) -> nội bộ. Giữ nguyên thứ tự."""
    return [make(x["id"], x["kind"], x["fresh"]) for x in raw_list]


def dump_one(item) -> dict:
    return {"id": item["id"], "kind": item["kind"], "fresh": float(item["fresh"])}


def dump(items) -> list:
    return [dump_one(x) for x in items]


def by_id(items) -> list:
    return sorted(items, key=lambda x: id_key(x["id"]))


def decay(items, amount: Fraction, tuning) -> list:
    """Trừ `amount` (kẹp 0) cho mọi cá thể. Trả các cá thể VỪA đi từ >= ngưỡng xuống < ngưỡng, sắp theo id."""
    th = threshold(tuning)
    crossed = []
    for x in items:
        before = x["fresh"]
        x["fresh"] = max(Fraction(0), before - amount)
        if before >= th > x["fresh"]:
            crossed.append(x)
    return by_id(crossed)


def pick_freshest(pool, kind: str, n: int, tuning, exclude=()) -> list:
    """n cá thể chưa ươn của `kind`, tươi nhất trước, hòa theo id; thiếu -> None."""
    ex = set(exclude)
    cands = [x for x in pool if x["kind"] == kind and x["id"] not in ex and usable(x, tuning)]
    cands.sort(key=lambda x: (-x["fresh"], id_key(x["id"])))
    return cands[:n] if len(cands) >= n else None


def counts(items, tuning=None, only_usable=False) -> dict:
    """Đếm theo loại (cho HUD/chọn món). only_usable=True bỏ hàng ươn."""
    out = {}
    for x in items:
        if only_usable and tuning is not None and is_spoiled(x, tuning):
            continue
        out[x["kind"]] = out.get(x["kind"], 0) + 1
    return {k: out[k] for k in sorted(out)}
