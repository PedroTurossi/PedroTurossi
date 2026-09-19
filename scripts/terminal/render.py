"""Assembles the terminal window: boot, neofetch, project panes and the tmux bar."""
import base64
from datetime import datetime, timezone
from pathlib import Path

from .chrome import effect_defs, effect_overlays, prompt, title_bar, tmux_bar
from .fmt import INF, esc, fill, format_int, format_pct, jround, num, warn
from .logo import load_logo
from .neofetch import render_neofetch
from .projects import render_projects
from .svg import Canvas
from .theme import resolve_theme

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:  # pragma: no cover
    ZoneInfo = None
    ZoneInfoNotFoundError = Exception


def speed_factor(speed):
    presets = {"slow": 1.6, "medium": 1, "fast": 0.55}
    if isinstance(speed, (int, float)) and not isinstance(speed, bool) and speed > 0:
        return 1 / speed
    if isinstance(speed, str) and speed in presets:
        return presets[speed]
    warn(f'invalid animation.speed "{speed}", using "medium".')
    return 1


def font_faces(root):
    css = ""
    for weight in (400, 700):
        path = Path(root) / "assets" / "fonts" / f"jetbrains-mono-{weight}.woff2"
        if not path.exists():
            continue
        b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        css += f"@font-face{{font-family:'TermMono';font-weight:{weight};src:url(data:font/woff2;base64,{b64}) format('woff2');}}"
    return css


def time_parts(iso, tz_name):
    moment = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    try:
        moment = moment.astimezone(ZoneInfo(tz_name))
    except (ZoneInfoNotFoundError, ValueError, TypeError):
        warn(f'timezone "{tz_name}" not found, using UTC.')
        moment = moment.astimezone(timezone.utc)
    return {"year": f"{moment.year:04d}", "month": f"{moment.month:02d}", "day": f"{moment.day:02d}",
            "hour": f"{moment.hour:02d}", "minute": f"{moment.minute:02d}"}


def render(cfg, state, S, root):
    T = resolve_theme(cfg["theme"])
    effects = cfg["effects"]
    c = Canvas(T, cfg["layout"], cfg["animation"]["enabled"], speed_factor(cfg["animation"]["speed"]), effects["glow"])
    k, animate = c.k, c.animate
    P = T.palette
    locale = cfg["locale"]
    when = time_parts(state["updatedAt"], cfg["timezone"])
    clock = f'{when["hour"]}:{when["minute"]}'
    repos_text = format_int(state.get("repos") or 0, locale)
    variables = {
        "user": cfg["prompt"]["user"], "host": cfg["prompt"]["host"], "username": cfg["username"],
        "repos": repos_text, "languageCount": format_int(state.get("languageCount") or 0, locale),
    }
    logo = load_logo(cfg["neofetch"]["logo"], root)

    # boot
    boot = []
    t = 0.35 * k
    boot_rows = 0
    boot_on = animate and cfg["boot"]["enabled"]
    if boot_on:
        lines = [fill(l, variables) for l in (cfg["boot"].get("lines") or S["boot"])]
        boot.append(c.reveal(c.spans(0, 0, [(fill(S["system"], variables), T["soft"], {"weight": 700})]), t))
        t += 0.3 * k
        for i, text_line in enumerate(lines):
            boot.append(c.reveal(c.spans(0, i + 2, [
                ("[", T["faint"]), ("  OK  ", P["green"], {"weight": 700}), ("] ", T["faint"]), (text_line, T["text"]),
            ]), t))
            t += 0.15 * k
        row = len(lines) + 3
        label = f'{S["session"]} '
        cells = 36
        boot.append(c.reveal(c.text(0, row, label, P["aqua"], weight=700), t))
        bar_svg, bar_end = c.block_bar(len(label), row, cells, 1, P["yellow"], t + 0.1 * k, 0.018 * k)
        boot.append(c.reveal(bar_svg, t))
        t = bar_end + 0.1 * k
        boot.append(c.reveal(c.text(len(label) + cells + 2, row, "100%", P["green"], weight=700), t))
        t += 0.4 * k
        boot_rows = row + 1
    clear_at = t

    # session
    main = []
    row = 0
    t = clear_at + 0.15 * k if boot_on else 0.3 * k
    neofetch_at = t

    neo_prompt = prompt(c, cfg, row, "~", clock, t, cfg["neofetch"]["command"])
    main.append(neo_prompt["svg"])
    t = neo_prompt["end"]
    row += 2

    neo = render_neofetch(c, cfg, state, S, logo, row, t)
    main.append(neo["svg"])
    row += neo["rows"] + 1
    t = neo["end"] + 0.4 * k

    projects_at = None
    if cfg["projects"]["items"]:
        projects_at = t
        proj_prompt = prompt(c, cfg, row, "~", clock, t, cfg["projects"]["command"])
        main.append(proj_prompt["svg"])
        t = proj_prompt["end"]
        row += 2
        projects = render_projects(c, cfg, S, row, t)
        main.append(projects["svg"])
        row += projects["rows"]
        t = projects["end"] + 0.2 * k

    final_prompt = prompt(c, cfg, row, "~/projects" if projects_at is not None else "~", clock, t)
    main.append(final_prompt["svg"])
    main.append(c.reveal(c.cursor(final_prompt["cmdCol"], row, t), t))
    row += 1

    content_rows = max(row, boot_rows)
    W = c.width
    bar = ""
    if effects["statusBar"]:
        bar_row = content_rows + 1
        windows = [{"name": name, "from": None, "to": INF} for name in S["tmux"]["windows"]]
        if boot_on:
            windows[0].update({"from": 0, "to": clear_at})
        windows[1].update({"from": neofetch_at if animate else None, "to": projects_at if projects_at is not None else INF})
        if projects_at is not None:
            windows[2].update({"from": projects_at if animate else 0, "to": INF})
        if not animate:
            windows[2 if projects_at is not None else 1]["from"] = 0
        sync = f'{when["year"]}-{when["month"]}-{when["day"]} {clock}'
        bar = tmux_bar(c, cfg, bar_row, S, windows, sync, repos_text)
        H = jround(c.top(bar_row) + c.lh)
    else:
        H = jround(c.top(content_rows) + 16)

    set_clear = f'<set attributeName="opacity" to="0" begin="{c.at(clear_at)}" fill="freeze"/>'
    boot_group = f'<g>{"".join(boot)}{set_clear}</g>' if boot_on else ""
    main_group = (f'<g opacity="0"><set attributeName="opacity" to="1" begin="{c.at(clear_at)}" fill="freeze"/>{"".join(main)}</g>'
                  if boot_on else f'<g>{"".join(main)}</g>')

    def raw(v):
        return "--" if v is None else num(v)

    description = ". ".join(x for x in [
        cfg["profile"]["name"], cfg["profile"]["description"],
        ", ".join(f'{l["name"]} {format_pct(l["percent"], locale)}%' for l in state["languages"][:cfg["languages"]["count"]]),
        f'{S["labels"]["commits"]}: {raw(state["stats"].get("commits"))}',
        f'{S["labels"]["followers"]}: {raw(state["stats"].get("followers"))}',
        f'{S["labels"]["views"]}: {raw(state["stats"].get("views"))}',
        *[": ".join(v for v in [p.get("name"), p.get("description")] if v) for p in cfg["projects"]["items"]],
    ] if x)

    title = f'{cfg["prompt"]["user"]}@{cfg["prompt"]["host"]}: ~'
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{num(W)}" height="{num(H)}" viewBox="0 0 {num(W)} {num(H)}" role="img" aria-labelledby="title desc">\n'
        f'<title id="title">{esc(title)}</title>\n'
        f'<desc id="desc">{esc(description)}</desc>\n'
        f"<style>{font_faces(root)}text{{font-family:'TermMono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:{num(c.fs)}px;white-space:pre;}}</style>\n"
        f'<defs><clipPath id="window"><rect width="{num(W)}" height="{num(H)}" rx="10"/></clipPath>{effect_defs(effects)}{"".join(c.defs)}</defs>\n'
        f'<g clip-path="url(#window)">\n'
        f'<rect width="{num(W)}" height="{num(H)}" fill="{T["background"]}"/>\n'
        f"{title_bar(c, cfg, W)}\n"
        f"{boot_group}\n"
        f"{main_group}\n"
        f"{bar}\n"
        f"{effect_overlays(effects, W, H)}\n"
        f"</g>\n"
        f'<rect x="0.5" y="0.5" width="{num(W - 1)}" height="{num(H - 1)}" rx="9.5" fill="none" stroke="{T["raised"]}"/>\n'
        f"</svg>\n"
    )
