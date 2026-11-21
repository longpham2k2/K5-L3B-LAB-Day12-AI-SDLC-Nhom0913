"""Nạp và kiểm scenario (Contract D). Trả về dict của đúng khối theo mode.

KHUNG: kiểm cú pháp, id trùng, bộ đếm âm, khoang vượt sức chứa, trường lạ.
TODO(nhóm): bổ sung kiểm mâu thuẫn mức luật mà nhóm cần (khách giữ chỗ quá kho, đơn assigned
phải có đúng một món, khách eating thiếu giá/tip...) — xem PRD-0 mục D và 'Mâu thuẫn -> mã 2'.
"""

import json

from .errors import BadInput
from .inventory import KINDS_P1, validate_items

GATHER_KEYS = {"player", "hold", "nodes", "fish", "random_fish", "time_left_ticks", "monsters"}
MONSTER_KEYS = {"id", "kind", "pos", "waypoints", "target_idx", "state", "state_ticks_left", "recoil_dir"}
GATHER_PLAYER_KEYS = {"pos", "vel", "heading_deg", "hp", "oxygen_ticks", "zero_oxy_ticks",
                      "invuln_ticks", "catch_cd_ticks"}
NODE_KINDS = ("bong_dien_dien", "bong_sung", "keo_neo")
FISH_KINDS = ("ca_linh", "ca_loc", "ca_keo")
QUAN_PLAYER_KEYS = {"pos", "vel"}
QUAN_KEYS = {"player", "stock", "hand", "stoves", "tables", "customers", "random_customers",
             "reputation", "time_left_ticks"}


DAY_KEYS = {"money", "earned", "reputation", "upgrades", "day_plan"}
DAY_PLAN_KEYS = {"day", "dishes", "ingredients"}


def _check_ids(name, arr):
    if not isinstance(arr, list):
        raise BadInput(f"{name} phải là mảng")
    seen = set()
    for e in arr:
        if not isinstance(e, dict) or not isinstance(e.get("id"), str) or not e["id"]:
            raise BadInput(f"{name}: mỗi phần tử cần id (chuỗi khác rỗng)")
        if e["id"] in seen:
            raise BadInput(f"{name}: id trùng {e['id']}")
        seen.add(e["id"])


def load_scenario(path, mode: str, tuning: dict) -> dict:
    if path is None:
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise BadInput(f"không đọc được scenario {path}: {e}")
    if mode == "day":
        if not isinstance(data, dict) or not set(data) <= {"day", "gather", "quan"}:
            raise BadInput("scenario day chỉ được có khối 'day', 'gather' hoặc 'quan'")
        return _validate_day(data, tuning)
    if not isinstance(data, dict) or not set(data) <= {"gather", "quan"}:
        raise BadInput("scenario chỉ được có khối 'gather' hoặc 'quan'")
    if set(data) - {mode}:
        raise BadInput(f"khối sai mode: chạy --mode {mode} chỉ nhận khối '{mode}'")
    block = data.get(mode, {})
    if not isinstance(block, dict):
        raise BadInput(f"khối {mode} phải là object")
    _validate_mode_block(mode, block, tuning)
    return block


def _validate_mode_block(mode, block, tuning):
    allowed = GATHER_KEYS if mode == "gather" else QUAN_KEYS
    extra = set(block) - allowed
    if extra:
        raise BadInput(f"trường lạ/chưa hỗ trợ trong {mode}: {sorted(extra)}")
    dur = int(round(tuning[mode]["duration_s"] * 60))
    if "time_left_ticks" in block:
        t = block["time_left_ticks"]
        if isinstance(t, bool) or not isinstance(t, int) or not (1 <= t <= dur):
            raise BadInput(f"time_left_ticks phải là số nguyên trong [1, {dur}]")
    if mode == "gather":
        _validate_gather(block, tuning)
    else:
        _validate_quan(block, tuning)


