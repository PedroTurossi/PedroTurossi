/**
 * Projects as TUI panes (2 per row). Each pane has its path on the top border,
 * a name and description, and a terminal "app" running below.
 *
 * Built-in apps: rhythm, pipeline, homelab, open. A list of ASCII lines also works.
 */
import { len, n2, pad, wrap } from './svg.mjs';

/* ───────────────────────────── helpers ─────────────────────────────── */

function rng(seed) {
  let s = seed >>> 0;
  return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 2 ** 32; };
}

const SPARK = '▁▂▃▄▅▆▇█';

function sparkSeries(seed, base, spread, length) {
  const rand = rng(seed);
  let level = base;
  return Array.from({ length }, () => {
    level = Math.max(0, Math.min(7, level + Math.round((rand() - 0.5) * spread)));
    if (rand() < 0.15) level = Math.max(0, Math.min(7, base + Math.round((rand() - 0.5) * spread * 2)));
    return SPARK[level];
  }).join('');
}

/** Discrete loop on an attribute. */
const loop = (c, attr, values, time, dur, extra = '') =>
  `<animate attributeName="${attr}" values="${values}" begin="${c.at(time)}" dur="${c.at(dur)}" calcMode="discrete" repeatCount="indefinite"${extra}/>`;

/* ───────────────────────────── apps ───────────────────────────── */

