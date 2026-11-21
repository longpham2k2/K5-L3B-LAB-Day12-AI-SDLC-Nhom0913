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

## Phase 3 (nhanh)
- Điều tốt:
  - Cô lập lần đổi schema kho cá thể v1.2 trên nhánh tích hợp `p3` (giữ `main` yên ở `phase-2`) và đẩy adapter `chonoi/items.py` + `docs/contracts/README.md` §6 trước giúp Lặn, Quán và `day`/HUD ghép nối theo đúng thứ tự.
  - Dùng `fractions.Fraction` cho hao hụt độ tươi (`-1/120` giỏ, `-1/240` kho quán) và `floor(price × mean(fresh) / 100)` tránh hoàn toàn sai số dấu phẩy động tại ngưỡng `< 30` và làm tròn giá.
  - Tự động hóa kiểm tra chéo bằng `tools/smoke_p3.sh` (tự chọn `os.pathsep` cho Linux/Windows): 4/4 kiểm tra file, 7/7 kiểm tra `day` và **140/140** test (`regression-p1-p2.txt`) đều xanh.
- Điều chưa tốt:
  - Đổi schema từ kho đếm sang mảng cá thể làm nhiều fixture P1–P2 vỡ đồng loạt (`test_quan_slice4.py`, `test_day_and_pause.py`, `test_p2_quan_shop.py`, `test_live.py`, `test_python_starter_units.py`); phần migrate & smoke cuối chỉ khép vòng được sau khi `AC-P3-03` lên nhánh `p3`.
- 1 hành động rút ra từ lần đổi kho:
  - Mọi lần đổi schema dữ liệu lõi cần khóa helper test dùng chung (`items(...)`), nhánh tích hợp riêng và chạy toàn bộ `discover -s tests` trước khi hợp nhất `p3 -> main`.

## Phase 4 (cuối)
- Rà lại hành động Phase 2: đã làm chưa? vì sao?
- Điều tốt / điều tệ:
- Số liệu: số commit theo người, cách đọc code của nhau, token theo người:
- Một lần AI sai và cách nhóm phát hiện:
- Nếu làm lại, đổi gì:
