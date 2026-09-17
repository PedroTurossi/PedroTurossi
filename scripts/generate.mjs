#!/usr/bin/env node
/**
 * terminal-readme
 * Reads config.json, collects GitHub telemetry and draws assets/terminal.svg.
 *
 *   node scripts/generate.mjs            fetch data and render
 *   node scripts/generate.mjs --offline  render from data/telemetry.json only (no network)
 *   node scripts/generate.mjs --demo     render with sample data (no network)
 *
 * Layout:
 *   lib/telemetry.mjs  GitHub data and profile view counter
 *   lib/theme.mjs      gruvbox palette and color roles
 *   lib/svg.mjs        cell grid and animation primitives
 *   lib/chrome.mjs     title bar, powerline prompt, tmux bar, effects
 *   lib/logo.mjs       neofetch logo (block art or text)
 *   lib/neofetch.mjs   logo + profile info
 *   lib/projects.mjs   TUI panes and project apps
 *   lib/strings.mjs    fixed strings (en, pt-BR)
 */
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { warn, fail } from './lib/log.mjs';
import { collect } from './lib/telemetry.mjs';
import { STRINGS } from './lib/strings.mjs';
import { resolveTheme } from './lib/theme.mjs';
import { createCanvas, esc, fill, len } from './lib/svg.mjs';
import { powerline, prompt, tmuxBar, titleBar, effectDefs, effectOverlays } from './lib/chrome.mjs';
import { loadLogo } from './lib/logo.mjs';
import { renderNeofetch, NEOFETCH_FIELDS } from './lib/neofetch.mjs';
import { renderProjects } from './lib/projects.mjs';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const ARGS = new Set(process.argv.slice(2));
const MODE = ARGS.has('--demo') ? 'demo' : ARGS.has('--offline') ? 'offline' : 'live';
const TOKEN = process.env.GH_TOKEN || process.env.GITHUB_TOKEN || '';

const PATHS = {
  config: resolve(ROOT, 'config.json'),
  state: resolve(ROOT, 'data/telemetry.json'),
  output: resolve(ROOT, 'assets/terminal.svg'),
  fonts: {
    400: resolve(ROOT, 'assets/fonts/jetbrains-mono-400.woff2'),
    700: resolve(ROOT, 'assets/fonts/jetbrains-mono-700.woff2'),
  },
};

/* ───────────────────────────── configuration ──────────────────────────── */

const DEFAULTS = {
  username: '',
  locale: 'en',
  timezone: 'America/Sao_Paulo',
  prompt: { user: 'user', host: 'github' },
  profile: { name: '', description: '' },
  focus: [],
  neofetch: { command: 'neofetch', logo: 'rooster', fields: NEOFETCH_FIELDS, extra: [] },
  projects: { command: 'tmux attach -t projects', items: [] },
  languages: { count: 6, exclude: [], colors: 'rainbow', includePrivate: false },
  stats: { countPrivateContributions: false },
  boot: { enabled: true, lines: [] },
  animation: { enabled: true, speed: 'medium' },
  effects: { glow: true, scanlines: true, vignette: true, statusBar: true },
  layout: { width: 900, fontSize: 14, lineHeight: 1.6, barCells: 20 },
  theme: { palette: {}, roles: {} },
};

function merge(base, over) {
  if (Array.isArray(base) || Array.isArray(over)) return over ?? base;
  if (typeof base !== 'object' || base === null) return over ?? base;
  const out = { ...base };
  for (const [key, value] of Object.entries(over ?? {})) out[key] = key in base ? merge(base[key], value) : value;
  return out;
}

async function loadConfig() {
  let raw;
  try {
    raw = JSON.parse(await readFile(PATHS.config, 'utf8'));
  } catch (err) {
    fail(`invalid config.json: ${err.message}`);
  }
  const cfg = merge(DEFAULTS, raw);
  if (!cfg.username) fail('config.json: set "username".');
  if (!STRINGS[cfg.locale]) {
    warn(`locale "${cfg.locale}" is not supported, using "en". Options: ${Object.keys(STRINGS).join(', ')}`);
    cfg.locale = 'en';
  }
  cfg.neofetch.fields = cfg.neofetch.fields.filter((f) => {
    if (NEOFETCH_FIELDS.includes(f)) return true;
    warn(`neofetch.fields: unknown "${f}" was ignored. Options: ${NEOFETCH_FIELDS.join(', ')}`);
    return false;
  });
  if (!['rainbow', 'accent', 'github'].includes(cfg.languages.colors)) {
    warn('languages.colors must be "rainbow", "accent" or "github", using "rainbow".');
    cfg.languages.colors = 'rainbow';
  }
  return cfg;
}