/** Rhythm game: 9 lanes, notes falling to the strike line, keys A S D F G H J K L. */
function rhythm(c, ctx, a, time) {
  const { T, k } = c;
  const P = T.palette;
  const S = ctx.S.apps.rhythm;
  const lanes = 9;
  const tw = lanes * 4 + 1;
  const ox = a.col + Math.floor((a.w - tw) / 2);
  const laneColors = [P.green, P.red, P.yellow, P.blue, P.orange, P.purple, P.aqua, P.yellow, P.green];
  const keys = 'ASDFGHJKL';
  const hw = { first: a.row + 1, last: a.row + 5, strike: a.row + 6 };
  const rows = [];

  rows.push(
    c.spans(a.col, a.row, [[S.score, T.muted, { weight: 700 }], [' 0048210', P.yellow, { weight: 700 }]]) +
    c.spans(a.col + a.w - len(S.combo) - 4, a.row, [[S.combo, T.muted, { weight: 700 }], [' x12', P.orange, { weight: 700 }]]),
  );

  const lane = (i) => ox + i * 4 + 1;
  let tint = '';
  for (let i = 0; i < lanes; i++) {
    tint += `<rect x="${c.X(lane(i))}" y="${c.top(hw.first)}" width="${n2(3 * c.cw)}" height="${n2(6 * c.lh)}" fill="${laneColors[i]}" fill-opacity="0.08"/>`;
  }
  const sep = Array.from({ length: tw }, (_, i) => (i % 4 === 0 ? (i === 0 || i === tw - 1 ? '┃' : '│') : ' ')).join('');
  for (let r = hw.first; r <= hw.last; r++) rows.push((r === hw.first ? tint : '') + c.tall(ox, r, sep, T.faint));
  rows.push(c.tall(ox, hw.strike, `╞${Array.from({ length: lanes }, () => '═══').join('╪')}╡`, T.soft));

  // keys
  let keyRow = '';
  for (let i = 0; i < lanes; i++) keyRow += c.text(lane(i) + 1, a.row + 7, keys[i], laneColors[i], { weight: 700 });
  rows.push(keyRow);

  // song progress: the elapsed clock and the bar share the same steps, so they stay in sync
  const barCells = a.w - 14;
  const bar = '━'.repeat(barCells);
  const songSeconds = 187;
  const clockAt = (i) => {
    const secs = Math.round((i / barCells) * songSeconds);
    return `${Math.floor(secs / 60)}:${String(secs % 60).padStart(2, '0')}`;
  };
  const staticStep = Math.floor(barCells * 0.45);
  rows.push(
    c.text(a.col, a.row + 8, '▶', P.green) +
    (c.animate ? '' : c.text(a.col + 2, a.row + 8, clockAt(staticStep), T.soft)) +
    c.text(a.col + 7, a.row + 8, bar, T.border) +
    c.text(a.col + 7 + barCells + 2, a.row + 8, clockAt(barCells), T.soft),
  );

  // animations
  const step = 0.2 * k;
  const period = 16;
  const chart = [[4, 0], [2, 2], [6, 2], [0, 4], [8, 6], [3, 8], [5, 8], [1, 10], [7, 12], [4, 13], [2, 14]];
  let overlay = '';

  if (c.animate) {
    const hiddenY = c.tallY(a.row - 3);
    const ys = [];
    for (let r = hw.first; r <= hw.strike; r++) ys.push(c.tallY(r));
    while (ys.length < period) ys.push(hiddenY);
    let notes = '';
    let flashes = '';
    chart.forEach(([ln, offset], n) => {
      const begin = time + offset * step;
      notes += c.glyphs(c.X(lane(ln)), hiddenY, '▄▄▄', laneColors[ln], { size: c.lh / 1.32 + 0.15, squeeze: true, seal: true })
        .replace('</text>', `${loop(c, 'y', ys.join(';'), begin, period * step)}</text>`);
      const hit = begin + 5 * step;
      const keyX = c.X(lane(ln));
      flashes +=
        `<rect x="${keyX}" y="${n2(c.top(a.row + 7) + 2)}" width="${n2(3 * c.cw)}" height="${n2(c.lh - 4)}" fill="${laneColors[ln]}" opacity="0">` +
        `<animate attributeName="opacity" values="1;0" keyTimes="0;0.08" begin="${c.at(hit)}" dur="${c.at(period * step)}" calcMode="discrete" repeatCount="indefinite"/></rect>` +
        `<g opacity="0">${c.text(lane(ln) + 1, a.row + 7, keys[ln], T.background, { weight: 700 })}` +
        `<animate attributeName="opacity" values="1;0" keyTimes="0;0.08" begin="${c.at(hit)}" dur="${c.at(period * step)}" calcMode="discrete" repeatCount="indefinite"/></g>`;
      if (n === 0) {
        flashes += `<g opacity="0">${c.text(a.col + Math.floor((a.w - len(S.hit)) / 2), a.row, S.hit, P.aqua, { weight: 700 })}` +
          `<animate attributeName="opacity" values="1;0" keyTimes="0;0.2" begin="${c.at(hit)}" dur="${c.at(period * step)}" calcMode="discrete" repeatCount="indefinite"/></g>`;
      }
    });
    overlay += c.clipWindow(ox, hw.first, tw, 6, c.glow(notes)) + flashes;

    // song bar advancing in a loop
    const songDur = barCells * 0.6;
    const id = c.id('song');
    const x0 = c.X(a.col + 7);
    const widths = Array.from({ length: barCells + 1 }, (_, i) => n2(i * c.cw)).join(';');
    c.defs.push(`<clipPath id="${id}"><rect x="${x0}" y="${c.top(a.row + 8)}" height="${c.lh}" width="0">${loop(c, 'width', widths, time, songDur)}</rect></clipPath>`);
    overlay += `<g clip-path="url(#${id})">${c.text(a.col + 7, a.row + 8, bar, P.yellow)}</g>`;

    // elapsed clock: a strip of every "m:ss" value, slid 4 cells per step inside a 4-cell window
    const strip = Array.from({ length: barCells + 1 }, (_, i) => clockAt(i)).join('');
    const clockCol = a.col + 2;
    const xs = Array.from({ length: barCells + 1 }, (_, i) => n2(c.X(clockCol) - i * 4 * c.cw)).join(';');
    const clock = c.text(clockCol, a.row + 8, strip, T.soft)
      .replace('</text>', `${loop(c, 'x', xs, time, songDur)}</text>`);
    overlay += c.clipWindow(clockCol, a.row + 8, 4, 1, clock);
  } else {
    let notes = '';
    chart.slice(0, 7).forEach(([ln, offset]) => {
      notes += c.tall(lane(ln), hw.first + (offset % 5), '▄▄▄', laneColors[ln], { seal: true });
    });
    overlay += notes + c.text(a.col + 7, a.row + 8, bar.slice(0, staticStep), P.yellow);
  }

  return { rows, overlay };
}

