// Hình vẽ tay bằng canvas — tự vẽ bởi nhóm Nhom0913 (không dùng tài sản ngoài). Theo PRD-0 mục 3 "Cảm giác và
// phong cách": Út Sen mặc áo bà ba, buộc khăn rằn, kính lặn tự chế, giỏ lưới; cá linh / cá lóc / cá kèo; Cá Sấu
// Năm Chèo; bông điên điển, bông súng, kèo nèo. Chỉ dùng ở cửa sổ chơi; headless/test không tải file này.
// Mỗi hàm trả true khi đã vẽ, để index.html giữ hình khối cũ làm dự phòng. window.SPRITES_OFF = true -> tắt (tương phản cao).
(function () {
  const off = () => window.SPRITES_OFF === true;
  const P = Math.PI;

  function ell(ctx, x, y, rx, ry, rot, fill, stroke, lw) {
    ctx.beginPath(); ctx.ellipse(x, y, rx, ry, rot || 0, 0, 2 * P);
    if (fill) { ctx.fillStyle = fill; ctx.fill(); }
    if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = lw || 1; ctx.stroke(); }
  }

  // Khăn rằn: ô caro đen trắng trong một dải.
  function khanRan(ctx, x, y, w, h) {
    const n = 6, cw = w / n;
    for (let i = 0; i < n; i++) for (let j = 0; j < 2; j++) {
      ctx.fillStyle = (i + j) % 2 ? "#1b1b1b" : "#f2f2f2";
      ctx.fillRect(x + i * cw, y + j * (h / 2), cw + 0.5, h / 2 + 0.5);
    }
  }

  // ----- Út Sen (mặt cắt ngang: nằm bơi khi lặn, đứng khi ở mặt nước) -----
  function utSenSide(ctx, x, y, s, headingDeg, underwater) {
    if (off()) return false;
    const a = ((headingDeg || 0) * P) / 180, faceLeft = Math.cos(a) < 0;
    ctx.save(); ctx.translate(x, y);
    if (underwater) { ctx.rotate(faceLeft ? a - P : a); } else { ctx.rotate(0); }
    if (faceLeft) ctx.scale(-1, 1);
    const u = s * 0.55;
    if (underwater) {
      // chân đập nước
      ctx.strokeStyle = "#3b2a1a"; ctx.lineWidth = Math.max(2, u * 0.35); ctx.lineCap = "round";
      ctx.beginPath(); ctx.moveTo(-1.2 * u, 0.15 * u); ctx.lineTo(-2.3 * u, -0.25 * u); ctx.moveTo(-1.2 * u, 0.3 * u); ctx.lineTo(-2.3 * u, 0.55 * u); ctx.stroke();
      // thân áo bà ba (chàm) + quần đen
      ell(ctx, -0.3 * u, 0.15 * u, 1.25 * u, 0.55 * u, 0, "#2f4b8f", "#1d2f5c", 1.5);
      ell(ctx, -1.15 * u, 0.2 * u, 0.5 * u, 0.42 * u, 0, "#1a1a1a");
      // giỏ lưới sau lưng
      ctx.strokeStyle = "#c9a464"; ctx.lineWidth = 1;
      for (let i = -2; i <= 2; i++) { ctx.beginPath(); ctx.moveTo(-0.9 * u + i * 0.18 * u, -0.45 * u); ctx.lineTo(-0.6 * u + i * 0.18 * u, -0.95 * u); ctx.stroke(); }
      ell(ctx, -0.45 * u, -0.7 * u, 0.55 * u, 0.32 * u, 0, null, "#c9a464", 1.5);
      // tay vươn tới trước
      ctx.strokeStyle = "#d9a476"; ctx.lineWidth = Math.max(2, u * 0.3);
      ctx.beginPath(); ctx.moveTo(0.6 * u, 0.05 * u); ctx.lineTo(1.6 * u, -0.2 * u); ctx.stroke();
      // đầu + khăn rằn + kính lặn
      ell(ctx, 1.15 * u, 0.0, 0.48 * u, 0.48 * u, 0, "#e3b48a", "#8a5a3a", 1);
      khanRan(ctx, 0.75 * u, -0.48 * u, 0.85 * u, 0.3 * u);
      ell(ctx, 1.38 * u, -0.02 * u, 0.2 * u, 0.16 * u, 0, "#9fe3ff", "#333", 2);
      ctx.strokeStyle = "#333"; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(1.18 * u, -0.02 * u); ctx.lineTo(0.75 * u, -0.08 * u); ctx.stroke();
      // bọt khí
      ctx.fillStyle = "rgba(255,255,255,.7)";
      ell(ctx, 1.75 * u, -0.6 * u, 0.09 * u, 0.09 * u, 0, "rgba(255,255,255,.75)");
      ell(ctx, 1.95 * u, -0.95 * u, 0.06 * u, 0.06 * u, 0, "rgba(255,255,255,.6)");
    } else {
      // đứng trên mặt nước: nửa người trên mặt nước
      ell(ctx, 0, 0.05 * u, 0.75 * u, 0.95 * u, 0, "#2f4b8f", "#1d2f5c", 1.5);
      ctx.fillStyle = "#e9e3d0"; ctx.fillRect(-0.06 * u, -0.6 * u, 0.12 * u, 0.9 * u); // nẹp áo bà ba
      ell(ctx, 0, -1.15 * u, 0.48 * u, 0.48 * u, 0, "#e3b48a", "#8a5a3a", 1);
      khanRan(ctx, -0.5 * u, -1.68 * u, 1.0 * u, 0.32 * u);
      ell(ctx, 0.18 * u, -1.15 * u, 0.17 * u, 0.13 * u, 0, "#9fe3ff", "#333", 2);
      ctx.strokeStyle = "#c9a464"; ctx.lineWidth = 1.5; ell(ctx, -0.75 * u, 0.15 * u, 0.4 * u, 0.5 * u, 0, null, "#c9a464", 1.5);
      ctx.strokeStyle = "rgba(255,255,255,.8)"; ctx.lineWidth = 1.5; // gợn nước
      ctx.beginPath(); ctx.moveTo(-1.1 * u, 0.55 * u); ctx.quadraticCurveTo(0, 0.35 * u, 1.1 * u, 0.55 * u); ctx.stroke();
    }
    ctx.restore();
    return true;
  }

  // ----- Út Sen nhìn từ trên xuống (nhà bè buổi tối) -----
  function utSenTop(ctx, x, y, s) {
    if (off()) return false;
    const u = s * 0.55;
    ctx.save(); ctx.translate(x, y);
    ell(ctx, 0, 0.25 * u, 0.85 * u, 0.6 * u, 0, "#2f4b8f", "#1d2f5c", 1.5);   // vai áo bà ba
    ell(ctx, 0, -0.15 * u, 0.5 * u, 0.5 * u, 0, "#2b1d14");                  // tóc
    khanRan(ctx, -0.5 * u, -0.32 * u, 1.0 * u, 0.28 * u);                    // khăn rằn
    ctx.restore();
    return true;
  }

  // ----- Cá (vẽ hướng sang phải rồi xoay theo heading) -----
  const FISH = {
    ca_linh: { len: 1.0, h: 0.42, body: "#c9d3dc", belly: "#eef3f7", fin: "#9aa8b4", spot: "#3a4652" },
    ca_loc: { len: 1.7, h: 0.4, body: "#4d5a3a", belly: "#b9b48a", fin: "#38412a", spot: "#2a301e" },
    ca_keo: { len: 1.4, h: 0.3, body: "#8a6a45", belly: "#c8ae86", fin: "#6b5033", spot: "#4a3824" },
  };
  function fish(ctx, f, x, y, s) {
    if (off()) return false;
    const c = FISH[f.kind];
    if (!c) return false;
    const a = ((f.heading_deg || 0) * P) / 180;
    const L = c.len * s, H = c.h * s;
    ctx.save(); ctx.translate(x, y);
    if (Math.cos(a) < 0) { ctx.rotate(a - P); ctx.scale(-1, 1); } else { ctx.rotate(a); }
    // đuôi
    ctx.fillStyle = c.fin; ctx.beginPath(); ctx.moveTo(-L * 0.85, 0); ctx.lineTo(-L * 1.3, -H * 0.9); ctx.lineTo(-L * 1.2, 0); ctx.lineTo(-L * 1.3, H * 0.9); ctx.closePath(); ctx.fill();
    // vây lưng
    ctx.beginPath(); ctx.moveTo(-L * 0.5, -H * 0.8); ctx.quadraticCurveTo(0, -H * 1.6, L * 0.35, -H * 0.85); ctx.closePath(); ctx.fill();
    // thân + bụng
    ell(ctx, 0, 0, L, H, 0, c.body, "rgba(0,0,0,.35)", 1);
    ell(ctx, 0.05 * L, H * 0.35, L * 0.8, H * 0.45, 0, c.belly);
    if (f.kind === "ca_loc") { // đốm loang cá lóc
      ctx.fillStyle = c.spot;
      for (let i = -3; i <= 2; i++) ell(ctx, i * L * 0.25, -H * 0.15 * (i % 2 ? 1 : -1), L * 0.09, H * 0.22, 0, c.spot);
    } else if (f.kind === "ca_linh") { // đốm sau mang cá linh
      ell(ctx, L * 0.35, -H * 0.05, L * 0.08, H * 0.25, 0, c.spot);
    } else { // sọc mảnh cá kèo
      ctx.strokeStyle = c.spot; ctx.lineWidth = 1;
      for (let i = -2; i <= 2; i++) { ctx.beginPath(); ctx.moveTo(i * L * 0.25, -H * 0.7); ctx.lineTo(i * L * 0.25 - L * 0.05, H * 0.2); ctx.stroke(); }
    }
    // mắt (cá kèo mắt lồi trên đỉnh đầu)
    const ey = f.kind === "ca_keo" ? -H * 0.85 : -H * 0.2, er = f.kind === "ca_keo" ? H * 0.32 : H * 0.22;
    ell(ctx, L * 0.7, ey, er, er, 0, "#fff", "#222", 1);
    ell(ctx, L * 0.74, ey, er * 0.5, er * 0.5, 0, "#111");
    ctx.restore();
    return true;
  }

  // ----- Cá Sấu Năm Chèo -----
  function caSau(ctx, m, x, y, s, playerX) {
    if (off()) return false;
    const faceLeft = playerX !== undefined ? playerX < x : false;
    const body = m.state === "chase" ? "#7a3b2e" : m.state === "recoil" ? "#7d8a8f" : "#4f6b34";
    const back = m.state === "chase" ? "#5a271d" : m.state === "recoil" ? "#5f6a6e" : "#36491f";
    const u = s * 0.7;
    ctx.save(); ctx.translate(x, y); if (faceLeft) ctx.scale(-1, 1);
    // đuôi cong
    ctx.fillStyle = body; ctx.beginPath(); ctx.moveTo(-1.2 * u, -0.25 * u); ctx.quadraticCurveTo(-2.6 * u, -0.1 * u, -3.0 * u, -0.6 * u);
    ctx.quadraticCurveTo(-2.4 * u, 0.35 * u, -1.2 * u, 0.3 * u); ctx.closePath(); ctx.fill();
    // chân
    ell(ctx, -0.6 * u, 0.5 * u, 0.25 * u, 0.15 * u, 0.4, back); ell(ctx, 0.9 * u, 0.5 * u, 0.25 * u, 0.15 * u, -0.4, back);
    // thân
    ell(ctx, 0, 0, 1.5 * u, 0.5 * u, 0, body, "rgba(0,0,0,.4)", 1.5);
    // gai lưng (năm chèo)
    ctx.fillStyle = back;
    for (let i = -4; i <= 3; i++) { ctx.beginPath(); ctx.moveTo(i * 0.32 * u, -0.42 * u); ctx.lineTo(i * 0.32 * u + 0.12 * u, -0.72 * u); ctx.lineTo(i * 0.32 * u + 0.24 * u, -0.42 * u); ctx.fill(); }
    // mõm dài + răng
    ctx.fillStyle = body; ctx.beginPath(); ctx.moveTo(1.2 * u, -0.35 * u); ctx.lineTo(2.6 * u, -0.12 * u); ctx.lineTo(2.6 * u, 0.12 * u); ctx.lineTo(1.2 * u, 0.35 * u); ctx.closePath(); ctx.fill();
    ctx.fillStyle = "#fffbe8";
    for (let i = 0; i < 5; i++) { const tx = 1.45 * u + i * 0.25 * u; ctx.beginPath(); ctx.moveTo(tx, 0.08 * u); ctx.lineTo(tx + 0.08 * u, 0.24 * u); ctx.lineTo(tx + 0.16 * u, 0.08 * u); ctx.fill(); }
    ctx.strokeStyle = "rgba(0,0,0,.5)"; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(1.2 * u, 0.05 * u); ctx.lineTo(2.6 * u, 0.02 * u); ctx.stroke();
    // mắt (đỏ khi đuổi)
    ell(ctx, 1.15 * u, -0.42 * u, 0.17 * u, 0.15 * u, 0, "#f4e27a", "#222", 1);
    ell(ctx, 1.18 * u, -0.42 * u, 0.06 * u, 0.12 * u, 0, m.state === "chase" ? "#d11" : "#111");
    ctx.restore();
    return true;
  }

  // ----- Nút hái trên mặt nước -----
  function node(ctx, n, x, y, s) {
    if (off()) return false;
    const ready = n.ready !== false, u = s * 0.6;
    ctx.save(); ctx.translate(x, y); ctx.globalAlpha = ready ? 1 : 0.35;
    if (n.kind === "bong_sung") {
      ell(ctx, 0, 0.05 * u, 1.3 * u, 0.4 * u, 0, "#3f8f3a", "#2c6a28", 1); // lá súng
      for (let i = 0; i < 6; i++) { const t = (i / 6) * P - P; ctx.save(); ctx.rotate(t * 0.5); ell(ctx, 0, -0.55 * u, 0.22 * u, 0.55 * u, 0, "#b07ad8", "#7d4aa8", 1); ctx.restore(); }
      ell(ctx, 0, -0.45 * u, 0.18 * u, 0.18 * u, 0, "#f6d74a");
    } else if (n.kind === "bong_dien_dien") {
      ctx.strokeStyle = "#4b7a2a"; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(0, 0.2 * u); ctx.lineTo(0, -0.9 * u); ctx.stroke();
      for (let i = 0; i < 7; i++) { const yy = -0.9 * u + i * 0.18 * u, xx = (i % 2 ? 1 : -1) * 0.3 * u; ell(ctx, xx, yy, 0.22 * u, 0.15 * u, 0, "#f5c518", "#c99a05", 1); }
      ell(ctx, 0, 0.15 * u, 0.9 * u, 0.18 * u, 0, "rgba(60,110,40,.8)");
    } else { // kèo nèo: lá xanh hình tim trên cọng dài
      ctx.strokeStyle = "#3e7d33"; ctx.lineWidth = 2;
      for (let i = -1; i <= 1; i++) { ctx.beginPath(); ctx.moveTo(0, 0.2 * u); ctx.quadraticCurveTo(i * 0.4 * u, -0.5 * u, i * 0.6 * u, -1.0 * u); ctx.stroke();
        ell(ctx, i * 0.6 * u, -1.05 * u, 0.32 * u, 0.24 * u, i * 0.4, "#5fb04a", "#3e7d33", 1); }
      ell(ctx, 0.1 * u, -0.35 * u, 0.12 * u, 0.12 * u, 0, "#f3f0d8");
    }
    ctx.restore();
    return true;
  }

  window.ART = { utSenSide, utSenTop, fish, caSau, node };
})();
