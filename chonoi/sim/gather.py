"""Buổi sáng — Lặn & Hái (`gather`). KHUNG: bơi, chặn mép, đồng hồ, cập bến, xuất kho.

Mặt cắt dòng sông nhìn NGANG: vị trí `[x, d]` (x sang phải, `d` độ sâu hướng xuống, d = 0 là mặt nước).
`move = [x, d]`: thành phần thứ hai DƯƠNG = bơi xuống. Hướng mặt là góc từ +x, dương = xuống.

Đã làm sẵn để smoke test chạy được: bơi + tăng/giảm tốc, chặn mép (d không âm), đồng hồ và hết giờ,
cập bến (`interact` trong vùng bến -> `gather_end` reason `docked`), xuất kho, snapshot đầy đủ trường gather.

Nhóm viết tiếp (đúng thứ tự một bước trong PRD mục 13.8, "Gather"):
  ĐÃ LÀM (lát 1, test: tests/test_gather_slice1.py): bơi + oxy + biên + giỏ
      - oxy: dưới nước (d > surface_depth) trừ 1 tick/tick, mặt nước hồi oxygen_refill_per_tick, kẹp [0, max]
      - ngạt: oxy = 0 và đang dưới nước -> đếm zero_oxy_ticks, đủ choke_interval_ticks thì -1 Máu (choke)
      - Máu về 0 -> ngất (faint, gather_end reason `fainted`, mất toàn bộ giỏ, kho rỗng)
      - sự kiện dive / surface / oxygen_empty / choke / faint
      - giỏ: thứ tự nhặt (LIFO), sức chứa hold_capacity
  ĐÃ LÀM (lát 2, test: tests/test_gather_slice2.py): hái + bắt cá + cập bến + kho
      - hái nút ở mặt nước (gather, hold_full), nút mọc lại (node_regrown đã có phần đếm ngược)
      - bắt đàn cá bằng `catch` (fish_caught, hold_full, hồi chiêu catch_cd_ticks, chỉ khi dưới nước)
      - cập bến xét TRƯỚC hái (đã có); ghi kho đúng một lần do runner lo
Các tính năng của phase sau chưa nằm trong khung này.
"""

import math

from ..ids import sort_by_id
from ..inventory import hold_to_items
from .ramp import ramp_velocity

TICK = 60.0
AXES = ("x", "d")


def _reflect(v, lo, hi):
    """Phản xạ phần quãng đường vượt mép; trả (vị trí, có đảo hướng không)."""
    if v > hi:
        return hi - (v - hi), True
    if v < lo:
        return lo + (lo - v), True
    return v, False


