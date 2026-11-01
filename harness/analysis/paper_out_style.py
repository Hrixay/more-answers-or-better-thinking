"""Figure style for the paper outputs: Karen's house style, page 3 (research/paper-notes/layout-benchmark.md at 795d18a, rules F1-F17)
as Edith's polish standard §8 adopts it (848056a). One colour per model from Okabe and Ito's colour-blind-safe palette (Haiku blue,
Sonnet orange, Opus green), the same in every figure, with darker shades for text in a model's colour; a marker shape per model as
the print cue (Haiku circle, Sonnet square, Opus diamond); effort is shown by position or a direct label, not by colour (F2, F13);
hollow means pieces and nothing else (F6). Fonts, sizes, frame and output come from paper.mplstyle, the one shared style file.
Deterministic files: fixed fonts and no dates in the PDF or PNG metadata.
"""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Dict, Tuple

PINNED = {"matplotlib": "3.9.4", "numpy": "1.26.4", "pillow": "11.3.0", "fonttools": "4.60.2", "pyparsing": "3.3.2",
          "kiwisolver": "1.4.7", "cycler": "0.12.1", "contourpy": "1.3.0"}          # harness/requirements-paper.txt

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "pareto-paper-mpl"))
os.environ.setdefault("SOURCE_DATE_EPOCH", "0")

import matplotlib                                               # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt                                 # noqa: E402
import numpy                                                    # noqa: E402
from matplotlib.colors import to_hex, to_rgb                    # noqa: E402


def check_versions() -> None:
    import importlib.metadata as md
    got = {k: md.version(k) for k in PINNED}
    bad = {k: (got[k], v) for k, v in PINNED.items() if got[k] != v}
    if bad:
        raise RuntimeError(f"figure libraries differ from the pins (got, pinned): {bad}; outputs would not be byte-identical")


MODEL_BASE = {"haiku": "#0072B2", "sonnet": "#B87F00", "opus": "#009E73"}       # marks and lines (F5; Sonnet is Okabe-Ito orange 20% toward black, 3.46:1, Karen 3273a82)
MODEL_TEXT = {"haiku": "#0072B2", "sonnet": "#9A6700", "opus": "#007A59"}       # text in a model's colour, at least 4.5:1 on white
MODEL_MARKER = {"haiku": "o", "sonnet": "s", "opus": "D"}
EFFORTS = ("off", "low", "medium", "high", "xhigh", "max")
REFERENCE = "#4D4D4D"           # non-model references: the zero line, margins, the q^N curve; also the axes' spines
CONTEXT = "#8C8C8C"             # context marks
ACCENT = "#D55E00"              # diagrams and worked examples only: the one change the reader must see
INK = "#0b0b0b"                 # text
INK_2 = REFERENCE               # secondary text and ticks (the names older code uses)
MUTED = CONTEXT
GRID = "#E6E6E6"                # horizontal gridlines on accuracy axes only (F9)
AXIS = REFERENCE

# Effort is not a colour (F2): every effort of a model draws in the model's colour; figures label efforts directly (F13).
SHADE: Dict[Tuple[str, str], str] = {(m, e): c for m, c in MODEL_BASE.items() for e in EFFORTS}
THINKING_OFF = {"color": MODEL_BASE["haiku"], "marker": MODEL_MARKER["haiku"]}       # an effort level like any other (F7: no extra shapes)


def color(model: str, effort: str) -> str:
    return SHADE[(model, effort)]


STYLE_FILE = Path(__file__).with_name("paper.mplstyle")     # the one shared figure style (fonts, sizes, frame, output)
# Computer Modern has no bold weight in cmr10: bold text (panel letters, panel titles) uses its bold cut, cmb10, by name.
BOLD = {"fontfamily": ["cmb10", "STIXGeneral"], "fontweight": "bold"}


def apply_rc() -> None:
    """Every paper figure starts from matplotlib's defaults plus paper.mplstyle (and nothing else), so all figures share one style."""
    plt.rcdefaults()
    plt.style.use(str(STYLE_FILE))


