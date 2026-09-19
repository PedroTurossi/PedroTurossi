"""
Projects as TUI panes (2 per row). Each pane has its path on the top border,
a name and description, a terminal "app" running below, and the status on the
bottom border.

Built-in apps: rhythm, pipeline, homelab, open. A list of ASCII lines also works.
"""
import math

from .chrome import powerline
from .fmt import INF, jround, n2, num, warn, wrap

SPARK = "▁▂▃▄▅▆▇█"


def _rng(seed):
    state = [seed % 2**32]

    def rand():
        state[0] = (state[0] * 1664525 + 1013904223) % 2**32
        return state[0] / 2**32
    return rand


def _spark_series(seed, base, spread, size):
    rand = _rng(seed)
    level = base
    out = []
    for _ in range(size):
        level = max(0, min(7, level + jround((rand() - 0.5) * spread)))
        if rand() < 0.15:
            level = max(0, min(7, base + jround((rand() - 0.5) * spread * 2)))
        out.append(SPARK[level])
    return "".join(out)


def _loop(c, attr, values, time, dur):
    """Discrete loop on an attribute."""
    return f'<animate attributeName="{attr}" values="{values}" begin="{c.at(time)}" dur="{c.at(dur)}" calcMode="discrete" repeatCount="indefinite"/>'


# ───────────────────────────── apps ─────────────────────────────

def rhythm(c, S, a, time):
    """Rhythm game: 9 lanes, notes falling to the strike line, keys A S D F G H J K L."""
    T, k, P = c.T, c.k, c.T.palette
    S = S["apps"]["rhythm"]
    lanes = 9
    tw = lanes * 4 + 1
    ox = a["col"] + math.floor((a["w"] - tw) / 2)
    lane_colors = [P["green"], P["red"], P["yellow"], P["blue"], P["orange"], P["purple"], P["aqua"], P["yellow"], P["green"]]
    keys = "ASDFGHJKL"
    first, last, strike = a["row"] + 1, a["row"] + 5, a["row"] + 6
    rows = []

    rows.append(
        c.spans(a["col"], a["row"], [(S["score"], T["muted"], {"weight": 700}), (" 0048210", P["yellow"], {"weight": 700})])
        + c.spans(a["col"] + a["w"] - len(S["combo"]) - 4, a["row"], [(S["combo"], T["muted"], {"weight": 700}), (" x12", P["orange"], {"weight": 700})])
    )

    def lane(i):
        return ox + i * 4 + 1

    tint = ""
    for i in range(lanes):
        tint += (f'<rect x="{num(c.X(lane(i)))}" y="{num(c.top(first))}" width="{num(n2(3 * c.cw))}" '
                 f'height="{num(n2(6 * c.lh))}" fill="{lane_colors[i]}" fill-opacity="0.08"/>')
    sep = "".join(("┃" if i in (0, tw - 1) else "│") if i % 4 == 0 else " " for i in range(tw))
    for r in range(first, last + 1):
        rows.append((tint if r == first else "") + c.tall(ox, r, sep, T["faint"]))
    rows.append(c.tall(ox, strike, "╞" + "╪".join(["═══"] * lanes) + "╡", T["soft"]))

    rows.append("".join(c.text(lane(i) + 1, a["row"] + 7, keys[i], lane_colors[i], weight=700) for i in range(lanes)))

    # song progress: the elapsed clock and the bar share the same steps, so they stay in sync
    bar_cells = a["w"] - 14
    bar = "━" * bar_cells
    song_seconds = 187

    def clock_at(i):
        secs = jround((i / bar_cells) * song_seconds)
        return f"{secs // 60}:{str(secs % 60).zfill(2)}"

    static_step = math.floor(bar_cells * 0.45)
    rows.append(
        c.text(a["col"], a["row"] + 8, "▶", P["green"])
        + ("" if c.animate else c.text(a["col"] + 2, a["row"] + 8, clock_at(static_step), T["soft"]))
        + c.text(a["col"] + 7, a["row"] + 8, bar, T["border"])
        + c.text(a["col"] + 7 + bar_cells + 2, a["row"] + 8, clock_at(bar_cells), T["soft"])
    )

    step = 0.2 * k
    period = 16
    chart = [(4, 0), (2, 2), (6, 2), (0, 4), (8, 6), (3, 8), (5, 8), (1, 10), (7, 12), (4, 13), (2, 14)]
    overlay = ""

    if c.animate:
        hidden_y = c.tallY(a["row"] - 3)
        ys = [c.tallY(r) for r in range(first, strike + 1)]
        while len(ys) < period:
            ys.append(hidden_y)
        ys_values = ";".join(num(y) for y in ys)
        notes = ""
        flashes = ""
        for n, (ln, offset) in enumerate(chart):
            begin = time + offset * step
            notes += c.glyphs(c.X(lane(ln)), hidden_y, "▄▄▄", lane_colors[ln], size=c.lh / 1.32 + 0.15, squeeze=True, seal=True) \
                .replace("</text>", f'{_loop(c, "y", ys_values, begin, period * step)}</text>', 1)
            hit = begin + 5 * step
            key_x = c.X(lane(ln))
            blink = (f'<animate attributeName="opacity" values="1;0" keyTimes="0;0.08" begin="{c.at(hit)}" '
                     f'dur="{c.at(period * step)}" calcMode="discrete" repeatCount="indefinite"/>')
            flashes += (f'<rect x="{num(key_x)}" y="{num(n2(c.top(a["row"] + 7) + 2))}" width="{num(n2(3 * c.cw))}" '
                        f'height="{num(n2(c.lh - 4))}" fill="{lane_colors[ln]}" opacity="0">{blink}</rect>'
                        f'<g opacity="0">{c.text(lane(ln) + 1, a["row"] + 7, keys[ln], T["background"], weight=700)}{blink}</g>')
            if n == 0:
                flashes += (f'<g opacity="0">{c.text(a["col"] + math.floor((a["w"] - len(S["hit"])) / 2), a["row"], S["hit"], P["aqua"], weight=700)}'
                            f'<animate attributeName="opacity" values="1;0" keyTimes="0;0.2" begin="{c.at(hit)}" '
                            f'dur="{c.at(period * step)}" calcMode="discrete" repeatCount="indefinite"/></g>')
        overlay += c.clip_window(ox, first, tw, 6, c.glow(notes)) + flashes

        # song bar advancing in a loop
        song_dur = bar_cells * 0.6
        cid = c.id("song")
        x0 = c.X(a["col"] + 7)
        widths = ";".join(num(n2(i * c.cw)) for i in range(bar_cells + 1))
        c.defs.append(f'<clipPath id="{cid}"><rect x="{num(x0)}" y="{num(c.top(a["row"] + 8))}" height="{num(c.lh)}" width="0">'
                      f'{_loop(c, "width", widths, time, song_dur)}</rect></clipPath>')
        overlay += f'<g clip-path="url(#{cid})">{c.text(a["col"] + 7, a["row"] + 8, bar, P["yellow"])}</g>'

        # elapsed clock: a strip of every "m:ss" value, slid 4 cells per step inside a 4-cell window
        strip = "".join(clock_at(i) for i in range(bar_cells + 1))
        clock_col = a["col"] + 2
        xs = ";".join(num(n2(c.X(clock_col) - i * 4 * c.cw)) for i in range(bar_cells + 1))
        clock = c.text(clock_col, a["row"] + 8, strip, T["soft"]).replace("</text>", f'{_loop(c, "x", xs, time, song_dur)}</text>', 1)
        overlay += c.clip_window(clock_col, a["row"] + 8, 4, 1, clock)
    else:
        notes = "".join(c.tall(lane(ln), first + (offset % 5), "▄▄▄", lane_colors[ln], seal=True) for ln, offset in chart[:7])
        overlay += notes + c.text(a["col"] + 7, a["row"] + 8, bar[:static_step], P["yellow"])

    return {"rows": rows, "overlay": overlay}