class GatherSim:
    mode = "gather"
    phase = "gather"

    def __init__(self, tuning, scenario, streams, ids, *, day=1, active_upgrades=None):
        t = tuning["gather"]
        self.t = t
        self.rng = streams
        self.ids = ids
        p = scenario.get("player", {})
        self.pos = [float(c) for c in p.get("pos", t["start_pos"])]
        self.vel = [float(c) for c in p.get("vel", [0.0, 0.0])]
        self._tgt = None
        self._ramp_left = 0
        self.heading = float(p.get("heading_deg", t["start_heading_deg"]))
        # cấp nâng cấp đang áp dụng (day) đổi oxy tối đa / Máu tối đa theo tuning.shop.upgrades (contracts §5)
        ups = active_upgrades or {}
        shop = tuning.get("shop", {}).get("upgrades", {})
        oxy_s, self.hp_max = t["oxygen_max_s"], int(t["hp_max"])
        if ups.get("oxygen"):
            oxy_s = shop["oxygen"][ups["oxygen"] - 1]["oxygen_max_s"]
        if ups.get("hp"):
            self.hp_max = int(shop["hp"][ups["hp"] - 1]["hp_max"])
        self.oxygen_max = int(round(oxy_s * TICK))
        self.oxygen_ticks = p.get("oxygen_ticks", self.oxygen_max)
        self.hp = p.get("hp", self.hp_max)
        self.zero_oxy_ticks = p.get("zero_oxy_ticks", 0)
        self.invuln_ticks = p.get("invuln_ticks", 0)
        self.catch_cd_ticks = p.get("catch_cd_ticks", 0)
        self.hold = list(scenario.get("hold", []))  # thứ tự nhặt, cuối mảng là mới nhất
        self.time_left_ticks = scenario.get("time_left_ticks", int(round(t["duration_s"] * TICK)))
        # nút và đàn cá: scenario THAY THẾ danh sách mặc định; random_fish=false tắt cá mặc định
        src_nodes = scenario["nodes"] if "nodes" in scenario else t["nodes"]
        self.nodes = [{"id": n["id"], "kind": n["kind"], "pos": [float(c) for c in n["pos"]],
                       "regrow_ticks": n.get("regrow_ticks", 0)} for n in src_nodes]
        # v1.1: random_fish=false tắt cá mặc định, bơi và sinh (cá fixture đứng yên);
        # khai fish khi cờ bật thì thay đàn ban đầu nhưng vẫn bơi/sinh.
        self.random_fish = scenario.get("random_fish", True)
        src_fish = scenario.get("fish", [])
        self.fish = [{"id": f["id"], "kind": f["kind"], "pos": [float(c) for c in f["pos"]],
                      "heading_deg": f.get("heading_deg", 0), "age_ticks": f.get("age_ticks", 0)}
                     for f in src_fish]
        # Cá Sấu: scenario.monsters thay danh sách; bỏ thì dùng bố trí đúng Ngày (from_day <= day)
        mon = t["monsters"]
        self.species = mon["species"]
        src_mon = scenario["monsters"] if "monsters" in scenario else \
            [dict(m, target_idx=1) for m in mon["spawns"] if m.get("from_day", 1) <= day]
        self.monsters = [{"id": m["id"], "kind": m["kind"], "pos": [float(c) for c in m["pos"]],
                          "waypoints": [[float(c) for c in w] for w in m["waypoints"]],
                          "target_idx": m.get("target_idx", 1), "state": m.get("state", "patrol"),
                          "state_ticks_left": m.get("state_ticks_left", 0),
                          "recoil_dir": [float(c) for c in m["recoil_dir"]] if m.get("recoil_dir") else None}
                         for m in src_mon]
        for coll in (self.nodes, self.fish, self.monsters):
            for e in coll:
                ids.reserve(e["id"])
        if "fish" not in scenario and self.random_fish:
            for _ in range(int(t["fish_initial"])):
                f = self._spawn_one()
                if f is None:
                    break
                self.fish.append(f)
        self.money = 0
        self.earned = 0
        self.reputation = tuning["quan"]["reputation_initial"]
        self.phase_tick = 0
        self.done = False
        self.reason = None

    # --- giao diện cho runner -------------------------------------------------
    def inventory_items(self) -> dict:
        return hold_to_items(self.hold)

    def snapshot(self) -> dict:
        return {
            "player": {"pos": self.pos, "vel": self.vel, "heading_deg": self.heading,
                       "oxygen_ticks": self.oxygen_ticks, "oxygen_max_ticks": self.oxygen_max,
                       "hp": self.hp, "hp_max": self.hp_max, "zero_oxy_ticks": self.zero_oxy_ticks,
                       "invuln_ticks": self.invuln_ticks, "catch_cd_ticks": self.catch_cd_ticks,
                       "at_surface": self._at_surface()},
            "hold": self.hold, "hold_count": len(self.hold),
            "hold_capacity": self.t["hold_capacity"],
            "nodes": [{"id": n["id"], "pos": n["pos"], "kind": n["kind"],
                       "ready": n["regrow_ticks"] == 0, "regrow_ticks": n["regrow_ticks"]}
                      for n in sort_by_id(self.nodes)],
            "monsters": [{k: m[k] for k in ("id", "kind", "pos", "waypoints", "target_idx", "state",
                                             "state_ticks_left", "recoil_dir")} for m in sort_by_id(self.monsters)],
            "fish": [{"id": f["id"], "pos": f["pos"], "kind": f["kind"], "heading_deg": f["heading_deg"],
                      "age_ticks": f["age_ticks"]} for f in sort_by_id(self.fish)],
        }

    # --- một bước ---------------------------------------------------------------
    def step(self, inp):
        events = []
        # 1. đồng hồ và hàng có sẵn: giảm bộ đếm, nút mọc lại
        self.phase_tick += 1
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        self.invuln_ticks = max(0, self.invuln_ticks - 1)
        self.catch_cd_ticks = max(0, self.catch_cd_ticks - 1)
        for n in sort_by_id(self.nodes):
            if n["regrow_ticks"] > 0:
                n["regrow_ticks"] -= 1
                if n["regrow_ticks"] == 0:
                    events.append(("node_regrown", {"node_id": n["id"]}))
        # 2. bơi + chặn mép, dive/surface, oxy, ngạt, ngất (PRD-0 mục F, Gather bước 2)
        was_surface = self._at_surface()
        self._move(inp)
        now_surface = self._at_surface()
        if was_surface != now_surface:
            events.append(("surface" if now_surface else "dive", {"pos": list(self.pos)}))
        if self._breathe(now_surface, events):
            return events
        # 3. quái: cập nhật theo id rồi xét tối đa một hit (TICKET-02 mục 1.2, 4.5)
        if self._monsters_step(events):
            return events
        # 3. interact: bến trước, rồi hái
        if inp.pressed("interact"):
            if self._in_dock():
                self._finish("docked", events)
                return events
            if self._at_surface():
                self._pick(events)
        # 4. bắt cá
        if inp.pressed("catch") and self.catch_cd_ticks == 0 and not self._at_surface():
            self._catch(events)
        # 5. hết giờ
        if self.time_left_ticks <= 0:
            self._finish("time", events)
            return events
        # 6. còn giờ: cá bơi, rồi sinh theo lịch (TICKET-02 mục 4.5). Bắt cá ở bước 4 dùng vị trí trước khi bơi.
        if self.random_fish:
            self._swim_fish()
            self._spawn_on_schedule(events)
        return events

    # --- Cá Sấu (TICKET-02 mục 1.2) ------------------------------------------------
    def _monsters_step(self, events) -> bool:
        """Cập nhật quái theo id, rồi tối đa một hit. Trả True nếu người chơi ngất (dừng bước)."""
        px, pd = self.pos
        just_free = set()  # vừa hết recoil: chỉ xét phát hiện/chạm từ bước kế
        for m in sort_by_id(self.monsters):
            sp = self.species[m["kind"]]
            if m["state"] == "recoil":
                step = float(sp["recoil_dist"]) / float(sp["recoil_ticks"])
                self._monster_move(m, m["pos"][0] + m["recoil_dir"][0] * step, m["pos"][1] + m["recoil_dir"][1] * step)
                m["state_ticks_left"] -= 1
                if m["state_ticks_left"] <= 0:
                    m["state"], m["state_ticks_left"], m["recoil_dir"] = "patrol", 0, None
                    just_free.add(m["id"])
                continue
            deep = pd >= float(sp["depths"][0])
            dist = math.dist(m["pos"], self.pos)
            if m["state"] == "patrol" and deep and dist <= float(sp["detect_radius"]):
                m["state"] = "chase"
            elif m["state"] == "chase" and (not deep or dist > float(sp["exit_radius"])):
                m["state"] = "patrol"
            if m["state"] == "chase":
                self._monster_toward(m, self.pos, float(sp["chase_speed"]) / TICK)
            else:
                wp = m["waypoints"][m["target_idx"]]
                if self._monster_toward(m, wp, float(sp["patrol_speed"]) / TICK):
                    m["target_idx"] = 1 - m["target_idx"]  # đến nơi: đổi mục tiêu cho bước sau
        if self.invuln_ticks > 0:
            return False
        hits = []
        for m in sort_by_id(self.monsters):
            sp = self.species[m["kind"]]
            if m["state"] == "recoil" or m["id"] in just_free or pd < float(sp["depths"][0]):
                continue
            dist = math.dist(m["pos"], self.pos)
            if dist <= float(sp["hit_radius"]):
                hits.append((dist, m))
        if not hits:
            return False
        _, m = min(hits, key=lambda h: h[0])  # sort_by_id + min ổn định -> hòa theo id
        mon = self.t["monsters"]
        sp = self.species[m["kind"]]
        self.hp = max(0, self.hp - 1)
        n = int(math.floor(len(self.hold) * float(mon["loss_ratio"])))
        lost = list(reversed(self.hold[len(self.hold) - n:])) if n else []
        if n:
            del self.hold[len(self.hold) - n:]
        self.invuln_ticks = int(mon["invuln_ticks"])
        dx, dd = m["pos"][0] - px, m["pos"][1] - pd
        norm = math.hypot(dx, dd)
        m["recoil_dir"] = [dx / norm, dd / norm] if norm > 0 else [1.0, 0.0]
        m["state"], m["state_ticks_left"] = "recoil", int(sp["recoil_ticks"])
        events.append(("monster_hit", {"monster_id": m["id"], "hp": self.hp, "lost": lost, "pos": list(self.pos)}))
        if self.hp > 0:
            return False
        rest = list(reversed(self.hold))
        self.hold = []
        events.append(("faint", {"cause": "monster", "lost": rest, "hp": 0}))
        self._finish("fainted", events)
        return True

    def _monster_toward(self, m, target, step) -> bool:
        """Đi tới `target` tối đa `step` m; trả True nếu đã tới nơi."""
        dx, dd = target[0] - m["pos"][0], target[1] - m["pos"][1]
        dist = math.hypot(dx, dd)
        if dist <= step + 1e-9:  # dung sai số thực: 4 m / (1/60 m) = đúng 240 bước
            self._monster_move(m, target[0], target[1])
            return True
        self._monster_move(m, m["pos"][0] + dx / dist * step, m["pos"][1] + dd / dist * step)
        return False

    def _monster_move(self, m, x, d):
        """Chặn theo biên map và dải độ sâu của loài."""
        b = self.t["bounds"]
        lo, hi = self.species[m["kind"]]["depths"]
        m["pos"] = [min(max(x, b["x"][0]), b["x"][1]),
                    min(max(d, max(lo, b["d"][0])), min(hi, b["d"][1]))]

    # --- cá bơi / sinh (TICKET-02 mục 1.1) ---------------------------------------
    def _swim_fish(self):
        t = self.t
        step = float(t["fish_speed"]) / TICK
        turn = int(t["fish_turn_ticks"])
        xlo, xhi = (float(c) for c in t["fish_x"])
        rng = self.rng.get("fish_turn")
        for f in sort_by_id(self.fish):
            n = f["age_ticks"] + 1  # bước bơi thứ n của đàn này
            if n % turn == 0:
                f["heading_deg"] = round(rng.random() * 360.0, 3)  # đổi hướng TRƯỚC khi di chuyển
            h = math.radians(f["heading_deg"])
            vx, vd = math.cos(h), math.sin(h)
            dlo, dhi = (float(c) for c in t["fish_depths"][f["kind"]])
            x, fx = _reflect(f["pos"][0] + vx * step, xlo, xhi)
            d, fd = _reflect(f["pos"][1] + vd * step, dlo, dhi)
            if fx or fd:
                vx, vd = (-vx if fx else vx), (-vd if fd else vd)
                f["heading_deg"] = round(math.degrees(math.atan2(vd, vx)) % 360.0, 3)
            f["pos"] = [x, d]
            f["age_ticks"] = n

    def _spawn_on_schedule(self, events):
        t = self.t
        if self.phase_tick % int(t["fish_spawn_ticks"]) != 0 or len(self.fish) >= int(t["fish_max"]):
            return
        f = self._spawn_one()
        if f is None:
            return  # hết điểm hợp lệ: bỏ lượt
        self.fish.append(f)  # tham gia bơi/bắt từ bước sau
        events.append(("fish_spawned", {"id": f["id"], "kind": f["kind"], "pos": list(f["pos"])}))

    # --- tiện ích ---------------------------------------------------------------
    def _at_surface(self) -> bool:
        return self.pos[1] <= self.t["surface_depth"]

    def _in_dock(self) -> bool:
        return math.dist(self.pos, self.t["dock_pos"]) <= self.t["dock_radius"]

    def _spawn_one(self):
        """Sinh một đàn (TICKET-02 mục 1.1): loài theo trọng số chuẩn hóa trên các loài còn điểm cách mọi
        đàn đang sống > clearance, rồi chọn đều một điểm của loài, hướng ban đầu theo seed. Hết điểm -> None."""
        t = self.t
        rng = self.rng.get("fish_spawn")
        clear = float(t["fish_spawn_clearance"])
        cands = {}
        for kind in sorted(t["fish_weights"]):
            pts = [[float(x), float(d)] for x in t["fish_spawn_x"] for d in t["fish_spawn_depths"][kind]
                   if all(math.dist((x, d), f["pos"]) > clear for f in self.fish)]
            if pts:
                cands[kind] = pts
        if not cands:
            return None
        total = sum(float(t["fish_weights"][k]) for k in cands)
        r, acc, kind = rng.random() * total, 0.0, None
        for k in cands:
            acc += float(t["fish_weights"][k])
            if r < acc:
                kind = k
                break
        kind = kind or list(cands)[-1]
        pos = rng.choice(cands[kind])
        heading = round(rng.random() * 360.0, 3)
        return {"id": self.ids.new("F"), "kind": kind, "pos": pos, "heading_deg": heading, "age_ticks": 0}

    def _nearest(self, items, radius):
        """Thực thể gần nhất trong bán kính (tính cả đúng mép), hòa theo id; không có thì None."""
        best = None
        for e in sort_by_id(items):
            dist = math.dist(self.pos, e["pos"])
            if dist <= radius and (best is None or dist < best[0]):
                best = (dist, e)
        return best[1] if best else None

    def _free(self) -> int:
        return int(self.t["hold_capacity"]) - len(self.hold)

    def _pick(self, events):
        n = self._nearest([n for n in self.nodes if n["regrow_ticks"] == 0], self.t["interact_radius"])
        if n is None:
            return
        amount = int(self.t["node_yield"])
        if self._free() < amount:
            events.append(("hold_full", {"action": "gather", "node_id": n["id"], "required": amount,
                                         "free": self._free()}))
            return
        self.hold.extend([n["kind"]] * amount)
        n["regrow_ticks"] = int(round(self.t["regrow_s"] * TICK))
        events.append(("gather", {"node_id": n["id"], "kind": n["kind"], "amount": amount}))

    def _catch(self, events):
        f = self._nearest(self.fish, self.t["catch_radius"])
        if f is None:
            return
        y = int(self.t["fish_yield"][f["kind"]])
        if self._free() < y:
            events.append(("hold_full", {"action": "catch", "fish_id": f["id"], "required": y, "free": self._free()}))
            return
        self.hold.extend([f["kind"]] * y)
        self.fish.remove(f)
        self.catch_cd_ticks = int(round(self.t["catch_cooldown_s"] * TICK))
        events.append(("fish_caught", {"fish_id": f["id"], "kind": f["kind"], "yield": y}))

    def _breathe(self, at_surface, events) -> bool:
        """Oxy theo d cuối bước. Trả True nếu ngất (bước dừng)."""
        t = self.t
        if at_surface:
            self.oxygen_ticks = min(self.oxygen_max, self.oxygen_ticks + int(t["oxygen_refill_per_tick"]))
            self.zero_oxy_ticks = 0
            return False
        before = self.oxygen_ticks
        self.oxygen_ticks = max(0, self.oxygen_ticks - 1)
        if before > 0 and self.oxygen_ticks == 0:
            events.append(("oxygen_empty", {"oxygen_ticks": 0}))
        if self.oxygen_ticks > 0:
            return False
        self.zero_oxy_ticks += 1
        if self.zero_oxy_ticks < int(t["choke_interval_ticks"]):
            return False
        self.zero_oxy_ticks = 0
        self.hp = max(0, self.hp - 1)
        events.append(("choke", {"hp": self.hp}))
        if self.hp > 0:
            return False
        lost = list(reversed(self.hold))  # nhặt sau bỏ trước (LIFO)
        self.hold = []
        events.append(("faint", {"cause": "choke", "lost": lost, "hp": 0}))
        self._finish("fainted", events)
        return True

    def _finish(self, reason, events):
        self.done = True
        self.reason = reason
        events.append(("gather_end", {"reason": reason, "inventory": {"items": self.inventory_items()}}))

    def _move(self, inp):
        speed = self.t["swim_speed"]
        mx, md = inp.move
        self.vel = ramp_velocity(self, (mx * speed, md * speed), int(self.t["ramp_max_ticks"]))
        if (mx, md) != (0.0, 0.0):
            self.heading = math.degrees(math.atan2(md, mx)) % 360
        b = self.t["bounds"]
        for i, axis in enumerate(AXES):
            self.pos[i] += self.vel[i] / TICK
            lo, hi = b[axis]
            if self.pos[i] <= lo:
                self.pos[i] = lo
                self.vel[i] = max(0.0, self.vel[i])
            elif self.pos[i] >= hi:
                self.pos[i] = hi
                self.vel[i] = min(0.0, self.vel[i])
