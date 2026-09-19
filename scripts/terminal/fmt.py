"""
Number and text helpers.

SVG coordinates are written with at most two decimals (``n2``) and without a
trailing ``.0`` on whole numbers, so the output stays small and stable between
runs. Rounding is "half away from zero" on the exact value, which keeps the
SVG identical from one run to the next.
"""
import math
import re
import sys
from decimal import Decimal, ROUND_HALF_UP

INF = math.inf


def warn(msg):
    print(f"[warn] {msg}", file=sys.stderr)


def fail(msg):
    print(f"[error] {msg}", file=sys.stderr)
    sys.exit(1)


def num(v):
    """Writes a number the way it appears in the SVG: 52, 12.5, 73.99999999999999."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, Decimal):
        v = float(v)
    if v != v:
        return "NaN"
    if v in (INF, -INF):
        return "Infinity" if v > 0 else "-Infinity"
    if v == 0:
        return "0"
    if v.is_integer() and abs(v) < 1e21:
        return str(int(v))
    text = repr(v)
    if "e" in text and 1e-7 <= abs(v) < 1e21:
        text = format(Decimal(text), "f")
    return text


def n2(v):
    """Rounds to 2 decimals (half away from zero)."""
    return float(Decimal(v).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def jround(x):
    """Rounds to the nearest integer; exact halves go up (2.5 -> 3, -2.5 -> -2)."""
    base = math.floor(x)
    return base + 1 if x - base >= 0.5 else base


def length(s):
    return len(str(s))


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&apos;"))


def fill(template, variables):
    """Replaces {name} with values from `variables`; unknown names stay as they are."""
    def sub(m):
        key = m.group(1)
        return str(variables[key]) if key in variables else m.group(0)
    return re.sub(r"\{(\w+)\}", sub, str(template), flags=re.ASCII)


def wrap(text, width):
    lines = []
    for paragraph in str(text).split("\n"):
        line = ""
        for word in [w for w in re.split(r"\s+", paragraph) if w]:
            if not line:
                line = word
            elif len(line) + 1 + len(word) <= width:
                line += f" {word}"
            else:
                lines.append(line)
                line = word
            while len(line) > width > 0:
                lines.append(line[:width])
                line = line[width:]
        lines.append(line)
    return lines


# ── locale-aware numbers (en: 1,234.5 · pt-BR: 1.234,5) ──

def _group(int_part, sep):
    s = str(int_part)
    out = []
    while len(s) > 3:
        out.insert(0, s[-3:])
        s = s[:-3]
    out.insert(0, s)
    return sep.join(out)


def _separators(locale):
    return (".", ",") if str(locale).lower().startswith("pt") else (",", ".")


def format_int(v, locale):
    """Whole numbers with thousands separators."""
    group, decimal = _separators(locale)
    if isinstance(v, float) and not v.is_integer():
        d = Decimal(v).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP).normalize()
        sign = "-" if d < 0 else ""
        whole, _, frac = format(abs(d), "f").partition(".")
        return f"{sign}{_group(whole, group)}" + (f"{decimal}{frac}" if frac else "")
    v = int(v)
    sign = "-" if v < 0 else ""
    return f"{sign}{_group(abs(v), group)}"


def format_pct(v, locale):
    """Exactly one decimal: 36.4, 2.0."""
    group, decimal = _separators(locale)
    d = Decimal(v).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    sign = "-" if d < 0 else ""
    whole, _, frac = format(abs(d), "f").partition(".")
    return f"{sign}{_group(whole, group)}{decimal}{frac or '0'}"