/** htop-style production panel: orders, stages, progress and a scrolling log. */
function pipeline(c, ctx, a, time) {
  const { T, k } = c;
  const P = T.palette;
  const S = ctx.S.apps.pipeline;
  const rows = [];
  const cols = { id: a.col + 1, stage: a.col + 10, bar: a.col + 24, pct: a.col + 35, icon: a.col + a.w - 2 };

  rows.push(
    c.bg(a.col, a.row, a.w, T.raised) +
    c.text(cols.id, a.row, S.headers[0], T.accent, { weight: 700 }) +
    c.text(cols.stage, a.row, S.headers[1], T.accent, { weight: 700 }) +
    c.text(cols.bar, a.row, S.headers[2], T.accent, { weight: 700 }),
  );

  const orders = [
    { id: 'OP-0917', progress: 1, color: P.green, state: 'done' },
    { id: 'OP-0918', progress: 0.76, color: P.yellow, state: 'run' },
    { id: 'OP-0919', progress: 0.42, color: P.orange, state: 'run' },
    { id: 'OP-0920', progress: 0.08, color: P.purple, state: 'wait' },
  ];
  let overlay = '';
  orders.forEach((o, i) => {
    const r = a.row + 1 + i;
    const bar = c.blockBar(cols.bar, r, 10, o.progress, o.color, time + (0.3 + i * 0.1) * k, 0.06 * k);
    let icon;
    if (o.state === 'done') icon = c.text(cols.icon, r, '✓', P.green, { weight: 700 });
    else if (o.state === 'wait') icon = c.text(cols.icon, r, '·', T.faint, { weight: 700 });
    else icon = c.ticker(cols.icon, r, '▖▘▝▗▖', 1, P.yellow, 4, 0.15 + i * 0.03, time, { weight: 700 });
    rows.push(
      c.text(cols.id, r, o.id, T.muted) +
      c.text(cols.stage, r, S.stages[i], T.text) +
      bar.svg +
      c.text(cols.pct, r, `${Math.round(o.progress * 100)}%`.padStart(4), T.bright, { weight: 700 }) +
      icon,
    );
  });

  rows.push(c.tall(a.col, a.row + 5, '─'.repeat(a.w), T.border));

  // scrolling log
  const logs = S.log;
  const icons = [['✓', P.green], ['›', P.yellow], ['›', P.orange], ['↗', P.aqua]];
  const stamps = ['21:50:12', '21:50:31', '21:51:04', '21:51:47'];
  const logLine = (i, r) => {
    const n = i % logs.length;
    return c.spans(a.col + 1, r, [
      [stamps[n], T.faint], [' '], [icons[n][0], icons[n][1], { weight: 700 }], [' '],
      [logs[n][0], T.text], ['  '], [logs[n][1], T.muted],
    ].map(([s, color = T.text, o]) => [s, color, o]));
  };
  rows.push('');
  rows.push('');
  if (c.animate) {
    let strip = '';
    for (let i = 0; i < logs.length + 2; i++) strip += logLine(i, a.row + 6 + i);
    const values = Array.from({ length: logs.length }, (_, i) => `0,${n2(-i * c.lh)}`).join(';');
    overlay += c.clipWindow(a.col, a.row + 6, a.w, 2,
      `<g>${strip}<animateTransform attributeName="transform" type="translate" values="${values}" begin="${c.at(time + 0.8 * k)}" dur="${c.at(logs.length * 1.6)}" calcMode="discrete" repeatCount="indefinite"/></g>`);
  } else {
    overlay += logLine(0, a.row + 6) + logLine(1, a.row + 7);
  }

  const vol = c.blockBar(a.col + 16, a.row + 8, a.w - 25, 0.95, P.green, time + 0.4 * k, 0.03 * k);
  rows.push(
    c.spans(a.col + 1, a.row + 8, [[S.volumes, T.muted], [' 38/40', T.bright, { weight: 700 }]]) +
    vol.svg +
    c.spans(a.col + a.w - 7, a.row + 8, [['▲ ', P.aqua], [S.rate, P.aqua, { weight: 700 }]]),
  );
  return { rows, overlay, overlayRow: 6 };
}

