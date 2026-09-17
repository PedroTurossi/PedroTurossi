/**
 * Drawing primitives on a grid of terminal cells.
 *
 * Each grid row is `lh` tall. Regular text uses the font at its normal size,
 * with the baseline centered in the cell. Box-drawing and block characters
 * (`╭─│█▄`) use "tall" mode: the font is scaled up until the glyph fills the whole
 * cell and squeezed horizontally, so lines and blocks connect without gaps
 * between rows, like in a real terminal.
 */

export const n2 = (v) => Number(Number(v).toFixed(2));

export const esc = (s) => String(s)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&apos;');

export const fill = (template, vars) => String(template).replace(/\{(\w+)\}/g, (m, k) => (k in vars ? vars[k] : m));

export const len = (s) => [...String(s)].length;

export const pad = (s, width, align = 'left') => {
  const str = [...String(s)].slice(0, width).join('');
  const space = ' '.repeat(Math.max(0, width - len(str)));
  return align === 'right' ? space + str : str + space;
};

export function wrap(text, width) {
  const lines = [];
  for (const paragraph of String(text).split('\n')) {
    let line = '';
    for (const word of paragraph.split(/\s+/).filter(Boolean)) {
      if (!line) line = word;
      else if (len(line) + 1 + len(word) <= width) line += ` ${word}`;
      else { lines.push(line); line = word; }
      while (len(line) > width) { lines.push([...line].slice(0, width).join('')); line = [...line].slice(width).join(''); }
    }
    lines.push(line);
  }
  return lines;
}

const EIGHTHS = ['', '▏', '▎', '▍', '▌', '▋', '▊', '▉'];