def save(fig, pdf_path: Path, png_path: Path) -> None:
    """PDF and PNG with no creation date or software stamp, so the same figure gives the same bytes."""
    fig.savefig(pdf_path, format="pdf", metadata={"CreationDate": None, "ModDate": None, "Producer": None, "Creator": None})
    fig.savefig(png_path, format="png", metadata={"Software": None})
    plt.close(fig)


# ---------------------------------------------------------------- the figure checks (Edith §8 at 848056a; Karen's F1-F17)

FONT_MIN, FONT_MAX, TICK_MIN = 8.0, 10.0, 7.5     # text at print size (§8.2, F11); tick labels may be 7.5 pt
WIDTHS = (6.5, 4.5)                              # 6.5 in for 2-3 panels, 4.5 in for one (§8.1, F14)
MAX_PANELS_PER_ROW, MAX_ROWS = 3, 2              # F4
MAX_HEIGHT = {1: 2.8, 2: 4.6}                    # F14: one row 2.0-2.6 in (with room for a legend row), two rows at most 4.6 in
MAX_LEGEND_ENTRIES = 4                           # F13
FIGURE_CHECKS_ENFORCED = True                    # every figure passes since the figure pass (batch h): a failing figure refuses the build
# cmr10 prints these wrongly outside math (Karen's test render): < as ¡, > as ¿, straight quotes the wrong way round
CMR10_TRAPS = re.compile(r"[<>\"']")


def palette() -> set:
    """Every colour a figure may draw with (§8.3, F5): the model colours and their text shades, the reference and context greys, the
    accent, ink, the grid grey, white and black."""
    cols = {*MODEL_BASE.values(), *MODEL_TEXT.values(), REFERENCE, CONTEXT, ACCENT, INK, GRID, "#ffffff", "#000000"}
    return {to_hex(c) for c in cols}


def _panels(fig) -> list:
    """The figure's panels: visible axes that are not inside another axes (an inset or a zoom box is part of its panel)."""
    axes = [ax for ax in fig.axes if ax.get_visible() and ax.axison]
    def inside(a, b) -> bool:
        pa, pb = a.get_position(), b.get_position()
        return a is not b and pa.x0 >= pb.x0 - 1e-6 and pa.x1 <= pb.x1 + 1e-6 and pa.y0 >= pb.y0 - 1e-6 and pa.y1 <= pb.y1 + 1e-6
    return [a for a in axes if not any(inside(a, b) for b in axes)]


def _outside_math(text: str) -> str:
    """The parts of a text matplotlib sets as plain text (not between unescaped $ signs)."""
    parts = re.split(r"(?<!\\)\$", text)
    return "".join(parts[k] for k in range(0, len(parts), 2))


