# tran85122-afk — phản tư cá nhân (≤ 200 từ)

- **Tôi đã làm (kèm link commit/bằng chứng):**
  - P1: Quán Lát 4 ([`acb8f9e`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/acb8f9e)), HUD ([`3fef940`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/3fef940)), QA P1 ([`16498e5`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/16498e5)).
  - P2: `--mode day`, `pause`, HUD ≥18px ([`a94aae5`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/a94aae5)), snapshot đổi pha ([`06933fb`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/06933fb)), `AC-P2-10`.
  - P3: `AC-P3-04/05/06` — giá theo tươi, `day`/Shop cá thể, HUD tươi, `smoke_p3.sh`, `verification` ([`871c67a`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/871c67a), [`270489f`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/270489f)).
  - P4 (`AC-P4-02/03/06`): `chonoi/bench.py` (`bench.json`: 119.95 FPS), 3 cảnh báo + tương phản cao `[C]` (`hud-hc-*.png`), `docs/verification/phase-4.md`.
- **Đã review / giúp ai:**
  - Review Lặn/Quán P1–P3 ([`ac00760`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/ac00760), [`62ebe41`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/62ebe41), [`df09aea`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/df09aea), [`9bb69d0`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/9bb69d0)); sửa `test_p4_soak.py` chạy được trên Windows giúp Long ([`c610b83`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/c610b83)) qua `contract_cmd`.
- **AI sai ở đâu và tôi phát hiện thế nào:**
  - Nhãn `"⚠ Sắp giận!"` ban đầu đè `T1` rồi nhân vật; `bench.py` thiếu timeout >30s và kiểm `window.snap` trả `undefined` — phát hiện khi đọc ảnh chụp và chạy thật 30s.
- **Điều tôi học được:**
  - Đo trực tiếp trên trình duyệt thật, kiểm ảnh và chạy trọn `discover -s tests` xuyên nền tảng tránh lỗi ẩn trước khi phát hành.
