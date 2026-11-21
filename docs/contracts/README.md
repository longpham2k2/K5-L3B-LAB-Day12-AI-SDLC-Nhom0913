# Hợp đồng tích hợp — Phase 1 (chốt bởi Integrator: Long)

Nguồn: PRD-0 mục D, E, G (`docs/prd/phase-1.md`). Đổi hợp đồng: báo cả nhóm, ghi lý do vào `docs/clarify.md`.

## 1. File kho (gather → quan)

```json
{"items": {"bong_sung": 2, "ca_loc": 1}}
```

- Chỉ một khóa gốc `items`: object `kind → số nguyên ≥ 0`. Kind hợp lệ: `ca_loc`, `ca_linh`, `bong_dien_dien`, `bong_sung`.
- Bên ghi (gather) bỏ khóa có lượng 0, sắp khóa theo tên. Kho rỗng: `{"items":{}}`.
- Bên đọc (quan) từ chối sai schema / kind lạ / số âm → mã thoát 2. Trần giỏ không áp lên kho quán.
- Ghi đúng **một lần** khi có `gather_end` (ngất → kho rỗng), khớp `gather_end.data.inventory`. Chạm `--ticks` trước khi kết thúc → không tạo / không ghi đè file. Ghi file tạm rồi thay thế nguyên tử.
- Ví dụ hợp lệ: [`inventory.sample.json`](inventory.sample.json). Kiểm bằng smoke: `docs/proof/phase-1/smoke-two-process.txt`.
- Trong quan: `stock` = tồn vật lý (gồm phần khách giữ chỗ); **khả dụng** = `stock − tổng reserved` của các khách.

## 2. Giao diện sim ↔ client/ui

- **UI gửi vào** (mỗi tick, `chonoi.inputs`): `move [x, y]` trong [−1, 1], `interact` (E), `catch` (Space). Nút chỉ có tác dụng ở cạnh lên.
- **UI chỉ đọc snapshot** (không sửa state sim):
  - Chung: `tick, phase_tick, state, time_left_ticks, money, earned, reputation, score`.
  - gather: `player{pos, vel, heading_deg, oxygen_ticks, oxygen_max_ticks, hp, hp_max, zero_oxy_ticks, catch_cd_ticks, at_surface}`, `hold, hold_count, hold_capacity`, `nodes[]{id, kind, pos, ready, regrow_ticks}`, `fish[]{id, kind, pos, heading_deg}`.
  - quan: `player{pos, vel}`, `stock`, `hand`, `stoves[]{id, pos, state, dish, cook_ticks_left, ready_ticks}`, `tables[]{id, pos, customer_id}`, `customers[]{id, table_id, dish_id, order_tick, state, patience_ticks_left, eat_ticks_left, order_status, reserved, base_price, tip}` (chỉ khách còn ngồi).
- Phần sáng tạo của UI (âm thanh, hiệu ứng…) không được đổi state sim, và tắt ở headless.

## 3. Sự kiện

| Sự kiện | data | Phát bởi | Trạng thái |
|---|---|---|---|
| `gather` / `node_regrown` | `node_id, kind, amount` / `node_id` | gather (lát 2) | xong |
| `hold_full` | `action (gather/catch), node_id \| fish_id, required, free` | gather (lát 2) | xong |
| `fish_caught` | `fish_id, kind, yield` | gather (lát 2) | xong |
| `dive` / `surface` | `pos` | gather (lát 1) | xong |
| `oxygen_empty` / `choke` | `oxygen_ticks: 0` / `hp` | gather (lát 1) | xong |
| `faint` | `cause: "choke", lost, hp: 0` | gather (lát 1) | xong |
| `gather_end` | `reason (time/docked/fainted), inventory` | gather | xong |
| `customer_arrived` / `no_dish` | `order_id, table_id, dish_id` / `{}` | quan (lát 3 — Huy) | xong |
| `customer_left` | `order_id, table_id, reason (patience/closing), reputation` | quan (lát 3 — Huy) | xong |
| `cook_started` | `stove_id, order_id, dish_id, items, base_price` | quan (lát 4 — Duy) | xong |
| `dish_ready` / `dish_picked` | `stove_id, order_id, dish_id` | quan (lát 4 — Duy) | xong |
| `served` | `order_id, table_id, dish_id, patience_ticks_left, base_price, tip` | quan (lát 4 — Duy) | xong |
| `paid` | `order_id, table_id, base_price, tip, amount, reason (finished_eating/closing)` | quan (lát 4 — Duy) | xong |
| `quan_end` | `reason: "time", money, earned, shift_earned, reputation` | quan (lát 4 — Duy) | xong |

## 4. Ranh giới lát 3 ↔ lát 4 trong `chonoi/sim/quan.py`

Khách là dict theo mục D. Lát 3 (Huy) sở hữu: sinh khách, chọn món, `reserved`, giảm `patience_ticks_left`, khách rời. Lát 4 (Duy) sở hữu: bếp, `hand`, `served`, ăn, trả tiền, boa, uy tín, `quan_end`. Khi đơn chuyển trạng thái (`reserved → assigned → served`), lát 4 đổi `order_status`; lát 3 chỉ đọc. Thứ tự trong `step()` theo PRD mục F "Quán" bước 1→5.

## 5. Phase 2 (v1.1) — giao diện sim ↔ `day` (chốt bởi Long, phút 0–10)

