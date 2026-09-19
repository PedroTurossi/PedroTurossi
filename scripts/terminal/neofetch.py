"""
Neofetch output: logo on the left, profile info on the right.

Profile lines use neofetch's own format, `Key: value`, with no column alignment.
Languages are the exception: they render as an aligned table of bars.
All numbers and languages come from data/telemetry.json, which the workflow refreshes.
"""
from .fmt import format_int, format_pct, wrap
from .logo import logo_row, logo_size

NEOFETCH_FIELDS = ["name", "description", "focus", "extra", "repos", "commits", "followers", "views", "languages", "palette"]


def render_neofetch(c, cfg, state, S, logo, start_row, start_time):
    T = c.T
    P = T.palette
    k = c.k
    locale = cfg["locale"]
    size_cols, size_rows = logo_size(logo)
    ic = size_cols + 3 if size_cols else 0
    labels = S["labels"]

    def label_of(field):
        return labels.get(field, field)

    def fmt(v):
        return "--" if v is None else format_int(v, locale)

    # Key colors by group: profile in yellow, numbers in aqua, languages in orange.
    key_color = {"profile": T["accent"], "stats": T["prompt"], "languages": T["secondary"]}

    def key(row, label, group):
        """Draws `Key:` and returns (svg, column where the value starts)."""
        svg = c.text(ic, row, label, key_color[group], weight=700) + c.text(ic + len(label), row, ":", T["soft"])
        return svg, ic + len(label) + 2

    info = []
    user, host = cfg["prompt"]["user"], cfg["prompt"]["host"]
    title = f"{user}@{host}"
    info.append(lambda r, t: c.glow(c.spans(ic, r, [
        (user, T["accent"], {"weight": 700}), ("@", T["soft"]), (host, T["prompt"], {"weight": 700}),
    ])))
    info.append(lambda r, t: c.tall(ic, r, "─" * len(title), T["faint"]))

    def line(label, group, value, color, weight=None):
        """A single `Key: value` line."""
        def draw(r, t):
            svg, value_col = key(r, label, group)
            return svg + c.text(value_col, r, value, color, weight=weight)
        info.append(draw)

    def wrapped(label, group, text, color):
        """`Key: value` where the value wraps; continuation lines start under the value."""
        value_col = ic + len(label) + 2
        for i, part in enumerate(wrap(text, c.cols - value_col)):
            info.append(lambda r, t, i=i, part=part:
                        (key(r, label, group)[0] if i == 0 else "") + c.text(value_col, r, part, color))

    def b_name():
        if cfg["profile"]["name"]:
            line(label_of("name"), "profile", cfg["profile"]["name"], T["bright"], 700)

    def b_description():
        if cfg["profile"]["description"]:
            wrapped(label_of("description"), "profile", cfg["profile"]["description"], T["soft"])

    def b_focus():
        # no "Focus:" key: each item starts at the info column, like every other line
        items = []
        for f in cfg["focus"]:
            if isinstance(f, str):
                items.append({"tag": "", "text": f})
            else:
                items.append({"tag": f.get("tag") or "", "text": f.get("text") or ""})
        if not items:
            info.append(lambda r, t: c.text(ic, r, S["emptyFocus"], T["muted"]))
            return
        tag_colors = [P["red"], P["purple"], P["blue"], P["green"], P["orange"]]
        tag_w = max((len(it["tag"]) + 2 if it["tag"] else 1) for it in items) + 1
        for n, item in enumerate(items):
            for i, part in enumerate(wrap(item["text"], c.cols - ic - tag_w)):
                def draw(r, t, i=i, part=part, item=item, n=n):
                    if i > 0:
                        head = ""
                    elif item["tag"]:
                        head = c.spans(ic, r, [("[", T["faint"]), (item["tag"], tag_colors[n % len(tag_colors)], {"weight": 700}), ("]", T["faint"])])
                    else:
                        head = c.text(ic, r, "•", T["muted"])
                    return head + c.text(ic + tag_w, r, part, T["text"])
                info.append(draw)

    def b_extra():
        for e in cfg["neofetch"]["extra"]:
            if isinstance(e, dict) and e.get("label") and e.get("value"):
                line(e["label"], "profile", e["value"], T["text"])

    def b_repos():
        line(label_of("repos"), "stats", fmt(state.get("repos")), P["yellow"], 700)

    def b_commits():
        line(label_of("commits"), "stats", fmt(state["stats"].get("commits")), P["green"], 700)

    def b_followers():
        line(label_of("followers"), "stats", fmt(state["stats"].get("followers")), P["blue"], 700)

    def b_views():
        line(label_of("views"), "stats", fmt(state["stats"].get("views")), P["purple"], 700)

    def b_languages():
        label = label_of("languages")
        items = state["languages"][:cfg["languages"]["count"]]
        if not items:
            line(label, "languages", S["emptyLanguages"], T["muted"])
            return
        vc = ic + len(label) + 2
        value_w = c.cols - vc
        rainbow = [P["yellow"], P["orange"], P["red"], P["purple"], P["blue"], P["aqua"], P["green"]]
        name_w = max(len(l["name"]) for l in items) + 2
        pct_w = max(len(f'{format_pct(l["percent"], locale)}%') for l in items)
        cells = max(8, min(cfg["layout"]["barCells"], value_w - name_w - pct_w - 2))
        top_pct = items[0]["percent"] or 1
        mode = cfg["languages"]["colors"]
        for i, lang in enumerate(items):
            def draw(r, time, i=i, lang=lang):
                if mode == "github" and lang.get("color"):
                    color = lang["color"]
                elif mode == "accent":
                    color = T["accent"]
                else:
                    color = rainbow[i % len(rainbow)]
                # the most used language fills the bar; the others are proportional to it
                bar_svg, bar_end = c.block_bar(vc + name_w, r, cells, lang["percent"] / top_pct, color, time + 0.05 * k, 0.018 * k)
                pct = c.text(vc + name_w + cells + 1, r, f'{format_pct(lang["percent"], locale)}%'.rjust(pct_w + 1), T["bright"], weight=700)
                return ((key(r, label, "languages")[0] if i == 0 else "")
                        + c.text(vc, r, lang["name"], T["text"]) + bar_svg + c.reveal(pct, bar_end))
            info.append(draw)

    def b_palette():
        dim = [P["bg1"], P["red_dim"], P["green_dim"], P["yellow_dim"], P["blue_dim"], P["purple_dim"], P["aqua_dim"], P["fg4"]]
        bright = [P["gray"], P["red"], P["green"], P["yellow"], P["blue"], P["purple"], P["aqua"], P["fg1"]]
        info.append(lambda r, t: "")
        for colors in (dim, bright):
            info.append(lambda r, t, colors=colors: "".join(c.tall(ic + i * 3, r, "███", color, seal=True) for i, color in enumerate(colors)))

    builders = {
        "name": b_name, "description": b_description, "focus": b_focus, "extra": b_extra,
        "repos": b_repos, "commits": b_commits, "followers": b_followers, "views": b_views,
        "languages": b_languages, "palette": b_palette,
    }
    for field in cfg["neofetch"]["fields"]:
        if field in builders:
            builders[field]()

    rows = max(size_rows, len(info))
    parts = []
    t = start_time
    for i in range(rows):
        row = start_row + i
        logo_svg = logo_row(c, logo, i, row) if logo and i < size_rows else ""
        parts.append(c.reveal(logo_svg + (info[i](row, t) if i < len(info) else ""), t))
        t += 0.06 * k
    return {"svg": "".join(parts), "rows": rows, "end": t}