def _validate_day(data, tuning):
    d = data.get("day", {})
    g = data.get("gather", {})
    q = data.get("quan", {})
    if not isinstance(d, dict) or not isinstance(g, dict) or not isinstance(q, dict):
        raise BadInput("các khối day/gather/quan phải là object")
    extra = set(d) - DAY_KEYS
    if extra:
        raise BadInput(f"trường lạ trong day: {sorted(extra)}")
    if "stock" in q or "reputation" in q:
        raise BadInput("cấm quan.stock và quan.reputation khi chạy day")
    if "money" in d or "earned" in d:
        if "money" not in d or "earned" not in d:
            raise BadInput("day phải khai cả money và earned khi có tiền đầu kỳ")
        _nonneg_int("day.money", d["money"])
        _nonneg_int("day.earned", d["earned"])
        if d["money"] > d["earned"]:
            raise BadInput("day.money không được vượt day.earned")
    if "reputation" in d:
        rep = d["reputation"]
        rmin, rmax = tuning["quan"]["reputation_min"], tuning["quan"]["reputation_max"]
        if not _num(rep) or not (rmin <= rep <= rmax):
            raise BadInput(f"day.reputation phải trong [{rmin}, {rmax}]")
    upgrades = d.get("upgrades", {})
    if not isinstance(upgrades, dict):
        raise BadInput("day.upgrades phải là object")
    shop_ups = tuning["shop"]["upgrades"]
    for k, lvl in upgrades.items():
        if k not in shop_ups:
            raise BadInput(f"day.upgrades có nâng cấp không hỗ trợ: {k}")
        if isinstance(lvl, bool) or not isinstance(lvl, int) or not (0 <= lvl <= len(shop_ups[k])):
            raise BadInput(f"day.upgrades.{k} phải là số nguyên trong [0, {len(shop_ups[k])}]")
    if "day_plan" in d:
        dp = d["day_plan"]
        if not isinstance(dp, list):
            raise BadInput("day.day_plan phải là mảng")
        seen_days = set()
        for entry in dp:
            if not isinstance(entry, dict) or set(entry) - DAY_PLAN_KEYS:
                raise BadInput("mục trong day.day_plan sai khóa")
            day_no = entry.get("day")
            if isinstance(day_no, bool) or not isinstance(day_no, int) or not (1 <= day_no <= 5) or day_no in seen_days:
                raise BadInput("day.day_plan[].day phải là số nguyên 1..5 và không trùng")
            seen_days.add(day_no)
            dishes = entry.get("dishes")
            if not isinstance(dishes, dict) or not dishes:
                raise BadInput(f"day_plan ngày {day_no}: dishes phải là object không rỗng")
            expected = {}
            for dish_id, cnt in dishes.items():
                if dish_id not in tuning["menu"]:
                    raise BadInput(f"day_plan ngày {day_no}: món lạ {dish_id}")
                if isinstance(cnt, bool) or not isinstance(cnt, int) or cnt <= 0:
                    raise BadInput(f"day_plan ngày {day_no}: số suất {dish_id} phải là số nguyên dương")
                for ing, qty in tuning["menu"][dish_id]["recipe"].items():
                    expected[ing] = expected.get(ing, 0) + qty * cnt
            if "ingredients" in entry:
                ing_map = validate_items(entry["ingredients"])
                if ing_map != expected:
                    raise BadInput(f"day_plan ngày {day_no}: ingredients không khớp tổng công thức")
    # Kiểm gather theo cấp hiệu lực từ day.upgrades
    eff = dict(tuning)
    eff_g = dict(tuning["gather"])
    if upgrades.get("oxygen", 0) > 0:
        eff_g["oxygen_max_s"] = shop_ups["oxygen"][upgrades["oxygen"] - 1]["oxygen_max_s"]
    if upgrades.get("hp", 0) > 0:
        eff_g["hp_max"] = shop_ups["hp"][upgrades["hp"] - 1]["hp_max"]
    eff["gather"] = eff_g
    _validate_mode_block("gather", g, eff)
    _validate_mode_block("quan", q, eff)
    return {"day": d, "gather": g, "quan": q}


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _nonneg_int(name, v):
    if isinstance(v, bool) or not isinstance(v, int) or v < 0:
        raise BadInput(f"{name} phải là số nguyên không âm")