Mục tiêu: Huy (quán, Shop), Long (gather) và Duy (`day`, pause, HUD) làm song song; `day` chỉ gọi các sim qua giao diện dưới đây, không đọc ruột sim.

**Mọi sim** (`GatherSim`, `QuanSim`, `ShopSim`) có: `phase` (`"gather"|"quan"|"shop"`), `step(inp) -> [(name, data), ...]`, `snapshot() -> dict` (phần riêng của pha), `done`, `reason`, `time_left_ticks`, `money`, `earned`, `reputation`. `inp` là `chonoi.inputs.InputState` (có `move`, `pressed(name)`, `buy`).

| Sim | Tham số thêm cho `day` (từ khóa, mặc định = chạy độc lập) | Ai |
|---|---|---|
| `GatherSim(tuning, scenario, streams, ids, *, day=1, active_upgrades=None)` | `day` chọn bố trí Cá Sấu (`from_day`); `active_upgrades` = `{"oxygen": n, "hp": n}` đổi `oxygen_max`/`hp_max` theo `tuning.shop.upgrades`. Kết quả bàn giao: `inventory_items()` | Long |
| `QuanSim(tuning, scenario, streams, ids, inventory=None, *, plan_dishes=None, carry=None)` | `plan_dishes` = list id món của kế hoạch Ngày (lọc menu TRƯỚC khi lọc nguyên liệu); `carry` = `{"money", "earned", "reputation"}` đầu ca (mặc định 0, 0, `reputation_initial`). `shift_earned` luôn bắt đầu 0. Kho dư sau ca: `stock` | Huy |
| `ShopSim(tuning, *, stock, carry, upgrades)` | `stock` = kho dư sau quán (chỉ để snapshot); `carry` như trên; `upgrades` = cấp **đã mua** `{"oxygen": n, "hp": n}`, ShopSim sửa tại chỗ khi `bought`. `time_left_ticks` = `shop.max_ticks` | Huy |

**`day` (Duy)** giữ trạng thái xuyên Ngày: `money`, `earned`, `reputation`, `upgrades` (đã mua), `active_upgrades` (sao từ `upgrades` CHỈ khi dựng Ngày mới), `days_completed`. Sau mỗi pha đọc `money/earned/reputation` của sim cũ làm `carry` cho sim mới. Thứ tự event và vỏ event (`day` trên mọi event, `phase_start`, `day_plan`…) theo `docs/prd/phase-2.md` mục 4.4–4.5.

**Inputs v1.1** (đã có trong `chonoi/inputs.py`): nút `interact, catch, pause, shop_done, attack, photo`; `inp.buy` là chuỗi chỉ ở đúng frame khai báo, ngược lại `None`. Pause xử lý ở `day`/runner, sim không thấy bước pause.

**Dữ liệu v1.1** ở `game.contract.json`: `tuning.day_plan[]`, `tuning.shop`, `tuning.gather.monsters`, khóa cá mới, 6 món, B1–B2, T1–T4. Kho: 6 nguyên liệu (`chonoi/inventory.KINDS`).

## 6. Phase 3 (v1.2) — kho cá thể (chốt bởi Long, nhánh `p3`)

**File kho / `gather_end.data.inventory`:** `{"items": [{"id": "I1", "kind": "ca_linh", "fresh": 100}, ...]}` — sắp theo id, `fresh` float đầy đủ trong file (JSONL làm tròn 3 chữ số). Kho đếm `{"items": {kind: n}}` → **mã 2**. Rỗng: `{"items": []}`.

**Trong sim** dùng `chonoi/items.py` (không tự viết số học độ tươi):

| Hàm | Dùng cho |
|---|---|
| `it.load(raw)` / `it.dump(items)` | fixture/file kho → nội bộ (`fresh` là `Fraction`) / nội bộ → JSON (snapshot, event) |
| `it.new(ids, kind, tuning)` | cá thể mới `I<n>` fresh 100 (IdAllocator dùng chung → id tăng xuyên pha/Ngày) |
| `it.decay(items, it.per_tick(tuning, "gather"/"quan"), tuning)` | hao 1 tick; trả cá thể **vừa** ươn, sắp theo id → phát `spoiled {item_id, kind, location}` |
| `it.is_spoiled(x, tuning)` / `it.usable(x, tuning)` | ươn khi `fresh < 30` (so Fraction, chính xác) |
| `it.pick_freshest(pool, kind, n, tuning, exclude=ids)` | giữ chỗ: n cá thể chưa ươn tươi nhất, hòa theo id; thiếu → `None` |
| `it.counts(items, tuning, only_usable=True)` | đếm theo loại (chọn món, HUD) |

**Giao diện giữa sim** (§5 giữ nguyên tên tham số, chỉ đổi kiểu): `GatherSim.inventory_items()` → **list cá thể nội bộ**; `QuanSim(..., inventory=list cá thể)`; `QuanSim.stock` → list cá thể; `ShopSim(stock=list cá thể)`. Quán: `customers[].reserved` là **mảng id**; giá chốt khi nấu `floor(price × mean(fresh) / 100)` tính trên Fraction. Snapshot `hold`/`stock` dùng `it.dump`.

**Fixture test:** `from helpers import items` → `items("ca_loc", "bong_sung")` = `[{"id":"I1","kind":"ca_loc","fresh":100}, {"id":"I2",...}]` (tham số `fresh=`, `start=`).
