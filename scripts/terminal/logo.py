"""
Neofetch logo.

Formats accepted in config.json (neofetch.logo):
  "tux-svg"                  pixel-art Tux (assets/logos/tux.svg), recolored by the palette
  "rooster", "owl", "tux"    block art from assets/logos/<name>.json
  "none"                     no logo
  { "lines": [...], "colors": [...] }   text logo, one color code per character
  { "lines": [...], "color": "yellow" } text logo in a single color

Color codes (they follow the theme palette):
  R/r red   G/g green  Y/y yellow  B/b blue  P/p purple  A/a aqua  O/o orange
  (uppercase = bright color, lowercase = _dim variant)
  1 fg0  2 fg1  3 fg2  4 fg3  5 fg4  6 gray  7 bg4  8 bg3  9 bg2  0 bg1  k bg0
  . (dot) uses the default text color
"""
import json
import re
from pathlib import Path

from .fmt import num, warn
from .theme import GRUVBOX

COLOR_KEYS = {
    "R": "red", "r": "red_dim", "G": "green", "g": "green_dim", "Y": "yellow", "y": "yellow_dim",
    "B": "blue", "b": "blue_dim", "P": "purple", "p": "purple_dim", "A": "aqua", "a": "aqua_dim",
    "O": "orange", "o": "orange_dim",
    "1": "fg0", "2": "fg1", "3": "fg2", "4": "fg3", "5": "fg4", "6": "gray", "7": "bg4", "8": "bg3", "9": "bg2", "0": "bg1", "k": "bg0",
}

_GRUVBOX_NAMES = {hex_.lower(): name for name, hex_ in GRUVBOX.items()}


def _at(seq, i):
    return seq[i] if 0 <= i < len(seq) else None


def load_logo(spec, root):
    logos = Path(root) / "assets" / "logos"
    if spec == "none" or spec is False:
        return None
    if spec == "tux-svg":
        path = logos / "tux.svg"
        if not path.exists():
            warn("neofetch.logo: tux.svg not found; using rooster.")
            return load_logo("rooster", root)
        raw = path.read_text(encoding="utf-8")
        match = re.search(r"<svg\b([^>]*)>([\s\S]*)</svg>", raw, re.I)
        if not match:
            warn("neofetch.logo: invalid tux.svg; using rooster.")
            return load_logo("rooster", root)
        w = re.search(r'\bwidth="([0-9.]+)"', match.group(1))
        h = re.search(r'\bheight="([0-9.]+)"', match.group(1))
        return {"kind": "svg", "inner": match.group(2), "width": float(w.group(1)) if w else 300,
                "height": float(h.group(1)) if h else 275, "cols": 35, "rows": 25}
    if isinstance(spec, str):
        path = logos / f"{spec}.json"
        if not path.exists():
            warn(f'neofetch.logo: "{spec}" not found in assets/logos, using "rooster".')
            return load_logo("rooster", root)
        data = json.loads(path.read_text(encoding="utf-8"))
        return {"kind": "blocks", **data}
    if isinstance(spec, dict) and isinstance(spec.get("lines"), list):
        return {"kind": "text", "lines": [str(l) for l in spec["lines"]], "colors": spec.get("colors"), "color": spec.get("color")}
    warn('invalid neofetch.logo, using "rooster".')
    return load_logo("rooster", root)


def logo_size(logo):
    if not logo:
        return 0, 0
    if logo["kind"] == "svg":
        return logo["cols"], logo["rows"]
    rows = logo["glyphs"] if logo["kind"] == "blocks" else logo["lines"]
    return max([0] + [len(r) for r in rows]), len(rows)


def _recolor(inner, palette):
    """tux.svg is drawn with Gruvbox colors; swap each one for the same name in the active palette."""
    def sub(m):
        name = _GRUVBOX_NAMES.get(m.group(1).lower())
        return f'="{palette[name]}"' if name and name in palette else m.group(0)
    return re.sub(r'="(#[0-9a-fA-F]{6})"', sub, inner)


def logo_row(c, logo, index, row):
    """Draws one logo row. Returns svg."""
    T = c.T
    if logo["kind"] == "svg":
        if index != 0:
            return ""
        x = c.X(0)
        y = c.top(row)
        w, h = num(logo["width"]), num(logo["height"])
        return f'<svg x="{num(x)}" y="{num(y)}" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{_recolor(logo["inner"], T.palette)}</svg>'

    def pal(key, fallback):
        return T.palette[COLOR_KEYS[key]] if key and key != "." and key in COLOR_KEYS else fallback

    if logo["kind"] == "text":
        line = list(_at(logo["lines"], index) or "")
        colors = list(_at(logo.get("colors") or [], index) or "")
        base = (T.color(logo["color"]) or T["text"]) if logo.get("color") else T["text"]
        out = ""
        i = 0
        while i < len(line):
            key = _at(colors, i)
            j = i
            while j < len(line) and _at(colors, j) == key:
                j += 1
            out += c.text(i, row, "".join(line[i:j]), pal(key, base), weight=700)
            i = j
        return out

    # blocks: backgrounds as continuous runs + block glyphs in "tall" mode
    glyphs = list(_at(logo["glyphs"], index) or "")
    fg = list(_at(logo["fg"], index) or "")
    bg = [(_at(fg, i) if _at(glyphs, i) == "█" else b) for i, b in enumerate(_at(logo["bg"], index) or "")]
    cells = [" " if g == "█" else g for g in glyphs]
    out = ""
    top = c.top(row)
    i = 0
    while i < len(cells):
        j = i
        while j < len(cells) and _at(bg, j) == _at(bg, i):
            j += 1
        color = pal(_at(bg, i), None)
        if color:
            out += f'<rect x="{num(c.X(i))}" y="{num(top - 0.4)}" width="{num((j - i) * c.cw + 0.8)}" height="{num(c.lh + 0.8)}" fill="{color}"/>'
        i = j
    i = 0
    while i < len(cells):
        if cells[i] == " ":
            i += 1
            continue
        j = i
        while j < len(cells) and cells[j] != " " and _at(fg, j) == _at(fg, i):
            j += 1
        out += c.tall(i, row, "".join(cells[i:j]), pal(_at(fg, i), T["text"]), seal=True)
        i = j
    return out
