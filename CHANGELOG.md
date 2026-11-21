# Changelog

## [1.2.0] — Phase 3 ("Mùa Nước Nổi", Test Contract v1.2)

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
