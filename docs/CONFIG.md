# Configuring the terminal

Everything in the README comes from `config.json`. Edit it, commit, and the workflow redraws `assets/terminal.svg` on its own in about a minute.

## Setup (once)

1. Copy all files into the repository.
2. In **Settings > Actions > General > Workflow permissions**, select **Read and write permissions**.
3. Push. The workflow runs automatically because `config.json` changed. You can also run it from **Actions > terminal > Run workflow**.

After that it refreshes the telemetry every 6 hours.

## What happens on screen

1. A systemd-style boot with `[ OK ]` lines and a session bar, then the screen clears.
2. The powerline prompt types `neofetch`: logo on the left, profile on the right.
3. The prompt types `tmux attach -t projects`: the projects open as panes, each running a terminal app.
4. A final prompt in `~/projects` with a blinking cursor.

The tmux bar at the bottom follows the animation and highlights the active window (`boot`, `neofetch`, `projects`).

## Profile and neofetch

| Field | What it does |
| --- | --- |
| `username` | GitHub user the data comes from. |
| `locale` | Language of the fixed strings: `en` or `pt-BR`. |
| `timezone` | Time zone for the prompt clock and the tmux bar. |
| `prompt.user`, `prompt.host` | Build the prompt and the neofetch title. |
| `profile.name`, `profile.description` | The `Name` and `Bio` lines. The bio wraps on its own; `\n` forces a break. |
| `focus` | Focus areas: plain text or `{ "tag": "algo", "text": "..." }`. They have no key; each item starts at the info column. |
| `neofetch.command` | Command typed before neofetch. |
| `neofetch.logo` | `"tux-svg"`, `"rooster"`, `"owl"`, `"none"`, or a text logo (see below). |
| `neofetch.fields` | Which lines appear and in what order: `name`, `description`, `focus`, `extra`, `repos`, `commits`, `followers`, `views`, `languages`, `palette`. |
| `neofetch.extra` | Free-form lines, like `{ "label": "Location", "value": "RS, Brazil" }`. |

Profile lines use neofetch's `Key: value` format, and focus items sit at the same column without a key. The languages are the one exception: they render as an aligned table of bars. Repos, commits, followers, views and languages are all refreshed by the workflow; nothing in that part is typed by hand.

### Text logo

```json
"logo": {
  "lines":  ["  /\\_/\\  ", "=( o.o )=", "  > ^ <  "],
  "colors": ["  OOOOO  ", "YYYAAAYYY", "  yyyyy  "]
}
```

Each character in `colors` paints the character at the same position in `lines`. Codes follow the theme palette:

| Code | Color | Code | Color |
| --- | --- | --- | --- |
| `R` `r` | red / red_dim | `1` `2` `3` `4` `5` | fg0 to fg4 |
| `G` `g` | green / green_dim | `6` | gray |
| `Y` `y` | yellow / yellow_dim | `7` `8` `9` | bg4, bg3, bg2 |
| `B` `b` | blue / blue_dim | `0` `k` | bg1, bg0 |
| `P` `p` | purple / purple_dim | `.` or space | default color |
| `A` `a` | aqua / aqua_dim | | |
| `O` `o` | orange / orange_dim | | |

For a single color, use `"color": "yellow"` instead of `colors`.

## Projects

| Field | What it does |
| --- | --- |
| `projects.command` | Command typed before the panes. |
| `projects.items` | List of projects, laid out as panes two per row. |

Each project accepts:

| Field | What it does |
| --- | --- |
| `path` | Path shown on the pane's top border. |
| `name`, `description` | Title and description. |
| `url` | Optional link below the description. |
| `status` | Green text on the bottom border. |
| `stack` | Technologies, on the right side of the bottom border. |
| `color` | Border color (palette name or hex). Without it, colors alternate. |
| `art` | The app running in the pane. |

Built-in apps for `art`:

- `rhythm`: 9 lanes with notes falling to the strike line; each key lights up on a hit, and the song clock follows the progress bar.
- `pipeline`: an htop-style table of orders, stages and progress, with a scrolling log and a volume count.
- `homelab`: `lab status` with services, pulsing states, scrolling CPU sparklines, memory and an `nmap` scan.
- `open`: creates the folder, opens `nvim` and types the first line while the statusline switches modes.

For something of your own, use a list of ASCII lines, centered in the pane:

```json
"art": [" _____ ", "| >_  |", "|_____|"]
```

## Data

| Field | What it does |
| --- | --- |
| `languages.count` | How many languages to show. |
| `languages.exclude` | Languages left out, for example `["HTML", "CSS"]`. |
| `languages.colors` | `rainbow` (one palette color per language), `accent` or `github`. |
| `languages.includePrivate` | Counts private repositories (needs `TERMINAL_TOKEN`). |
| `stats.countPrivateContributions` | Adds private contributions to commits (needs `TERMINAL_TOKEN`). |

Language bars are proportional to the most used language; the percentage next to each bar is its real share of the total.

## Animation, effects and layout

| Field | What it does |
| --- | --- |
| `boot.enabled`, `boot.lines` | Turn the boot on and replace its lines. Accepts `{user}`, `{host}`, `{repos}`, `{languageCount}`. |
| `animation.enabled` | `false` renders a static image in its final state. |
| `animation.speed` | `slow`, `medium`, `fast`, or a number (`2` is twice as fast). |
| `effects.glow` | Phosphor glow on borders, prompts and notes. |
| `effects.scanlines` | Horizontal CRT scanlines. |
| `effects.vignette` | Soft darkening in the corners. |
| `effects.statusBar` | tmux bar at the bottom. |
| `layout.width` | Window width. Height adapts to the content. |
| `layout.fontSize`, `layout.lineHeight` | Text size and spacing. |
| `layout.barCells` | Maximum width of the language bars. |

## Theme

The theme has two parts. `palette` holds the named colors (gruvbox dark by default). `roles` says which color each part of the interface uses, pointing to a palette name or a hex value.

```json
"theme": {
  "palette": { "yellow": "#fabd2f" },
  "roles": { "accent": "yellow", "prompt": "aqua" }
}
```

Leave both empty for pure gruvbox. Changing a palette color also changes the logo and the apps.

Palette: `bg0_h` `bg0` `bg1` `bg2` `bg3` `bg4` `fg0` `fg1` `fg2` `fg3` `fg4` `gray` `red` `green` `yellow` `blue` `purple` `aqua` `orange`, plus a `_dim` variant of each color.

Roles: `background`, `surface` (panes and title bar), `raised` (bars), `border`, `faint`, `text`, `bright`, `soft`, `muted`, `accent` (first prompt segment, profile keys), `secondary`, `prompt`, `ok`, `info`, `error`, `special`, `cursor`.

## About the data

**Commits** add up commit contributions from every year of the account.

**Views** come from the komarev.com counter that was already on the profile. The 1-pixel image in the README is what records visits, so keep it. Reads made by the workflow are subtracted automatically.

If an API fails, the terminal keeps the last saved values.

## Code layout

```
scripts/generate.mjs       configuration and window assembly
scripts/lib/telemetry.mjs  GitHub data and profile view counter
scripts/lib/theme.mjs      palette and color roles
scripts/lib/svg.mjs        cell grid and animations
scripts/lib/chrome.mjs     title bar, powerline prompt, tmux, effects
scripts/lib/logo.mjs       neofetch logo
scripts/lib/neofetch.mjs   profile info
scripts/lib/projects.mjs   panes and apps
scripts/lib/strings.mjs    fixed strings (en, pt-BR)
assets/logos/              logos (tux.svg, rooster.json, owl.json)
assets/fonts/              JetBrains Mono (OFL), subset to the characters in use
```

## Testing locally

Requires Node 20 or newer, no dependencies.

```bash
node scripts/generate.mjs --demo      # sample data, no network
node scripts/generate.mjs --offline   # uses data/telemetry.json
GH_TOKEN=your_token node scripts/generate.mjs
```

Open `assets/terminal.svg` in a browser to watch the animation.