def _pos(name, pos, bounds, axes=("x", "d")):
    if not (isinstance(pos, list) and len(pos) == 2 and all(_num(c) for c in pos)):
        raise BadInput(f"{name} phải là [{axes[0]}, {axes[1]}]")
    for c, axis in zip(pos, axes):
        lo, hi = bounds[axis]
        if not (lo <= c <= hi):
            raise BadInput(f"{name} nằm ngoài vùng nước ({axis} ∈ [{lo}, {hi}])")


def _validate_gather(b, tuning):
    g = tuning["gather"]
    bounds = g["bounds"]
    for arr in ("nodes", "fish"):
        if arr in b:
            _check_ids(arr, b[arr])
    if "random_fish" in b and not isinstance(b["random_fish"], bool):
        raise BadInput("random_fish phải là boolean")
    if "hold" in b:
        h = b["hold"]
        if not isinstance(h, list) or any(k not in KINDS_P1 for k in h):
            raise BadInput("hold phải là mảng id nguyên liệu hợp lệ")
        if len(h) > g["hold_capacity"]:
            raise BadInput("hold vượt sức chứa")
    p = b.get("player", {})
    if not isinstance(p, dict):
        raise BadInput("player phải là object")
    extra = set(p) - GATHER_PLAYER_KEYS
    if extra:
        raise BadInput(f"trường lạ/chưa hỗ trợ trong gather.player: {sorted(extra)}")
    if "pos" in p:
        _pos("player.pos", p["pos"], bounds)
    if "vel" in p and not (isinstance(p["vel"], list) and len(p["vel"]) == 2 and all(_num(c) for c in p["vel"])):
        raise BadInput("player.vel phải là [x, d]")
    if "heading_deg" in p and not _num(p["heading_deg"]):
        raise BadInput("player.heading_deg phải là số")
    for key in ("invuln_ticks", "catch_cd_ticks", "zero_oxy_ticks", "oxygen_ticks", "hp"):
        if key in p:
            _nonneg_int(f"player.{key}", p[key])
    omax = int(round(g["oxygen_max_s"] * 60))
    if "oxygen_ticks" in p and p["oxygen_ticks"] > omax:
        raise BadInput("player.oxygen_ticks vượt oxy tối đa")
    if "hp" in p and not (1 <= p["hp"] <= g["hp_max"]):
        raise BadInput("player.hp phải trong [1, hp_max]")
    if "zero_oxy_ticks" in p:
        pos = p.get("pos", g["start_pos"])
        oxy = p.get("oxygen_ticks", omax)
        if p["zero_oxy_ticks"] > 59:
            raise BadInput("player.zero_oxy_ticks phải trong [0, 59]")
        if p["zero_oxy_ticks"] > 0 and not (oxy == 0 and pos[1] > g["surface_depth"]):
            raise BadInput("player.zero_oxy_ticks > 0 chỉ khi oxy = 0 và đang dưới nước")
    for n in b.get("nodes", []):
        if n.get("kind") not in NODE_KINDS:
            raise BadInput(f"nodes.{n['id']}: kind phải là một trong {NODE_KINDS}")
        _pos(f"nodes.{n['id']}.pos", n.get("pos"), bounds)
        if n["pos"][1] != 0:
            raise BadInput(f"nodes.{n['id']}: nút hái nằm ở mặt nước (d = 0)")
        if "regrow_ticks" in n:
            _nonneg_int(f"nodes.{n['id']}.regrow_ticks", n["regrow_ticks"])
    for f in b.get("fish", []):
        if f.get("kind") not in FISH_KINDS:
            raise BadInput(f"fish.{f['id']}: kind phải là một trong {FISH_KINDS}")
        _pos(f"fish.{f['id']}.pos", f.get("pos"), bounds)
        if f["pos"][1] <= g["surface_depth"]:
            raise BadInput(f"fish.{f['id']}: đàn cá phải ở dưới nước")
        if "heading_deg" in f and not _num(f["heading_deg"]):
            raise BadInput(f"fish.{f['id']}.heading_deg phải là số")
        if "age_ticks" in f:
            _nonneg_int(f"fish.{f['id']}.age_ticks", f["age_ticks"])
    if "monsters" in b:
        _validate_monsters(b["monsters"], g)


