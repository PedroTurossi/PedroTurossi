/**
 * Terminal chrome: title bar, powerline prompt, tmux status bar
 * and screen effects (glow, scanlines, vignette).
 */
import { len, n2 } from './svg.mjs';

/** Powerline segments. direction "right" grows rightwards from `col`;
 *  "left" ends at `col` and grows leftwards. */
export function powerline(c, col, row, segments, direction = 'right') {
  const y0 = n2(c.top(row) + 3);
  const h = n2(c.lh - 6);
  const widths = segments.map((s) => len(s.text) + 2);
  let out = '';

  if (direction === 'right') {
    let x = col;
    segments.forEach((seg, i) => {
      const start = i === 0 ? x : x - 1;            // covers the previous arrow cell
      const w = widths[i] + (i === 0 ? 0 : 1);
      out += `<rect x="${c.X(start)}" y="${y0}" width="${n2(w * c.cw)}" height="${h}" fill="${seg.bg}"/>`;
      if (i > 0) out += arrowRight(c, x - 1, y0, h, segments[i - 1].bg);
      out += c.text(x + 1, row, seg.text, seg.fg, { weight: seg.bold ? 700 : undefined });
      x += widths[i] + 1;
    });
    out += arrowRight(c, x - 1, y0, h, segments.at(-1).bg);
    return { svg: out, end: x };
  }

  // layout: [arrow0][seg0][arrow1][seg1]... ending at `col`
  const total = widths.reduce((a, b) => a + b, 0) + segments.length;
  const start = col - total;
  let x = start;
  const arrows = [];
  segments.forEach((seg, i) => {
    arrows.push([x, seg.bg]);
    const segStart = x + 1;
    const cover = widths[i] + (i < segments.length - 1 ? 1 : 0);   // covers the next arrow
    out += `<rect x="${c.X(segStart)}" y="${y0}" width="${n2(cover * c.cw)}" height="${h}" fill="${seg.bg}"/>`;
    out += c.text(segStart + 1, row, seg.text, seg.fg, { weight: seg.bold ? 700 : undefined });
    x = segStart + widths[i];
  });
  for (const [cell, color] of arrows) out += arrowLeft(c, cell + 1, y0, h, color);
  return { svg: out, start };
}

function arrowRight(c, col, y0, h, color) {
  const x = c.X(col);
  return `<polygon points="${x},${y0} ${n2(x + c.cw)},${n2(y0 + h / 2)} ${x},${n2(y0 + h)}" fill="${color}"/>`;
}

function arrowLeft(c, col, y0, h, color) {
  const x = c.X(col);
  return `<polygon points="${x},${y0} ${n2(x - c.cw)},${n2(y0 + h / 2)} ${x},${n2(y0 + h)}" fill="${color}"/>`;
}

/** Full prompt: user, directory, clock on the right and a typed command. */
export function prompt(c, { cfg, row, dir, clock, command, time }) {
  const T = c.T;
  const left = powerline(c, 0, row, [
    { text: `${cfg.prompt.user}@${cfg.prompt.host}`, fg: T.background, bg: T.accent, bold: true },
    { text: dir, fg: T.text, bg: T.border },
  ]);
  const right = clock ? powerline(c, c.cols, row, [{ text: clock, fg: T.soft, bg: T.raised }], 'left').svg : '';
  const base = c.glow(left.svg) + right;

  if (!command) return { svg: c.reveal(base, time), cmdCol: left.end + 1, end: time };

  const col = left.end + 1;
  const start = time + 0.3 * c.k;
  const typing = c.typed(col, row, command, T.bright, start, 0.05 * c.k, { weight: 700 });
  let cursor = '';
  if (c.animate) {
    const values = Array.from({ length: len(command) + 1 }, (_, i) => c.X(col + i)).join(';');
    cursor = `<rect x="${c.X(col)}" y="${n2(c.top(row) + 2)}" width="${n2(c.cw)}" height="${n2(c.lh - 4)}" fill="${T.cursor}">` +
      `<animate attributeName="x" values="${values}" begin="${c.at(start)}" dur="${c.at(len(command) * 0.05 * c.k)}" calcMode="discrete" fill="freeze"/>` +
      `<set attributeName="visibility" to="hidden" begin="${c.at(typing.end + 0.15 * c.k)}" fill="freeze"/></rect>`;
  }
  return { svg: c.reveal(base + cursor, time) + typing.svg, cmdCol: col, end: typing.end + 0.25 * c.k };
}

