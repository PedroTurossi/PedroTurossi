"""
Terminal chrome: title bar, powerline prompt, tmux status bar and screen
effects (glow, scanlines, vignette).
"""
from .fmt import INF, n2, num


def powerline(c, col, row, segments, direction="right"):
    """Powerline segments. "right" grows rightwards from `col`; "left" ends at `col`.
    Returns {"svg", "end"} or {"svg", "start"}."""
    y0 = n2(c.top(row) + 3)
    h = n2(c.lh - 6)
    widths = [len(s["text"]) + 2 for s in segments]
    out = ""

    if direction == "right":
        x = col
        for i, seg in enumerate(segments):
            start = x if i == 0 else x - 1            # covers the previous arrow cell
            w = widths[i] + (0 if i == 0 else 1)
            out += f'<rect x="{num(c.X(start))}" y="{num(y0)}" width="{num(n2(w * c.cw))}" height="{num(h)}" fill="{seg["bg"]}"/>'
            if i > 0:
                out += _arrow_right(c, x - 1, y0, h, segments[i - 1]["bg"])
            out += c.text(x + 1, row, seg["text"], seg["fg"], weight=700 if seg.get("bold") else None)
            x += widths[i] + 1
        out += _arrow_right(c, x - 1, y0, h, segments[-1]["bg"])
        return {"svg": out, "end": x}

    # layout: [arrow0][seg0][arrow1][seg1]... ending at `col`
    total = sum(widths) + len(segments)
    start = col - total
    x = start
    arrows = []
    for i, seg in enumerate(segments):
        arrows.append((x, seg["bg"]))
        seg_start = x + 1
        cover = widths[i] + (1 if i < len(segments) - 1 else 0)   # covers the next arrow
        out += f'<rect x="{num(c.X(seg_start))}" y="{num(y0)}" width="{num(n2(cover * c.cw))}" height="{num(h)}" fill="{seg["bg"]}"/>'
        out += c.text(seg_start + 1, row, seg["text"], seg["fg"], weight=700 if seg.get("bold") else None)
        x = seg_start + widths[i]
    for cell, color in arrows:
        out += _arrow_left(c, cell + 1, y0, h, color)
    return {"svg": out, "start": start}


def _arrow_right(c, col, y0, h, color):
    x = c.X(col)
    return f'<polygon points="{num(x)},{num(y0)} {num(n2(x + c.cw))},{num(n2(y0 + h / 2))} {num(x)},{num(n2(y0 + h))}" fill="{color}"/>'


def _arrow_left(c, col, y0, h, color):
    x = c.X(col)
    return f'<polygon points="{num(x)},{num(y0)} {num(n2(x - c.cw))},{num(n2(y0 + h / 2))} {num(x)},{num(n2(y0 + h))}" fill="{color}"/>'


def prompt(c, cfg, row, directory, clock, time, command=None):
    """Full prompt: user, directory, clock on the right and a typed command."""
    T = c.T
    left = powerline(c, 0, row, [
        {"text": f'{cfg["prompt"]["user"]}@{cfg["prompt"]["host"]}', "fg": T["background"], "bg": T["accent"], "bold": True},
        {"text": directory, "fg": T["text"], "bg": T["border"]},
    ])
    right = powerline(c, c.cols, row, [{"text": clock, "fg": T["soft"], "bg": T["raised"]}], "left")["svg"] if clock else ""
    base = c.glow(left["svg"]) + right

    if not command:
        return {"svg": c.reveal(base, time), "cmdCol": left["end"] + 1, "end": time}

    col = left["end"] + 1
    start = time + 0.3 * c.k
    typing_svg, typing_end = c.typed(col, row, command, T["bright"], start, 0.05 * c.k, weight=700)
    cursor = ""
    if c.animate:
        values = ";".join(num(c.X(col + i)) for i in range(len(command) + 1))
        cursor = (f'<rect x="{num(c.X(col))}" y="{num(n2(c.top(row) + 2))}" width="{num(n2(c.cw))}" height="{num(n2(c.lh - 4))}" fill="{T["cursor"]}">'
                  f'<animate attributeName="x" values="{values}" begin="{c.at(start)}" dur="{c.at(len(command) * 0.05 * c.k)}" calcMode="discrete" fill="freeze"/>'
                  f'<set attributeName="visibility" to="hidden" begin="{c.at(typing_end + 0.15 * c.k)}" fill="freeze"/></rect>')
    return {"svg": c.reveal(base + cursor, time) + typing_svg, "cmdCol": col, "end": typing_end + 0.25 * c.k}


