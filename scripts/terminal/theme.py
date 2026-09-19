"""
Theme: a palette of named colors (Gruvbox dark by default) and roles that point
to those colors. Changing the palette updates everything, logo art included.
"""
import re

from .fmt import warn

GRUVBOX = {
    "bg0_h": "#1d2021", "bg0": "#282828", "bg1": "#3c3836", "bg2": "#504945", "bg3": "#665c54", "bg4": "#7c6f64",
    "fg0": "#fbf1c7", "fg1": "#ebdbb2", "fg2": "#d5c4a1", "fg3": "#bdae93", "fg4": "#a89984", "gray": "#928374",
    "red": "#fb4934", "green": "#b8bb26", "yellow": "#fabd2f", "blue": "#83a598",
    "purple": "#d3869b", "aqua": "#8ec07c", "orange": "#fe8019",
    "red_dim": "#cc241d", "green_dim": "#98971a", "yellow_dim": "#d79921", "blue_dim": "#458588",
    "purple_dim": "#b16286", "aqua_dim": "#689d6a", "orange_dim": "#d65d0e",
}

ROLES = {
    "background": "bg0_h", "surface": "bg0", "raised": "bg1", "border": "bg2", "faint": "bg3",
    "text": "fg1", "bright": "fg0", "soft": "fg3", "muted": "gray",
    "accent": "yellow", "secondary": "orange", "prompt": "aqua", "ok": "green",
    "info": "blue", "error": "red", "special": "purple", "cursor": "fg1",
}

_HEX = re.compile(r"#([0-9a-f]{3}|[0-9a-f]{6}|[0-9a-f]{8})", re.I)


def is_hex(value):
    return isinstance(value, str) and _HEX.fullmatch(value) is not None


class Theme(dict):
    """Role -> hex color (T["accent"]), plus the full palette (T.palette["red"])."""

    def __init__(self, palette):
        super().__init__()
        self.palette = palette

    def color(self, value):
        if is_hex(value):
            return value
        return self.palette.get(value) if isinstance(value, str) else None


def resolve_theme(theme_cfg=None):
    theme_cfg = theme_cfg or {}
    palette = dict(GRUVBOX)
    for name, value in (theme_cfg.get("palette") or {}).items():
        if str(name).startswith("_"):
            continue  # notes/comments inside the JSON
        if is_hex(value):
            palette[name] = value
        else:
            warn(f'theme.palette.{name} = "{value}" is not a hex color, ignored.')
    T = Theme(palette)
    roles = theme_cfg.get("roles") or {}
    for role, fallback in ROLES.items():
        value = roles.get(role)
        if value is None:
            value = fallback
        resolved = T.color(value)
        if not resolved:
            warn(f'theme.roles.{role} = "{value}" is neither a hex color nor a palette name, using "{fallback}".')
        T[role] = resolved or T.color(fallback)
    return T
