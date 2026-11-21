# Retro nhóm

## Phase 2 (nhanh)
- Điều tốt:
  - Chốt sớm giao diện sim ↔ `day` (`docs/contracts/README.md` §5) ở phút 0–10 → 3 người làm song song gather / quán+Shop / `day`, `day` nối được sim thật ngay lần đầu.
  - Test trước ở mọi lát (gather cá 10 test, Cá Sấu 13, quán+Shop 6, day+pause ~10); review chéo trước tag bắt được lỗi thật: thiếu snapshot đổi pha, áp nâng cấp hai lần.
  - `tools/smoke_p2.sh` chạy lại toàn bộ bằng chứng bằng 1 lệnh, đóng dấu commit (11/11 kiểm tra, 118/118 test). Một Ngày headless 0.42 s (giới hạn 20 s).
- Điều tệ:
  - **Push thiếu file làm đỏ `main` hai lần** (`37af687`, `ddad94f`): test xanh trên máy nhưng đỏ trên repo, file proof còn ghi "OK" không khớp commit.
  - **Stash/pop làm rơi phần đã stage** hai lần → commit `9ce0e2b` thiếu `AGENTS.md` và plan, phải commit bù.
  - Nhóm 3 người cho 4 lát: `day` + pause + HUD dồn hết vào Duy, là rủi ro lớn nhất với hạn 1:55.
- 1 hành động cho Phase 3:
  - **Trước khi push phải chạy test trên bản sạch**: thêm hook `pre-push` chạy `PYTHONPATH=tests:. python3 -m unittest discover -s tests` (ghi vào mục Skills/hooks của `AGENTS.md`). **Người nhận: Huy.** Kiểm ở retro cuối: Phase 3 không có lần `main` đỏ nào do thiếu file.

## Phase 4 (cuối)
- Rà lại hành động Phase 2: đã làm chưa? vì sao?
- Điều tốt / điều tệ:
- Số liệu: số commit theo người, cách đọc code của nhau, token theo người:
- Một lần AI sai và cách nhóm phát hiện:
- Nếu làm lại, đổi gì:
