# HyperSyst — phản tư cá nhân (≤ 200 từ)

- **Tôi đã làm (kèm link commit):**
  - Làm Lát 3 `sim/quan`: khách đến theo lịch, chọn món còn nguyên liệu, giữ chỗ `reserved`, kiên nhẫn, `customer_left`, `no_dish` và trạng thái `unfulfillable`; viết 7 test tại `tests/test_quan_slice3.py` ([`7e426f8`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/7e426f8), [`62ebe41`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/62ebe41)).
  - Cập nhật hướng dẫn README và bằng chứng cho AC-P1-03/AC-P1-09.
- **Tôi đã review (kèm link):**
  - Đối chiếu trường khách/đơn, event và thứ tự bước của Lát 3 với `docs/contracts/README.md` và PRD trước khi sửa vòng cuối ([`62ebe41`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/62ebe41)).
- **AI sai ở đâu và tôi phát hiện thế nào:**
  - Bản đầu có test xanh nhưng snapshot xử lý sai nguyên liệu đã giữ chỗ, event có trường thừa và thứ tự khách rời chưa đúng. Tôi đối chiếu từng payload với PRD, thêm test cho closing, cấp phát theo `(order_tick, table_id)` và fixture không đủ kho.
- **Điều tôi học được:**
  - Test đơn vị xanh chưa đủ; phải kiểm hợp đồng liên module, thứ tự event và trạng thái kho quan sát được.
