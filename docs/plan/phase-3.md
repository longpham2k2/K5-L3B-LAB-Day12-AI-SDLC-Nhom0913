# Kế hoạch Phase 3 — TICKET-03 "Mùa Nước Nổi", Test Contract v1.2 (35 phút, tag trước 2:30)

**Mục tiêu:** kho cá thể `{id, kind, fresh}` qua file và trong `day`; hao tươi, `spoiled`, giữ chỗ theo id, giá theo tươi; HUD độ tươi. Regression P1–P2 còn hiệu lực đạt. **Không làm mở rộng** (dòng lũ, khách đặt trước) — nhóm 3 người không bắt buộc.

## Quyết định đổi schema & thứ tự tích hợp (giữ `main` chạy được)

1. **Nhánh tích hợp `p3`.** `main` đứng yên ở tag `phase-2` (xanh) trong lúc đổi schema. Mọi người `git switch p3`, commit/push vào `p3`. Long gộp `p3` → `main` (fast-forward) khi `p3` xanh toàn bộ, ~phút 25.
2. **Thứ tự:** (a) Long đẩy adapter v1.2 trước (phút 0–10): contract 1.2, `chonoi/items.py`, `inventory.py`, `scenario.py`, helper test `items()` → (b) Lặn / Quán / day+HUD song song theo schema đã chốt → (c) phút 20 smoke kho trên `p3` → (d) migrate fixture test cũ, regression, gộp `main`, tag.
3. **Số học độ tươi:** `fractions.Fraction` (chính xác tuyệt đối): giỏ −1/120 điểm/tick, kho quán −1/240 điểm/tick, ươn khi `< 30`, giá `floor(price × mean(fresh) / 100)` tính trên Fraction. Chỉ đổi sang `float` khi xuất JSONL/file kho (file kho ghi `float` đầy đủ, không làm tròn 3 chữ số).
4. **Id cá thể** cấp bằng `IdAllocator` họ `I` (dùng chung toàn lượt, kể cả xuyên Ngày) → `I1, I2, …` theo thứ tự vào giỏ.

## Phân tích tác động

| Module | File cần đổi | Test bị ảnh hưởng | Người |
|---|---|---|---|
| Adapter / schema | `game.contract.json` (1.2, `freshness`), `chonoi/items.py` (mới), `chonoi/inventory.py` (đọc/ghi mảng cá thể, kho đếm → mã 2), `chonoi/scenario.py` (`hold`/`stock` mảng cá thể, `reserved` mảng id, id vật lý duy nhất), `tests/helpers.py` (`items()`) | Thêm `tests/test_p3_inventory.py`; đổi `test_smoke_p1` (kho đếm → mã 2) | Long |
| Lặn | `chonoi/sim/gather.py`: giỏ là cá thể, hao 0.5/s, `spoiled` (location `hold`), `lost` là cá thể, `inventory_items()` trả mảng | Thêm `tests/test_p3_gather_fresh.py`; migrate fixture `hold` ở `test_gather_slice1/2`, `test_gather_monsters_p2` | Long |
| Quán | `chonoi/sim/quan.py`: `stock` cá thể, hao 0.25/s (kể cả hàng giữ chỗ), `spoiled` (`stock`), `reserved` = id tươi nhất (hòa id), nhả + giữ lại một lần khi hàng giữ vừa ươn, thiếu → `unfulfillable` | Thêm `tests/test_p3_quan_fresh.py`; migrate `test_quan_slice3`, `test_p2_quan_shop` | Huy |
| Bếp / giá / day | `chonoi/sim/quan.py` (nấu tiêu đúng id giữ, `base_price` theo tươi, `cook_started.items` cá thể sắp theo kind rồi id), `chonoi/sim/shop.py` (`stock` cá thể), `chonoi/runner.py` (bàn giao cá thể trong `day`, Ngày đầu giữ id fixture, Ngày kế cấp id mới) | Thêm test giá theo tươi + day; migrate `test_quan_slice4`, `test_day_and_pause` | Duy |
| HUD | `chonoi/web/index.html`, `chonoi/live.py`: hiện độ tươi / nhãn "ươn" ở giỏ và kho | `test_live` | Duy |
| QA / tài liệu | `CHANGELOG.md` (breaking change + cách sửa fixture), `docs/verification/phase-3.md`, `docs/proof/phase-3/`, `tools/smoke_p2.sh` → smoke v1.2 | Regression P1–P2 | Duy (QA) + Long |

## Việc

| ID | Việc | Người | Phụ thuộc | Trạng thái |
|---|---|---|---|---|
| AC-P3-01 | Adapter v1.2 (hàng 1 bảng trên) | Long | — | Xong (`chonoi/items.py`, contracts §6) |
| AC-P3-02 | Lặn: giỏ cá thể, hao tươi, `spoiled`, `lost` cá thể, bàn giao | Long | 01 | Xong (`tests/test_p3_gather_fresh.py` 10 test; migrate fixture gather ở slice1/2, monsters, smoke_p1 — 2 test bàn giao chờ quán AC-P3-03) |
| AC-P3-03 | Quán: kho cá thể, hao tươi, `spoiled`, giữ theo id + giữ lại khi ươn | Huy | 01 | Xong (`tests/test_p3_quan_fresh.py`, 5 test; suite P3 15/15) |
| AC-P3-04 | Nấu tiêu id giữ, giá theo tươi, `cook_started.items`; `day` bàn giao cá thể; Shop stock | Duy | 01, 03 | |
| AC-P3-05 | HUD độ tươi / hàng ươn | Duy | 02, 03 | |
| AC-P3-06 | Migrate fixture test cũ (ghi lý do), smoke file + day (`docs/proof/phase-3/`), regression, CHANGELOG, verification, gộp `main`, tag | Long + Duy (QA) | 02–05 | |

## Rủi ro
- **Đổi schema chạm mọi module** → nhánh `p3`, adapter trước, `main` không đỏ.
- **55 fixture cũ** dùng kho đếm → helper `items()` để migrate nhanh, mỗi file test ghi lý do "v1.2 kho cá thể".
- **Ngưỡng 30 và floor giá** dễ lệch do số thực → Fraction.
- 35 phút cho 3 người → không làm mở rộng; HUD tối thiểu (số % + nhãn ươn).
