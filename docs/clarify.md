# Clarify — câu hỏi và câu trả lời (PO ghi, cả nhóm dùng chung)

| # | Ngày giờ | Câu hỏi | Trả lời / giả định | Ai quyết |
|---|---|---|---|---|
| 1 | 2026-11-21 | Nhóm chỉ có 3 người, đề yêu cầu 4–6 (`tools/check_team.py` báo không đạt). Có được làm 3 người không? | Chưa có trả lời — tạm làm với 3 người, `team_size: 3`, 4 lát chia cho 3 người (xem `docs/plan/phase-1.md`). | Long (PO) hỏi giảng viên |
| 2 | 2026-11-21 | (Q1) Khi nào đơn thành `unfulfillable`? Mục D định nghĩa trạng thái nhưng mục F không có luật chuyển. | **Giả định:** chỉ xuất hiện từ fixture (khách thiếu `reserved` mà cấp theo `order_tick` rồi id bàn không đủ nguyên liệu). Khách mới không bao giờ unfulfillable — thiếu món thì phát `no_dish`. | Nhóm tự giả định (chưa liên lạc được Anh Năm) |
| 3 | 2026-11-21 | (Q2) Bếp idle có bắt đầu nấu được khi tay đang cầm món không? F chỉ nói bếp ready giao món cho "tay trống". | **Giả định:** nấu không cần tay trống; chỉ lấy món từ bếp ready mới cần tay trống. | Nhóm tự giả định |
| 4 | 2026-11-21 | (Q3) Tỷ lệ kiên nhẫn để boa chia cho gì khi khách fixture có kiên nhẫn ban đầu < đầy? "Đạt" là `>=` hay `>`? | **Giả định:** chia cho `patience_s × 60` của tuning; "đạt" là `>=`. | Nhóm tự giả định |
| 5 | 2026-11-21 | (Q4) Khách trả tiền xong (`paid`, `finished_eating`) có phát thêm `customer_left` không? (lý do `customer_left` chỉ có patience/closing) | **Giả định:** không; `paid` là đủ, khách rời bàn không thêm event. | Nhóm tự giả định |
| 6 | 2026-11-21 | (Q5) Khách ăn xong đúng bước hết ca: `paid` lý do `finished_eating` hay `closing`? | **Giả định:** `finished_eating` (bước 4 xét khách ăn xong theo id bàn trước, rồi mới dọn ca). | Nhóm tự giả định |
| 7 | 2026-11-21 | (Q6) Khách có đơn `assigned` (đang nấu/trên tay) có tiếp tục giảm kiên nhẫn không? | **Giả định:** có, mọi khách `waiting` đều giảm; rời thì bỏ món của đơn (bếp về idle / tay rỗng), nguyên liệu không hoàn. | Nhóm tự giả định |
| 8 | 2026-11-21 | (Q7) "Tính giá trước định dạng" ám chỉ giá có phép tính; Phase 1 giá có phụ thuộc uy tín không? | **Giả định:** `base_price = menu.price`, `tip = floor(base_price × tip_rate)`, `amount = base_price + tip`. Khớp ví dụ end của PRD (72 = 60 + 12, uy tín 3.0 + 0.2 = 3.2). | Nhóm tự giả định |
| 9 | 2026-11-21 | (Q8) PRD không nêu thuật toán "chọn đều theo seed". | **Giả định:** dùng `Streams` của starter, một luồng con tên cố định, chọn trong danh sách món khả dụng sắp theo mã Unicode. Test của nhóm chỉ kiểm tất định hoặc fixture có đúng 1 món khả dụng. | Nhóm tự giả định |
| 10 | 2026-11-21 | (Q9) Đối tượng gần nhất không tương tác được (bếp idle không có đơn reserved, bàn không khớp món trên tay, bếp đang nấu) thì có thử đối tượng kế tiếp không? | **Giả định:** không — "bỏ lượt" theo nghĩa đen, không xét đối tượng khác. | Nhóm tự giả định |
| 11 | 2026-11-21 | (G1) `node_yield` khác 1 thì `amount`/`required` là bao nhiêu? F ghi "thêm 1 nguyên liệu". | **Giả định:** dùng `node_yield` ở mọi chỗ, không hái một phần; thiếu chỗ (< `node_yield`) thì `hold_full`. Đã cài như vậy (lát 2). | Long |
| 12 | 2026-11-21 | (G2) Bến đo trên `[x,d]` với bán kính 3 m → cập bến được khi đang lặn (d ≤ 3). Có đúng ý không? | **Giả định:** đúng theo chữ, cho cập bến dưới nước. Đã cài như vậy. | Long |
| 13 | 2026-11-21 | (G3) `random_fish: true` mà fixture có `fish[]` thì cá có bơi không? | **Giả định:** Phase 1 mọi đàn cá đứng yên. | Long |
| 14 | 2026-11-21 | (G4) Nút fixture có `regrow_ticks` lớn hơn `regrow_s × 60` có hợp lệ không? | **Giả định:** chấp nhận mọi số nguyên không âm. | Long |
| 15 | 2026-11-21 | (G5) Snapshot của starter có `invuln_ticks` không có trong PRD. | **Giả định:** giữ nguyên (trường thừa không ảnh hưởng), không có tác dụng ở Phase 1. | Long |
| 16 | 2026-11-21 | (P1) Mục "Mở rộng" không liệt kê mục nào cho Phase 1. | Không ảnh hưởng nhóm 3 người; hỏi giảng viên danh sách áp dụng ở phase nào. | Long (PO) hỏi giảng viên |
| 17 | 2026-11-21 | (P3) HUD cần "kho khả dụng" nhưng snapshot `stock` là tồn vật lý (gồm phần giữ). | **Quyết định:** snapshot giữ tồn vật lý theo mục D; UI tự tính khả dụng = `stock − Σ reserved`. | Long (Integrator) |
| 18 | 2026-11-21 | (P4) `money` / `earned` / `shift_earned` khác nhau thế nào ở Phase 1 (chưa có chi tiêu)? | **Giả định:** Phase 1 cả ba bằng nhau; khác biệt để dành cho phase sau. | Nhóm tự giả định |
| 19 | 2026-11-21 (P2) | `fish_initial` "là số 8" — 8 đàn đầu ca chọn thế nào? | **Giả định:** lặp 8 lần đúng thuật toán sinh cá (loài theo trọng số chuẩn hóa trên loài còn điểm cách mọi đàn > 1 m, chọn đều điểm, hướng theo seed), luồng RNG `fish_spawn`, id F1–F8. | Long |
| 20 | 2026-11-21 (P2) | "Hướng ban đầu theo seed" — góc liên tục hay rời rạc? | **Giả định:** góc đều trong [0, 360) độ, làm tròn 3 chữ số. | Long |
| 21 | 2026-11-21 (P2) | `attack`/`photo` khi chưa bật mở rộng: mã 2 hay bỏ qua? | **Quyết định:** theo mục 4.2 "mở rộng chưa bật thì bỏ qua" → nút hợp lệ, bị bỏ qua. Đã sửa test P1 (trước coi `attack` là nút lạ). | Long |

> **Cách làm khi chưa hỏi được Anh Năm:** làm trước phần PRD đã rõ; chỗ mơ hồ cài theo giả định trên, viết test ghi rõ "giả định #n", để dễ sửa khi có câu trả lời. Có trả lời thì cập nhật cột "Trả lời / giả định" và ghi giờ.
