/**
 * Neofetch logo.
 *
 * Formats accepted in config.json (neofetch.logo):
 *   "rooster", "owl"           built-in art from assets/logos/<name>.json
 *   "none"                     no logo
 *   { "lines": [...], "colors": [...] }
 *     lines:  lines of text
 *     colors: (optional) one row per text line, one color code per character
 *   { "lines": [...], "color": "yellow" }  every line in a single color
 *
 * Color codes (they follow the theme palette):
 *   R/r red   G/g green  Y/y yellow  B/b blue  P/p purple  A/a aqua  O/o orange
 *   (uppercase = bright color, lowercase = _dim variant)
 *   1 fg0  2 fg1  3 fg2  4 fg3  5 fg4  6 gray  7 bg4  8 bg3  9 bg2  0 bg1  k bg0
 *   . (dot) uses the default text color
 */
import { readFileSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { len } from './svg.mjs';

export const COLOR_KEYS = {
  R: 'red', r: 'red_dim', G: 'green', g: 'green_dim', Y: 'yellow', y: 'yellow_dim',
  B: 'blue', b: 'blue_dim', P: 'purple', p: 'purple_dim', A: 'aqua', a: 'aqua_dim',
  O: 'orange', o: 'orange_dim',
  1: 'fg0', 2: 'fg1', 3: 'fg2', 4: 'fg3', 5: 'fg4', 6: 'gray', 7: 'bg4', 8: 'bg3', 9: 'bg2', 0: 'bg1', k: 'bg0',
};

export function loadLogo(spec, root, warn) {
  if (spec === 'none' || spec === false) return null;
  if (spec === 'tux-svg') {
    const path = resolve(root, 'assets/logos', 'tux.svg');
    if (!existsSync(path)) { warn('neofetch.logo: tux.svg not found; using rooster.'); return loadLogo('rooster', root, warn); }
    const raw = readFileSync(path, 'utf8');
    const match = raw.match(/<svg\b([^>]*)>([\s\S]*)<\/svg>/i);
    if (!match) { warn('neofetch.logo: invalid tux.svg; using rooster.'); return loadLogo('rooster', root, warn); }
    const width = Number((match[1].match(/\bwidth="([0-9.]+)"/) || [])[1] || 300);
    const height = Number((match[1].match(/\bheight="([0-9.]+)"/) || [])[1] || 275);
    return { kind: 'svg', inner: match[2], width, height, cols: 35, rows: 25 };
  }
  if (typeof spec === 'string') {
    const path = resolve(root, 'assets/logos', `${spec}.json`);
    if (!existsSync(path)) {
      warn(`neofetch.logo: "${spec}" not found in assets/logos, using "rooster".`);
      return loadLogo('rooster', root, warn);
    }
    const data = JSON.parse(readFileSync(path, 'utf8'));
    return { kind: 'blocks', ...data };
  }
  if (spec && Array.isArray(spec.lines)) {
    return { kind: 'text', lines: spec.lines.map(String), colors: spec.colors, color: spec.color };
  }
  warn('invalid neofetch.logo, using "rooster".');
  return loadLogo('rooster', root, warn);
}

export function logoSize(logo) {
  if (!logo) return { cols: 0, rows: 0 };
  if (logo.kind === 'svg') return { cols: logo.cols, rows: logo.rows };
  const rows = logo.kind === 'blocks' ? logo.glyphs : logo.lines;
  return { cols: Math.max(0, ...rows.map(len)), rows: rows.length };
}

/** Draws one logo row. Returns svg. */
export function logoRow(c, logo, index, row) {
  const T = c.T;
  if (logo.kind === 'svg') {
    if (index !== 0) return '';
    const x = c.X(0);
    const y = c.top(row);
    return `<svg x="${x}" y="${y}" width="${logo.width}" height="${logo.height}" viewBox="0 0 ${logo.width} ${logo.height}">${logo.inner}</svg>`;
  }
  const pal = (key, fallback) => (key && key !== '.' && COLOR_KEYS[key] ? T.palette[COLOR_KEYS[key]] : fallback);

  if (logo.kind === 'text') {
    const line = [...(logo.lines[index] ?? '')];
    const colors = [...(logo.colors?.[index] ?? '')];
    const base = logo.color ? T.color(logo.color) ?? T.text : T.text;
    let out = '';
    for (let i = 0; i < line.length;) {
      const key = colors[i];
      let j = i;
      while (j < line.length && colors[j] === key) j++;
      out += c.text(i, row, line.slice(i, j).join(''), pal(key, base), { weight: 700 });
      i = j;
    }
    return out;
  }

  // blocks: backgrounds as continuous runs + block glyphs in "tall" mode
  const glyphs = [...(logo.glyphs[index] ?? '')];
  const fg = [...(logo.fg[index] ?? '')];
  const bg = [...(logo.bg[index] ?? '')].map((b, i) => (glyphs[i] === '█' ? fg[i] : b));
  const cells = glyphs.map((g) => (g === '█' ? ' ' : g));
  let out = '';
  const top = c.top(row);
  for (let i = 0; i < cells.length;) {
    let j = i;
    while (j < cells.length && bg[j] === bg[i]) j++;
    const color = pal(bg[i], null);
    if (color) {
      out += `<rect x="${c.X(i)}" y="${top - 0.4}" width="${(j - i) * c.cw + 0.8}" height="${c.lh + 0.8}" fill="${color}"/>`;
    }
    i = j;
  }
  for (let i = 0; i < cells.length;) {
    if (cells[i] === ' ') { i++; continue; }
    let j = i;
    while (j < cells.length && cells[j] !== ' ' && fg[j] === fg[i]) j++;
    out += c.tall(i, row, cells.slice(i, j).join(''), pal(fg[i], T.text), { seal: true });
    i = j;
  }
  return out;
}
