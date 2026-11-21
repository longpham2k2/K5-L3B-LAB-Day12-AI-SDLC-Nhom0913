# Kế hoạch Phase 4 — TICKET-04 Phát hành v1.0.0, Test Contract v1.3 (30 phút, tag + Release trước 3:00)

**Làm thẳng trên `main`** (thay đổi nhỏ, tách file, không đổi schema). **Không làm mở rộng** (leaderboard, phụ đề SFX).

| ID | Việc | Vai | Người | Trạng thái |
|---|---|---|---|---|
| AC-P4-01 | `contract_version: "1.3"`, `bench_cmd` + `soak_cmd` ở gốc manifest; `soak_cmd` (`python3 -m chonoi.soak`): 10 Ngày một tiến trình, D1–D5 lặp ở Ngày 6–10, `soak.json` + test | Integrator | Long | Xong (`tests/test_p4_soak.py` 5 test; `docs/proof/phase-4/soak.json` 10/10 Ngày, 0 crash) |
| AC-P4-02 | `bench_cmd` (`python3 -m chonoi.bench`): render cảnh sáng chuẩn 1280×720 trên trình duyệt, seed 42, nóng 3 s + đo 30 s, `bench.json` 5 trường; lưu artifact `docs/proof/phase-4/bench.json` | Bench/QA | Duy | |
| AC-P4-03 | Ba cảnh báo có chữ/biểu tượng (thủy quái gần, oxy sắp hết, khách sắp giận) + chế độ tương phản cao; chơi thử, chụp ảnh `docs/proof/phase-4/` | Bench/QA | Duy | |
| AC-P4-04 | Đóng gói: thử clone sạch (≤ 3 lệnh macOS/Linux), README (môi trường, điều khiển, test, headless, bench, soak), rà `CREDITS.md`/`LICENSE`, bản đóng gói `.zip` | Đóng gói | Huy | |
| AC-P4-05 | Retro P4 (rà hành động P2 — hook `pre-push`), phản tư `docs/members/` đủ 3 người, standup, ai-usage-log, clarify | Điều phối retro | Huy + mọi người | |
| AC-P4-06 | `docs/verification/phase-4.md`, regression P1–P3 | Bench/QA | Duy | |
| AC-P4-07 | Release notes, rà `CHANGELOG.md` theo phase, tag `phase-4` + GitHub Release v1.0.0 (đính kèm .zip) cùng commit trên `main` | Release | Long | |

**Mốc:** phút 0–15 song song 01–04 · phút 15–25 retro, phản tư, verification · phút 25–30 kiểm commit/artifact → tag + Release (Long).

**Rủi ro:** bench cần trình duyệt thật (không có thì lệnh báo lỗi rõ, mã 1); soak Ngày 6–10 cần lặp kế hoạch D1–D5 (runner đang tra `plans[day]`); thời gian 30 phút → bỏ mở rộng.