/** tmux status bar; the active window changes as the animation progresses. */
export function tmuxBar(c, { cfg, row, S, windows, sync, repos }) {
  const T = c.T;
  const y = c.top(row);
  let out = `<rect x="0" y="${y}" width="${c.width}" height="${c.lh}" fill="${T.raised}"/>`;

  const session = powerline(c, 0, row, [{ text: cfg.prompt.host, fg: T.background, bg: T.ok, bold: true }]);
  out += session.svg;

  let col = session.end + 1;
  windows.forEach((win, i) => {
    const label = `${i}:${win.name}`;
    const w = len(label) + 2;
    const active =
      `<rect x="${c.X(col)}" y="${n2(y + 3)}" width="${n2(w * c.cw)}" height="${n2(c.lh - 6)}" fill="${T.accent}"/>` +
      c.text(col + 1, row, `${label}*`, T.background, { weight: 700 });
    const idle = c.text(col + 1, row, label, T.soft);
    if (win.from === null) out += idle;
    else {
      out += c.during(idle, 0, win.from) + c.during(active, win.from, win.to);
      if (win.to !== Infinity) out += c.during(idle, win.to, Infinity);
    }
    col += w + 1;
  });

  out += powerline(c, c.cols, row, [
    { text: `${repos} ${S.tmux.repos}`, fg: T.soft, bg: T.border },
    { text: sync, fg: T.text, bg: T.faint },
    { text: cfg.username, fg: T.background, bg: T.prompt, bold: true },
  ], 'left').svg;
  return out;
}

export function titleBar(c, { cfg, W }) {
  const T = c.T;
  const cy = c.titleH / 2;
  const dots = [T.error, T.accent, T.ok]
    .map((color, i) => `<circle cx="${22 + i * 20}" cy="${cy}" r="6" fill="${color}"/>`).join('');
  const title = `${cfg.prompt.user}@${cfg.prompt.host}: ~`;
  return `<rect width="${W}" height="${c.titleH}" fill="${T.surface}"/>` +
    `<line x1="0" y1="${c.titleH - 0.5}" x2="${W}" y2="${c.titleH - 0.5}" stroke="${T.raised}"/>` + dots +
    c.glyphs(W / 2, cy + 4.5, title, T.soft, { size: 13, anchor: 'middle', weight: 700 });
}

export function effectDefs(effects) {
  let defs = '';
  if (effects.glow) {
    defs += '<filter id="glow" x="-5%" y="-20%" width="110%" height="140%">' +
      '<feGaussianBlur in="SourceGraphic" stdDeviation="2.2" result="blur"/>' +
      '<feComponentTransfer in="blur" result="soft"><feFuncA type="linear" slope="0.55"/></feComponentTransfer>' +
      '<feMerge><feMergeNode in="soft"/><feMergeNode in="SourceGraphic"/></feMerge></filter>';
  }
  if (effects.scanlines) {
    defs += '<pattern id="scan" width="6" height="3" patternUnits="userSpaceOnUse"><rect width="6" height="1" fill="#000" fill-opacity="0.16"/></pattern>';
  }
  if (effects.vignette) {
    defs += '<radialGradient id="vignette" cx="50%" cy="50%" r="75%">' +
      '<stop offset="55%" stop-color="#000" stop-opacity="0"/><stop offset="100%" stop-color="#000" stop-opacity="0.38"/></radialGradient>';
  }
  return defs;
}

export function effectOverlays(effects, W, H) {
  let out = '';
  if (effects.scanlines) out += `<rect width="${W}" height="${H}" fill="url(#scan)" pointer-events="none"/>`;
  if (effects.vignette) out += `<rect width="${W}" height="${H}" fill="url(#vignette)" pointer-events="none"/>`;
  return out;
}
