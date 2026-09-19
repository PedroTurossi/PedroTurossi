# Configuring the terminal

Everything in the README comes from **`config.json`**. Edit it, commit, and the workflow collects fresh telemetry and redraws `assets/terminal.svg` in about a minute. Keys starting with `_` (like `_leia_me`) are notes and are ignored.

## Setup (once)

1. Copy all files into the profile repository (`PedroTurossi/PedroTurossi`).
2. In **Settings > Actions > General > Workflow permissions**, select **Read and write permissions**.
3. Push. The workflow runs automatically because `config.json` changed. You can also run it from **Actions > terminal > Run workflow**.

After that it refreshes every 6 hours.

## How the data flows

```
.github/workflows/terminal.yml
  ├─ python scripts/telemetry.py   GitHub API  ->  data/telemetry.json
  └─ python scripts/render.py      config.json + data/telemetry.json  ->  assets/terminal.svg
```

**Which profile is read?** The one in `"username"`, not the repository the workflow lives in. If `"username"` is left empty, it falls back to the owner of the repository. No profile link is needed, only the login (`PedroTurossi`).

**Languages** are ranked the way GitHub measures them: bytes of code per language, added up across the repositories the user owns (forks excluded). The telemetry keeps only the top `languages.count`; percentages are each language's share of all code.

**Tokens.** The workflow uses the built-in `github.token`, which reads public data. To also count private repositories or private contributions, create a personal access token, save it as the repository secret `TERMINAL_TOKEN`, and turn on `languages.includePrivate` / `stats.countPrivateContributions`. If the GraphQL API refuses the token, the script falls back to the REST API automatically. If every source fails, the last saved values are kept.

## The fields you will touch most

### Username and prompt

```json
"username": "PedroTurossi",
"prompt": { "user": "pedro", "host": "turossi" }
```

`username` is the GitHub login the data comes from (also shown on the right of the tmux bar). `prompt` only changes the `pedro@turossi` text.

### Name and Bio: label and value

```json
"profile": {
  "name": { "label": "Name", "value": "Pedro H. Turossi" },
  "bio":  { "label": "Bio",  "value": "Just a student who builds algorithms... and games maybe?" }
}
```

`label` is the yellow key on the left, `value` is the text. The Bio wraps on its own and continuation lines stay aligned under the text, whatever the label length. `\n` forces a line break.

### Focus (algo, game): label and value

```json
"focus": [
  { "label": "algo", "value": "Algorithms, data structures, problem solving" },
  { "label": "game", "value": "Game dev: gameplay systems and rhythm games" }
]
```

`label` is the text inside `[ ]`, `value` the line after it. Label colors follow the order: red, purple, blue, green, orange. The values line up after the longest label automatically. Add or remove entries freely.

### Languages

```json
"languages": { "count": 6, "exclude": [], "colors": "rainbow", "includePrivate": false }
```