/** Homelab: service status with CPU sparklines and a port scan. */
function homelab(c, ctx, a, time) {
  const { T, k } = c;
  const P = T.palette;
  const S = ctx.S.apps.homelab;
  const rows = [];
  const cols = { name: a.col + 1, state: a.col + 13, cpu: a.col + 24, mem: a.col + 37 };

  rows.push(
    c.spans(a.col, a.row, [['❯ ', P.aqua, { weight: 700 }], [S.command, T.bright, { weight: 700 }]]) +
    c.spans(a.col + a.w - 6, a.row, [['4/5 ', P.green, { weight: 700 }], ['●', P.green]]),
  );
  rows.push(S.headers.map((h, i) => c.text([cols.name, cols.state, cols.cpu, cols.mem][i], a.row + 1, h, T.muted, { weight: 700 })).join(''));

  const services = [
    { name: 'hypervisor', state: 'up', base: 3, spread: 3, mem: 0.62 },
    { name: 'firewall', state: 'up', base: 1, spread: 2, mem: 0.21 },
    { name: 'attack-box', state: 'scan', base: 5, spread: 4, mem: 0.78 },
    { name: 'gitea', state: 'up', base: 1, spread: 3, mem: 0.34 },
    { name: 'media', state: 'idle', base: 0, spread: 1, mem: 0.12 },
  ];
  const stateColor = { up: P.green, scan: P.orange, idle: T.muted };
  const window = cols.mem - cols.cpu - 2;
  const steps = 24;

  services.forEach((svc, i) => {
    const r = a.row + 2 + i;
    const color = stateColor[svc.state];
    const series = sparkSeries(i * 97 + 11, svc.base, svc.spread, steps);
    const spark = c.ticker(cols.cpu, r, series + series.slice(0, window), window, svc.state === 'idle' ? T.faint : svc.state === 'scan' ? P.orange : P.aqua, steps, 0.35 + i * 0.04, time + 0.2 * k);
    const dot = c.animate && svc.state !== 'idle'
      ? `<g>${c.text(cols.state, r, '●', color)}${loop(c, 'opacity', '1;0.35', time, svc.state === 'scan' ? 0.6 : 1.8)}</g>`
      : c.text(cols.state, r, '●', color);
    rows.push(
      c.text(cols.name, r, svc.name, T.text) + dot +
      c.text(cols.state + 2, r, S.states[svc.state], color) +
      spark +
      c.blockBar(cols.mem, r, 7, svc.mem, svc.mem > 0.7 ? P.red : P.blue, time + 0.3 * k, 0.05 * k).svg,
    );
  });

  rows.push(c.spans(a.col, a.row + 7, [['❯ ', P.aqua, { weight: 700 }], [S.scan, T.text]]));
  const ports = [['22', 'ssh'], ['53', 'dns'], ['443', 'https'], ['8080', 'http']];
  rows.push(c.spans(a.col + 2, a.row + 8, ports.flatMap(([port, name]) => [[port, P.aqua, { weight: 700 }], [`/${name}  `, T.muted]])));
  return { rows, overlay: '' };
}

