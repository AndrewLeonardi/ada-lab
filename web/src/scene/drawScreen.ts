import type { ScreenContent } from "../world/protocol";

// Draws what a monitor in the room is showing onto a canvas (used as an emissive texture).
// `t` is seconds since the content appeared: it drives typing, scrolling and blinking.

const FONT = "Nunito, system-ui, sans-serif";
const MONO = "'JetBrains Mono', ui-monospace, monospace";

function wrap(g: CanvasRenderingContext2D, text: string, maxW: number): string[] {
  const out: string[] = [];
  for (const para of text.split("\n")) {
    let line = "";
    for (const word of para.split(/\s+/)) {
      const test = line ? line + " " + word : word;
      if (g.measureText(test).width > maxW && line) {
        out.push(line);
        line = word;
      } else line = test;
    }
    out.push(line);
  }
  return out;
}

const imageCache = new Map<string, HTMLImageElement>();
function getImage(src: string): HTMLImageElement | null {
  let img = imageCache.get(src);
  if (!img) {
    img = new Image();
    img.src = src;
    imageCache.set(src, img);
  }
  return img.complete && img.naturalWidth ? img : null;
}

function chrome(g: CanvasRenderingContext2D, W: number, title: string, url?: string) {
  g.fillStyle = "#1b2b33";
  g.fillRect(0, 0, W, 34);
  ["#ff6b5e", "#ffbd3e", "#3fcf5c"].forEach((c, i) => {
    g.fillStyle = c;
    g.beginPath();
    g.arc(16 + i * 16, 17, 5, 0, Math.PI * 2);
    g.fill();
  });
  g.fillStyle = "#cfe3ea";
  g.font = `600 14px ${FONT}`;
  g.fillText(title.slice(0, 48), 70, 22);
  if (url) {
    g.fillStyle = "#0f1c22";
    g.fillRect(10, 40, W - 20, 24);
    g.fillStyle = "#7fa9b6";
    g.font = `12px ${MONO}`;
    g.fillText(url.slice(0, 70), 18, 57);
  }
}

