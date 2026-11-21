# Standup giữa phase (mỗi người một dòng, 2–3 phút)

| Phase | Người | Đã xong | Sắp làm | Vướng gì |
|---|---|---|---|---|
| 1 (phút 20) | `tran85122-afk` (Duy) | Đọc PRD-0 mục D/E/F, chốt hợp đồng `customer`/event với Huy & Long, viết 15 test Lát 4 (`tests/test_quan_slice4.py`) | Cài đặt Lát 4 trong `chonoi/sim/quan.py` và gộp với Lát 3 của Huy | Máy Windows thiếu alias `python3` → thêm fallback `sys.executable` trong `tests/helpers.py` |
| 1 (phút 40) | `tran85122-afk` (Duy) | Xong Lát 4 `sim/quan`, gộp sạch với Lát 3 (`62ebe41`), sửa HUD `chonoi/web/index.html` (`st.dish.dish_id`, kho khả dụng) + chụp `hud-quan.png` (77/77 test OK) | Hoàn thiện ma trận truy vết `docs/verification/phase-1.md` và báo Long gắn tag `phase-1` | Không còn vướng |
| 1 (phút 20) | `longpham2k2` (Long) | Lát 1 + Lát 2 `sim/gather` xong (54/54 test), chép PRD vào repo, chốt hợp đồng kho/sự kiện, smoke hai tiến trình đạt | Review Lát 3 của Huy, ghi các chỗ PRD mơ hồ vào `clarify.md` | Chưa liên lạc được Anh Năm → nhóm tự đặt giả định |
| 1 (phút 40) | `longpham2k2` (Long) | Review Lát 3 qua 3 vòng (event, `stock`, thứ tự bước, đóng ca); 17 giả định trong `clarify.md` | Review Lát 4 + HUD của Duy, gắn tag `phase-1` | Rủi ro `base_price` ở fixture `assigned` (mã 2) chưa sửa |