/** Open project: creates the folder and opens nvim while the first line is typed. */
function open(c, ctx, a, time) {
  const { T, k } = c;
  const P = T.palette;
  const S = ctx.S.apps.open;
  const rows = [];
  let overlay = '';

  const mk = c.typed(a.col + 2, a.row, S.mkdir, T.text, time + 0.2 * k, 0.03 * k);
  const nv = c.typed(a.col + 2, a.row + 1, `nvim ${S.file}`, T.text, mk.end + 0.3 * k, 0.05 * k);
  rows.push(c.text(a.col, a.row, '❯', P.aqua, { weight: 700 }));
  rows.push(c.text(a.col, a.row + 1, '❯', P.aqua, { weight: 700 }));
  overlay += mk.svg + nv.svg;

  const vimAt = nv.end + 0.3 * k;
  const heading = `# ${S.heading}`;
  let buffer = c.bg(a.col, a.row + 2, a.w, T.background, 6);
  buffer += c.bg(a.col, a.row + 2, 4, T.surface, 6);
  buffer += c.text(a.col, a.row + 2, '  1', T.accent, { weight: 700 });
  for (let r = 3; r < 8; r++) buffer += c.text(a.col + 1, a.row + r, '~', P.blue_dim, { weight: 700 });

  const textCol = a.col + 5;
  const typing = c.grow(
    c.spans(textCol, a.row + 2, [['# ', P.orange, { weight: 700 }], [S.heading, P.yellow, { weight: 700 }]]),
    textCol, a.row + 2, len(heading), vimAt + 0.5 * k, 0.07 * k,
  );
  const typingEnd = typing.end;
  let cursor = '';
  if (c.animate) {
    const xs = Array.from({ length: len(heading) + 1 }, (_, i) => c.X(textCol + i)).join(';');
    cursor = `<rect x="${c.X(textCol)}" y="${n2(c.top(a.row + 2) + 2)}" width="${n2(c.cw)}" height="${n2(c.lh - 4)}" fill="${T.cursor}">` +
      `<animate attributeName="x" values="${xs}" begin="${c.at(vimAt + 0.5 * k)}" dur="${c.at(len(heading) * 0.07 * k)}" calcMode="discrete" fill="freeze"/>` +
      `<animate attributeName="opacity" values="1;0" dur="1.1s" begin="${c.at(typingEnd + 0.4 * k)}" calcMode="discrete" repeatCount="indefinite"/></rect>`;
  } else {
    cursor = c.cursor(textCol + len(heading), a.row + 2, 0);
  }

  // statusline
  const mode = (label, bg) => ctx.powerline(c, a.col, a.row + 8, [
    { text: label, fg: T.background, bg, bold: true },
    { text: `${S.file} [+]`, fg: T.text, bg: T.border },
  ]).svg;
  const right = ctx.powerline(c, a.col + a.w, a.row + 8, [
    { text: 'markdown', fg: T.soft, bg: T.raised },
    { text: `1:${len(heading) + 1}`, fg: T.background, bg: T.soft, bold: true },
  ], 'left').svg;
  const status = c.bg(a.col, a.row + 8, a.w, T.surface) + right +
    c.during(mode('NORMAL', P.green), 0, vimAt + 0.5 * k) +
    c.during(mode('INSERT', P.blue), vimAt + 0.5 * k, typingEnd + 0.3 * k) +
    c.during(mode('NORMAL', P.green), typingEnd + 0.3 * k, Infinity);

  overlay += c.reveal(buffer + typing.svg + cursor + status, vimAt);
  for (let r = 2; r < 9; r++) rows.push('');
  return { rows, overlay };
}

/** Custom art: ASCII lines centered in the app area. */
function asciiArt(c, ctx, a, lines) {
  const shown = lines.slice(0, a.h).map((l) => [...String(l)].slice(0, a.w).join(''));
  const blockW = Math.max(0, ...shown.map(len));
  const col = a.col + Math.floor((a.w - blockW) / 2);
  const row0 = a.row + Math.floor((a.h - shown.length) / 2);
  const rows = Array.from({ length: a.h }, (_, i) => {
    const line = shown[i - (row0 - a.row)];
    return line ? c.text(col, a.row + i, line, c.T.soft) : '';
  });
  return { rows, overlay: '' };
}

export const APPS = { rhythm, pipeline, homelab, open };

/* ───────────────────────────── panes ─────────────────────────────── */

