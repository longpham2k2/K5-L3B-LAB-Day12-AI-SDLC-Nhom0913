# Kế hoạch Phase 2 (≤ 1 trang) — TICKET-02, Test Contract v1.1

- **Mục tiêu:** số liệu chuẩn v1.1 (6 nguyên liệu, 6 món, 2 bếp/4 bàn); cá bơi/sinh; Cá Sấu, Máu, ngất; `--mode day` chạy trọn D1–D5 qua Shop; pause; HUD/menu. Regression P1 vẫn đạt với số mới. Tag `phase-2` trước 1:55.
- **Không làm mở rộng** (nhóm 3 người không bắt buộc) — dồn sức cho lõi.

## Việc / người / phụ thuộc

| ID | Việc | Người | Phụ thuộc | Trạng thái |
|---|---|---|---|---|
| AC-P2-01 | **Nền v1.1 (làm trước, phút 0–10):** `game.contract.json` 1.1 đủ khóa mục 4.1; `contract.py` kiểm 8 đàn / 3 loài / 3 loại nút; kho 6 nguyên liệu; `--mode day` + `--days` ở CLI; sửa test P1 dùng số cũ (ghi lý do) | Long | — | Xong (77/77 test; `docs/contracts/README.md` §5) |
| AC-P2-02 | Gather: N5/N6 kèo nèo, cá kèo; cá bơi (1.5 m/s, đổi hướng mỗi 120 bước, phản xạ mép), sinh cá mỗi 360 tick (`fish_spawned`), `age_ticks` | Long | AC-P2-01 | Xong (`tests/test_gather_fish_p2.py`, 10 test) |
| AC-P2-03 | Gather: Cá Sấu M1/M2 (patrol/chase/recoil), `monster_hit`, bất tử 90 tick, rơi floor(n/2) LIFO, `faint` cause monster; thứ tự bước mục 4.5 | Long | AC-P2-01 | Xong (`tests/test_gather_monsters_p2.py`, 13 test) |
| AC-P2-04 | Quán: B2, T2–T4, 6 món (test với số mới); tham số lọc menu theo kế hoạch ngày (`plan_dishes`) | Huy | AC-P2-01 | Xong (3 test AC; regression 117/117; `docs/proof/phase-2/test-p2-quan-shop.txt`) |
| AC-P2-05 | Shop: `ShopSim` — `buy` oxygen/hp, `bought`/`buy_failed` (funds/max_level/unknown), `shop_done`, tự đóng sau 600 tick, `shop_end` | Huy | AC-P2-01 | Xong (3 test AC; regression 117/117; `docs/proof/phase-2/test-p2-quan-shop.txt`) |
| AC-P2-06 | `--mode day`: chuỗi `day_start → day_plan → phase_start`, gather → quan → shop trong một tiến trình, giữ tiền/earned/uy tín/cấp qua Ngày, `active_upgrades` từ Ngày kế, `days_completed`, end `days_complete`, trường `day` trên event/snapshot | Duy | AC-P2-01; dùng sim của AC-P2-02..05 qua giao diện ở `docs/contracts/README.md` §5 | Xong (runner/scenario/headless nối GatherSim v1.1 + QuanSim(plan_dishes, carry) + ShopSim thật qua §5; Session("shop") cho test AC-P2-05) — `docs/proof/phase-2/test-day-and-pause.txt` |
| AC-P2-07 | Pause ở cả 3 mode (`paused`/`resumed`, chỉ tăng tick ngoài, `state:"paused"`) | Duy | AC-P2-06 | Xong (pause cả 3 mode; `docs/proof/phase-2/test-day-and-pause.txt`) |
| AC-P2-08 | Live/HUD: menu chính, DayIntro, EveningIntro, DayResult, Shop, Summary, pause; HUD mới (cần lấy/đã lấy, độ sâu, "Thủy quái!", "Hết hơi!", chữ ≥ 18 px) | Duy | AC-P2-06 | Xong (`chonoi/live.py`, `chonoi/web/index.html`, `docs/proof/phase-2/test-live-p2.txt`, `hud-day.png`) |
| AC-P2-09 | Smoke tích hợp phút 20 (`docs/proof/phase-2/integration.*`), smoke `day --days 1` và nhiều Ngày, regression P1 | Long | AC-P2-02..06 | Xong (`bash tools/smoke_p2.sh` → `docs/proof/phase-2/integration.txt`, `day-smoke.txt`, `regression-p1.txt`; 11/11 kiểm tra đạt) |
| AC-P2-10 | `docs/verification/phase-2.md`, retro P1+P2, clarify, ai-usage-log, standup | Duy (QA) + mọi người | Tất cả | |

## Mốc trong phase

- Phút 0–10: Long đẩy nền v1.1 (AC-P2-01). Huy/Duy đọc `docs/prd/phase-2.md` + `docs/contracts/README.md` §5, viết test trước cho lát của mình.
- Phút 20: smoke tích hợp + standup; điều người xong sang lát trễ (ưu tiên AC-P2-06 day).
- Phút 35–45: smoke day, regression P1, verification, tag (Long).
- Phút 45–50: retro.

## Rủi ro

- **Ít người, nhiều việc** (4 lát gợi ý cho 3 người) → bỏ mở rộng; HUD/menu (AC-P2-08) làm sau cùng, tối thiểu đủ mục PRD.
- **`day` chạm khung chung** (`runner.py`, `headless.py`) → chỉ Duy sửa runner; Long sửa CLI ở AC-P2-01; báo nhóm trước khi sửa (AGENTS.md).
- **Test P1 dùng số cũ** (6 đàn, `day` → mã 2) → sửa kèm lý do trong commit, không sửa test cho xanh khi luật sai.
- **Thứ tự bước gather mới** (quái trước tương tác, bắt cá theo vị trí cá trước khi bơi) dễ sai → test bám đúng câu mục 4.5.
