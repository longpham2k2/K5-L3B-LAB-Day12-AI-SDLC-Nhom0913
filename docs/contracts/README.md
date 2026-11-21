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
| `customer_arrived` / `no_dish` | `order_id, table_id, dish_id` / `{}` | quan (lát 3 — Huy) | |
| `customer_left` | `order_id, table_id, reason (patience/closing), reputation` | quan (lát 3 — Huy) | |
| `cook_started` | `stove_id, order_id, dish_id, items, base_price` | quan (lát 4 — Duy) | |
| `dish_ready` / `dish_picked` | `stove_id, order_id, dish_id` | quan (lát 4 — Duy) | |
| `served` | `order_id, table_id, dish_id, patience_ticks_left, base_price, tip` | quan (lát 4 — Duy) | |
| `paid` | `order_id, table_id, base_price, tip, amount, reason (finished_eating/closing)` | quan (lát 4 — Duy) | |
| `quan_end` | `reason: "time", money, earned, shift_earned, reputation` | quan (lát 4 — Duy) | |

## 4. Ranh giới lát 3 ↔ lát 4 trong `chonoi/sim/quan.py`

Khách là dict theo mục D. Lát 3 (Huy) sở hữu: sinh khách, chọn món, `reserved`, giảm `patience_ticks_left`, khách rời. Lát 4 (Duy) sở hữu: bếp, `hand`, `served`, ăn, trả tiền, boa, uy tín, `quan_end`. Khi đơn chuyển trạng thái (`reserved → assigned → served`), lát 4 đổi `order_status`; lát 3 chỉ đọc. Thứ tự trong `step()` theo PRD mục F "Quán" bước 1→5.
