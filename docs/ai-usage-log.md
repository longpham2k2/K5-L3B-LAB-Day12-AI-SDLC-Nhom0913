# Nhật ký dùng AI (theo phase và theo người)

| Phase | Người | Công cụ / model | Việc | Token / chi phí ước tính | Ghi chú (AI sai ở đâu?) |
|---|---|---|---|---|---|
| 1 | longpham2k2 | Claude Code (VS Code) · Claude Opus 5.5 | Đọc starter + tìm `TODO(nhóm)`, tóm tắt cấu trúc khung | _điền từ `/cost`_ | AI không đọc được PRD trên lab board (nội dung nạp từ DB của artifact, cần đăng nhập) → người phải copy PRD vào chat. Bản in PDF đầu tiên bị cắt ở mục F, AI phát hiện thiếu và yêu cầu phần còn lại thay vì đoán luật. |
| 1 | longpham2k2 | Claude Code · Claude Opus 5.5 | Đề xuất chia 4 lát cho 3 người, điền `TEAM.md`, `docs/plan/phase-1.md`, `team_size` | (gộp ở trên) | Đề xuất hợp lý nhưng nhóm 3 người làm `tools/check_team.py` báo không đạt (cần 4–6) → đã ghi câu hỏi vào `docs/clarify.md`, người chịu trách nhiệm hỏi giảng viên. |
| 1 | longpham2k2 | Claude Code · Claude Opus 5.5 | Lát 1 gather (oxy, ngạt, Máu, ngất, dive/surface): viết test trước (`tests/test_gather_slice1.py`, 9 test) rồi code trong `chonoi/sim/gather.py` | (gộp ở trên) | Test viết trước, chạy đỏ rồi mới code; mỗi test trích câu PRD mục F bước 2. Người đọc lại diff trước khi commit. Không thấy lỗi luật. |
| 1 | longpham2k2 | Claude Code · Claude Opus 5.5 | Chép PRD-0 vào `docs/prd/phase-1.md`; chốt hợp đồng kho/sự kiện/giao diện UI (`docs/contracts/README.md`) | (gộp ở trên) | AI định dạng lại bảng/markdown; người kiểm nội dung khớp bản trên lab board. |
| 1 | longpham2k2 | Claude Code · Claude Opus 5.5 | Lát 2 gather (hái, bắt cá, `hold_full`, hồi bắt, bước cuối): 13 test trước (`tests/test_gather_slice2.py`) rồi code; chạy smoke hai tiến trình mục G | (gộp ở trên) | 9/13 test đỏ trước khi code (4 test "không có sự kiện" vốn đã xanh). Sau khi code: 54/54 test OK, smoke đúng `{"bong_sung":2,"ca_loc":1}` (`docs/proof/phase-1/`). |

## Cách nhóm dùng AI (thống nhất)

- Agent đọc `AGENTS.md`, `docs/prd/phase-<n>.md` và `docs/contracts/README.md` trước khi viết code.
- Test trước, code sau; mỗi test bám một câu cụ thể trong PRD. Không sửa test cho xanh khi luật sai.
- Người đọc lại diff và chạy `PYTHONPATH=tests:. python3 -m unittest discover -s tests -v` trước khi commit; lưu kết quả vào `docs/proof/`.
- Mỗi người tự ghi dòng của mình (handle, công cụ, việc, token, AI sai ở đâu).
