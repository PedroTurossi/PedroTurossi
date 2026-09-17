/**
 * Theme: a palette of named colors (gruvbox dark by default) and roles that
 * point to those colors. Changing the palette updates everything, logo art included.
 */

export const GRUVBOX = {
  bg0_h: '#1d2021', bg0: '#282828', bg1: '#3c3836', bg2: '#504945', bg3: '#665c54', bg4: '#7c6f64',
  fg0: '#fbf1c7', fg1: '#ebdbb2', fg2: '#d5c4a1', fg3: '#bdae93', fg4: '#a89984', gray: '#928374',
  red: '#fb4934', green: '#b8bb26', yellow: '#fabd2f', blue: '#83a598',
  purple: '#d3869b', aqua: '#8ec07c', orange: '#fe8019',
  red_dim: '#cc241d', green_dim: '#98971a', yellow_dim: '#d79921', blue_dim: '#458588',
  purple_dim: '#b16286', aqua_dim: '#689d6a', orange_dim: '#d65d0e',
};

export const ROLES = {
  background: 'bg0_h', surface: 'bg0', raised: 'bg1', border: 'bg2', faint: 'bg3',
  text: 'fg1', bright: 'fg0', soft: 'fg3', muted: 'gray',
  accent: 'yellow', secondary: 'orange', prompt: 'aqua', ok: 'green',
  info: 'blue', error: 'red', special: 'purple', cursor: 'fg1',
};

const isHex = (v) => /^#([0-9a-f]{3}|[0-9a-f]{6}|[0-9a-f]{8})$/i.test(String(v));

export function resolveTheme(themeCfg = {}, warn) {
  const palette = { ...GRUVBOX };
  for (const [name, value] of Object.entries(themeCfg.palette ?? {})) {
    if (isHex(value)) palette[name] = value;
    else warn(`theme.palette.${name} = "${value}" is not a hex color, ignored.`);
  }
  const color = (value) => (isHex(value) ? value : palette[value]);
  const T = { palette, color };
  for (const [role, fallback] of Object.entries(ROLES)) {
    const value = themeCfg.roles?.[role] ?? fallback;
    const resolved = color(value);
    if (!resolved) warn(`theme.roles.${role} = "${value}" is neither a hex color nor a palette name, using "${fallback}".`);
    T[role] = resolved ?? color(fallback);
  }
  return T;
}
