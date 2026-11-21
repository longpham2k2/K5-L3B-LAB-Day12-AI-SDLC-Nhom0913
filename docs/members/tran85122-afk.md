# tran85122-afk — phản tư cá nhân (≤ 200 từ)

- **Tôi đã làm (kèm link commit):**
  - P1: Quán Lát 4 ([`acb8f9e`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/acb8f9e)), HUD ([`3fef940`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/3fef940)), QA 77/77 test ([`16498e5`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/16498e5)).
  - P2: `--mode day`, `pause`, HUD ≥18px ([`a94aae5`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/a94aae5)), snapshot đổi pha ([`06933fb`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/06933fb)), QA `AC-P2-10` (118/118 test).
  - P3 (`p3`): `AC-P3-04/05/06` — nấu chốt giá theo tươi (`Fraction`), bàn giao cá thể & `ShopSim` v1.2, HUD `%`/`ươn` (`hud-fresh.png`), `smoke_p3.sh`, `CHANGELOG.md`, `verification/phase-3.md` (140/140 test).
- **Tôi đã review (kèm link):**
  - P1: Gather ([`ac00760`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/ac00760), [`01966ba`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/01966ba)) & Quán ([`62ebe41`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/62ebe41)).
  - P2: Gather & smoke ([`1d712ad`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/1d712ad), [`77df558`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/77df558), [`9ce0e2b`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/9ce0e2b)), Quán/Shop ([`288f3bf`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/288f3bf)).
  - P3: Adapter `items.py` & §6 ([`df09aea`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/df09aea)), Gather tươi ([`ae298f5`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/ae298f5)), Quán cá thể ([`9bb69d0`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/9bb69d0)).
- **AI sai ở đâu và tôi phát hiện thế nào:**
  - HUD P2 sai phím Quán & thiếu snapshot đổi pha; ở P3 `smoke_p3.sh` ban đầu lỗi `PYTHONPATH` trên Windows và điều kiện `spoiled` Ngày 2 — phát hiện qua kiểm thử trình duyệt và chạy smoke lặp lại.
- **Điều tôi học được:**
  - Khóa `Fraction`, hợp đồng §5–§6 và script smoke cross-platform giúp đổi schema lớn trên `p3` mà `main` vẫn xanh.
