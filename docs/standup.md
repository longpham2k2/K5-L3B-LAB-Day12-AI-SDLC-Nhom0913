# Standup giữa phase (mỗi người một dòng, 2–3 phút)

| Phase | Người | Đã xong | Sắp làm | Vướng gì |
|---|---|---|---|---|
| 1 (phút 20) | `tran85122-afk` (Duy) | Đọc PRD-0 mục D/E/F, chốt hợp đồng `customer`/event với Huy & Long, viết 15 test Lát 4 (`tests/test_quan_slice4.py`) | Cài đặt Lát 4 trong `chonoi/sim/quan.py` và gộp với Lát 3 của Huy | Máy Windows thiếu alias `python3` → thêm fallback `sys.executable` trong `tests/helpers.py` |
| 1 (phút 40) | `tran85122-afk` (Duy) | Xong Lát 4 `sim/quan`, gộp sạch với Lát 3 (`62ebe41`), sửa HUD `chonoi/web/index.html` (`st.dish.dish_id`, kho khả dụng) + chụp `hud-quan.png` (77/77 test OK) | Hoàn thiện ma trận truy vết `docs/verification/phase-1.md` và báo Long gắn tag `phase-1` | Không còn vướng |