def tmux_bar(c, cfg, row, S, windows, sync, repos):
    """tmux status bar; the active window changes as the animation progresses."""
    T = c.T
    y = c.top(row)
    out = f'<rect x="0" y="{num(y)}" width="{num(c.width)}" height="{num(c.lh)}" fill="{T["raised"]}"/>'

    session = powerline(c, 0, row, [{"text": cfg["prompt"]["host"], "fg": T["background"], "bg": T["ok"], "bold": True}])
    out += session["svg"]

    col = session["end"] + 1
    for i, win in enumerate(windows):
        label = f'{i}:{win["name"]}'
        w = len(label) + 2
        active = (f'<rect x="{num(c.X(col))}" y="{num(n2(y + 3))}" width="{num(n2(w * c.cw))}" height="{num(n2(c.lh - 6))}" fill="{T["accent"]}"/>'
                  + c.text(col + 1, row, f"{label}*", T["background"], weight=700))
        idle = c.text(col + 1, row, label, T["soft"])
        if win["from"] is None:
            out += idle
        else:
            out += c.during(idle, 0, win["from"]) + c.during(active, win["from"], win["to"])
            if win["to"] != INF:
                out += c.during(idle, win["to"], INF)
        col += w + 1

    out += powerline(c, c.cols, row, [
        {"text": f'{repos} {S["tmux"]["repos"]}', "fg": T["soft"], "bg": T["border"]},
        {"text": sync, "fg": T["text"], "bg": T["faint"]},
        {"text": cfg["username"], "fg": T["background"], "bg": T["prompt"], "bold": True},
    ], "left")["svg"]
    return out


def title_bar(c, cfg, W):
    T = c.T
    cy = c.titleH / 2
    dots = "".join(f'<circle cx="{22 + i * 20}" cy="{num(cy)}" r="6" fill="{color}"/>'
                   for i, color in enumerate([T["error"], T["accent"], T["ok"]]))
    title = f'{cfg["prompt"]["user"]}@{cfg["prompt"]["host"]}: ~'
    return (f'<rect width="{num(W)}" height="{c.titleH}" fill="{T["surface"]}"/>'
            f'<line x1="0" y1="{num(c.titleH - 0.5)}" x2="{num(W)}" y2="{num(c.titleH - 0.5)}" stroke="{T["raised"]}"/>' + dots
            + c.glyphs(W / 2, cy + 4.5, title, T["soft"], size=13, anchor="middle", weight=700))


def effect_defs(effects):
    defs = ""
    if effects.get("glow"):
        defs += ('<filter id="glow" x="-5%" y="-20%" width="110%" height="140%">'
                 '<feGaussianBlur in="SourceGraphic" stdDeviation="2.2" result="blur"/>'
                 '<feComponentTransfer in="blur" result="soft"><feFuncA type="linear" slope="0.55"/></feComponentTransfer>'
                 '<feMerge><feMergeNode in="soft"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')
    if effects.get("scanlines"):
        defs += '<pattern id="scan" width="6" height="3" patternUnits="userSpaceOnUse"><rect width="6" height="1" fill="#000" fill-opacity="0.16"/></pattern>'
    if effects.get("vignette"):
        defs += ('<radialGradient id="vignette" cx="50%" cy="50%" r="75%">'
                 '<stop offset="55%" stop-color="#000" stop-opacity="0"/><stop offset="100%" stop-color="#000" stop-opacity="0.38"/></radialGradient>')
    return defs


def effect_overlays(effects, W, H):
    out = ""
    if effects.get("scanlines"):
        out += f'<rect width="{num(W)}" height="{num(H)}" fill="url(#scan)" pointer-events="none"/>'
    if effects.get("vignette"):
        out += f'<rect width="{num(W)}" height="{num(H)}" fill="url(#vignette)" pointer-events="none"/>'
    return out
