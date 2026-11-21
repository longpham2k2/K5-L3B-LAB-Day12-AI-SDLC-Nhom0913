// Sprite CC0 "Fish Pack 2.0" (chỉ rong + đá đáy sông; cá/người/Cá Sấu/hoa vẽ tay ở art.js) — Kenney (www.kenney.nl), CC0 1.0 (xem chonoi/web/assets/LICENSE-kenney-fish-pack.txt).
// Chỉ dùng ở cửa sổ chơi (chonoi.live). Headless/test không tải file này. Ảnh chưa tải xong -> trả false để
// index.html vẽ hình khối như cũ (fallback), nên thiếu ảnh không làm hỏng game.
(function () {
  const load = (name) => { const img = new Image(); img.src = "/assets/" + name + ".png"; return img; };
    const BED = [load("seaweed_a"), load("rock_a"), load("seaweed_b")];
  const ready = (img) => img && img.complete && img.naturalWidth > 0;
  window.SPRITES_OFF = false; // chế độ tương phản cao có thể đặt true để chỉ vẽ hình khối

  // Rong và đá trang trí ở đáy sông (cố định theo vị trí, không ảnh hưởng gameplay).
  window.drawSeabed = function (ctx, sx, sy, X, D, s) {
    if (window.SPRITES_OFF || !BED.every(ready)) return;
    const size = 3 * s;
    for (let x = 4, i = 0; x < X; x += 9, i++) {
      ctx.drawImage(BED[i % BED.length], sx(x) - size / 2, sy(D) - size, size, size);
    }
  };
})();
