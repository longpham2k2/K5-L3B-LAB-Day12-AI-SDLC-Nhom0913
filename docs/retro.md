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
## Phase 4 (cuối)
- **Rà lại hành động Phase 2** ("trước khi push phải chạy test trên bản sạch — hook `pre-push`, người nhận: Huy"): **chưa làm.** Không có hook nào trong `.git/hooks`, không có mục hook trong `AGENTS.md`. Hệ quả đo được: ở Phase 3 lại có một push thiếu `quan.py` ([`8a0fbfc`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/8a0fbfc), chỉ có file test) làm nhánh `p3` đỏ tới khi có [`9bb69d0`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/9bb69d0). Vì sao: mỗi phase quá ngắn, hành động không có hạn cụ thể và không ai nhắc ở standup. Điều đã giảm thiểu được: làm Phase 3 trên nhánh `p3` + chạy `tools/smoke_p3.sh` (140/140 test) trước khi gộp nên lỗi không chạm `main`.
- **Điều tốt:**
  - Chốt hợp đồng sớm ở mọi phase (`docs/contracts/README.md` §1–§6) → 3 người làm song song, tích hợp ít xung đột.
  - Test trước + review chéo bằng kịch bản thật bắt được lỗi trước tag (tên trường event P1, `base_price` đơn assigned, thiếu snapshot đổi pha P2, `test_p4_soak.py` lỗi `python3` trên Windows được sửa qua `helpers.contract_cmd`).
  - Bằng chứng chạy lại được bằng script & đo thật (`tools/smoke_p2.sh`, `tools/smoke_p3.sh`, `tools/package_release.sh`; benchmark `1280×720` đạt **119.95 FPS** / **1% low 89.69 FPS** / **load 1334.9 ms**; `soak 10 Ngày` **0** crash; **149/149** test xanh).
- **Điều tệ:**
  - Push thiếu file 3 lần (P2 ×2, P3 ×1); tag `phase-3` lần đầu trỏ nhầm commit Phase 2 (lệnh gộp/tag sai thứ tự) phải gắn lại.
  - Việc dồn không đều: `day`/HUD/bench rơi vào Duy ở P2 và P4.
- **Số liệu:** commit không tính merge từ đầu lab — longpham2k2 24 (tới `9bd0a95`), HyperSyst 14, tran85122-afk 9 (+ commit hoàn thiện P4) *(cộng với các commit starter của Hai Duong)*. Đọc code của nhau: Long review mọi push của Huy/Duy bằng `git show --stat` + chạy kịch bản headless; Duy review chéo gather/smoke/soak (xem `docs/members/`). Token theo người: không đo được (ghi `—` trong `docs/ai-usage-log.md`).
- **Một lần AI sai và cách nhóm phát hiện:**
  - Ở P3 (`Long`): test ngưỡng dùng `fresh = 30 + 2/120` không biểu diễn chính xác bằng float JSON nên ươn sớm 1 tick; phát hiện vì test đỏ ở biên, xác minh bằng tay với `Fraction`, sửa thành 30.5 (`docs/clarify.md` #26).
  - Ở P4 (`Duy`): nhãn `"⚠ Sắp giận!"` ban đầu đè `T1`/nhân vật và `bench.py` thiếu timeout >30s + kiểm `window.snap`; phát hiện khi đọc ảnh chụp `hud-hc-quan-alert.png` và chạy benchmark 30s thật.
- **Hành động tiếp theo:** cài hook `pre-push` chạy toàn bộ test (`contract_cmd` đa nền tảng) **ngay đầu buổi**, và đưa "hành động retro" thành một dòng có hạn trong plan của phase kế.
- **Nếu làm lại, đổi gì:** chia `day`/HUD cho 2 người từ đầu; luôn kiểm ảnh chụp UI sau mỗi sửa đổi, tạo tag sau khi `main` đã push và kiểm `git ls-remote` ngay.