| Field | What it does |
| --- | --- |
| `count` | How many languages are collected by the telemetry **and** shown. |
| `exclude` | Languages left out before ranking, e.g. `["HTML", "CSS", "Jupyter Notebook"]`. |
| `colors` | `rainbow` (one palette color per row), `accent` (all yellow), or `github` (GitHub's language colors). |
| `includePrivate` | Counts private repositories (needs `TERMINAL_TOKEN`). |

Bars are proportional to the most used language; the percentage is its real share.

### Project statuses

```json
"projects": {
  "borderColors": ["yellow", "aqua", "orange", "purple"],
  "statuses": {
    "developed":      { "text": "developed",      "color": "green" },
    "in development": { "text": "in development", "color": "green" },
    "ongoing":        { "text": "ongoing",        "color": "green" },
    "planning":       { "text": "planning",       "color": "green" }
  },
  "items": [
    { "name": "Nine Lanes", "status": "in development", "borderColor": "yellow", "...": "..." }
  ]
}
```

Each project's `"status"` is one of the keys above. `text` is what appears on the pane's bottom border (with the `●`), `color` is a palette name or hex for that status dot/text. They all start green, which is how the design looked originally; change the color to tell them apart. An unknown status still shows, as typed, and the workflow log prints a warning.

Project pane borders use `borderColor` on each project. If a project does not set it, the renderer rotates through `projects.borderColors`. Both fields accept palette names (`yellow`, `aqua`, `orange`, `purple`, `green`, `blue`, etc.) or hex colors like `"#ff6b00"`.

### Palette (Gruvbox by default)

```json
"theme": {
  "palette": { "bg0_h": "#1d2021", "yellow": "#fabd2f", "...": "..." },
  "roles":   { "background": "bg0_h", "accent": "yellow", "...": "..." }
}
```

`palette` holds every named color, already filled with Gruvbox dark. Change a hex value and everything using that color follows, **including the Tux pixel art and the moon**. `roles` says which palette color each part of the interface uses (or a hex directly).

Palette names: `bg0_h` `bg0` `bg1` `bg2` `bg3` `bg4` `fg0` `fg1` `fg2` `fg3` `fg4` `gray` `red` `green` `yellow` `blue` `purple` `aqua` `orange`, plus a `_dim` variant of each color.

Roles: `background`, `surface` (panes and title bar), `raised` (bars), `border`, `faint`, `text`, `bright`, `soft`, `muted`, `accent` (first prompt segment, profile keys), `secondary` (Languages key), `prompt` (stats keys), `ok`, `info`, `error`, `special`, `cursor`.

## Everything else

### Projects

| Field | What it does |
| --- | --- |
| `projects.command` | Command typed before the panes. |
| `projects.borderColors` | Default border colors rotated between projects when an item has no `borderColor`. |
| `path` | Path on the pane's top border. |
| `name`, `description` | Title and description (wraps automatically). |
| `url` | Optional link below the description. |
| `status` | A key from `projects.statuses`. |
| `stack` | Technologies, on the right of the bottom border. |
| `borderColor` | Border color for this project (palette name or hex). The old name `color` still works. |
| `art` | The app in the pane: `rhythm`, `pipeline`, `homelab`, `open`, or a list of ASCII lines. |

### Neofetch

| Field | What it does |
| --- | --- |
| `neofetch.command` | Command typed before neofetch. |
| `neofetch.logo` | `"tux-svg"`, `"tux"`, `"rooster"`, `"owl"`, `"none"`, or a text logo. |
| `neofetch.fields` | Which lines appear and in what order: `name`, `bio`, `focus`, `extra`, `repos`, `commits`, `followers`, `views`, `languages`, `palette`. |
| `neofetch.extra` | Free lines, like `{ "label": "Location", "value": "RS, Brazil" }`. |
| `labels` | Keys of the stats lines: `repos`, `commits`, `followers`, `views`, `languages`. |

Text logo:

```json
"logo": { "lines": ["  /\\_/\\  ", "=( o.o )=", "  > ^ <  "], "colors": ["  OOOOO  ", "YYYAAAYYY", "  yyyyy  "] }
```

Each character in `colors` paints the character at the same position: `R G Y B P A O` bright colors, lowercase for `_dim`, `1`-`5` fg0-fg4, `6` gray, `7 8 9` bg4-bg2, `0` bg1, `k` bg0, `.` default.

### Locale, animation, effects and layout

| Field | What it does |
| --- | --- |
| `locale` | Fixed interface text: `en` or `pt-BR` (the text lives in `assets/strings.json`). |
| `timezone` | Time zone for the prompt clock and the tmux bar. |
| `boot.enabled`, `boot.lines` | Boot screen and its lines. Accepts `{user}`, `{host}`, `{repos}`, `{languageCount}`. |
| `animation.enabled` | `false` renders a still image in its final state. |
| `animation.speed` | `slow`, `medium`, `fast`, or a number (`2` = twice as fast). |
| `effects` | `glow`, `scanlines`, `vignette`, `statusBar` on/off. |
| `layout` | `width`, `fontSize`, `lineHeight`, `barCells`. Height adapts to the content. |
| `stats.countPrivateContributions` | Adds private contributions to commits (needs `TERMINAL_TOKEN`). |

## About the data

**Commits** add up commit contributions from every year of the account. On the REST fallback this is an approximate search count.

**Views** come from the komarev.com counter. The 1-pixel image in the README is what records visits, so keep it. Reads made by the workflow are subtracted automatically.

## Testing locally

Python 3.9 or newer, no packages to install.

```bash
python scripts/render.py --demo            # sample data, no network: preview config changes
GH_TOKEN=your_token python scripts/telemetry.py
python scripts/render.py                   # uses data/telemetry.json
```

Open `assets/terminal.svg` in a browser to watch the animation. If `config.json` has a typo (a missing comma, usually), the script prints the line where JSON parsing stopped.

## Code layout

```
scripts/telemetry.py            step 1: GitHub data -> data/telemetry.json
scripts/render.py               step 2: config + telemetry -> assets/terminal.svg
scripts/terminal/config.py      reads config.json, defaults and validation
scripts/terminal/telemetry.py   GitHub GraphQL/REST and the view counter
scripts/terminal/theme.py       palette and color roles
scripts/terminal/svg.py         cell grid and animations
scripts/terminal/chrome.py      title bar, powerline prompt, tmux, effects
scripts/terminal/logo.py        neofetch logo (recolors tux.svg with the palette)
scripts/terminal/neofetch.py    profile info
scripts/terminal/projects.py    panes and apps
scripts/terminal/render.py      window assembly
scripts/terminal/fmt.py         number formatting and text helpers
assets/strings.json             fixed interface text (en, pt-BR)
assets/logos/                   tux.svg, tux.json, rooster.json, owl.json
assets/fonts/                   JetBrains Mono (OFL), Latin + box-drawing subset
```
