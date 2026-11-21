# Kế hoạch Phase 1 (≤ 1 trang)

- **Mục tiêu:** chơi được cả hai buổi `gather` và `quan` đúng lõi PRD-0; headless đúng Test Contract v1.0; smoke hai tiến trình (gather ghi kho → quan đọc kho) xanh trên `main`; gắn tag `phase-1` trước 1:00.

## Việc / người / phụ thuộc

| ID | Việc | Người | Phụ thuộc | Trạng thái |
|---|---|---|---|---|
| AC-P1-01 | Lát 1: bơi, oxy, ngạt, Máu, ngất (giỏ LIFO), dive/surface | Long | — | Xong (`tests/test_gather_slice1.py`) |
| AC-P1-02 | Lát 2: hái nút ở mặt nước, nút mọc lại, bắt cá (`catch`, hồi chiêu), `hold_full`, cập bến, ghi file kho | Long | AC-P1-01 | Đang làm |
| AC-P1-03 | Lát 3: khách đến theo lịch, chọn món nấu được, giữ chỗ nguyên liệu, kiên nhẫn, `customer_left`, `no_dish` | Huy | Hợp đồng kho (AC-P1-07) | Chưa bắt đầu |
| AC-P1-04 | Lát 4: bếp (`cook_started`, `dish_ready`), bưng (`dish_picked`), phục vụ (`served`), ăn, trả tiền (`paid`), boa, uy tín, `quan_end` | Duy | AC-P1-03 (trường khách/đơn) | Chưa bắt đầu |
| AC-P1-05 | HUD: buổi sáng (thời gian, oxy, Máu, giỏ); buổi tối (kho khả dụng, món gọi, kiên nhẫn, bếp, món trên tay, tiền, uy tín) | Duy | AC-P1-02, AC-P1-04 | Chưa bắt đầu |
| AC-P1-06 | Ma trận truy vết `docs/verification/phase-1.md` + bằng chứng `docs/proof/phase-1/` | Duy | Tất cả | Chưa bắt đầu |
| AC-P1-07 | Hợp đồng kho `docs/contracts/` (schema + ví dụ), danh sách sự kiện, giao diện sim ↔ UI | Long | — | Chưa bắt đầu |
| AC-P1-08 | Chép đủ PRD-0 (mục F Quan, mục G) vào `docs/prd/phase-1.md`; câu hỏi mơ hồ vào `docs/clarify.md` | Long | — | Chưa bắt đầu |
| AC-P1-09 | README: chạy từ clone sạch ≤ 3 lệnh, điều khiển, cách tính điểm, lệnh test | Huy | AC-P1-02, AC-P1-04 | Chưa bắt đầu |
| AC-P1-10 | Ghi chép: `docs/ai-usage-log.md`, `docs/members/<handle>.md`, `docs/standup.md` | Mọi người | — | Liên tục |

## Mốc trong phase

- Phút 0–15: chia vai (xong), chốt hợp đồng kho và trường khách/đơn giữa Huy và Duy.
- Phút 20: standup lần 1 — rà lát đang vướng, người xong sớm hỗ trợ `sim/quan`.
- Phút 25: thử xuất file kho thật từ `gather` và nạp vào `quan`.
- Phút 40: standup lần 2.
- Phút 45–55: smoke hai tiến trình + chơi thử trên `main`, hoàn thiện ma trận truy vết.
- Phút 55–60: gắn tag `phase-1` (Long).

## Rủi ro

- **Nhóm 3 người**, ít hơn mức 4–6 trong đề → hỏi giảng viên và ghi vào `docs/clarify.md`; ít người dự phòng hơn.
- **`sim/quan` là phần nặng nhất** và hai lát cùng sửa `chonoi/sim/quan.py` → chốt trường khách/đơn sớm, viết ở các hàm riêng, gộp thường xuyên.
- **Bản PRD-0 nhóm có bị cắt** (thiếu cuối mục F và mục G) → chép đủ từ lab board trước khi làm lát 2–4; test ẩn so chính xác thứ tự xử lý.
- Lệch kho giữa `gather` và `quan` → dùng `docs/contracts/inventory.sample.json` để làm quán trong lúc chờ lát 2.
