# Kế hoạch Phase 4 — TICKET-04 Phát hành v1.0.0, Test Contract v1.3 (30 phút, tag + Release trước 3:00)

**Làm thẳng trên `main`** (thay đổi nhỏ, tách file, không đổi schema). **Không làm mở rộng** (leaderboard, phụ đề SFX).

| ID | Việc | Vai | Người | Trạng thái |
|---|---|---|---|---|
| AC-P4-01 | `contract_version: "1.3"`, `bench_cmd` + `soak_cmd` ở gốc manifest; `soak_cmd` (`python3 -m chonoi.soak`): 10 Ngày một tiến trình, D1–D5 lặp ở Ngày 6–10, `soak.json` + test | Integrator | Long | Xong (`tests/test_p4_soak.py` 5 test; `docs/proof/phase-4/soak.json` 10/10 Ngày, 0 crash) |
| AC-P4-02 | `bench_cmd` (`python3 -m chonoi.bench`): render cảnh sáng chuẩn 1280×720 trên trình duyệt, seed 42, nóng 3 s + đo 30 s, `bench.json` 5 trường; lưu artifact `docs/proof/phase-4/bench.json` | Bench/QA | Duy | Xong (`chonoi/bench.py`, `tests/test_p4_bench.py` 3/3 OK, `docs/proof/phase-4/bench.json`: avg 119.95 FPS, 1% low 89.69 FPS, load 1334.9 ms) |
| AC-P4-03 | Ba cảnh báo có chữ/biểu tượng (thủy quái gần, oxy sắp hết, khách sắp giận) + chế độ tương phản cao; chơi thử, chụp ảnh `docs/proof/phase-4/` | Bench/QA | Duy | Xong (`chonoi/web/index.html`, `tests/test_live.py` 6/6 OK, `docs/proof/phase-4/hud-hc-gather-alerts.png` & `hud-hc-quan-alert.png`) |
| AC-P4-04 | Đóng gói: thử clone sạch (≤ 3 lệnh macOS/Linux), README (môi trường, điều khiển, test, headless, bench, soak), rà `CREDITS.md`/`LICENSE`, bản đóng gói `.zip` | Đóng gói | Huy | Xong (`docs/proof/phase-4/clean-clone.txt`, `dist/chonoi-v1.0.0.zip`) |
| AC-P4-05 | Retro P4 (rà hành động P2 — hook `pre-push`), phản tư `docs/members/` đủ 3 người, standup, ai-usage-log, clarify | Điều phối retro | Huy + mọi người | Xong (`.githooks/pre-push`, `docs/retro.md`, `docs/members/`, standup/log/clarify) |
| AC-P4-06 | `docs/verification/phase-4.md`, regression P1–P3 | Bench/QA | Duy | Xong (`tests/helpers.py::contract_cmd`, sửa `test_p4_soak.py`, regression P1–P3 `141/141` OK, toàn suite `149/149` OK, `docs/verification/phase-4.md`) |
| AC-P4-07 | Release notes, rà `CHANGELOG.md` theo phase, tag `phase-4` + GitHub Release v1.0.0 (đính kèm .zip) cùng commit trên `main` | Release | Long | Xong (tag `phase-4` = Release `v1.0.0` = `f575d8d`; https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/releases/tag/v1.0.0) |

**Mốc:** phút 0–15 song song 01–04 · phút 15–25 retro, phản tư, verification · phút 25–30 kiểm commit/artifact → tag + Release (Long).

**Rủi ro:** bench cần trình duyệt thật (không có thì lệnh báo lỗi rõ, mã 1); soak Ngày 6–10 cần lặp kế hoạch D1–D5 (runner đang tra `plans[day]`); thời gian 30 phút → bỏ mở rộng.