def pipeline(c, S, a, time):
    """htop-style production panel: orders, stages, progress and a scrolling log."""
    T, k, P = c.T, c.k, c.T.palette
    S = S["apps"]["pipeline"]
    rows = []
    cols = {"id": a["col"] + 1, "stage": a["col"] + 10, "bar": a["col"] + 24, "pct": a["col"] + 35, "icon": a["col"] + a["w"] - 2}

    rows.append(
        c.bg(a["col"], a["row"], a["w"], T["raised"])
        + c.text(cols["id"], a["row"], S["headers"][0], T["accent"], weight=700)
        + c.text(cols["stage"], a["row"], S["headers"][1], T["accent"], weight=700)
        + c.text(cols["bar"], a["row"], S["headers"][2], T["accent"], weight=700)
    )

    orders = [
        {"id": "OP-0917", "progress": 1, "color": P["green"], "state": "done"},
        {"id": "OP-0918", "progress": 0.76, "color": P["yellow"], "state": "run"},
        {"id": "OP-0919", "progress": 0.42, "color": P["orange"], "state": "run"},
        {"id": "OP-0920", "progress": 0.08, "color": P["purple"], "state": "wait"},
    ]
    overlay = ""
    for i, o in enumerate(orders):
        r = a["row"] + 1 + i
        bar_svg, _ = c.block_bar(cols["bar"], r, 10, o["progress"], o["color"], time + (0.3 + i * 0.1) * k, 0.06 * k)
        if o["state"] == "done":
            icon = c.text(cols["icon"], r, "✓", P["green"], weight=700)
        elif o["state"] == "wait":
            icon = c.text(cols["icon"], r, "·", T["faint"], weight=700)
        else:
            icon = c.ticker(cols["icon"], r, "▖▘▝▗▖", 1, P["yellow"], 4, 0.15 + i * 0.03, time, weight=700)
        rows.append(
            c.text(cols["id"], r, o["id"], T["muted"])
            + c.text(cols["stage"], r, S["stages"][i], T["text"])
            + bar_svg
            + c.text(cols["pct"], r, f'{jround(o["progress"] * 100)}%'.rjust(4), T["bright"], weight=700)
            + icon
        )

    rows.append(c.tall(a["col"], a["row"] + 5, "─" * a["w"], T["border"]))

    # scrolling log
    logs = S["log"]
    icons = [("✓", P["green"]), ("›", P["yellow"]), ("›", P["orange"]), ("↗", P["aqua"])]
    stamps = ["21:50:12", "21:50:31", "21:51:04", "21:51:47"]

    def log_line(i, r):
        n = i % len(logs)
        return c.spans(a["col"] + 1, r, [
            (stamps[n], T["faint"]), (" ", T["text"]), (icons[n][0], icons[n][1], {"weight": 700}), (" ", T["text"]),
            (logs[n][0], T["text"]), ("  ", T["text"]), (logs[n][1], T["muted"]),
        ])

    rows.append("")
    rows.append("")
    if c.animate:
        strip = "".join(log_line(i, a["row"] + 6 + i) for i in range(len(logs) + 2))
        values = ";".join(f"0,{num(n2(-i * c.lh))}" for i in range(len(logs)))
        overlay += c.clip_window(a["col"], a["row"] + 6, a["w"], 2,
                                 f'<g>{strip}<animateTransform attributeName="transform" type="translate" values="{values}" '
                                 f'begin="{c.at(time + 0.8 * k)}" dur="{c.at(len(logs) * 1.6)}" calcMode="discrete" repeatCount="indefinite"/></g>')
    else:
        overlay += log_line(0, a["row"] + 6) + log_line(1, a["row"] + 7)

    vol_svg, _ = c.block_bar(a["col"] + 16, a["row"] + 8, a["w"] - 25, 0.95, P["green"], time + 0.4 * k, 0.03 * k)
    rows.append(
        c.spans(a["col"] + 1, a["row"] + 8, [(S["volumes"], T["muted"]), (" 38/40", T["bright"], {"weight": 700})])
        + vol_svg
        + c.spans(a["col"] + a["w"] - 7, a["row"] + 8, [("▲ ", P["aqua"]), (S["rate"], P["aqua"], {"weight": 700})])
    )
    return {"rows": rows, "overlay": overlay, "overlayRow": 6}