export function drawScreen(g: CanvasRenderingContext2D, W: number, H: number, c: ScreenContent, t: number) {
  g.fillStyle = "#0f1e24";
  g.fillRect(0, 0, W, H);
  const blink = Math.floor(t * 2) % 2 === 0;

  if (c.app === "idle") {
    const grd = g.createLinearGradient(0, 0, W, H);
    grd.addColorStop(0, "#14303a");
    grd.addColorStop(1, "#0b1a20");
    g.fillStyle = grd;
    g.fillRect(0, 0, W, H);
    g.fillStyle = "#6fb3b0";
    g.font = `800 30px ${FONT}`;
    g.textAlign = "center";
    g.fillText(c.title ?? "", W / 2, H / 2);
    g.textAlign = "left";
    return;
  }

  if (c.app === "search") {
    chrome(g, W, c.source, c.url);
    const typed = c.query.slice(0, Math.max(0, Math.floor(t * 18)));
    g.fillStyle = "#e8f3f5";
    g.fillRect(16, 76, W - 32, 36);
    g.fillStyle = "#1b2b33";
    g.font = `600 17px ${FONT}`;
    g.fillText(typed + (typed.length < c.query.length || blink ? "|" : ""), 26, 100);
    if (typed.length >= c.query.length) {
      let y = 138;
      const shown = Math.min(c.results.length, Math.floor((t - c.query.length / 18) * 2.5));
      for (const r of c.results.slice(0, shown)) {
        g.fillStyle = "#8fd3ff";
        g.font = `700 15px ${FONT}`;
        for (const l of wrap(g, r.title, W - 40).slice(0, 2)) {
          g.fillText(l, 20, y);
          y += 19;
        }
        g.fillStyle = "#8aa3ab";
        g.font = `12px ${FONT}`;
        g.fillText(r.meta.slice(0, 80), 20, y);
        y += 26;
        if (y > H - 20) break;
      }
    }
    return;
  }

  if (c.app === "paper") {
    chrome(g, W, c.source, c.url);
    g.fillStyle = "#f2f6f7";
    g.fillRect(12, 72, W - 24, H - 84);
    g.fillStyle = "#1f2d35";
    g.font = `800 17px ${FONT}`;
    let y = 98;
    for (const l of wrap(g, c.title, W - 52).slice(0, 3)) {
      g.fillText(l, 26, y);
      y += 21;
    }
    g.fillStyle = "#56707a";
    g.font = `12px ${FONT}`;
    g.fillText(`${c.authors} · ${c.journal}`.slice(0, 84), 26, y + 2);
    y += 22;
    g.font = `14px ${FONT}`;
    g.fillStyle = "#2c3e46";
    const lines = wrap(g, c.body, W - 52);
    const scroll = Math.max(0, (t - 3) * 9); // she reads: the page scrolls slowly
    g.save();
    g.beginPath();
    g.rect(12, y, W - 24, H - y - 14);
    g.clip();
    lines.forEach((l, i) => g.fillText(l, 26, y + 16 + i * 19 - scroll));
    g.restore();
    return;
  }

  if (c.app === "notebook") {
    chrome(g, W, c.title);
    let y = 54;
    const shown = Math.floor(t * 1.2) + 1;
    for (const cell of c.cells.slice(0, shown)) {
      const isCode = cell.kind === "code";
      g.font = isCode ? `13px ${MONO}` : `14px ${FONT}`;
      const lines = wrap(g, cell.text, W - 56);
      const h = lines.length * 18 + 12;
      g.fillStyle = isCode ? "#16272e" : cell.kind === "output" ? "#0f1e24" : "#1d3038";
      g.fillRect(14, y - 14, W - 28, h);
      g.fillStyle = isCode ? "#9fe0a8" : cell.kind === "output" ? "#e7d38a" : "#cfe3ea";
      lines.forEach((l, i) => g.fillText(l, 24, y + 4 + i * 18));
      y += h + 8;
      if (y > H) break;
    }
    return;
  }

  if (c.app === "trial") {
    chrome(g, W, c.title);
    g.fillStyle = "#cfe3ea";
    g.font = `600 14px ${FONT}`;
    g.fillText(c.status, 18, 60);
    g.fillStyle = "#24414a";
    g.fillRect(18, 70, W - 36, 10);
    g.fillStyle = "#5fd3a5";
    g.fillRect(18, 70, (W - 36) * Math.min(1, c.progress), 10);
    // Kaplan-Meier axes
    const x0 = 50, y0 = H - 40, x1 = W - 24, y1 = 100;
    g.strokeStyle = "#4d6b74";
    g.lineWidth = 1.5;
    g.beginPath(); g.moveTo(x0, y1); g.lineTo(x0, y0); g.lineTo(x1, y0); g.stroke();
    g.fillStyle = "#7d9aa3";
    g.font = `11px ${FONT}`;
    g.fillText("survival", 8, y1 + 8);
    g.fillText("months", x1 - 40, y0 + 18);
    const maxM = Math.max(1, ...((c.arms ?? []).flatMap((a) => a.curve.map((p) => p[0]))));
    (c.arms ?? []).forEach((arm, ai) => {
      g.strokeStyle = arm.color;
      g.lineWidth = 3;
      g.beginPath();
      const reveal = Math.min(1, t / 4); // curves draw in
      let prevY = y1;
      arm.curve.forEach(([m, s], i) => {
        if (m / maxM > reveal) return;
        const X = x0 + (m / maxM) * (x1 - x0);
        const Y = y0 - s * (y0 - y1);
        if (i === 0) g.moveTo(X, Y);
        else { g.lineTo(X, prevY); g.lineTo(X, Y); }
        prevY = Y;
      });
      g.stroke();
      g.fillStyle = arm.color;
      g.font = `700 12px ${FONT}`;
      g.fillText(`${arm.name}${arm.median ? "  median " + arm.median : ""}`, x0 + 10, y1 + 16 + ai * 16);
    });
    return;
  }

  if (c.app === "tissue") {
    chrome(g, W, c.title);
    const img = getImage(c.image);
    if (img) {
      const s = Math.min((W - 20) / img.naturalWidth, (H - 70) / img.naturalHeight);
      const w = img.naturalWidth * s, h = img.naturalHeight * s;
      g.drawImage(img, (W - w) / 2, 40, w, h);
    }
    g.fillStyle = "#cfe3ea";
    g.font = `12px ${FONT}`;
    g.fillText(c.caption.slice(0, 90), 14, H - 12);
  }
}
