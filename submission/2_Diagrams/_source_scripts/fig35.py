"""Figure 35: a composite of the running application, from real screenshots."""
import sys
sys.path.insert(0, "/home/claude/report/figsrc")
from figkit import OUT, DPI, INK, MUTED, LINE
from PIL import Image, ImageDraw, ImageFont
import os

SH = "/home/claude/report/screenshots"


def _font(size, bold=False):
    base = "/usr/share/fonts/truetype/dejavu/"
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(base + name, size)
    except OSError:
        return ImageFont.load_default()


def compose():
    a = Image.open(f"{SH}/01_dashboard_overview.png").convert("RGB")
    b = Image.open(f"{SH}/02_prediction_with_lineage.png").convert("RGB")

    W = 2600
    pad, gap, cap = 24, 26, 46
    aw = W - 2 * pad
    a = a.resize((aw, int(a.height * aw / a.width)), Image.LANCZOS)
    bw = int(aw * 0.62)
    b = b.resize((bw, int(b.height * bw / b.width)), Image.LANCZOS)

    H = pad + cap + a.height + gap + cap + b.height + pad
    canvas = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(canvas)

    y = pad
    d.text((pad, y + 10), "(a)  dashboard: deployment status, candidate comparison and per-feature drift, all read from the ledger at request time",
           font=_font(26), fill=INK)
    y += cap
    canvas.paste(a, (pad, y)); d.rectangle([pad, y, pad + a.width - 1, y + a.height - 1], outline=LINE, width=2)
    y += a.height + gap

    d.text((pad, y + 10), "(b)  a worn-tool reading scored at 83.36 %, returned with the deployment version and model digest that produced it",
           font=_font(26), fill=INK)
    y += cap
    canvas.paste(b, (pad, y)); d.rectangle([pad, y, pad + b.width - 1, y + b.height - 1], outline=LINE, width=2)

    path = os.path.join(OUT, "Fig 35 Prediction Service and Lineage Explorer.png")
    canvas.save(path, dpi=(DPI, DPI))
    print(f"  Fig 35  Prediction Service and Lineage Explorer   ({os.path.getsize(path)/1024:.0f} KB)")
    return path


if __name__ == "__main__":
    compose()