def figure_problems(fig) -> list:
    """Edith's §8 and Karen's measurable rules on a built figure: print width and height, panels per row and rows, every visible text
    at 8-10 pt (tick labels from 7.5) in one family, no cmr10 trap characters outside math, no raster image, only the palette's
    colours, sentence-case axis labels, accuracy axes never past 100, horizontal gridlines only, and short legends."""
    from matplotlib.collections import Collection
    from matplotlib.image import AxesImage
    from matplotlib.legend import Legend
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    from matplotlib.text import Text
    out = []
    w, h = fig.get_size_inches()
    if not any(abs(w - x) < 0.005 for x in WIDTHS):
        out.append(f"width {w:.2f} in (the paper sets figures at {' or '.join(map(str, WIDTHS))} in)")
    panels = _panels(fig)
    rows: list = []
    for ax in sorted(panels, key=lambda a: -a.get_position().y1):
        p = ax.get_position()
        for row in rows:
            q = row[0].get_position()
            if min(p.y1, q.y1) - max(p.y0, q.y0) > 0.5 * min(p.height, q.height):
                row.append(ax)
                break
        else:
            rows.append([ax])
    if any(len(r) > MAX_PANELS_PER_ROW for r in rows):
        out.append(f"{max(len(r) for r in rows)} panels in a row (at most {MAX_PANELS_PER_ROW})")
    if len(rows) > MAX_ROWS:
        out.append(f"{len(rows)} rows of panels (at most {MAX_ROWS})")
    if rows and h > MAX_HEIGHT.get(len(rows), MAX_HEIGHT[2]) + 1e-6:
        out.append(f"height {h:.2f} in for {len(rows)} row(s) (at most {MAX_HEIGHT.get(len(rows), MAX_HEIGHT[2])} in)")
    ticks = set()
    for ax in fig.axes:
        for axis in (ax.xaxis, ax.yaxis):
            for tk in axis.get_major_ticks() + axis.get_minor_ticks():
                ticks.update({id(tk.label1), id(tk.label2)})
            ticks.add(id(axis.get_offset_text()))
    sizes, families, traps = {}, set(), set()
    for t in fig.findobj(Text):
        text = t.get_text()
        if not t.get_visible() or not text.strip():
            continue
        s = round(float(t.get_fontsize()), 2)
        low = TICK_MIN if id(t) in ticks else FONT_MIN
        if s < low - 1e-6 or s > FONT_MAX + 1e-6:
            sizes.setdefault(s, text.strip()[:40])
        if not (text.startswith("$") and text.endswith("$")):
            # Computer Modern's cuts (cmr10, cmb10, ...) are one family
            families.add(tuple("Computer Modern" if f.startswith("cm") else f for f in t.get_fontfamily()))
        if CMR10_TRAPS.search(_outside_math(text)):
            traps.add(text.strip()[:40])
    out += [f"text at {s} pt (8-10 pt at print size, tick labels from 7.5), e.g. {x!r}" for s, x in sorted(sizes.items())]
    if len(families) > 1:
        out.append(f"more than one font family: {sorted(families)}")
    out += [f"a character cmr10 prints wrongly outside math (< > or a straight quote): {x!r}" for x in sorted(traps)]
    if fig.findobj(AxesImage):
        out.append("a raster image inside the figure (vector only)")
    allowed = palette()
    seen = set()
    def add(c) -> None:
        try:
            rgba = matplotlib.colors.to_rgba(c)
        except (ValueError, TypeError):
            return
        if rgba[3] == 0:
            return
        seen.add(to_hex(rgba[:3]))
    for o in fig.findobj(lambda o: isinstance(o, (Line2D, Patch, Collection))):
        if not o.get_visible():
            continue
        if isinstance(o, Line2D):
            if any(o is l for ax in fig.axes for l in ax.get_xgridlines() + ax.get_ygridlines()):
                continue
            for c in (o.get_color(), o.get_markerfacecolor(), o.get_markeredgecolor()):
                add(c)
        elif isinstance(o, Patch):
            if o is fig.patch or any(o is ax.patch for ax in fig.axes):
                continue
            add(o.get_facecolor()); add(o.get_edgecolor())
        else:
            for c in list(o.get_facecolor()) + list(o.get_edgecolor()):
                add(c)
    extra = sorted(seen - allowed)
    if extra:
        out.append(f"colours outside the palette: {extra}")
    for ax in panels:
        for lab in (ax.get_xlabel(), ax.get_ylabel()):
            # sentence case: a capital first, unless the label starts with a symbol ("k", "d (points)", "$q^N$")
            if lab and lab[0].islower() and not re.match(r"^[a-z](?:\W|_|$)", lab):
                out.append(f"axis label {lab!r} is not in sentence case")
        ylab = ax.get_ylabel().lower()
        if "accuracy" in ylab and "%" in ylab and ax.get_ylim()[1] > 100.5:
            out.append(f"accuracy axis {ax.get_ylabel()!r} runs past 100 (to {ax.get_ylim()[1]:.1f})")
        if any(g.get_visible() for g in ax.get_xgridlines()):
            out.append("vertical gridlines (horizontal only, on accuracy axes)")
    for lg in fig.findobj(Legend):
        n = len([t for t in lg.get_texts() if t.get_text().strip()])
        if n > MAX_LEGEND_ENTRIES:
            out.append(f"a legend of {n} entries (at most {MAX_LEGEND_ENTRIES}; label series directly)")
    return out
