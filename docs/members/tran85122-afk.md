# tran85122-afk — phản tư cá nhân (≤ 200 từ)

- **Tôi đã làm (kèm link commit):**
  - Cài đặt Lát 4 `sim/quan` (`cook_started`, `dish_ready`, `dish_picked`, `served`, `paid`, tính boa & uy tín bằng `Decimal`, đóng ca `closing`/`quan_end`, kiểm mâu thuẫn scenario mức luật) và 15 test hộp đen/unit trong `tests/test_quan_slice4.py`, gộp Lát 3 + Lát 4 ([`acb8f9e`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/acb8f9e)).
  - Hoàn thiện HUD `chonoi/web/index.html` (`st.dish.dish_id`, kho khả dụng `stock − Σ reserved`, trạng thái bếp/tay/ngạt/ăn), thêm test trong `tests/test_live.py` và chụp bằng chứng `docs/proof/phase-1/hud-quan.png` ([`3fef940`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/3fef940)).
  - Tổng hợp ma trận truy vết `docs/verification/phase-1.md` và bằng chứng `docs/proof/phase-1/all-tests.txt` (77/77 test OK).
- **Tôi đã review (kèm link):**
  - Đọc và đối chiếu Lát 1 & Lát 2 `sim/gather` của Long ([`ac00760`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/ac00760), [`01966ba`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/01966ba)).
  - Review và tích hợp Lát 3 `sim/quan` & `chonoi/scenario.py` của Huy ([`7e426f8`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/7e426f8), [`62ebe41`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/62ebe41)).
- **AI sai ở đâu và tôi phát hiện thế nào:**
  - Bản đầu của `test_quan_slice4.py` do AI sinh có 2 frame trùng `tick` (`pick_tick + 1`), phát hiện ngay ở bước chạy test đỏ (thoát mã 2). Khi rebase với Lát 3, phát hiện `chonoi/scenario.py` dòng 191 kiểm `reserved != recipe` cho mọi khách `waiting` làm lỗi đơn `assigned`, sửa lại bằng điều kiện `order_status == "reserved"`.
- **Điều tôi học được:**
  - Chốt hợp đồng tích hợp (`docs/contracts/README.md`) và viết test hộp đen trước giúp gộp 2 lát cùng sửa `quan.py` rất nhanh mà không vỡ luật.
