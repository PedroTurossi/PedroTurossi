/**
 * Neofetch output: logo on the left, profile info on the right.
 *
 * Profile lines use neofetch's own format, `Key: value`, with no column alignment.
 * Languages are the exception: they render as an aligned table of bars.
 * All numbers and languages come from data/telemetry.json, which the workflow refreshes.
 */
import { len, wrap } from './svg.mjs';
import { logoRow, logoSize } from './logo.mjs';

export const NEOFETCH_FIELDS = ['name', 'description', 'focus', 'extra', 'repos', 'commits', 'followers', 'views', 'languages', 'palette'];

export function renderNeofetch(c, { cfg, state, S, nf, pf, logo }, startRow, startTime) {
  const T = c.T;
  const P = T.palette;
  const k = c.k;
  const size = logoSize(logo);
  const ic = size.cols ? size.cols + 3 : 0;
  const fields = cfg.neofetch.fields;
  const labelOf = (field) => S.labels[field] ?? field;
  const fmt = (v) => (v === null || v === undefined ? '--' : nf.format(v));

  // Key colors by group: profile in yellow, numbers in aqua, languages in orange.
  const keyColor = { profile: T.accent, stats: T.prompt, languages: T.secondary };

  /** Draws `Key:` and returns the column where the value starts. */
  const key = (row, label, group) => ({
    svg: c.text(ic, row, label, keyColor[group], { weight: 700 }) + c.text(ic + len(label), row, ':', T.soft),
    valueCol: ic + len(label) + 2,
  });

  const info = [];
  const title = `${cfg.prompt.user}@${cfg.prompt.host}`;
  info.push((r) => c.glow(c.spans(ic, r, [
    [cfg.prompt.user, T.accent, { weight: 700 }], ['@', T.soft], [cfg.prompt.host, T.prompt, { weight: 700 }],
  ])));
  info.push((r) => c.tall(ic, r, '─'.repeat(len(title)), T.faint));

  /** A single `Key: value` line. */
  const line = (label, group, value, color, weight) => info.push((r) => {
    const k0 = key(r, label, group);
    return k0.svg + c.text(k0.valueCol, r, value, color, { weight });
  });

  /** `Key: value` where the value wraps; continuation lines start under the value. */
  const wrapped = (label, group, text, color) => {
    const valueCol = ic + len(label) + 2;
    wrap(text, c.cols - valueCol).forEach((part, i) => info.push((r) =>
      (i === 0 ? key(r, label, group).svg : '') + c.text(valueCol, r, part, color)));
  };

  const builders = {
    name() {
      if (cfg.profile.name) line(labelOf('name'), 'profile', cfg.profile.name, T.bright, 700);
    },
    description() {
      if (cfg.profile.description) wrapped(labelOf('description'), 'profile', cfg.profile.description, T.soft);
    },
    focus() {
      // no "Focus:" key: each item starts at the info column, like every other line
      const items = cfg.focus.map((f) => (typeof f === 'string' ? { tag: '', text: f } : { tag: f.tag ?? '', text: f.text ?? '' }));
      if (!items.length) {
        info.push((r) => c.text(ic, r, S.emptyFocus, T.muted));
        return;
      }
      const tagColors = [P.red, P.purple, P.blue, P.green, P.orange];
      const tagW = Math.max(...items.map((it) => (it.tag ? len(it.tag) + 2 : 1))) + 1;
      items.forEach((item, n) => {
        wrap(item.text, c.cols - ic - tagW).forEach((part, i) => {
          info.push((r) => (i > 0 ? '' : item.tag
            ? c.spans(ic, r, [['[', T.faint], [item.tag, tagColors[n % tagColors.length], { weight: 700 }], [']', T.faint]])
            : c.text(ic, r, '•', T.muted))
            + c.text(ic + tagW, r, part, T.text));
        });
      });
    },
    extra() {
      for (const e of cfg.neofetch.extra) if (e?.label && e?.value) line(e.label, 'profile', e.value, T.text);
    },
    repos() { line(labelOf('repos'), 'stats', fmt(state.repos), P.yellow, 700); },
    commits() { line(labelOf('commits'), 'stats', fmt(state.stats.commits), P.green, 700); },
    followers() { line(labelOf('followers'), 'stats', fmt(state.stats.followers), P.blue, 700); },
    views() { line(labelOf('views'), 'stats', fmt(state.stats.views), P.purple, 700); },

    languages() {
      const label = labelOf('languages');
      const list = state.languages.slice(0, cfg.languages.count);
      if (!list.length) {
        line(label, 'languages', S.emptyLanguages, T.muted);
        return;
      }
      const vc = ic + len(label) + 2;
      const valueW = c.cols - vc;
      const rainbow = [P.yellow, P.orange, P.red, P.purple, P.blue, P.aqua, P.green];
      const nameW = Math.max(...list.map((l) => len(l.name))) + 2;
      const pctW = Math.max(...list.map((l) => len(`${pf.format(l.percent)}%`)));
      const cells = Math.max(8, Math.min(cfg.layout.barCells, valueW - nameW - pctW - 2));
      const topPct = list[0].percent || 1;
      list.forEach((lang, i) => info.push((r, time) => {
        const color = cfg.languages.colors === 'github' && lang.color ? lang.color
          : cfg.languages.colors === 'accent' ? T.accent
            : rainbow[i % rainbow.length];
        // the most used language fills the bar; the others are proportional to it
        const bar = c.blockBar(vc + nameW, r, cells, lang.percent / topPct, color, time + 0.05 * k, 0.018 * k);
        const pct = c.text(vc + nameW + cells + 1, r, `${pf.format(lang.percent)}%`.padStart(pctW + 1), T.bright, { weight: 700 });
        return (i === 0 ? key(r, label, 'languages').svg : '')
          + c.text(vc, r, lang.name, T.text) + bar.svg + c.reveal(pct, bar.end);
      }));
    },

    palette() {
      const dim = [P.bg1, P.red_dim, P.green_dim, P.yellow_dim, P.blue_dim, P.purple_dim, P.aqua_dim, P.fg4];
      const bright = [P.gray, P.red, P.green, P.yellow, P.blue, P.purple, P.aqua, P.fg1];
      info.push(() => '');
      for (const set of [dim, bright]) {
        info.push((r) => set.map((color, i) => c.tall(ic + i * 3, r, '███', color, { seal: true })).join(''));
      }
    },
  };

  for (const field of fields) builders[field]?.();

  const rows = Math.max(size.rows, info.length);
  const parts = [];
  let t = startTime;
  for (let i = 0; i < rows; i++) {
    const row = startRow + i;
    const logoSvg = logo && i < size.rows ? logoRow(c, logo, i, row) : '';
    parts.push(c.reveal(logoSvg + (info[i] ? info[i](row, t) : ''), t));
    t += 0.06 * k;
  }
  return { svg: parts.join(''), rows, end: t };
}
