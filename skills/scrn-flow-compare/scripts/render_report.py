"""Render a comparison REPORT as a multi-page PDF (A4 landscape) with clickable SCRN links.

Usage:
  python render_report.py report.json out.pdf      # PDF with clickable «Сценарий в SCRN» buttons
  python render_report.py report.json out_dir/     # one JPG per page (for a post or a deck), no buttons
  [--theme path/to/theme.json] [--png-dir dir]

Dark scrn.gallery look; colours, fonts, logo and accent come from the theme (default assets/theme-scrn.json).
Needs Pillow + reportlab (reportlab only for the final PDF; with --png-dir pages are also saved as PNG).

Spec (all text printed as given — write it in the user's language):
{
  "title": "Рецепт → корзина",
  "subtitle": "Как 5 доставок продуктов продают рецепт целиком",
  "meta": "iOS, сняты 2025–2026 · scrn.gallery · 23.11.2026",
  "apps": [{"name": "Самокат", "logo": "<cdn id or file>", "url": "https://scrn.gallery/app/samokat"}],
  "matrix": {                                   # optional: who does what
    "title": "Кто что умеет",
    "columns": ["Набор одной кнопкой", "Замена товара", "Порции"],
    "rows": [{"app": "Самокат", "cells": ["✓", "✓", "—"]}],
    "note": "— = в снятых сценариях не видели"
  },
  "findings": [{                                # one page each
    "app": "Самокат", "tail": "ИИ-поиск",
    "title": "Рецепт по одной фразе",
    "body": "2–4 sentences of evidence, interface text quoted verbatim.",
    "why": "optional: why it matters (design / product), 1–2 sentences",
    "confidence": "Факт",                       # or "Гипотеза"
    "link": {"text": "Сценарий в SCRN", "url": "https://scrn.gallery/app/samokat?tab=flows&flow=<id>"},
    "screens": [{"screen": "<image id>", "label": "Запрос", "crop": [0, 0, 1, 1],
                 "url": "https://scrn.gallery/app/samokat?screen=<screen _id>"},
                {"label": "28 порций", "parts": [{"screen": "<id>", "crop": [...]}, {"screen": "<id>", "crop": [...]}]}]
                # 1–3 screens; "parts" stacks crops of several screens into one column
  }],
  "summary": {"title": "Итог", "bullets": [{"app": "Самокат", "text": "..."}],
              "conclusion": "one clear takeaway", "caveats": "what was not captured, platform, dates"}
}
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from PIL import Image, ImageDraw, ImageFilter  # noqa: E402
import render_carousel as rc  # noqa: E402
from render_carousel import aa_rrect, aa_mask, wrap, prep  # noqa: E402
from screens import load, fetch_many  # noqa: E402

W, H, M = 1754, 1240, 88          # A4 landscape at 150 dpi
BG, CARD, LINE = (255, 255, 255), (243, 243, 245), (226, 226, 230)
TEXT, MUTED = (17, 17, 19), (98, 99, 104)


def prep_any(s):
    """A screen entry, or {"parts": [{screen, crop}, ...]} stacked into one image."""
    if not s.get("parts"):
        return prep(s)
    ims = [prep(p) for p in s["parts"]]; w = max(i.width for i in ims)
    ims = [i.resize((w, int(i.height * w / i.width)), Image.LANCZOS) for i in ims]
    gap = int(w * 0.03); out = Image.new("RGB", (w, sum(i.height for i in ims) + gap * (len(ims) - 1)), BG)
    y = 0
    for i in ims: out.paste(i, (0, y)); y += i.height + gap
    return out


def logo_img(ref, size, spec_dir):
    lp = os.path.join(spec_dir, ref) if ref else ""
    im = load(lp) if ref and os.path.exists(lp) else (load(ref) if ref else None)
    if im is None:
        im = Image.new("RGB", (size, size), (200, 200, 205))
    w, h = im.size; k = min(w, h)
    im = im.crop(((w - k) // 2, (h - k) // 2, (w + k) // 2, (h + k) // 2)).resize((size, size), Image.LANCZOS)
    return im, aa_mask((size, size), circle=True)


class Report:
    def __init__(self, T, spec, spec_dir):
        self.T, self.spec, self.dir = T, spec, spec_dir
        self.acc = T.c["accent"]
        self.logos = {a["name"]: a.get("logo") for a in spec.get("apps", [])}
        self.pages = []          # (image, [(box, url), ...])
        self.pdf = False         # link buttons are drawn only in a PDF (they are clickable there)

    def f(self, w, s): return self.T.font(w, s)

    def new(self, n, total):
        c = Image.new("RGB", (W, H), BG); dr = ImageDraw.Draw(c); links = []
        T = self.T
        if T.logo:
            lg = T.logo.resize((int(T.logo.width * 44 / T.logo.height), 44), Image.LANCZOS); c.paste(lg, (M, 52), lg)
            x = M + lg.width + 24
        else:
            x = M
        dr.text((x, 58), self.spec.get("title", ""), fill=MUTED, font=self.f("medium", 26))
        if n:
            t = f"{n} / {total}"; fw = dr.textlength(t, font=self.f("medium", 26))
            dr.text((W - M - fw, 58), t, fill=MUTED, font=self.f("medium", 26))
        dr.line((M, 124, W - M, 124), fill=LINE, width=2)
        return c, dr, links

    def chip(self, c, dr, x, y, name, tail=None, h=72, size=30):
        logo = self.logos.get(name); fn = self.f("semibold", size); ft = self.f("medium", size - 2)
        tail_txt = f"  ·  {tail}" if tail else ""; ic = h - 16
        left = 8 + ic + 16 if logo else 28
        w = left + dr.textlength(name, font=fn) + dr.textlength(tail_txt, font=ft) + 30
        aa_rrect(c, (x, y, x + w, y + h), h // 2, fill=CARD)
        if logo:
            im, m = logo_img(logo, ic, self.dir); c.paste(im, (x + 8, y + 8), m)
        a, d = fn.getmetrics(); tx = x + left
        dr.text((tx, y + (h - a - d) // 2 - 1), name, fill=TEXT, font=fn)
        if tail_txt:
            a2, d2 = ft.getmetrics()
            dr.text((tx + dr.textlength(name, font=fn), y + (h - a2 - d2) // 2), tail_txt, fill=MUTED, font=ft)
        return h

    @staticmethod
    def vtop(font, n, lh, top, h):
        """y to draw n lines so that their cap height sits optically centred in a box (fonts differ in descent)."""
        b = font.getbbox("НОДЖ"); block = (n - 1) * lh + (b[3] - b[1])
        return top + (h - block) / 2 - b[1]

    def text(self, dr, x, y, s, font, fill, maxw, lh):
        for ln in wrap(dr, s, font, maxw):
            dr.text((x, y), ln, fill=fill, font=font); y += lh
        return y

    def button(self, c, dr, x, y, text, url, links):
        fn = self.f("semibold", 28); w = dr.textlength(text + "  →", font=fn) + 64; h = 68
        aa_rrect(c, (x, y, x + w, y + h), h // 2, fill=self.acc); a_, d_ = fn.getmetrics()
        dr.text((x + 32, y + (h - a_ - d_) // 2 - 1), text + "  →", fill=self.T.c["accent_text"], font=fn)
        links.append(((x, y, x + w, y + h), url)); return h

    # ---- pages ----
    def cover_icons(self, total):
        """Bright cover: big title on the left, large tilted app icons bleeding off the right edge."""
        s = self.spec; T = self.T; c = Image.new("RGB", (W, H), BG); dr = ImageDraw.Draw(c); links = []
        if T.logo:
            lg = T.logo.resize((int(T.logo.width * 60 / T.logo.height), 60), Image.LANCZOS); c.paste(lg, (M, 70), lg)
        y = 250; ft = self.f("semibold", 150)
        CW = 740                                   # left column; icons start at ~x 860
        lines = []
        for para in s.get("cover_title", s["title"]).split("\n"):
            cur = ""
            for wd in para.split(" "):
                nxt = (cur + " " + wd).strip()
                if cur and dr.textlength(nxt, font=ft) > CW: lines.append(cur); cur = wd
                else: cur = nxt
            lines.append(cur)
        while ft.size > 90 and max(dr.textlength(l, font=ft) for l in lines) > CW:
            ft = self.f("semibold", ft.size - 10)
        step = int(ft.size * 0.9)                 # tight leading for the display title
        for ln in lines:
            dr.text((M - 6, y), ln, fill=TEXT, font=ft); y += step
        y = y - step + ft.getbbox("Н")[3]          # baseline of the last title line
        if s.get("subtitle"):
            fs = self.f("medium", 42); y = self.text(dr, M, y + 56 - fs.getbbox("Н")[1], s["subtitle"], fs, MUTED, 820, 52)
        if s.get("meta"):
            fm = self.f("regular", 28); mh = 36 * (1 + int(dr.textlength(s["meta"], font=fm) // CW))
            self.text(dr, M, H - 70 - mh, s["meta"], fm, MUTED, CW, 36)
        apps = [a for a in s.get("apps", []) if a.get("logo")][:6]
        spots = [(1080, 270, -6), (1530, 240, 7), (1110, 690, 5), (1560, 670, -6), (1070, 1110, -4), (1520, 1100, 6)]
        size, K = 410, 2
        for a, (cx, cy, rot) in zip(apps, spots):
            sz = size * K; bw = 16 * K
            im, _ = logo_img(a["logo"], sz, self.dir)
            tile = Image.new("RGBA", (sz + 2 * bw, sz + 2 * bw), (0, 0, 0, 0))
            tile.paste(Image.new("RGBA", tile.size, BG + (255,)), (0, 0), aa_mask(tile.size, int((sz + 2 * bw) * 0.235)))
            tile.paste(im, (bw, bw), aa_mask((sz, sz), int(sz * 0.225)))
            tile = tile.rotate(rot, resample=Image.BICUBIC, expand=True)
            tile = tile.resize((tile.width // K, tile.height // K), Image.LANCZOS)
            c.paste(tile, (cx - tile.width // 2, cy - tile.height // 2), tile)
        self.pages.append((c, links))

    def cover(self, total):
        if self.spec.get("cover", "icons") == "icons" and len([a for a in self.spec.get("apps", []) if a.get("logo")]) >= 3:
            return self.cover_icons(total)
        s = self.spec; c, dr, links = self.new(None, total)
        y = 250
        y = self.text(dr, M, y, s["title"], self.f("semibold", 120), TEXT, W - 2 * M, 126) + 10
        if s.get("subtitle"): y = self.text(dr, M, y, s["subtitle"], self.f("medium", 44), MUTED, W - 2 * M, 54)
        apps = s.get("apps", []); n = max(len(apps), 1)
        ic = min(200, int((W - 2 * M - (n - 1) * 40) / n)); x = M; yy = H - 160 - ic - 60
        for a in apps:
            im, m = logo_img(a.get("logo"), ic, self.dir); c.paste(im, (x, yy), m)
            fn = self.f("semibold", 30); tw = dr.textlength(a["name"], font=fn)
            dr.text((x + (ic - tw) / 2, yy + ic + 18), a["name"], fill=TEXT, font=fn)
            if a.get("url"): links.append(((x, yy, x + ic, yy + ic + 60), a["url"]))
            x += ic + 40
        if s.get("meta"): dr.text((M, H - 110), s["meta"], fill=MUTED, font=self.f("regular", 28))
        self.pages.append((c, links))

    def matrix(self, n, total):
        mx = self.spec["matrix"]; c, dr, links = self.new(n, total)
        y = 170; dr.text((M, y), mx.get("title", "Кто что умеет"), fill=TEXT, font=self.f("semibold", 64)); y += 110
        cols = mx["columns"]; rows = mx["rows"]; first = 330
        cw = (W - 2 * M - first) / len(cols); fh = self.f("semibold", 24); fc = self.f("medium", 27)
        hl = [wrap(dr, col, fh, cw - 24) for col in cols]; hh = max(len(l) for l in hl) * 32 + 30
        for i, l in enumerate(hl):
            for j, ln in enumerate(l): dr.text((M + first + i * cw + 12, y + 12 + j * 32), ln, fill=MUTED, font=fh)
        y += hh
        avail = H - 150 - y; rh = min(130, max(84, avail / max(len(rows), 1)))
        for k, r in enumerate(rows):
            if k % 2 == 0: aa_rrect(c, (M, y, W - M, y + rh), 24, fill=CARD)
            im, m = logo_img(self.logos.get(r["app"]), 52, self.dir); c.paste(im, (M + 18, int(y + (rh - 52) / 2)), m)
            dr.text((M + 86, y + rh / 2 - 18), r["app"], fill=TEXT, font=self.f("semibold", 30))
            for i, cell in enumerate(r["cells"]):
                col = self.acc if cell.strip() == "✓" else (MUTED if cell.strip() in ("—", "-", "") else TEXT)
                fnt = self.f("semibold", 40) if cell.strip() in ("✓", "—") else fc
                lines = wrap(dr, cell, fnt, cw - 24); lh = 34
                ty = self.vtop(fnt, len(lines), lh, y, rh)
                for ln in lines:
                    tw = dr.textlength(ln, font=fnt)
                    dr.text((M + first + i * cw + (cw - tw) / 2, ty), ln, fill=col, font=fnt); ty += lh
            y += rh
        if mx.get("note"): dr.text((M, H - 100), mx["note"], fill=MUTED, font=self.f("regular", 26))
        self.pages.append((c, links))

    def finding(self, fd, n, total):
        c, dr, links = self.new(n, total)
        three = len(fd.get("screens", [])) >= 3 and not fd.get("callouts")
        LW = 540 if three else 660; y = 170   # 3 screens: narrower text so the screens stay large
        y += self.chip(c, dr, M, y, fd["app"], fd.get("tail")) + 40
        y = self.text(dr, M, y, fd["title"], self.f("semibold", 54), TEXT, LW, 58) + 20
        y = self.text(dr, M, y, fd.get("body", ""), self.f("regular", 30), TEXT, LW, 39) + 34
        if fd.get("why"):
            fl = self.f("semibold", 22); dr.text((M, y), "ПОЧЕМУ ЭТО ВАЖНО", fill=self.acc, font=fl); y += 38
            y = self.text(dr, M, y, fd["why"], self.f("regular", 28), MUTED, LW, 36) + 28
        if fd.get("confidence") and fd["confidence"] != "Факт":   # only a hypothesis needs a tag
            fn = self.f("semibold", 24); t = fd["confidence"]; w = dr.textlength(t, font=fn) + 40; h = 46
            aa_rrect(c, (M, y, M + w, y + h), h // 2, fill=CARD); a_, d_ = fn.getmetrics()
            dr.text((M + 20, y + (h - a_ - d_) // 2), t, fill=MUTED, font=fn); y += h + 24
        if fd.get("link") and self.pdf:
            self.button(c, dr, M, max(y, H - 170), fd["link"].get("text", "Открыть в SCRN"), fd["link"]["url"], links)
        # screens
        scr = fd.get("screens", [])[:3]; x0 = M + LW + (60 if three else 70); aw = W - M - x0; top = 170; ah = H - 90 - top
        if fd.get("callouts"):
            self.callouts(c, dr, fd, x0, aw, top, ah)
        elif scr:
            gap = 28 if three else 32; sw = int((aw - gap * (len(scr) - 1)) / len(scr))
            ims = [prep_any(s) for s in scr]
            # fit by height: label row 56 px
            for k, (s, im) in enumerate(zip(scr, ims)):
                w = sw; h = int(im.height * w / im.width)
                if h > ah - 64: h = ah - 64; w = int(im.width * h / im.height)
                x = int(x0 + k * (sw + gap) + (sw - w) / 2)
                if s.get("label"):
                    dr.text((x, top), s["label"], fill=MUTED, font=self.f("semibold", 26))
                im2 = im.resize((w, h), Image.LANCZOS); r = 24 if (s.get("crop") or s.get("parts")) else int(w * 0.09)
                aa_rrect(c, (x - 2, top + 54, x + w + 2, top + 58 + h), r + 2, fill=LINE)
                c.paste(im2, (x, top + 56), aa_mask((w, h), r))
                if s.get("url"): links.append(((x, top + 56, x + w, top + 56 + h), s["url"]))
        self.pages.append((c, links))

    def callouts(self, c, dr, fd, x0, aw, top, ah):
        """One big screen plus floating cards cut from the interface in other states:
        "screens": [{main}], "callouts": [{"label", "parts": [{screen, crop}, ...]}, ...] (2–3 cards)."""
        main = fd["screens"][0]; im = prep_any(main)
        h = ah - 56; w = int(im.width * h / im.height); x = x0 + 8
        if main.get("label"): dr.text((x, top), main["label"], fill=MUTED, font=self.f("semibold", 26))
        aa_rrect(c, (x - 2, top + 54, x + w + 2, top + 58 + h), int(w * 0.09) + 2, fill=LINE)
        c.paste(im.resize((w, h), Image.LANCZOS), (x, top + 56), aa_mask((w, h), int(w * 0.09)))
        cards = fd["callouts"][:3]; cw = min(500, aw - w + 70); cx = x0 + aw - cw
        built = []
        for co in cards:
            ims = [prep(p) for p in co["parts"]]
            ims = [i.resize((cw, int(i.height * cw / i.width)), Image.LANCZOS) for i in ims]
            card = Image.new("RGB", (cw, sum(i.height for i in ims) + 2 * (len(ims) - 1)), (232, 232, 236))
            y = 0
            for i in ims: card.paste(i, (0, y)); y += i.height + 2
            built.append((co, card))
        fl = self.f("semibold", 28); a_, d_ = fl.getmetrics(); ph = 52; lab = ph + 14; gap = 56
        total_h = sum(cd.height + lab for _, cd in built) + gap * (len(built) - 1)
        y = top + 56 + max(0, (h - total_h) // 2)
        for k, (co, card) in enumerate(built):
            col = self.acc if k == len(built) - 1 else TEXT
            if co.get("label"):   # a pill, so the label reads even where it overlaps the main screen
                pw = int(dr.textlength(co["label"], font=fl)) + 44
                aa_rrect(c, (cx, y, cx + pw, y + ph), ph // 2, fill=col if k == len(built) - 1 else CARD)
                dr.text((cx + 22, self.vtop(fl, 1, 0, y, ph)), co["label"], fill=self.T.c["accent_text"] if k == len(built) - 1 else TEXT, font=fl)
            y += lab; r = 26
            sh = Image.new("L", (card.width + 120, card.height + 120), 0)
            ImageDraw.Draw(sh).rounded_rectangle((60, 60, 60 + card.width, 60 + card.height), r, fill=200)
            sh = sh.filter(ImageFilter.GaussianBlur(24))
            c.paste(Image.new("RGB", sh.size, (0, 0, 0)), (cx - 60, y - 60 + 14), sh)
            aa_rrect(c, (cx - 3, y - 3, cx + card.width + 3, y + card.height + 3), r + 3, fill=col)
            c.paste(card, (cx, y), aa_mask(card.size, r))
            y += card.height + gap

    def summary(self, n, total):
        sm = self.spec["summary"]; c, dr, links = self.new(n, total)
        y = 170; dr.text((M, y), sm.get("title", "Итог"), fill=TEXT, font=self.f("semibold", 64)); y += 110
        fb = self.f("medium", 30)
        for b in sm.get("bullets", []):
            lines = wrap(dr, b["text"], fb, W - 2 * M - 140); bh = max(len(lines) * 42 + 30, 80)
            aa_rrect(c, (M, y, W - M, y + bh), 28, fill=CARD)
            if b.get("app") and self.logos.get(b["app"]):
                im, m = logo_img(self.logos[b["app"]], 52, self.dir); c.paste(im, (M + 20, y + (bh - 52) // 2), m)
            ty = self.vtop(fb, len(lines), 42, y, bh)
            for i, ln in enumerate(lines): dr.text((M + 96, ty + i * 42), ln, fill=TEXT, font=fb)
            y += bh + 12
        if sm.get("conclusion"):
            fc = self.f("semibold", 34); lines = wrap(dr, sm["conclusion"], fc, W - 2 * M - 80)
            bh = len(lines) * 42 + 48; y += 10
            aa_rrect(c, (M, y, W - M, y + bh), 28, fill=self.acc)
            for i, ln in enumerate(lines):
                tw = dr.textlength(ln, font=fc)
                dr.text(((W - tw) / 2, self.vtop(fc, len(lines), 42, y, bh) + i * 42), ln, fill=self.T.c["accent_text"], font=fc)
            y += bh + 24
        if sm.get("caveats"): self.text(dr, M, y, sm["caveats"], self.f("regular", 26), MUTED, W - 2 * M, 33)
        self.pages.append((c, links))

    def build(self):
        s = self.spec
        total = 1 + bool(s.get("matrix")) + len(s.get("findings", [])) + bool(s.get("summary"))
        n = 1; self.cover(total)
        if s.get("matrix"): n += 1; self.matrix(n, total)
        for fd in s.get("findings", []): n += 1; self.finding(fd, n, total)
        if s.get("summary"): n += 1; self.summary(n, total)


def save_pdf(pages, out):
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    pw, ph = 842, 595; k = pw / W
    cv = canvas.Canvas(out, pagesize=(pw, ph))
    for img, links in pages:
        cv.drawImage(ImageReader(img), 0, 0, pw, ph)
        for (x0, y0, x1, y1), url in links:
            cv.linkURL(url, (x0 * k, ph - y1 * k, x1 * k, ph - y0 * k), relative=0)
        cv.showPage()
    cv.save()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec"); ap.add_argument("out", help="out.pdf, or a folder for one JPG per page")
    ap.add_argument("--theme", default=os.path.join(HERE, "..", "assets", "theme-scrn.json"))
    ap.add_argument("--png-dir")
    a = ap.parse_args()
    spec = json.load(open(a.spec)); T = rc.Theme(a.theme)
    global BG, CARD, LINE, TEXT, MUTED   # same dark look as the carousel (theme colours)
    BG, CARD, LINE, TEXT, MUTED = T.c["bg"], T.c["card"], T.c["line"], T.c["text"], T.c["muted"]
    refs = [x.get("logo") for x in spec.get("apps", []) if x.get("logo")]
    refs += [p["screen"] for fd in spec.get("findings", []) for sc in fd.get("screens", []) for p in (sc.get("parts") or [sc])]
    fetch_many([r for r in refs if not os.path.exists(os.path.join(os.path.dirname(os.path.abspath(a.spec)), r))])
    R = Report(T, spec, os.path.dirname(os.path.abspath(a.spec))); R.pdf = a.out.lower().endswith(".pdf"); R.build()
    if not R.pdf:
        os.makedirs(a.out, exist_ok=True)
        for i, (img, _) in enumerate(R.pages, 1):
            p = os.path.join(a.out, f"page_{i:02d}.jpg"); img.save(p, quality=93); print(p)
        return
    if a.png_dir:
        os.makedirs(a.png_dir, exist_ok=True)
        for i, (img, _) in enumerate(R.pages, 1): img.save(os.path.join(a.png_dir, f"page_{i:02d}.png"))
    try:
        save_pdf(R.pages, a.out); print(a.out)
    except ImportError:
        R.pages[0][0].save(a.out, save_all=True, append_images=[p for p, _ in R.pages[1:]], resolution=150)
        print(a.out, "(no reportlab: links are not clickable)")


if __name__ == "__main__":
    main()
