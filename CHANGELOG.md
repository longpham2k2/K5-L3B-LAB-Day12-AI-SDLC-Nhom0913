# Changelog

Mỗi phase của lab là một phiên bản Test Contract; bản phát hành công khai đầu tiên là **v1.0.0** (Phase 4).

## [1.0.0] — Phase 4 (TICKET-04 "Phát hành v1.0.0", Test Contract v1.3)

### Thêm
- `contract_version: "1.3"`; khai `bench_cmd` (`python3 -m chonoi.bench`) và `soak_cmd` (`python3 -m chonoi.soak`) ở gốc `game.contract.json`. Gameplay, tuning, kho và JSONL giữ như v1.2.
- `soak_cmd --seed <int> --days <N> --out soak.json`: chạy N Ngày trong một tiến trình headless (bot tất định), kế hoạch D1–D5 lặp ở Ngày 6+, ghi `days, days_completed, crashes, results[], duration_s`.
- Cửa sổ chơi: hình vẽ tay (`chonoi/web/art.js`: Út Sen áo bà ba/khăn rằn, cá linh/lóc/kèo, Cá Sấu, bông điên điển/bông súng/kèo nèo), rong/đá CC0 Kenney, nhật ký sự kiện dạng câu tiếng Việt, nhãn dùng tên thật thay id.
- `run_cmd` và README chạy vòng ngày đầy đủ: `python3 -m chonoi.live --mode day --days 5`.

### Sửa
- `day`: kế hoạch Ngày 6+ tra theo vòng D1–D5 (trước đây lỗi `KeyError` ở Ngày 6).

## [0.3.0] — Phase 3 ("Mùa Nước Nổi", Test Contract v1.2)

### Breaking changes
- **Kho đếm → kho cá thể (`{id, kind, fresh}`):**
  - File `--inventory-out` / `--inventory`, `gather_end.data.inventory`, `gather.hold`, `quan.stock`, snapshot `hold` và `stock` (Quán & Shop) đều dùng mảng cá thể `[{"id": "I1", "kind": "ca_linh", "fresh": 100}, ...]`.
  - File hoặc fixture dùng schema kho đếm cũ (`{"items": {kind: n}}`) bị từ chối với **mã thoát 2**.
- **Giữ chỗ theo id cá thể:** `customers[].reserved` chuyển từ map đếm `{kind: n}` sang mảng id cá thể `["I1", ...]`.
- **Sự kiện & giá theo độ tươi:**
  - Thêm sự kiện `spoiled` (`{item_id, kind, location}` với `location` là `"hold"` hoặc `"stock"`) khi độ tươi đi từ `>= 30` xuống `< 30`.
  - `cook_started.data.items` chuyển từ mảng tên loại sang mảng cá thể `{id, kind, fresh}` sắp theo `(kind, id)`.
  - `base_price` chốt lúc nấu theo độ tươi: `floor(giá niêm yết × mean(fresh) / 100)` (tính chính xác bằng `Fraction`); boa tính trên `base_price` đã chốt.
  - `gather_end.lost` / `monster_hit.lost` / `faint.lost` chuyển từ danh sách loại sang mảng cá thể theo thứ tự bỏ LIFO.
- **Fixture `--mode day`:** `gather.hold` ở Ngày đầu giữ nguyên `id` trong fixture; từ Ngày 2 trở đi cấp `id` mới (`I<n>`) theo thứ tự mảng với `kind`/`fresh` ban đầu.

### Cách cập nhật fixture & test từ v1.1 sang v1.2
1. Dùng helper `from helpers import items`: đổi `["ca_loc", "bong_sung"]` hoặc `{"ca_loc": 1, "bong_sung": 1}` thành `items("ca_loc", "bong_sung")` (hoặc khai báo tường minh `[{"id": "I1", "kind": "ca_loc", "fresh": 80}]`).
2. Trong scenario `quan`: đổi `"stock": {}` thành `"stock": []`, và `"reserved": {}` / `{"ca_loc": 1}` thành `"reserved": []` / `["I1"]`.
3. Các assertion đọc `hold`/`stock` trong snapshot hoặc event dùng `[x["kind"] for x in ...]` hoặc kiểm trực tiếp `(x["id"], x["kind"], x["fresh"])`. Các test kiểm giá sau tick hao tươi cần tính `floor(price * mean(fresh) / 100)`.

## [0.2.0] — Phase 2 (TICKET-02 "Một ngày ở chợ nổi", Test Contract v1.1)

### Thêm
- Số liệu chuẩn: 6 nguyên liệu (thêm `ca_keo`, `keo_neo`), 6 món, bếp B1–B2, bàn T1–T4, nút N1–N6.
- Gather: 8 đàn đầu ca, cá bơi 1.5 m/s (đổi hướng mỗi 120 bước, phản xạ mép), sinh cá mỗi 360 tick (`fish_spawned`); Cá Sấu M1 (M2 từ Ngày 3) patrol/chase/recoil, `monster_hit`, bất tử 90 tick, rơi floor(n/2) LIFO, `faint` do quái.
- `--mode day` (`--days 1..5`): DayIntro → gather → quán → Shop, giữ tiền/earned/uy tín/cấp qua Ngày, `active_upgrades` áp từ Ngày kế; `day_plan` D1–D5.
- Shop: nâng cấp `oxygen` (45/60 s) và `hp` (4/5 Máu), `bought`/`buy_failed`/`shop_end`, tự đóng sau 600 tick.
- Pause ở cả 3 mode (`paused`/`resumed`, `state: "paused"`); inputs `pause`, `shop_done`, `buy`.

### Đổi (ảnh hưởng test P1)
- Đầu ca 8 đàn thay vì 6; `attack`/`photo` là nút hợp lệ (bị bỏ qua khi chưa bật mở rộng); `--mode day` không còn mã 2.

## [0.1.0] — Phase 1 (PRD-0, Test Contract v1.0)

### Thêm
- Buổi sáng `gather`: bơi `[x,d]`, oxy/ngạt/Máu/ngất, hái nút ở mặt nước, bắt cá (`catch`, hồi chiêu), giỏ LIFO, cập bến, file kho.
- Buổi tối `quan`: khách theo lịch, giữ chỗ nguyên liệu, kiên nhẫn, bếp → bưng → phục vụ, trả tiền, boa, uy tín, đóng ca.
- Headless theo Test Contract v1.0 (JSONL tất định, mã thoát 0/1/2), smoke hai tiến trình gather → quan qua file kho.