def homelab(c, S, a, time):
    """Homelab: service status with CPU sparklines and a port scan."""
    T, k, P = c.T, c.k, c.T.palette
    S = S["apps"]["homelab"]
    rows = []
    cols = {"name": a["col"] + 1, "state": a["col"] + 13, "cpu": a["col"] + 24, "mem": a["col"] + 37}

    rows.append(
        c.spans(a["col"], a["row"], [("❯ ", P["aqua"], {"weight": 700}), (S["command"], T["bright"], {"weight": 700})])
        + c.spans(a["col"] + a["w"] - 6, a["row"], [("4/5 ", P["green"], {"weight": 700}), ("●", P["green"])])
    )
    header_cols = [cols["name"], cols["state"], cols["cpu"], cols["mem"]]
    rows.append("".join(c.text(header_cols[i], a["row"] + 1, h, T["muted"], weight=700) for i, h in enumerate(S["headers"])))

    services = [
        {"name": "hypervisor", "state": "up", "base": 3, "spread": 3, "mem": 0.62},
        {"name": "firewall", "state": "up", "base": 1, "spread": 2, "mem": 0.21},
        {"name": "attack-box", "state": "scan", "base": 5, "spread": 4, "mem": 0.78},
        {"name": "gitea", "state": "up", "base": 1, "spread": 3, "mem": 0.34},
        {"name": "media", "state": "idle", "base": 0, "spread": 1, "mem": 0.12},
    ]
    state_color = {"up": P["green"], "scan": P["orange"], "idle": T["muted"]}
    window = cols["mem"] - cols["cpu"] - 2
    steps = 24

    for i, svc in enumerate(services):
        r = a["row"] + 2 + i
        color = state_color[svc["state"]]
        series = _spark_series(i * 97 + 11, svc["base"], svc["spread"], steps)
        spark_color = T["faint"] if svc["state"] == "idle" else P["orange"] if svc["state"] == "scan" else P["aqua"]
        spark = c.ticker(cols["cpu"], r, series + series[:window], window, spark_color, steps, 0.35 + i * 0.04, time + 0.2 * k)
        if c.animate and svc["state"] != "idle":
            dot = f'<g>{c.text(cols["state"], r, "●", color)}{_loop(c, "opacity", "1;0.35", time, 0.6 if svc["state"] == "scan" else 1.8)}</g>'
        else:
            dot = c.text(cols["state"], r, "●", color)
        mem_svg, _ = c.block_bar(cols["mem"], r, 7, svc["mem"], P["red"] if svc["mem"] > 0.7 else P["blue"], time + 0.3 * k, 0.05 * k)
        rows.append(c.text(cols["name"], r, svc["name"], T["text"]) + dot
                    + c.text(cols["state"] + 2, r, S["states"][svc["state"]], color) + spark + mem_svg)

    rows.append(c.spans(a["col"], a["row"] + 7, [("❯ ", P["aqua"], {"weight": 700}), (S["scan"], T["text"])]))
    ports = [("22", "ssh"), ("53", "dns"), ("443", "https"), ("8080", "http")]
    segs = []
    for port, name in ports:
        segs += [(port, P["aqua"], {"weight": 700}), (f"/{name}  ", T["muted"])]
    rows.append(c.spans(a["col"] + 2, a["row"] + 8, segs))
    return {"rows": rows, "overlay": ""}


def open_app(c, S, a, time):
    """Open project: creates the folder and opens nvim while the first line is typed."""
    T, k, P = c.T, c.k, c.T.palette
    S = S["apps"]["open"]
    rows = []
    overlay = ""

    mk_svg, mk_end = c.typed(a["col"] + 2, a["row"], S["mkdir"], T["text"], time + 0.2 * k, 0.03 * k)
    nv_svg, nv_end = c.typed(a["col"] + 2, a["row"] + 1, f'nano -l {S["file"]}', T["text"], mk_end + 0.3 * k, 0.05 * k)
    rows.append(c.text(a["col"], a["row"], "❯", P["aqua"], weight=700))
    rows.append(c.text(a["col"], a["row"] + 1, "❯", P["aqua"], weight=700))
    overlay += mk_svg + nv_svg

    vim_at = nv_end + 0.3 * k
    heading = f'# {S["heading"]}'
    buffer = c.bg(a["col"], a["row"] + 2, a["w"], T["background"], 6)
    buffer += c.bg(a["col"], a["row"] + 2, 4, T["surface"], 6)
    buffer += c.text(a["col"], a["row"] + 2, "  1", T["accent"], weight=700)
    for r in range(3, 8):
        buffer += c.text(a["col"] + 1, a["row"] + r, "~", P["blue_dim"], weight=700)

    text_col = a["col"] + 5
    typing_svg, typing_end = c.grow(
        c.spans(text_col, a["row"] + 2, [("# ", P["orange"], {"weight": 700}), (S["heading"], P["yellow"], {"weight": 700})]),
        text_col, a["row"] + 2, len(heading), vim_at + 0.5 * k, 0.07 * k,
    )
    if c.animate:
        xs = ";".join(num(c.X(text_col + i)) for i in range(len(heading) + 1))
        cursor = (f'<rect x="{num(c.X(text_col))}" y="{num(n2(c.top(a["row"] + 2) + 2))}" width="{num(n2(c.cw))}" height="{num(n2(c.lh - 4))}" fill="{T["cursor"]}">'
                  f'<animate attributeName="x" values="{xs}" begin="{c.at(vim_at + 0.5 * k)}" dur="{c.at(len(heading) * 0.07 * k)}" calcMode="discrete" fill="freeze"/>'
                  f'<animate attributeName="opacity" values="1;0" dur="1.1s" begin="{c.at(typing_end + 0.4 * k)}" calcMode="discrete" repeatCount="indefinite"/></rect>')
    else:
        cursor = c.cursor(text_col + len(heading), a["row"] + 2, 0)

    # statusline
    def mode(label, bg):
        return powerline(c, a["col"], a["row"] + 8, [
            {"text": label, "fg": T["background"], "bg": bg, "bold": True},
            {"text": f'{S["file"]} [+]', "fg": T["text"], "bg": T["border"]},
        ])["svg"]

    right = powerline(c, a["col"] + a["w"], a["row"] + 8, [
        {"text": "markdown", "fg": T["soft"], "bg": T["raised"]},
        {"text": f"1:{len(heading) + 1}", "fg": T["background"], "bg": T["soft"], "bold": True},
    ], "left")["svg"]
    status = (c.bg(a["col"], a["row"] + 8, a["w"], T["surface"]) + right
              + c.during(mode("NORMAL", P["green"]), 0, vim_at + 0.5 * k)
              + c.during(mode("INSERT", P["blue"]), vim_at + 0.5 * k, typing_end + 0.3 * k)
              + c.during(mode("NORMAL", P["green"]), typing_end + 0.3 * k, INF))

    overlay += c.reveal(buffer + typing_svg + cursor + status, vim_at)
    rows += [""] * 7
    return {"rows": rows, "overlay": overlay}


