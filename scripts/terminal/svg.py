"""
Drawing primitives on a grid of terminal cells.

Each grid row is `lh` tall. Regular text uses the font at its normal size, with
the baseline centered in the cell. Box-drawing and block characters (╭─│█▄)
use "tall" mode: the font is scaled up until the glyph fills the whole cell and
squeezed horizontally, so lines and blocks connect without gaps between rows,
like in a real terminal.
"""
import math

from .fmt import INF, esc, jround, n2, num

EIGHTHS = ["", "▏", "▎", "▍", "▌", "▋", "▊", "▉"]


class Canvas:
    def __init__(self, theme, layout, animate, k, glow):
        self.T = theme
        self.fs = layout["fontSize"]
        self.cw = self.fs * 0.6
        self.lh = n2(self.fs * layout["lineHeight"])
        self.padX = 26
        self.titleH = 36
        self.originY = self.titleH + 16
        self.cols = math.floor((layout["width"] - self.padX * 2) / self.cw)
        self.tallSize = n2(self.lh / 1.32 + 0.15)
        self.width = layout["width"]
        self.animate = animate
        self.k = k
        self._glow = glow
        self.defs = []
        self._uid = 0

    # ── coordinates ──
    def id(self, prefix="i"):
        value = f"{prefix}{self._uid}"
        self._uid += 1
        return value

    def X(self, col):
        return n2(self.padX + col * self.cw)

    def top(self, row):
        return n2(self.originY + row * self.lh)

    def Y(self, row):
        return n2(self.originY + row * self.lh + (self.lh + 0.72 * self.fs) / 2)

    def tallY(self, row):
        return n2(self.originY + row * self.lh + 1.02 * self.tallSize - 0.08)

    def at(self, s):
        return f"{num(n2(s))}s"

    # ── drawing ──
    def glow(self, inner):
        """Soft phosphor glow around the content (when enabled)."""
        return f'<g filter="url(#glow)">{inner}</g>' if self._glow and inner else inner

    def glyphs(self, x, y, s, color, size=None, weight=None, anchor=None, squeeze=False,
               opacity=None, seal=False, **_):
        s = str(s)
        n = len(s)
        if not n or not s.strip():
            return ""
        size = self.fs if size is None else size
        attrs = [f'x="{num(n2(x))}"', f'y="{num(n2(y))}"', f'fill="{color}"']
        advance = self.cw if squeeze else size * 0.6
        if n > 1 or squeeze:
            attrs.append(f'textLength="{num(n2(n * advance))}"')
            attrs.append(f'lengthAdjust="{"spacingAndGlyphs" if squeeze else "spacing"}"')
        if size != self.fs:
            attrs.append(f'style="font-size:{num(size)}px"')
        if weight:
            attrs.append(f'font-weight="{weight}"')
        if anchor:
            attrs.append(f'text-anchor="{anchor}"')
        if opacity is not None:
            attrs.append(f'fill-opacity="{num(opacity)}"')
        if seal:
            # a thin same-color stroke closes antialiasing gaps between blocks
            attrs.append(f'stroke="{color}"')
            attrs.append('stroke-width="0.6"')
        return f"<text {' '.join(attrs)}>{esc(s)}</text>"

    def text(self, col, row, s, color, **opts):
        return self.glyphs(self.X(col), self.Y(row), s, color, **opts)

    def tall(self, col, row, s, color, **opts):
        """Box-drawing and block characters filling the whole cell."""
        opts = {**opts, "size": self.tallSize, "squeeze": True}
        return self.glyphs(self.X(col), self.tallY(row), s, color, **opts)

    def spans(self, col, row, segments):
        """Sequence of colored spans: [(text, color, {options}), ...]."""
        cursor = col
        out = ""
        for seg in segments:
            s, color = seg[0], seg[1]
            opts = seg[2] if len(seg) > 2 and seg[2] else {}
            out += self.tall(cursor, row, s, color, **opts) if opts.get("tall") else self.text(cursor, row, s, color, **opts)
            cursor += len(str(s))
        return out

    def bg(self, col, row, width_cols, color, rows=1):
        """Cell background."""
        return (f'<rect x="{num(self.X(col))}" y="{num(self.top(row))}" width="{num(n2(width_cols * self.cw))}" '
                f'height="{num(n2(rows * self.lh))}" fill="{color}"/>')

    # ── animation ──
    def reveal(self, inner, time):
        if self.animate and inner:
            return f'<g opacity="0"><set attributeName="opacity" to="1" begin="{self.at(time)}" fill="freeze"/>{inner}</g>'
        return inner

    def during(self, inner, start, end):
        """Visible only between two instants (the end can be INF)."""
        if not self.animate:
            return inner if end == INF else ""
        off = "" if end == INF else f'<set attributeName="visibility" to="hidden" begin="{self.at(end)}" fill="freeze"/>'
        return (f'<g visibility="hidden"><set attributeName="visibility" to="visible" begin="{self.at(start)}" fill="freeze"/>'
                f"{off}{inner}</g>")

    def grow(self, inner, col, row, cells, time, step, rows=1):
        """Horizontal clip that grows cell by cell (typing, bars). Returns (svg, end)."""
        if not self.animate or cells <= 0:
            return inner, time
        cid = self.id("g")
        values = ";".join(num(n2(i * self.cw + 3)) if i else "0" for i in range(cells + 1))
        self.defs.append(
            f'<clipPath id="{cid}"><rect x="{num(n2(self.X(col) - 1))}" y="{num(self.top(row))}" '
            f'height="{num(n2(rows * self.lh))}" width="0">'
            f'<animate attributeName="width" values="{values}" begin="{self.at(time)}" dur="{self.at(cells * step)}" '
            f'calcMode="discrete" fill="freeze"/></rect></clipPath>'
        )
        return f'<g clip-path="url(#{cid})">{inner}</g>', time + cells * step

    def typed(self, col, row, s, color, time, per_char, **opts):
        node = self.text(col, row, s, color, **opts)
        return self.grow(node, col, row, len(str(s)), time, per_char)

    def cursor(self, col, row, time, color=None):
        """Block cursor; blinks from `time` on."""
        color = color or self.T["cursor"]
        rect = (f'x="{num(self.X(col))}" y="{num(n2(self.top(row) + 2))}" width="{num(n2(self.cw))}" '
                f'height="{num(n2(self.lh - 4))}" fill="{color}"')
        if self.animate:
            return (f'<rect {rect} opacity="0"><animate attributeName="opacity" values="1;0" dur="1.1s" '
                    f'begin="{self.at(time)}" calcMode="discrete" repeatCount="indefinite"/></rect>')
        return f"<rect {rect}/>"

    def block_bar(self, col, row, cells, fraction, color, time, step, track=None):
        """Progress bar with 1/8-cell precision. Returns (svg, end)."""
        track = track or self.T["border"]
        eighths = jround(max(0, min(1, fraction)) * cells * 8)
        full = eighths // 8
        part = EIGHTHS[eighths % 8]
        filled = "█" * full + part
        used = full + (1 if part else 0)
        track_svg = self.text(col + used, row, "░" * max(0, cells - used), track)
        grown, end = self.grow(self.text(col, row, filled, color, seal=True), col, row, used, time, step)
        return track_svg + grown, end

    def ticker(self, col, row, strip, window_cols, color, steps, step, time, **opts):
        """Text strip scrolling inside a window of `window_cols` cells."""
        def node(x):
            if opts.get("tall"):
                return self.glyphs(x, self.tallY(row), strip, color, **{**opts, "size": self.tallSize, "squeeze": True})
            return self.glyphs(x, self.Y(row), strip, color, **opts)

        if not self.animate:
            return f"<g>{self.clip_window(col, row, window_cols, 1, node(self.X(col)))}</g>"
        values = ";".join(num(n2(self.X(col) - i * self.cw)) for i in range(steps))
        moving = node(self.X(col)).replace("<text ", '<text data-t="1" ', 1).replace(
            "</text>",
            f'<animate attributeName="x" values="{values}" begin="{self.at(time)}" dur="{self.at(steps * step)}" '
            f'calcMode="discrete" repeatCount="indefinite"/></text>', 1)
        return self.clip_window(col, row, window_cols, 1, moving)

    def clip_window(self, col, row, width_cols, rows, inner):
        cid = self.id("w")
        self.defs.append(
            f'<clipPath id="{cid}"><rect x="{num(self.X(col))}" y="{num(self.top(row))}" '
            f'width="{num(n2(width_cols * self.cw))}" height="{num(n2(rows * self.lh))}"/></clipPath>'
        )
        return f'<g clip-path="url(#{cid})">{inner}</g>'
