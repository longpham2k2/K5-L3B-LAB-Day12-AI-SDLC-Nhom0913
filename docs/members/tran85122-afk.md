# tran85122-afk — phản tư cá nhân (≤ 200 từ)

- **Tôi đã làm (kèm link commit):**
  - P1: Lát 4 `sim/quan` + 15 test ([`acb8f9e`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/acb8f9e)), HUD `index.html` + `hud-quan.png` ([`3fef940`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/3fef940)), kiểm chứng 77/77 test ([`16498e5`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/16498e5)).
  - P2: `--mode day`, `pause`, `live.py` + Menu/Shop/Summary/HUD ≥ 18px (`hud-day.png`, [`a94aae5`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/a94aae5)), sửa snapshot đổi pha & `clarify.md` #25 ([`06933fb`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/06933fb)), QA `AC-P2-10` (118/118 test).
- **Tôi đã review (kèm link):**
  - P1: Gather Lát 1–2 ([`ac00760`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/ac00760), [`01966ba`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/01966ba)) và tích hợp Quán Lát 3 ([`62ebe41`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/62ebe41)).
  - P2: đối chiếu §5 với nền v1.1, Gather v1.1 & smoke P2 ([`1d712ad`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/1d712ad), [`77df558`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/77df558), [`9ce0e2b`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/9ce0e2b)) và Quán/Shop ([`288f3bf`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/288f3bf)).
- **AI sai ở đâu và tôi phát hiện thế nào:**
  - Frontend đầu gửi sai hướng phím pha `quan` trong `--mode day`, và `run()` thiếu snapshot lúc đổi pha khi `snapshot_every` lớn — phát hiện qua kiểm thử trình duyệt thật và test `test_phase_change_writes_snapshot_with_phase_tick_zero`.
- **Điều tôi học được:**
  - Khóa chặt hợp đồng §5 và kiểm thử cả CLI lẫn trình duyệt giúp tích hợp 3 người trơn tru và tìm lỗi biên nhanh.
