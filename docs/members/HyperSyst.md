# HyperSyst — phản tư cá nhân (≤ 200 từ)

- Tôi làm logic Quán P1/P2 và chuyển kho Quán sang cá thể ở P3: hao `1/240`/tick, `spoiled`, giữ theo id tươi nhất và giữ lại khi ươn ([`9bb69d0`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/9bb69d0)). Tôi cũng rà đóng gói P4: README, CREDITS/LICENSE, artifact zip và hook pre-push.
- Tôi hỗ trợ tích hợp bằng cách đối chiếu event/snapshot Quán với PRD và test lại từ worktree sạch.
- AI từng báo xong P3 khi commit `8a0fbfc` chỉ có test. Tôi dùng `git show --stat`, thấy thiếu `quan.py`, rồi khôi phục và push commit đúng.
- Bài học: kết quả test chỉ đáng tin khi commit, diff staged và bản clone/package cùng chứa thay đổi; hook phải được version hóa, không chỉ ghi trong retro.