/* ───────────────────────────── rendering ───────────────────────────── */

function speedFactor(speed) {
  const presets = { slow: 1.6, medium: 1, fast: 0.55 };
  if (typeof speed === 'number' && speed > 0) return 1 / speed;
  if (presets[speed]) return presets[speed];
  warn(`invalid animation.speed "${speed}", using "medium".`);
  return 1;
}

async function fontFaces() {
  let css = '';
  for (const [weight, path] of Object.entries(PATHS.fonts)) {
    if (!existsSync(path)) continue;
    const b64 = (await readFile(path)).toString('base64');
    css += `@font-face{font-family:'TermMono';font-weight:${weight};src:url(data:font/woff2;base64,${b64}) format('woff2');}`;
  }
  return css;
}

function timeParts(iso, timezone) {
  return Object.fromEntries(new Intl.DateTimeFormat('en-GB', {
    timeZone: timezone, day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).formatToParts(new Date(iso)).map((p) => [p.type, p.value]));
}

function render(cfg, state, fontCss) {
  const S = STRINGS[cfg.locale];
  const T = resolveTheme(cfg.theme, warn);
  const effects = cfg.effects;
  const c = createCanvas({
    theme: T, layout: cfg.layout, animate: cfg.animation.enabled,
    k: speedFactor(cfg.animation.speed), glow: effects.glow,
  });
  const { k, animate } = c;
  const P = T.palette;
  const nf = new Intl.NumberFormat(cfg.locale);
  const pf = new Intl.NumberFormat(cfg.locale, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const when = timeParts(state.updatedAt, cfg.timezone);
  const clock = `${when.hour}:${when.minute}`;
  const vars = {
    user: cfg.prompt.user, host: cfg.prompt.host, username: cfg.username,
    repos: nf.format(state.repos ?? 0), languageCount: nf.format(state.languageCount ?? 0),
  };
  const logo = loadLogo(cfg.neofetch.logo, ROOT, warn);

  /* boot */
  const boot = [];
  let t = 0.35 * k;
  let bootRows = 0;
  const bootOn = animate && cfg.boot.enabled;
  if (bootOn) {
    const lines = (cfg.boot.lines?.length ? cfg.boot.lines : S.boot).map((l) => fill(l, vars));
    boot.push(c.reveal(c.spans(0, 0, [[fill(S.system, vars), T.soft, { weight: 700 }]]), t));
    t += 0.3 * k;
    lines.forEach((line, i) => {
      boot.push(c.reveal(c.spans(0, i + 2, [
        ['[', T.faint], ['  OK  ', P.green, { weight: 700 }], ['] ', T.faint], [line, T.text],
      ]), t));
      t += 0.15 * k;
    });
    const row = lines.length + 3;
    const label = `${S.session} `;
    const cells = 36;
    boot.push(c.reveal(c.text(0, row, label, P.aqua, { weight: 700 }), t));
    const bar = c.blockBar(len(label), row, cells, 1, P.yellow, t + 0.1 * k, 0.018 * k);
    boot.push(c.reveal(bar.svg, t));
    t = bar.end + 0.1 * k;
    boot.push(c.reveal(c.text(len(label) + cells + 2, row, '100%', P.green, { weight: 700 }), t));
    t += 0.4 * k;
    bootRows = row + 1;
  }
  const clearAt = t;

  /* session */
  const main = [];
  let row = 0;
  t = bootOn ? clearAt + 0.15 * k : 0.3 * k;
  const neofetchAt = t;

  const neoPrompt = prompt(c, { cfg, row, dir: '~', clock, command: cfg.neofetch.command, time: t });
  main.push(neoPrompt.svg);
  t = neoPrompt.end;
  row += 2;

  const neo = renderNeofetch(c, { cfg, state, S, nf, pf, logo }, row, t);
  main.push(neo.svg);
  row += neo.rows + 1;
  t = neo.end + 0.4 * k;

  let projectsAt = null;
  if (cfg.projects.items.length) {
    projectsAt = t;
    const projPrompt = prompt(c, { cfg, row, dir: '~', clock, command: cfg.projects.command, time: t });
    main.push(projPrompt.svg);
    t = projPrompt.end;
    row += 2;
    const projects = renderProjects(c, { cfg, S, warn, powerline }, row, t);
    main.push(projects.svg);
    row += projects.rows;
    t = projects.end + 0.2 * k;
  }

  const finalPrompt = prompt(c, { cfg, row, dir: projectsAt !== null ? '~/projects' : '~', clock, time: t });
  main.push(finalPrompt.svg);
  main.push(c.reveal(c.cursor(finalPrompt.cmdCol, row, t), t));
  row += 1;

  const contentRows = Math.max(row, bootRows);
  const W = c.width;
  let barSvg = '';
  let H;
  if (effects.statusBar) {
    const barRow = contentRows + 1;
    const windows = S.tmux.windows.map((name) => ({ name, from: null, to: Infinity }));
    if (bootOn) Object.assign(windows[0], { from: 0, to: clearAt });
    Object.assign(windows[1], { from: animate ? neofetchAt : null, to: projectsAt ?? Infinity });
    if (projectsAt !== null) Object.assign(windows[2], { from: animate ? projectsAt : 0, to: Infinity });
    if (!animate) windows[projectsAt !== null ? 2 : 1].from = 0;
    barSvg = tmuxBar(c, { cfg, row: barRow, S, windows, sync: `${when.year}-${when.month}-${when.day} ${clock}`, repos: nf.format(state.repos ?? 0) });
    H = Math.round(c.top(barRow) + c.lh);
  } else {
    H = Math.round(c.top(contentRows) + 16);
  }

  const bootGroup = bootOn
    ? `<g>${boot.join('')}<set attributeName="opacity" to="0" begin="${c.at(clearAt)}" fill="freeze"/></g>`
    : '';
  const mainGroup = bootOn
    ? `<g opacity="0"><set attributeName="opacity" to="1" begin="${c.at(clearAt)}" fill="freeze"/>${main.join('')}</g>`
    : `<g>${main.join('')}</g>`;

  const description = [
    cfg.profile.name, cfg.profile.description,
    state.languages.slice(0, cfg.languages.count).map((l) => `${l.name} ${pf.format(l.percent)}%`).join(', '),
    `${S.labels.commits}: ${state.stats.commits ?? '--'}`,
    `${S.labels.followers}: ${state.stats.followers ?? '--'}`,
    `${S.labels.views}: ${state.stats.views ?? '--'}`,
    ...cfg.projects.items.map((p) => [p.name, p.description].filter(Boolean).join(': ')),
  ].filter(Boolean).join('. ');

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-labelledby="title desc">
<title id="title">${esc(`${cfg.prompt.user}@${cfg.prompt.host}: ~`)}</title>
<desc id="desc">${esc(description)}</desc>
<style>${fontCss}text{font-family:'TermMono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:${c.fs}px;white-space:pre;}</style>
<defs><clipPath id="window"><rect width="${W}" height="${H}" rx="10"/></clipPath>${effectDefs(effects)}${c.defs.join('')}</defs>
<g clip-path="url(#window)">
<rect width="${W}" height="${H}" fill="${T.background}"/>
${titleBar(c, { cfg, W })}
${bootGroup}
${mainGroup}
${barSvg}
${effectOverlays(effects, W, H)}
</g>
<rect x="0.5" y="0.5" width="${W - 1}" height="${H - 1}" rx="9.5" fill="none" stroke="${T.raised}"/>
</svg>
`;
}

/* ───────────────────────────── main ───────────────────────────── */

const cfg = await loadConfig();
const prev = existsSync(PATHS.state)
  ? await readFile(PATHS.state, 'utf8').then(JSON.parse).catch(() => { warn('data/telemetry.json is corrupted and will be recreated.'); return null; })
  : null;
const state = await collect(cfg, prev, { mode: MODE, token: TOKEN, wantsViews: cfg.neofetch.fields.includes('views') });
const svg = render(cfg, state, await fontFaces());

await mkdir(dirname(PATHS.output), { recursive: true });
await writeFile(PATHS.output, svg);
if (MODE === 'live') {
  await mkdir(dirname(PATHS.state), { recursive: true });
  await writeFile(PATHS.state, `${JSON.stringify(state, null, 2)}\n`);
}

console.log(`[ok] assets/terminal.svg (${(svg.length / 1024).toFixed(1)} KB, ${MODE} mode)`);
console.log(`     commits ${state.stats.commits ?? '--'} | followers ${state.stats.followers ?? '--'} | views ${state.stats.views ?? '--'}`);
console.log(`     ${state.languages.slice(0, cfg.languages.count).map((l) => `${l.name} ${l.percent.toFixed(1)}%`).join(', ') || 'no languages'}`);