def _validate_monsters(arr, g):
    """TICKET-02 mục 4.3: gather.monsters[] thay danh sách mặc định."""
    _check_ids("monsters", arr)
    species = g["monsters"]["species"]
    bounds = g["bounds"]
    for m in arr:
        mid = m["id"]
        extra = set(m) - MONSTER_KEYS
        if extra:
            raise BadInput(f"monsters.{mid}: trường lạ {sorted(extra)}")
        if m.get("kind") not in species:
            raise BadInput(f"monsters.{mid}: kind phải thuộc {sorted(species)}")
        lo, hi = species[m["kind"]]["depths"]
        _pos(f"monsters.{mid}.pos", m.get("pos"), bounds)
        if not (lo <= m["pos"][1] <= hi):
            raise BadInput(f"monsters.{mid}.pos: d phải trong dải loài [{lo}, {hi}]")
        wps = m.get("waypoints")
        if not (isinstance(wps, list) and len(wps) == 2):
            raise BadInput(f"monsters.{mid}.waypoints phải có đúng 2 điểm")
        for i, wp in enumerate(wps):
            _pos(f"monsters.{mid}.waypoints[{i}]", wp, bounds)
        if m.get("target_idx", 1) not in (0, 1) or isinstance(m.get("target_idx"), bool):
            raise BadInput(f"monsters.{mid}.target_idx phải là 0 hoặc 1")
        state = m.get("state", "patrol")
        if state not in ("patrol", "chase", "recoil"):
            raise BadInput(f"monsters.{mid}.state phải là patrol, chase hoặc recoil")
        left, rdir = m.get("state_ticks_left", 0), m.get("recoil_dir")
        _nonneg_int(f"monsters.{mid}.state_ticks_left", left)
        if state == "recoil":
            if left <= 0:
                raise BadInput(f"monsters.{mid}: recoil cần state_ticks_left > 0")
            if not (isinstance(rdir, list) and len(rdir) == 2 and all(_num(c) for c in rdir)
                    and abs(rdir[0] ** 2 + rdir[1] ** 2 - 1) < 1e-6):
                raise BadInput(f"monsters.{mid}: recoil cần recoil_dir là vector đơn vị")
        elif left != 0 or rdir is not None:
            raise BadInput(f"monsters.{mid}: {state} không có state_ticks_left/recoil_dir")