export function renderProjects(c, ctx, startRow, startTime) {
  const { cfg, S, warn } = ctx;
  const T = c.T;
  const P = T.palette;
  const k = c.k;
  const items = cfg.projects.items.filter(Boolean);
  const gap = 2;
  const paneCols = Math.floor((c.cols - gap) / 2);
  const innerW = paneCols - 4;
  const appRows = 9;
  const accents = [P.yellow, P.aqua, P.orange, P.purple, P.green, P.blue];

  const panes = items.map((item, i) => {
    const desc = item.description ? wrap(item.description, innerW) : [];
    const head = 1 + desc.length + (item.url ? 1 : 0);
    const accent = (item.color && T.color(item.color)) || accents[i % accents.length];
    return { item, desc, head, accent, index: i + 1 };
  });

  const parts = [];
  let t = startTime;
  let row = startRow;

  for (let p = 0; p < panes.length; p += 2) {
    const pair = panes.slice(p, p + 2);
    const headRows = Math.max(...pair.map((x) => x.head));
    const total = 1 + headRows + 1 + appRows + 1;

    pair.forEach((pane, j) => {
      const col = j * (paneCols + gap);
      const inner = col + 2;
      const { item, accent } = pane;
      const last = col + paneCols - 1;
      const sepRow = row + 1 + headRows;
      const bottomRow = row + total - 1;

      // background, borders and path
      const path = ` ${item.path ?? '~/projects'} `;
      const idx = ` ${pane.index} `;
      // ╭─ path ───────── idx ─╮
      const fillTop = Math.max(1, paneCols - 4 - len(path) - len(idx));
      let frame = `<rect x="${c.X(col)}" y="${c.top(row)}" width="${n2(paneCols * c.cw)}" height="${n2(total * c.lh)}" fill="${T.surface}"/>`;
      let sides = '';
      for (let r = row + 1; r < bottomRow; r++) {
        if (r === sepRow) continue;
        sides += c.tall(col, r, '│', accent) + c.tall(last, r, '│', accent);
      }
      frame += c.glow(
        c.tall(col, row, '╭─', accent) +
        c.tall(col + 2 + len(path), row, '─'.repeat(fillTop), accent) +
        c.tall(last - 1, row, '─╮', accent) +
        sides +
        c.tall(col, sepRow, `├${'─'.repeat(paneCols - 2)}┤`, accent),
      );
      frame += c.text(col + 2 + len(path) + fillTop, row, idx, T.bright, { weight: 700 });
      parts.push(c.reveal(frame, t));

      const pathTyped = c.typed(col + 2, row, path, accent, t + 0.05 * k, 0.025 * k, { weight: 700 });
      parts.push(c.animate ? c.reveal(pathTyped.svg, t) : pathTyped.svg);
      t = pathTyped.end + 0.1 * k;

      // header
      let r = row + 1;
      parts.push(c.reveal(c.text(inner, r, item.name ?? '', T.bright, { weight: 700 }), t));
      t += 0.06 * k;
      r += 1;
      for (const line of pane.desc) {
        parts.push(c.reveal(c.text(inner, r, line, T.soft), t));
        t += 0.06 * k;
        r += 1;
      }
      if (item.url) {
        parts.push(c.reveal(c.spans(inner, r, [['↗ ', P.blue], [item.url, P.blue]]), t));
        t += 0.06 * k;
      }

      // app
      const area = { col: inner, row: sepRow + 1, w: innerW, h: appRows };
      let app;
      if (Array.isArray(item.art)) app = asciiArt(c, ctx, area, item.art);
      else if (APPS[item.art]) app = APPS[item.art](c, ctx, area, t);
      else {
        if (item.art) warn(`projects: unknown app "${item.art}" in "${item.name ?? item.path}". Options: ${Object.keys(APPS).join(', ')} or a list of ASCII lines.`);
        app = open(c, ctx, area, t);
      }
      app.rows.forEach((svg, i) => {
        if (svg) parts.push(c.reveal(svg, t + i * 0.05 * k));
      });
      if (app.overlay) parts.push(c.reveal(app.overlay, t + (app.overlayRow ?? 0) * 0.05 * k));
      t += app.rows.length * 0.05 * k;

      // footer with status and stack
      const status = item.status ? ` ● ${item.status} ` : '';
      const stack = item.stack ? ` ${item.stack} ` : '';
      const fillBottom = Math.max(1, paneCols - 4 - len(status) - len(stack));
      const footer =
        c.glow(
          c.tall(col, bottomRow, '╰─', accent) +
          c.tall(col + 2 + len(status), bottomRow, '─'.repeat(fillBottom), accent) +
          c.tall(last - 1, bottomRow, '─╯', accent),
        ) +
        (status ? c.spans(col + 2, bottomRow, [[' ● ', P.green], [`${item.status} `, P.green, { weight: 700 }]]) : '') +
        (stack ? c.text(col + 2 + len(status) + fillBottom, bottomRow, stack, T.soft) : '');
      parts.push(c.reveal(footer, t));
      t += 0.25 * k;
    });

    row += total + 1;
  }

  return { svg: parts.join(''), rows: row - startRow, end: t };
}
