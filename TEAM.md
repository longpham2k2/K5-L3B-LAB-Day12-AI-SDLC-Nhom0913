# TEAM

**Tên nhóm:** Nhom0913  **Số người:** 3 (khớp `team_size` trong `game.contract.json`)

| Thành viên | GitHub handle | Module chính | Vai quy trình | Người dự phòng cho |
|---|---|---|---|---|
| Phạm Ngọc Long | longpham2k2 | `sim/gather` (lát 1, 2) | PO, Integrator | Nguyễn Công Huy |
| Nguyễn Công Huy | HyperSyst | `sim/quan` (lát 3) | Scrum/Release | Trần Đức Duy |
| Trần Đức Duy | tran85122-afk | `sim/quan` (lát 4), `client/ui` (HUD) | QA lead | Phạm Ngọc Long |

**Vai quy trình:** PO (đầu mối hỏi giảng viên, giữ `docs/clarify.md`) · Integrator (giữ `docs/contracts/`, gắn tag) · QA lead · Scrum/Release. Có thể kiêm.

## Thỏa thuận làm việc nhóm (điền trong 15 phút kickoff, ≤ 10 dòng)

- Kênh liên lạc: nhóm chat chung của 3 người; việc gấp thì nói trực tiếp.
- Khi bất đồng về thiết kế: mỗi bên nói 2 phút, không xong thì Integrator (Long) quyết và ghi lý do vào `docs/clarify.md`.
- Khi ai đó trễ hoặc vướng quá 10 phút: báo ngay trong kênh, người dự phòng vào hỗ trợ hoặc nhận việc.
- Giờ standup giữa phase: phút 20 và phút 40 của mỗi phase, 2–3 phút (đã xong / sắp làm / đang vướng); Huy điều phối.
- Cách đọc code của nhau: mỗi người đọc lát của người mình dự phòng trước khi gộp; hai lát `sim/quan` (Huy, Duy) thống nhất trường khách/đơn trước khi code.
- Cách làm việc với Git: nhánh ngắn theo lát, chạy test xanh rồi gộp vào `main`; chỉ Long (Integrator) gắn tag `phase-n` sau khi Duy (QA) xác nhận smoke hai tiến trình.
