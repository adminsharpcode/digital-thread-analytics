"""Shared drawing toolkit for the manuscript figures.

Every figure in the report is generated from code so that it can be
regenerated at any resolution and so that nothing in the document is a
screenshot of a drawing tool. Output is 600 DPI as the guidelines require.
"""
from __future__ import annotations

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle, Circle, Wedge
import numpy as np

OUT = "/home/claude/report/diagrams"
DPI = 600

INK       = "#1f2933"
MUTED     = "#5b6875"
LINE      = "#c9d2db"
BLUE      = "#3d5a80"; BLUE_F   = "#e4ecf5"
GREEN     = "#3f7350"; GREEN_F  = "#dfeee4"
VIOLET    = "#5c4b8a"; VIOLET_F = "#e8e2f2"
AMBER     = "#a9761f"; AMBER_F  = "#f6e6c8"
ORANGE    = "#b06d1d"; ORANGE_F = "#fbe7cf"
RED       = "#9c4221"; RED_F    = "#f9dcd6"
GREY      = "#8b97a3"; GREY_F   = "#eceff2"
TEAL      = "#2a6f7a"; TEAL_F   = "#dceef0"

PAIRS = [(BLUE, BLUE_F), (GREEN, GREEN_F), (VIOLET, VIOLET_F),
         (AMBER, AMBER_F), (ORANGE, ORANGE_F), (RED, RED_F),
         (TEAL, TEAL_F), (GREY, GREY_F)]

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "axes.edgecolor": LINE,
    "axes.labelcolor": INK,
    "text.color": INK,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "axes.titlesize": 10,
})


def canvas(w=10.0, h=5.6, xlim=100, ylim=56):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, xlim); ax.set_ylim(0, ylim); ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, text, fill=BLUE_F, edge=BLUE, fs=8.5, bold=False,
        r=0.03, lw=1.3, sub=None, sub_fs=6.8, z=2, align="center",
        text_color=None):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                 boxstyle=f"round,pad=0,rounding_size={r}",
                 linewidth=lw, edgecolor=edge, facecolor=fill, zorder=z))
    cx = x + w / 2
    ty = y + h / 2 + (h * 0.14 if sub else 0)
    ax.text(cx, ty, text, ha="center", va="center", fontsize=fs,
            fontweight="bold" if bold else "normal",
            color=text_color or INK, zorder=z + 2, linespacing=1.35)
    if sub:
        ax.text(cx, y + h * 0.26, sub, ha="center", va="center",
                fontsize=sub_fs, color=MUTED, zorder=z + 2, linespacing=1.35)


def arrow(ax, p1, p2, color=GREY, lw=1.3, rad=0.0, ms=9, ls="-", z=3,
          style="-|>"):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle=style, mutation_scale=ms,
                 linewidth=lw, color=color, linestyle=ls,
                 connectionstyle=f"arc3,rad={rad}", shrinkA=0, shrinkB=0,
                 zorder=z))


def label(ax, x, y, text, fs=7.0, color=MUTED, ha="center", va="center",
          bold=False, italic=False, z=6):
    ax.text(x, y, text, ha=ha, va=va, fontsize=fs, color=color,
            fontweight="bold" if bold else "normal",
            style="italic" if italic else "normal", zorder=z,
            linespacing=1.4)


def band(ax, x, y, w, h, title, body, fill=GREY_F, edge=GREY, title_color=None,
         fs=9.0, body_fs=7.0):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                 boxstyle="round,pad=0,rounding_size=0.03",
                 linewidth=1.4, edgecolor=edge, facecolor=fill, zorder=1))
    ax.text(x + 2.0, y + h - (3.0 if body else h / 2), title, ha="left",
            va="center", fontsize=fs, fontweight="bold",
            color=title_color or edge, zorder=4)
    if body:
        ax.text(x + 2.0, y + h * 0.30, body, ha="left", va="center",
                fontsize=body_fs, color=MUTED, zorder=4, linespacing=1.5)


def chain(ax, items, y, h, left=3.0, right=97.0, gap=3.0, fs=8.2,
          pair=(BLUE, BLUE_F), numbered=False, arrow_color=None):
    """A left-to-right row of boxes joined by arrows."""
    n = len(items)
    w = (right - left - gap * (n - 1)) / n
    centers = []
    for i, it in enumerate(items):
        x = left + i * (w + gap)
        title, sub = (it if isinstance(it, tuple) else (it, None))
        box(ax, x, y, w, h, title, fill=pair[1], edge=pair[0], fs=fs,
            bold=True, sub=sub)
        if numbered:
            ax.add_patch(Circle((x + 1.8, y + h - 1.8), 1.25,
                        facecolor=pair[0], edgecolor="none", zorder=4))
            ax.text(x + 1.8, y + h - 1.8, str(i + 1), ha="center",
                    va="center", color="white", fontsize=6.8,
                    fontweight="bold", zorder=5)
        centers.append(x + w / 2)
        if i < n - 1:
            arrow(ax, (x + w + 0.3, y + h / 2), (x + w + gap - 0.3, y + h / 2),
                  color=arrow_color or pair[0], lw=1.5, ms=10)
    return centers, w


def stack(ax, items, x, w, top, h, gap=2.0, fs=8.2, pairs=None, subs=None):
    """A top-to-bottom stack of layer bands."""
    ys = []
    for i, it in enumerate(items):
        y = top - (i + 1) * h - i * gap
        pair = (pairs[i % len(pairs)] if pairs else PAIRS[i % len(PAIRS)])
        sub = subs[i] if subs else None
        box(ax, x, y, w, h, it, fill=pair[1], edge=pair[0], fs=fs, bold=True,
            sub=sub)
        ys.append(y)
    return ys


def save(fig, number, name, tight=True):
    os.makedirs(OUT, exist_ok=True)
    fname = f"Fig {number:02d} {name}.png"
    path = os.path.join(OUT, fname)
    if tight:
        fig.tight_layout(pad=0.25)
    fig.savefig(path, dpi=DPI, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    size = os.path.getsize(path) / 1024
    print(f"  Fig {number:02d}  {name}   ({size:.0f} KB)")
    return path
