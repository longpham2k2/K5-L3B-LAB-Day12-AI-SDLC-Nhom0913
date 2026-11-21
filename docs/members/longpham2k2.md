# longpham2k2 — phản tư cá nhân (≤ 200 từ)

- **Tôi đã làm (kèm link commit):**
  - Lát 1 `sim/gather`: oxy, ngạt, Máu, ngất, dive/surface + 9 test ([`ac00760`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/ac00760)).
  - Lát 2: hái, bắt cá, `hold_full`, hồi bắt + 13 test, smoke hai tiến trình ([`01966ba`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/01966ba)).
  - PO/Integrator: kickoff `TEAM.md` + kế hoạch ([`a52fd29`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/a52fd29)), chép PRD + hợp đồng tích hợp ([`d288605`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/d288605)), 17 giả định trong `clarify.md` ([`3d10c7d`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/3d10c7d)).
- **Tôi đã review (kèm link):**
  - Lát 3 của Huy qua 3 vòng: tên trường event, `stock` vật lý, thứ tự bước, đóng ca ([`7e426f8`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/7e426f8) → [`62ebe41`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/62ebe41)).
  - Lát 4 + HUD của Duy: chạy trọn một vòng quán khớp dòng end ví dụ PRD (72 / 3.2 / 372); phát hiện fixture `assigned` có `base_price` bị mã 2 ([`acb8f9e`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/acb8f9e), [`3fef940`](https://github.com/longpham2k2/K5-L3B-LAB-Day12-AI-SDLC-Nhom0913/commit/3fef940)).
- **AI sai ở đâu và tôi phát hiện thế nào:**
  - AI không đọc được PRD trên lab board; bản PDF bị cắt — AI báo thiếu thay vì đoán, tôi copy toàn văn.
  - Bản đầu lát 3 có test xanh nhưng sai PRD (tên trường event) — tôi dùng AI đối chiếu từng dòng với mục E và chạy kịch bản thật mới thấy.
- **Điều tôi học được:**
  - Test xanh chưa đủ: phải bám câu chữ PRD và chạy kịch bản thật.