def ascii_art(c, a, lines):
    """Custom art: ASCII lines centered in the app area."""
    shown = [str(l)[:a["w"]] for l in lines[:a["h"]]]
    block_w = max([0] + [len(l) for l in shown])
    col = a["col"] + math.floor((a["w"] - block_w) / 2)
    row0 = a["row"] + math.floor((a["h"] - len(shown)) / 2)
    rows = []
    for i in range(a["h"]):
        j = i - (row0 - a["row"])
        line = shown[j] if 0 <= j < len(shown) else ""
        rows.append(c.text(col, a["row"] + i, line, c.T["soft"]) if line else "")
    return {"rows": rows, "overlay": ""}


def _status(T, cfg, key):
    """Looks the project status up in projects.statuses: (text shown, color)."""
    if not key:
        return "", T.palette["green"]
    entry = (cfg["projects"].get("statuses") or {}).get(str(key).lower())
    if not entry:
        return str(key), T.palette["green"]
    color = T.color(entry.get("color"))
    if not color:
        warn(f'projects.statuses: color "{entry.get("color")}" is neither a hex color nor a palette name, using green.')
        color = T.palette["green"]
    return entry["text"], color


def _project_border_color(T, item, fallback, label):
    """Resolves an individual project's border color."""
    value = item.get("borderColor", item.get("color"))
    if value is None:
        return fallback
    color = T.color(value)
    if not color:
        warn(f'projects.items: borderColor "{value}" in "{label}" is neither a hex color nor a palette name, using the default border color.')
        return fallback
    return color


APPS = {"rhythm": rhythm, "pipeline": pipeline, "homelab": homelab, "open": open_app}


# ───────────────────────────── panes ─────────────────────────────

