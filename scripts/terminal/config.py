"""
Reads config.json and turns it into the settings the renderer uses.

Every key is optional except `username`; missing keys fall back to DEFAULTS.
Keys starting with "_" are notes for humans and are ignored.
"""
import copy
import json
import os
from pathlib import Path

from .fmt import fail, warn
from .neofetch import NEOFETCH_FIELDS

STATUS_DEFAULTS = {
    "developed": {"text": "developed", "color": "green"},
    "in development": {"text": "in development", "color": "green"},
    "ongoing": {"text": "ongoing", "color": "green"},
    "planning": {"text": "planning", "color": "green"},
}

DEFAULTS = {
    "username": "",
    "locale": "en",
    "timezone": "America/Sao_Paulo",
    "prompt": {"user": "user", "host": "github"},
    "profile": {"name": {"label": None, "value": ""}, "bio": {"label": None, "value": ""}},
    "focus": [],
    "labels": {},
    "neofetch": {"command": "neofetch", "logo": "tux-svg", "fields": NEOFETCH_FIELDS, "extra": []},
    "projects": {
        "command": "tmux attach -t projects",
        "borderColors": ["yellow", "aqua", "orange", "purple", "green", "blue"],
        "statuses": STATUS_DEFAULTS,
        "items": [],
    },
    "languages": {"count": 6, "exclude": [], "colors": "rainbow", "includePrivate": False},
    "stats": {"countPrivateContributions": False},
    "boot": {"enabled": True, "lines": []},
    "animation": {"enabled": True, "speed": "medium"},
    "effects": {"glow": True, "scanlines": True, "vignette": True, "statusBar": True},
    "layout": {"width": 900, "fontSize": 14, "lineHeight": 1.6, "barCells": 20},
    "theme": {"palette": {}, "roles": {}},
}

FIELD_ALIASES = {"bio": "description"}


def _strip_notes(value):
    if isinstance(value, dict):
        return {k: _strip_notes(v) for k, v in value.items() if not str(k).startswith("_")}
    if isinstance(value, list):
        return [_strip_notes(v) for v in value]
    return value


def _merge(base, over):
    if isinstance(base, list) or isinstance(over, list):
        return base if over is None else over
    if not isinstance(base, dict) or not isinstance(over, dict):
        return base if over is None else over
    out = dict(base)
    for key, value in (over or {}).items():
        out[key] = _merge(base[key], value) if key in base else value
    return out


def _labeled(entry, fallback_label):
    """Accepts {"label": ..., "value": ...} or a plain string."""
    if isinstance(entry, dict):
        return entry.get("label") or fallback_label, str(entry.get("value") or "")
    return fallback_label, str(entry or "")


def load_strings(root, locale):
    strings = json.loads((Path(root) / "assets" / "strings.json").read_text(encoding="utf-8"))
    strings = _strip_notes(strings)
    if locale not in strings:
        warn(f'locale "{locale}" is not supported, using "en". Options: {", ".join(strings)}')
        locale = "en"
    return locale, strings[locale]


def load_config(root):
    path = Path(root) / "config.json"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail("config.json not found.")
    except json.JSONDecodeError as err:
        fail(f"invalid config.json: {err} (look for a missing comma or quote near that line)")

    cfg = _merge(copy.deepcopy(DEFAULTS), _strip_notes(raw))
    cfg["username"] = str(cfg["username"] or os.environ.get("GITHUB_REPOSITORY_OWNER", "")).strip()
    if not cfg["username"]:
        fail('config.json: set "username".')

    cfg["locale"], S = load_strings(root, cfg["locale"])
    S = copy.deepcopy(S)

    # profile: label + value for Name and Bio
    name_label, name_value = _labeled(cfg["profile"].get("name"), S["labels"]["name"])
    bio_label, bio_value = _labeled(cfg["profile"].get("bio", cfg["profile"].get("description")), S["labels"]["description"])
    S["labels"]["name"], S["labels"]["description"] = name_label, bio_label
    cfg["profile"] = {"name": name_value, "description": bio_value}

    # other neofetch keys (Repos, Commits, Followers, Views, Languages)
    for key, value in (cfg.get("labels") or {}).items():
        if isinstance(value, str) and value:
            S["labels"][FIELD_ALIASES.get(key, key)] = value

    # focus: label in brackets + value
    focus = []
    for item in cfg["focus"]:
        if isinstance(item, str):
            focus.append({"tag": "", "text": item})
        elif isinstance(item, dict):
            focus.append({"tag": str(item.get("label", item.get("tag")) or ""), "text": str(item.get("value", item.get("text")) or "")})
    cfg["focus"] = focus

    # neofetch fields
    fields = []
    for field in cfg["neofetch"]["fields"]:
        field = FIELD_ALIASES.get(field, field)
        if field in NEOFETCH_FIELDS:
            fields.append(field)
        else:
            warn(f'neofetch.fields: unknown "{field}" was ignored. Options: bio, {", ".join(f for f in NEOFETCH_FIELDS if f != "description")}')
    cfg["neofetch"]["fields"] = fields

    # languages
    count = cfg["languages"]["count"]
    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        warn(f'languages.count must be a whole number of 1 or more (got "{count}"), using 6.')
        cfg["languages"]["count"] = 6
    if cfg["languages"]["colors"] not in ("rainbow", "accent", "github"):
        warn('languages.colors must be "rainbow", "accent" or "github", using "rainbow".')
        cfg["languages"]["colors"] = "rainbow"
    cfg["languages"]["exclude"] = [str(x) for x in (cfg["languages"]["exclude"] or [])]

    # project statuses
    statuses = {}
    for key, value in (cfg["projects"].get("statuses") or {}).items():
        if isinstance(value, str):
            value = {"text": value}
        if isinstance(value, dict):
            statuses[str(key).lower()] = {"text": str(value.get("text") or key), "color": value.get("color") or "green"}
    cfg["projects"]["statuses"] = statuses
    for item in cfg["projects"]["items"]:
        if isinstance(item, dict) and item.get("status") and str(item["status"]).lower() not in statuses:
            warn(f'projects: status "{item["status"]}" in "{item.get("name")}" is not in projects.statuses '
                 f'({", ".join(statuses)}); it is shown as typed.')

    return cfg, S