export function createCanvas({ theme, layout, animate, k, glow }) {
  const fs = layout.fontSize;
  const cw = fs * 0.6;
  const lh = n2(fs * layout.lineHeight);
  const padX = 26;
  const titleH = 36;
  const originY = titleH + 16;
  const cols = Math.floor((layout.width - padX * 2) / cw);
  const tallSize = n2(lh / 1.32 + 0.15);
  const defs = [];
  let uid = 0;

  const c = {
    T: theme, fs, cw, lh, padX, titleH, originY, cols, animate, k, defs,
    width: layout.width,

    id: (prefix = 'i') => `${prefix}${uid++}`,
    X: (col) => n2(padX + col * cw),
    top: (row) => n2(originY + row * lh),
    Y: (row) => n2(originY + row * lh + (lh + 0.72 * fs) / 2),
    tallY: (row) => n2(originY + row * lh + 1.02 * tallSize - 0.08),
    at: (s) => `${n2(s)}s`,

    /** Soft phosphor glow around the content (when enabled). */
    glow: (inner) => (glow && inner ? `<g filter="url(#glow)">${inner}</g>` : inner),

    /** Text at pixel coordinates. */
    glyphs(x, y, str, color, { size = fs, weight, anchor, squeeze, opacity, seal } = {}) {
      const n = len(str);
      if (!n || !String(str).trim()) return '';
      const attrs = [`x="${n2(x)}"`, `y="${n2(y)}"`, `fill="${color}"`];
      const advance = squeeze ? cw : size * 0.6;
      if (n > 1 || squeeze) attrs.push(`textLength="${n2(n * advance)}"`, `lengthAdjust="${squeeze ? 'spacingAndGlyphs' : 'spacing'}"`);
      if (size !== fs) attrs.push(`style="font-size:${size}px"`);
      if (weight) attrs.push(`font-weight="${weight}"`);
      if (anchor) attrs.push(`text-anchor="${anchor}"`);
      if (opacity !== undefined) attrs.push(`fill-opacity="${opacity}"`);
      // "seal": a thin same-color stroke closes antialiasing gaps between blocks
      if (seal) attrs.push(`stroke="${color}"`, 'stroke-width="0.6"');
      return `<text ${attrs.join(' ')}>${esc(str)}</text>`;
    },

    text: (col, row, str, color, opts) => c.glyphs(c.X(col), c.Y(row), str, color, opts),

    /** Box-drawing and block characters filling the whole cell. */
    tall: (col, row, str, color, opts = {}) =>
      c.glyphs(c.X(col), c.tallY(row), str, color, { ...opts, size: tallSize, squeeze: true }),

    /** Sequence of colored spans: [[text, color, options], ...]. */
    spans(col, row, segments) {
      let cursor = col;
      let out = '';
      for (const [str, color, opts] of segments) {
        out += opts?.tall ? c.tall(cursor, row, str, color, opts) : c.text(cursor, row, str, color, opts);
        cursor += len(str);
      }
      return out;
    },

    /** Cell background. */
    bg: (col, row, widthCols, color, rows = 1) =>
      `<rect x="${c.X(col)}" y="${c.top(row)}" width="${n2(widthCols * cw)}" height="${n2(rows * lh)}" fill="${color}"/>`,

    reveal: (inner, time) => (animate && inner
      ? `<g opacity="0"><set attributeName="opacity" to="1" begin="${c.at(time)}" fill="freeze"/>${inner}</g>`
      : inner),

    /** Visible only between two instants (the end can be Infinity). */
    during(inner, from, to) {
      if (!animate) return to === Infinity ? inner : '';
      const off = to === Infinity ? '' : `<set attributeName="visibility" to="hidden" begin="${c.at(to)}" fill="freeze"/>`;
      return `<g visibility="hidden"><set attributeName="visibility" to="visible" begin="${c.at(from)}" fill="freeze"/>${off}${inner}</g>`;
    },

    /** Horizontal clip that grows cell by cell (typing, bars). */
    grow(inner, col, row, cells, time, stepDur, rows = 1) {
      if (!animate || cells <= 0) return { svg: inner, end: time };
      const id = c.id('g');
      const values = Array.from({ length: cells + 1 }, (_, i) => (i ? n2(i * cw + 3) : 0)).join(';');
      defs.push(
        `<clipPath id="${id}"><rect x="${n2(c.X(col) - 1)}" y="${c.top(row)}" height="${n2(rows * lh)}" width="0">` +
        `<animate attributeName="width" values="${values}" begin="${c.at(time)}" dur="${c.at(cells * stepDur)}" calcMode="discrete" fill="freeze"/></rect></clipPath>`,
      );
      return { svg: `<g clip-path="url(#${id})">${inner}</g>`, end: time + cells * stepDur };
    },

    typed(col, row, str, color, time, perChar, opts) {
      const node = c.text(col, row, str, color, opts);
      return c.grow(node, col, row, len(str), time, perChar);
    },

    /** Block cursor; blinks from `time` on. */
    cursor(col, row, time, color = theme.cursor) {
      const rect = `x="${c.X(col)}" y="${n2(c.top(row) + 2)}" width="${n2(cw)}" height="${n2(lh - 4)}" fill="${color}"`;
      return animate
        ? `<rect ${rect} opacity="0"><animate attributeName="opacity" values="1;0" dur="1.1s" begin="${c.at(time)}" calcMode="discrete" repeatCount="indefinite"/></rect>`
        : `<rect ${rect}/>`;
    },

    /** Progress bar with 1/8-cell precision. */
    blockBar(col, row, cells, fraction, color, time, stepDur, track = theme.border) {
      const eighths = Math.round(Math.max(0, Math.min(1, fraction)) * cells * 8);
      const full = Math.floor(eighths / 8);
      const part = EIGHTHS[eighths % 8];
      const filled = '█'.repeat(full) + part;
      const used = full + (part ? 1 : 0);
      const trackSvg = c.text(col + used, row, '░'.repeat(Math.max(0, cells - used)), track);
      const grown = c.grow(c.text(col, row, filled, color, { seal: true }), col, row, used, time, stepDur);
      return { svg: trackSvg + grown.svg, end: grown.end };
    },

    /**
     * Text strip scrolling inside a window of `windowCols` cells.
     * `strip` needs `steps + windowCols` characters for a seamless loop.
     */
    ticker(col, row, strip, windowCols, color, steps, stepDur, time, opts = {}) {
      const node = (x) => (opts.tall
        ? c.glyphs(x, c.tallY(row), strip, color, { ...opts, size: tallSize, squeeze: true })
        : c.glyphs(x, c.Y(row), strip, color, opts));
      if (!animate) return `<g>${c.clipWindow(col, row, windowCols, 1, node(c.X(col)))}</g>`;
      const values = Array.from({ length: steps }, (_, i) => n2(c.X(col) - i * cw)).join(';');
      const moving = node(c.X(col)).replace('<text ', `<text data-t="1" `)
        .replace('</text>', `<animate attributeName="x" values="${values}" begin="${c.at(time)}" dur="${c.at(steps * stepDur)}" calcMode="discrete" repeatCount="indefinite"/></text>`);
      return c.clipWindow(col, row, windowCols, 1, moving);
    },

    clipWindow(col, row, widthCols, rows, inner) {
      const id = c.id('w');
      defs.push(`<clipPath id="${id}"><rect x="${c.X(col)}" y="${c.top(row)}" width="${n2(widthCols * cw)}" height="${n2(rows * lh)}"/></clipPath>`);
      return `<g clip-path="url(#${id})">${inner}</g>`;
    },
  };
  return c;
}