def render_projects(c, cfg, S, start_row, start_time):
    T, k, P = c.T, c.k, c.T.palette
    items = [it for it in cfg["projects"]["items"] if it]
    gap = 2
    pane_cols = math.floor((c.cols - gap) / 2)
    inner_w = pane_cols - 4
    app_rows = 9
    border_specs = cfg["projects"].get("borderColors") or ["yellow", "aqua", "orange", "purple", "green", "blue"]
    accents = []
    for spec in border_specs:
        color = T.color(spec)
        if color:
            accents.append(color)
        else:
            warn(f'projects.borderColors: "{spec}" is neither a hex color nor a palette name, ignored.')
    if not accents:
        accents = [P["yellow"], P["aqua"], P["orange"], P["purple"], P["green"], P["blue"]]

    panes = []
    for i, item in enumerate(items):
        desc = wrap(item["description"], inner_w) if item.get("description") else []
        head = 1 + len(desc) + (1 if item.get("url") else 0)
        label = item.get("name") or item.get("path") or f"project {i + 1}"
        fallback = accents[i % len(accents)]
        accent = _project_border_color(T, item, fallback, label)
        panes.append({"item": item, "desc": desc, "head": head, "accent": accent, "index": i + 1})

    parts = []
    t = start_time
    row = start_row

    for p in range(0, len(panes), 2):
        pair = panes[p:p + 2]
        head_rows = max(x["head"] for x in pair)
        total = 1 + head_rows + 1 + app_rows + 1

        for j, pane in enumerate(pair):
            col = j * (pane_cols + gap)
            inner = col + 2
            item, accent = pane["item"], pane["accent"]
            last = col + pane_cols - 1
            sep_row = row + 1 + head_rows
            bottom_row = row + total - 1

            # background, borders and path:  ╭─ path ───────── idx ─╮
            path = f' {item.get("path") if item.get("path") is not None else "~/projects"} '
            idx = f' {pane["index"]} '
            fill_top = max(1, pane_cols - 4 - len(path) - len(idx))
            frame = (f'<rect x="{num(c.X(col))}" y="{num(c.top(row))}" width="{num(n2(pane_cols * c.cw))}" '
                     f'height="{num(n2(total * c.lh))}" fill="{T["surface"]}"/>')
            sides = ""
            for r in range(row + 1, bottom_row):
                if r == sep_row:
                    continue
                sides += c.tall(col, r, "│", accent) + c.tall(last, r, "│", accent)
            frame += c.glow(
                c.tall(col, row, "╭─", accent)
                + c.tall(col + 2 + len(path), row, "─" * fill_top, accent)
                + c.tall(last - 1, row, "─╮", accent)
                + sides
                + c.tall(col, sep_row, "├" + "─" * (pane_cols - 2) + "┤", accent)
            )
            frame += c.text(col + 2 + len(path) + fill_top, row, idx, T["bright"], weight=700)
            parts.append(c.reveal(frame, t))

            path_svg, path_end = c.typed(col + 2, row, path, accent, t + 0.05 * k, 0.025 * k, weight=700)
            parts.append(c.reveal(path_svg, t) if c.animate else path_svg)
            t = path_end + 0.1 * k

            # header
            r = row + 1
            parts.append(c.reveal(c.text(inner, r, item.get("name") if item.get("name") is not None else "", T["bright"], weight=700), t))
            t += 0.06 * k
            r += 1
            for text_line in pane["desc"]:
                parts.append(c.reveal(c.text(inner, r, text_line, T["soft"]), t))
                t += 0.06 * k
                r += 1
            if item.get("url"):
                parts.append(c.reveal(c.spans(inner, r, [("↗ ", P["blue"]), (item["url"], P["blue"])]), t))
                t += 0.06 * k

            # app
            area = {"col": inner, "row": sep_row + 1, "w": inner_w, "h": app_rows}
            art = item.get("art")
            if isinstance(art, list):
                app = ascii_art(c, area, art)
            elif isinstance(art, str) and art in APPS:
                app = APPS[art](c, S, area, t)
            else:
                if art:
                    warn(f'projects: unknown app "{art}" in "{item.get("name") or item.get("path")}". '
                         f'Options: {", ".join(APPS)} or a list of ASCII lines.')
                app = open_app(c, S, area, t)
            for i, svg in enumerate(app["rows"]):
                if svg:
                    parts.append(c.reveal(svg, t + i * 0.05 * k))
            if app["overlay"]:
                parts.append(c.reveal(app["overlay"], t + app.get("overlayRow", 0) * 0.05 * k))
            t += len(app["rows"]) * 0.05 * k

            # footer with status and stack
            status_text, status_color = _status(T, cfg, item.get("status"))
            status = f" ● {status_text} " if status_text else ""
            stack = f' {item["stack"]} ' if item.get("stack") else ""
            fill_bottom = max(1, pane_cols - 4 - len(status) - len(stack))
            footer = (
                c.glow(
                    c.tall(col, bottom_row, "╰─", accent)
                    + c.tall(col + 2 + len(status), bottom_row, "─" * fill_bottom, accent)
                    + c.tall(last - 1, bottom_row, "─╯", accent)
                )
                + (c.spans(col + 2, bottom_row, [(" ● ", status_color), (f"{status_text} ", status_color, {"weight": 700})]) if status else "")
                + (c.text(col + 2 + len(status) + fill_bottom, bottom_row, stack, T["soft"]) if stack else "")
            )
            parts.append(c.reveal(footer, t))
            t += 0.25 * k

        row += total + 1

    return {"svg": "".join(parts), "rows": row - start_row, "end": t}
