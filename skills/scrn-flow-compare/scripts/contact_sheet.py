"""Build contact sheets: many screens on one image, one row-group per flow.

Usage:
  python contact_sheet.py rows.json out/sheet            # overview, 150 px screens
  python contact_sheet.py rows.json out/zoom --width 360 --cols 4   # read small text

rows.json:
  {"rows": [
     {"label": "2025 · Send via SBP", "screens": ["<id>", "<id>", ...]},
     {"label": "2026 · Transferring via SBP", "screens": [...], "pick": [1, 4, 7]}
  ]}
`pick` (optional) keeps only these 1-based positions; numbers on the sheet stay
the original positions in the flow, so you can cite "2026 #7".

Output: out/sheet_1.jpg, out/sheet_2.jpg, ... Each page is kept under
--max-height px (default 1500) so the image viewer does not downscale it.
"""
import argparse
import json
import os
from PIL import Image, ImageDraw, ImageFont
from screens import load, fetch_many

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "..", "assets", "fonts", "Inter-SemiBold.otf")


def font(size):
    try:
        return ImageFont.truetype(FONT, size)
    except Exception:
        return ImageFont.load_default()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rows")
    ap.add_argument("out")
    ap.add_argument("--width", type=int, default=150, help="screen width in px (150 overview, 360 to read fine print)")
    ap.add_argument("--cols", type=int, default=10)
    ap.add_argument("--max-height", type=int, default=1500)
    ap.add_argument("--max-screen-ratio", type=float, default=2.3, help="crop very long screenshots to width*ratio")
    a = ap.parse_args()

    spec = json.load(open(a.rows))
    W, C = a.width, a.cols
    pad, head, num = 4, 26, 18
    fh, fn = font(16 if W < 250 else 20), font(13 if W < 250 else 18)

    blocks = []  # (label, [(pos, img)])
    for row in spec["rows"]:
        ids = row["screens"]
        pos = row.get("pick") or list(range(1, len(ids) + 1))
        fetch_many([ids[p - 1] for p in pos])
        items = []
        for p in pos:
            im = load(ids[p - 1])
            if im is not None:
                im = im.resize((W, int(im.height * W / im.width)))
                im = im.crop((0, 0, W, min(im.height, int(W * a.max_screen_ratio))))
            items.append((p, im))
        blocks.append((row.get("label", ""), items))

    # lay out row-groups, paginate
    pages, cur, cur_h = [], [], 0
    for label, items in blocks:
        rh = max([im.height for _, im in items if im] or [W * 2])
        nrows = (len(items) + C - 1) // C
        for r in range(nrows):
            chunk = items[r * C:(r + 1) * C]
            h = (head if r == 0 else 0) + rh + num + pad
            if cur and cur_h + h > a.max_height:
                pages.append(cur); cur, cur_h = [], 0
            cur.append((label if r == 0 else None, chunk, rh)); cur_h += h
    if cur:
        pages.append(cur)

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    width = C * (W + pad) + pad
    for i, page in enumerate(pages, 1):
        H = sum((head if lab is not None else 0) + rh + num + pad for lab, _, rh in page)
        c = Image.new("RGB", (width, H), "white"); dr = ImageDraw.Draw(c); y = 0
        for lab, chunk, rh in page:
            if lab is not None:
                n = sum(len(it) for l2, it in blocks if l2 == lab)
                dr.rectangle([0, y, width, y + head - 2], fill="black")
                dr.text((6, y + 3), f"{lab} — {n} screens", fill="white", font=fh); y += head
            for k, (p, im) in enumerate(chunk):
                x = pad + k * (W + pad)
                dr.text((x, y), str(p), fill="red", font=fn)
                if im is not None:
                    c.paste(im, (x, y + num))
                else:
                    dr.rectangle([x, y + num, x + W, y + num + rh], outline="red")
            y += rh + num + pad
        path = f"{a.out}_{i}.jpg"; c.save(path, quality=85); print(path, c.size)


if __name__ == "__main__":
    main()