def _validate_quan(b, tuning):
    for arr in ("stoves", "tables", "customers"):
        if arr in b:
            _check_ids(arr, b[arr])
    if "stock" in b:
        validate_items(b["stock"])
    if "random_customers" in b and not isinstance(b["random_customers"], bool):
        raise BadInput("random_customers phải là boolean")
    p = b.get("player", {})
    if not isinstance(p, dict) or set(p) - QUAN_PLAYER_KEYS:
        raise BadInput("quan.player chỉ có pos và vel")
    qb = tuning["quan"]["bounds"]
    if "pos" in p:
        _pos("player.pos", p["pos"], qb, axes=("x", "z"))
    if "vel" in p and not (isinstance(p["vel"], list) and len(p["vel"]) == 2 and all(_num(c) for c in p["vel"])):
        raise BadInput("player.vel phải là [x, z]")
    table_ids = [c.get("table_id") for c in b.get("customers", [])]
    known = {t["id"] for t in tuning["quan"]["tables"]} | {t.get("id") for t in b.get("tables", [])}
    for c in b.get("customers", []):
        if not isinstance(c.get("table_id"), str) or c["table_id"] not in known:
            raise BadInput(f"customers.{c['id']}: table_id phải là bàn có thật")
        if "dish_id" in c:
            if c["dish_id"] is not None and c["dish_id"] not in tuning["menu"]:
                raise BadInput(f"customers.{c['id']}: dish_id không có trong menu")
        if "order_tick" in c:
            _nonneg_int(f"customers.{c['id']}.order_tick", c["order_tick"])
        order_status = c.get("order_status", "reserved")
        if order_status not in ("reserved", "assigned", "unfulfillable", "served"):
            raise BadInput(f"customers.{c['id']}: order_status không hợp lệ")
        state = c.get("state", "waiting")
        if state not in ("waiting", "eating"):
            raise BadInput(f"customers.{c['id']}: state phải là waiting hoặc eating")
        if "patience_ticks_left" in c:
            _nonneg_int(f"customers.{c['id']}.patience_ticks_left", c["patience_ticks_left"])
        if "reserved" in c:
            try:
                validate_items(c["reserved"])
            except BadInput as e:
                raise BadInput(f"customers.{c['id']}.reserved: {e}")
        if order_status in ("assigned", "unfulfillable") and c.get("reserved", {}) != {}:
            raise BadInput(f"customers.{c['id']}: reserved phải rỗng")
        if order_status == "assigned" and state != "waiting":
            raise BadInput(f"customers.{c['id']}: đơn assigned phải đang waiting")
        if order_status == "unfulfillable" and state != "waiting":
            raise BadInput(f"customers.{c['id']}: đơn unfulfillable phải đang waiting")
        if state == "waiting":
            dish_id = c.get("dish_id")
            reserved = c.get("reserved")
            if order_status == "reserved" and dish_id is not None:
                recipe = tuning["menu"][dish_id]["recipe"]
                if reserved is not None and reserved != recipe:
                    raise BadInput(f"customers.{c['id']}: giữ khác công thức món")
            if reserved is not None:
                if "stock" in b:
                    stock = b["stock"]
                    for item, amount in reserved.items():
                        if amount > stock.get(item, 0):
                            raise BadInput(f"customers.{c['id']}: giữ vượt tồn kho")
        elif state == "eating":
            if c.get("order_status") != "served":
                raise BadInput(f"customers.{c['id']}: khách eating phải là served")
            if "eat_ticks_left" not in c:
                raise BadInput(f"customers.{c['id']}: eating thiếu eat_ticks_left")
            eat_ticks = c["eat_ticks_left"]
            if isinstance(eat_ticks, bool) or not isinstance(eat_ticks, int) or eat_ticks <= 0:
                raise BadInput(f"customers.{c['id']}.eat_ticks_left phải là số nguyên dương")
            if "base_price" not in c or isinstance(c["base_price"], bool) or not isinstance(c["base_price"], int) or c["base_price"] <= 0:
                raise BadInput(f"customers.{c['id']}: eating khai base_price nguyên dương")
            if "tip" in c:
                _nonneg_int(f"customers.{c['id']}.tip", c["tip"])
    if len(table_ids) != len(set(table_ids)):
        raise BadInput("hai khách cùng bàn")
    if "stock" in b:
        reserved_total = {}
        for c in b.get("customers", []):
            if "reserved" in c:
                reserved = c["reserved"]
            else:
                reserved = None
            if reserved:
                for item, amount in reserved.items():
                    reserved_total[item] = reserved_total.get(item, 0) + amount
        for item, amount in reserved_total.items():
            if amount > b["stock"].get(item, 0):
                raise BadInput("tổng giữ chỗ nguyên liệu vượt tồn kho")
