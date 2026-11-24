"""Render a comparison carousel (1080x1350 JPG slides) from a JSON spec.

Usage:
  python render_carousel.py slides.json out_dir [--theme path/to/theme.json]

Default theme: assets/theme-scrn.json (scrn.gallery look: Inter, #050505, orange accent, SCRN logo).
To rebrand, copy the theme file, change colors / fonts / logo / cta, pass --theme.

Spec format (all text is printed exactly as given — write it in the user's language):
{
  "slides": [
    {"type": "cover",
     "chip": "OTP Bank · 2025 → 2026",
     "title": "What changed in SBP transfers",
     "subtitle": "26 screens from two versions of the app",
     "left":  {"label": "October 2025",   "screen": "<image id>", "crop": [0,0,1,1]},
     "right": {"label": "September 2026", "screen": "<image id>"}},

    {"type": "pair",
     "chip": "Transfer form",
     "title": "The whole transfer on one screen",
     "body": "Two or three short sentences of evidence.",
     "left":  {"label": "2025", "screen": "<id>", "crop": [0, 0.23, 1, 1]},
     "right": {"label": "2026", "screen": "<id>", "blur": [[0.10, 0.45, 0.40, 0.48]]}},

    {"type": "stack",               # same element from both sides, one above the other (banners, rows, chips)
     "chip": "...", "title": "...", "body": "...",
     "items": [{"label": "2025", "screen": "<id>", "crop": [0, 0.68, 1, 0.80]},
               {"label": "2026", "screen": "<id>", "crop": [0, 0.67, 1, 0.77]}]},

    {"type": "summary",
     "chip": "Summary", "title": "Where OTP is heading",
     "bullets": ["...", "...", "..."],
     "cta": {"title": "scrn.gallery", "subtitle": "All screens of both versions"}}
  ]
}
- crop / blur boxes are FRACTIONS of the screenshot: [x0, y0, x1, y1] in 0..1.
- The right-hand / last label gets the accent colour (= "now" / "the app in focus").
  Override per side with "accent": true/false.
- blur hides personal data that the source screenshot left visible.
"""
import argparse
import sys
import json
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from screens import load, fetch_many

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))


_CMAPS = {}


def _cmap(path):
    """Set of code points the font file covers (None if fontTools is missing)."""
    if path not in _CMAPS:
        try:
            from fontTools.ttLib import TTFont
            _CMAPS[path] = set(TTFont(path, lazy=True).getBestCmap())
        except Exception:
            _CMAPS[path] = None
    return _CMAPS[path]


def _runs(text, f):
    out = []
    for ch in text:
        fb = ord(ch) not in f._cmap and not ch.isspace()
        if out and out[-1][1] == fb: out[-1][0] += ch
        else: out.append([ch, fb])
    return out


_orig_text, _orig_len = ImageDraw.ImageDraw.text, ImageDraw.ImageDraw.textlength


def _text(self, xy, text, fill=None, font=None, *a, **kw):
    if font is None or not hasattr(font, "_fb") or all(ord(c) in font._cmap or c.isspace() for c in str(text)):
        return _orig_text(self, xy, text, fill, font, *a, **kw)
    x, y = xy; dy = font.getmetrics()[0] - font._fb.getmetrics()[0]
    for run, fb in _runs(str(text), font):
        f = font._fb if fb else font
        _orig_text(self, (x, y + (dy if fb else 0)), run, fill, f, *a, **kw); x += _orig_len(self, run, font=f)


def _textlength(self, text, font=None, *a, **kw):
    if font is None or not hasattr(font, "_fb"):
        return _orig_len(self, text, font, *a, **kw)
    return sum(_orig_len(self, run, font=(font._fb if fb else font)) for run, fb in _runs(str(text), font))


ImageDraw.ImageDraw.text, ImageDraw.ImageDraw.textlength = _text, _textlength


def hexrgb(h):
    h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


class Theme:
    def __init__(self, path):
        t = json.load(open(path))
        base = os.path.dirname(os.path.abspath(path))
        def res(p):
            if not p: return None
            for cand in (p, os.path.join(base, p), os.path.join(ROOT, p)):
                if os.path.exists(cand): return cand
            return None
        self.W, self.H = t.get("size", [1080, 1350])
        self.M = t.get("margin", 64)
        self.c = {k: hexrgb(v) for k, v in t["colors"].items()}
        self.fonts = {k: res(v) for k, v in t["fonts"].items()}
        self.fallback = {k: res(v) for k, v in t.get("fallback_fonts", {}).items()}
        self.logo = Image.open(res(t["logo"])).convert("RGBA") if res(t.get("logo")) else None
        self.cta = t.get("cta", {})
        self.credit = t.get("credit")
        self.name = t.get("name", "custom")
        self.force_fb = t.get("fallback_chars", {})

    def font(self, w, s):
        p = self.fonts.get(w) or self.fonts.get("regular")
        try: f = ImageFont.truetype(p, s)
        except Exception: return ImageFont.load_default()
        fb = self.fallback.get(w) or self.fallback.get("regular")
        cmap = _cmap(p)
        if fb and cmap is not None:          # glyphs the brand font lacks (→, ✓, +) are drawn with the fallback
            force = self.force_fb.get(w, "")     # chars the brand font has but draws oddly (Zangezi Black «*»)
            f._fb = ImageFont.truetype(fb, s); f._cmap = set(cmap) - {ord(ch) for ch in force}
        return f


def frac_box(im, box):
    w, h = im.size; x0, y0, x1, y1 = box
    return (int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h))


def prep(side):
    im = load(side["screen"])
    if im is None:
        im = Image.new("RGB", (600, 1300), (60, 60, 60))
    for b in side.get("blur", []):
        bb = frac_box(im, b); im.paste(im.crop(bb).filter(ImageFilter.GaussianBlur(10)), bb[:2])
    if side.get("crop"):
        im = im.crop(frac_box(im, side["crop"]))
    return im


def rmask(size, r):
    m = Image.new("L", size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), r, fill=255); return m


def paste(c, im, x, y, w, maxh, r):
    im = im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)
    if im.height > maxh: im = im.crop((0, 0, w, maxh))
    c.paste(im, (x, y), rmask(im.size, r)); return im.height


NBSP = "\u00a0"
_SHORT = {"для", "без", "при", "про", "над", "под", "или", "как", "что", "это", "его", "она", "они", "его", "все", "уже"}


def typo(text):
    """Russian typography for line breaking: glue short words (prepositions, conjunctions, particles)
    to the next word, numbers to their units, and an em dash to the word before it."""
    import re
    s = str(text)
    s = re.sub(r" (—|–)", NBSP + r"\1", s)                       # no line starts with a dash
    s = re.sub(r"(\d) (?=\S)", "\\1" + NBSP, s)                  # 6 шт, 1419 ₽, 2 порции
    s = re.sub(r"([✓→№]) ", "\\1" + NBSP, s)                     # ✓ с видео, № 1
    def glue(m):
        w = m.group(1)
        return w + NBSP if (len(w) <= 2 or w.lower() in _SHORT) else m.group(0)
    for _ in range(2):                                            # «и в магазин» — both
        s = re.sub(r"(?:(?<=^)|(?<=[\s«(\u00a0]))([A-Za-zА-Яа-яЁё]{1,3}) ", glue, s)
    return s


def wrap(dr, text, f, maxw):
    """Wrap by width with hanging-preposition control and no one-word last line."""
    out = []
    for para in typo(text).split("\n"):
        lines, line = [], ""
        words = []
        for w_ in para.split(" "):          # a glued chain wider than the line is split back at its NBSPs
            if NBSP in w_ and dr.textlength(w_, font=f) > maxw:
                parts, cur, chunk = w_.split(NBSP), "", []   # fill from the right: short words stay with the next one
                for p_ in reversed(parts):
                    c_ = (p_ + NBSP + cur) if cur else p_
                    if cur and dr.textlength(c_, font=f) > maxw: chunk.append(cur); cur = p_
                    else: cur = c_
                chunk.append(cur); words += list(reversed(chunk))
            else:
                words.append(w_)
        for w_ in words:
            t_ = (line + " " + w_).strip()
            if not line or dr.textlength(t_, font=f) <= maxw: line = t_
            else: lines.append(line); line = w_
        lines.append(line)
        # widow: a lone short word on the last line -> pull one word down
        if len(lines) > 1 and " " not in lines[-1] and len(lines[-1]) < 12 and lines[-2].count(" ") >= 2:
            head, last = lines[-2].rsplit(" ", 1)
            cand = last + " " + lines[-1]
            if dr.textlength(cand, font=f) <= maxw: lines[-2], lines[-1] = head, cand
        out += lines
    return out


class _BaseR:
    def __init__(self, T): self.T = T

    def new(self):
        T = self.T; c = Image.new("RGB", (T.W, T.H), T.c["bg"]); return c, ImageDraw.Draw(c)

    def pill(self, dr, x, y, text, size=24, fg=None, bg=None, outline=None, h=48, padx=22, right=False):
        f = self.T.font("semibold", size); w = dr.textlength(text, font=f) + 2 * padx
        if right: x -= w
        dr.rounded_rectangle((x, y, x + w, y + h), h // 2, fill=bg, outline=outline, width=2 if outline else 0)
        a, d = f.getmetrics(); dr.text((x + padx, y + (h - (a + d)) // 2 - 1), text, fill=fg, font=f); return w

    def topbar(self, c, dr, n, total):
        T = self.T
        if T.logo:
            lg = T.logo.resize((int(T.logo.width * 46 / T.logo.height), 46), Image.LANCZOS); c.paste(lg, (T.M, 60), lg)
        if n:
            self.pill(dr, T.W - T.M, 60, f"{n} / {total}", fg=T.c["muted"], bg=T.c["card"], h=46, right=True)

    def text_block(self, dr, y, chip, title, body, tsize=64):
        T = self.T; L, Rr = T.M, T.W - T.M
        if chip:
            self.pill(dr, L, y, chip, fg=T.c["chip_text"], outline=T.c["line"]); y += 78
        ft = T.font("semibold", tsize)
        for ln in wrap(dr, title, ft, Rr - L): dr.text((L, y), ln, fill=T.c["text"], font=ft); y += int(tsize * 1.19)
        if body:
            y += 14; fb = T.font("regular", 31)
            for ln in wrap(dr, body, fb, Rr - L): dr.text((L, y), ln, fill=T.c["muted"], font=fb); y += 44
        return y

    def label_colors(self, side, default_accent):
        acc = side.get("accent", default_accent); T = self.T
        return (T.c["accent"], T.c["accent_text"]) if acc else (T.c["neutral_pill"], T.c["chip_text"])

    def cover(self, s, n, total):
        T = self.T; c, dr = self.new(); self.topbar(c, dr, None, total); L, Rr = T.M, T.W - T.M
        y = 170
        if s.get("chip"):
            self.pill(dr, L, y, s["chip"], size=26, fg=T.c["chip_text"], outline=T.c["line"], h=52); y += 88
        ft = T.font("semibold", 88)
        for ln in wrap(dr, s["title"], ft, Rr - L): dr.text((L, y), ln, fill=T.c["text"], font=ft); y += 98
        if s.get("subtitle"):
            dr.text((L, y + 18), s["subtitle"], fill=T.c["muted"], font=T.font("regular", 33)); y += 60
        y0 = y + 60; sw = 430
        for k, side in enumerate([s["left"], s["right"]]):
            x = L + 10 if k == 0 else Rr - 10 - sw
            bg, fg = self.label_colors(side, k == 1)
            paste(c, prep(side), x, y0 + 64, sw, T.H - y0 - 24, int(sw * 0.09))
            self.pill(dr, x, y0, side["label"], size=26, fg=fg, bg=bg, h=50, padx=20)
        return c

    def pair(self, s, n, total):
        T = self.T; c, dr = self.new(); self.topbar(c, dr, n, total); L, Rr = T.M, T.W - T.M
        y = self.text_block(dr, 150, s.get("chip"), s["title"], s.get("body")) + 36
        gap = 24; cw = (Rr - L - gap) // 2; ch = T.H - y
        for k, side in enumerate([s["left"], s["right"]]):
            x = L + k * (cw + gap)
            dr.rounded_rectangle((x, y, x + cw, T.H + 60), 44, fill=T.c["card"])
            bg, fg = self.label_colors(side, k == 1)
            self.pill(dr, x + 24, y + 24, side["label"], size=26, fg=fg, bg=bg, h=50, padx=20)
            sw = cw - 48; r = 28 if side.get("crop") else int(sw * 0.09)
            paste(c, prep(side), x + 24, y + 96, sw, ch - 96, r)
        return c

    def stack(self, s, n, total):
        T = self.T; c, dr = self.new(); self.topbar(c, dr, n, total); L, Rr = T.M, T.W - T.M
        y = self.text_block(dr, 150, s.get("chip"), s["title"], s.get("body")) + 40
        items = s["items"]; avail = T.H - 40 - y - 24 * (len(items) - 1)
        ims = [prep(it) for it in items]
        iw = Rr - L - 48
        while iw > 300 and sum(int(im.height * iw / im.width) + 120 for im in ims) > avail: iw -= 20
        for k, (it, im) in enumerate(zip(items, ims)):
            bh = int(im.height * iw / im.width) + 120
            dr.rounded_rectangle((L, y, Rr, y + bh), 44, fill=T.c["card"])
            bg, fg = self.label_colors(it, k == len(items) - 1)
            self.pill(dr, L + 24, y + 24, it["label"], size=26, fg=fg, bg=bg, h=50, padx=20)
            paste(c, im, (T.W - iw) // 2, y + 96, iw, 2000, 28); y += bh + 24
        return c

    def summary(self, s, n, total):
        T = self.T; c, dr = self.new(); self.topbar(c, dr, n, total); L, Rr = T.M, T.W - T.M
        y = 170
        if s.get("chip"):
            self.pill(dr, L, y, s["chip"], fg=T.c["chip_text"], outline=T.c["line"]); y += 80
        ft = T.font("semibold", 72)
        for ln in wrap(dr, s["title"], ft, Rr - L): dr.text((L, y), ln, fill=T.c["text"], font=ft); y += 86
        y += 34; fb = T.font("medium", 31)
        for b in s.get("bullets", []):
            lines = wrap(dr, b, fb, Rr - L - 120); bh = len(lines) * 42 + 40
            dr.rounded_rectangle((L, y, Rr, y + bh), 32, fill=T.c["card"])
            dr.ellipse((L + 30, y + bh // 2 - 11, L + 52, y + bh // 2 + 11), fill=T.c["accent"])
            for i, ln in enumerate(lines): dr.text((L + 84, y + 20 + i * 42), ln, fill=T.c["text"], font=fb)
            y += bh + 12
        cta = {**T.cta, **s.get("cta", {})}
        if cta:
            by = T.H - T.M - 170
            dr.rounded_rectangle((L, by, Rr, T.H - T.M), 44, fill=T.c["cta_bg"])
            tx = L + 40
            if T.logo:
                lg = T.logo.resize((int(T.logo.width * 90 / T.logo.height), 90), Image.LANCZOS); c.paste(lg, (L + 40, by + 40), lg); tx = L + 80 + lg.width
            dr.text((tx, by + 42), cta.get("title", ""), fill=T.c["cta_text"], font=T.font("semibold", 44))
            dr.text((tx, by + 100), cta.get("subtitle", ""), fill=T.c["cta_muted"], font=T.font("regular", 28))
        if T.name != "scrn" and T.credit:  # keep source credit when rebranded
            f = T.font("regular", 22); dr.text((L, T.H - 40), T.credit, fill=T.c["muted"], font=f)
        return c



# ---- v2: anti-aliased shapes, app chips with icons, icon cover, parts, conclusion card ----
S = 4  # supersampling factor

def aa_mask(size, r=None, circle=False):
    w, h = size; m = Image.new("L", (w * S, h * S), 0); d = ImageDraw.Draw(m)
    if circle: d.ellipse((0, 0, w * S - 1, h * S - 1), fill=255)
    else: d.rounded_rectangle((0, 0, w * S - 1, h * S - 1), r * S, fill=255)
    return m.resize((w, h), Image.LANCZOS)



def aa_rrect(cv, box, r, fill=None, outline=None, width=0):
    x0, y0, x1, y1 = [int(round(v)) for v in box]; w, h = x1 - x0, y1 - y0
    lay = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rounded_rectangle((0, 0, w * S - 1, h * S - 1), r * S,
                        fill=(fill + (255,)) if fill else None,
                        outline=(outline + (255,)) if outline else None, width=width * S)
    lay = lay.resize((w, h), Image.LANCZOS); cv.paste(lay, (x0, y0), lay)

def icon(lid, size):
    im = load(lid)
    if im is None: im = Image.new("RGB", (size, size), (80, 80, 80))
    w, h = im.size; k = min(w, h); im = im.crop(((w - k) // 2, (h - k) // 2, (w + k) // 2, (h + k) // 2))
    return im.convert("RGB").resize((size, size), Image.LANCZOS), aa_mask((size, size), circle=True)

CH, IC, PAD = 84, 64, 10  # chip height, icon size, inner padding (left = top = bottom)

class R(_BaseR):
    def new(self):
        c, dr = _BaseR.new(self); self.cv = c; return c, dr

    def pill(self, dr, x, y, text, size=24, fg=None, bg=None, outline=None, h=48, padx=22, right=False):
        f = self.T.font("semibold", size); w = dr.textlength(text, font=f) + 2 * padx
        if right: x -= w
        aa_rrect(self.cv, (x, y, x + w, y + h), h // 2, fill=bg, outline=outline, width=2 if outline else 0)
        a, d = f.getmetrics(); dr.text((x + padx, y + (h - (a + d)) // 2 - 1), text, fill=fg, font=f); return w

    def chip(self, c, dr, x, y, name, tail=None, logo=None):
        T = self.T; fn = T.font("semibold", 34); ftl = T.font("medium", 31)
        tail_txt = f"  ·  {tail}" if tail else ""
        left = PAD + IC + 18 if logo else 32
        w = left + dr.textlength(name, font=fn) + dr.textlength(tail_txt, font=ftl) + 32
        aa_rrect(c, (x, y, x + w, y + CH), CH // 2, fill=T.c["card"])
        if logo:
            im, m = icon(logo, IC); c.paste(im, (x + PAD, y + (CH - IC) // 2), m)
        tx = x + left; a, d = fn.getmetrics()
        dr.text((tx, y + (CH - (a + d)) // 2 - 1), name, fill=T.c["text"], font=fn)
        if tail_txt:
            tx += dr.textlength(name, font=fn); a2, d2 = ftl.getmetrics()
            dr.text((tx, y + (CH - (a2 + d2)) // 2), tail_txt, fill=T.c["muted"], font=ftl)
        return CH

    def side_card(self, c, dr, x, y, cw, ch, side, accent):
        T = self.T
        aa_rrect(c, (x, y, x + cw, T.H + 60), 44, fill=T.c["card"])
        bg, fg = self.label_colors(side, accent)
        self.pill(dr, x + 24, y + 24, side["label"], size=26, fg=fg, bg=bg, h=50, padx=20)
        sw = cw - 48; yy = y + 96
        if side.get("parts"):
            for p in side["parts"]:
                yy += paste(c, prep(p), x + 24, yy, sw, T.H - yy - 10, 24) + 16
        else:
            r = 28 if side.get("crop") else int(sw * 0.09)
            paste(c, prep(side), x + 24, yy, sw, ch - 96, r)

    def pair(self, s, n, total):
        T = self.T; c, dr = self.new(); self.topbar(c, dr, n, total); L, Rr = T.M, T.W - T.M
        if "app" in s: y = 146 + self.chip(c, dr, L, 146, s["app"]["name"], s.get("chip"), s["app"]["logo"]) + 28
        elif s.get("chip"): y = 146 + self.chip(c, dr, L, 146, s["chip"]) + 28
        else: y = 150
        y = self.text_block(dr, y, None, s["title"], s.get("body")) + 36
        gap = 24; cw = (Rr - L - gap) // 2; ch = T.H - y
        for k, side in enumerate([s["left"], s["right"]]):
            self.side_card(c, dr, L + k * (cw + gap), y, cw, ch, side, k == 1)
        return c

    def cover(self, s, n, total):
        T = self.T; c, dr = self.new(); self.topbar(c, dr, None, total); L, Rr = T.M, T.W - T.M
        y = 166
        if s.get("chip"): self.chip(c, dr, L, y, s["chip"])
        if s.get("logos"):
            ic = 72; x = Rr - len(s["logos"]) * (ic + 12) + 12
            for lid in s["logos"]:
                im, m = icon(lid, ic); c.paste(im, (x, y + (CH - ic) // 2), m); x += ic + 12
        y += CH + 40
        ft = T.font("semibold", 88)
        for ln in wrap(dr, s["title"], ft, Rr - L): dr.text((L, y), ln, fill=T.c["text"], font=ft); y += 98
        if s.get("subtitle"):
            dr.text((L, y + 18), s["subtitle"], fill=T.c["muted"], font=T.font("regular", 33)); y += 60
        y0 = y + 50; sw = 430
        for k, side in enumerate([s["left"], s["right"]]):
            x = L + 10 if k == 0 else Rr - 10 - sw
            bg, fg = self.label_colors(side, k == 1)
            paste(c, prep(side), x, y0 + 64, sw, T.H - y0 - 24, int(sw * 0.09))
            self.pill(dr, x, y0, side["label"], size=26, fg=fg, bg=bg, h=50, padx=20)
        return c

    def summary(self, s, n, total):
        T = self.T; c, dr = self.new(); self.topbar(c, dr, n, total); L, Rr = T.M, T.W - T.M
        y = 166
        if s.get("chip"): y += self.chip(c, dr, L, y, s["chip"]) + 28
        ft = T.font("semibold", 72)
        for ln in wrap(dr, s["title"], ft, Rr - L): dr.text((L, y), ln, fill=T.c["text"], font=ft); y += 86
        y += 18; fb = T.font("medium", 31)
        for b in s.get("bullets", []):
            b = b if isinstance(b, dict) else {"text": b}
            lines = wrap(dr, b["text"], fb, Rr - L - 130); bh = max(len(lines) * 42 + 30, 80)
            aa_rrect(c, (L, y, Rr, y + bh), 32, fill=T.c["card"])
            if b.get("logo"):
                im, m = icon(b["logo"], 52); c.paste(im, (L + 22, y + (bh - 52) // 2), m)
            else:
                d = Image.new("RGBA", (22, 22)); d.paste(T.c["accent"] + (255,), (0, 0, 22, 22))
                c.paste(d, (L + 37, y + bh // 2 - 11), aa_mask((22, 22), circle=True))
            ty = y + (bh - len(lines) * 42) // 2 - 2
            for i, ln in enumerate(lines): dr.text((L + 96, ty + i * 42), ln, fill=T.c["text"], font=fb)
            y += bh + 10
        if s.get("conclusion"):
            fc = T.font("semibold", 32); lines = wrap(dr, s["conclusion"], fc, Rr - L - 72)
            bh = len(lines) * 44 + 44; y += 8
            aa_rrect(c, (L, y, Rr, y + bh), 32, fill=T.c["accent"])
            for i, ln in enumerate(lines): dr.text((L + 36, y + 20 + i * 44), ln, fill=T.c["accent_text"], font=fc)
        cta = {**T.cta, **s.get("cta", {})}
        by = T.H - T.M - 170
        aa_rrect(c, (L, by, Rr, T.H - T.M), 44, fill=T.c["cta_bg"]); tx = L + 40
        if T.logo:
            lg = T.logo.resize((int(T.logo.width * 90 / T.logo.height), 90), Image.LANCZOS); c.paste(lg, (L + 40, by + 40), lg); tx = L + 80 + lg.width
        dr.text((tx, by + 42), cta.get("title", ""), fill=T.c["cta_text"], font=T.font("semibold", 44))
        dr.text((tx, by + 100), cta.get("subtitle", ""), fill=T.c["cta_muted"], font=T.font("regular", 28))
        return c

    def cover_icons(self, s, n, total):
        """Bright cover: big title + large tilted app icons bleeding off the bottom."""
        import os
        T = self.T; c, dr = self.new(); self.topbar(c, dr, None, total); L, Rr = T.M, T.W - T.M
        y = 166
        if s.get("chip"): y += self.chip(c, dr, L, y, s["chip"]) + 34
        ft = T.font("semibold", s.get("title_size", 132))
        for ln in s["title"].split("\n"):
            dr.text((L - 6, y), ln, fill=T.c["text"], font=ft); y += int(s.get("title_size", 132) * 1.08)
        if s.get("subtitle"):
            fs = T.font("medium", 38); y += 14
            for ln in wrap(dr, s["subtitle"], fs, Rr - L): dr.text((L, y), ln, fill=T.c["muted"], font=fs); y += 50
        here = os.path.dirname(os.path.abspath(sys.argv[1]))
        for it in s["icons"]:
            size = it.get("size", 400); K = 2; sz = size * K; bw = 16 * K
            ref = it.get("path") or it.get("logo"); lp = os.path.join(here, ref)
            im = (load(lp) if os.path.exists(lp) else load(ref)) or Image.new("RGB", (sz, sz), (80, 80, 80))
            im = im.resize((sz, sz), Image.LANCZOS)
            tile = Image.new("RGBA", (sz + 2 * bw, sz + 2 * bw), (0, 0, 0, 0))
            # dark outline like the channel covers
            ol = Image.new("RGBA", tile.size, T.c["bg"] + (255,))
            tile.paste(ol, (0, 0), aa_mask(tile.size, int((sz + 2 * bw) * 0.235)))
            tile.paste(im, (bw, bw), aa_mask((sz, sz), int(sz * 0.225)))
            tile = tile.rotate(it.get("rot", 0), resample=Image.BICUBIC, expand=True)
            tile = tile.resize((tile.width // K, tile.height // K), Image.LANCZOS)
            cx, cy = it["at"]; c.paste(tile, (cx - tile.width // 2, cy - tile.height // 2), tile)
        return c


def rmask(size, r):  # anti-aliased mask for screenshots (overrides the plain one above)
    return aa_mask(size, r)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec"); ap.add_argument("out")
    ap.add_argument("--theme", default=os.path.join(ROOT, "assets", "theme-scrn.json"))
    a = ap.parse_args()
    T = Theme(a.theme); spec = json.load(open(a.spec)); r = R(T)
    slides = spec["slides"]; total = len(slides)
    refs = []
    for s in slides:
        for k in ("left", "right"):
            if k in s: refs.append(s[k]["screen"])
        refs += [it["screen"] for it in s.get("items", [])]
        for k in ("left", "right"):
            refs += [p["screen"] for p in s.get(k, {}).get("parts", [])]
    fetch_many(refs)
    os.makedirs(a.out, exist_ok=True); outs = []
    for i, s in enumerate(slides, 1):
        img = getattr(r, s["type"])(s, i, total)
        p = os.path.join(a.out, f"slide_{i:02d}.jpg"); img.save(p, quality=92); outs.append(p)
    th = [Image.open(p).resize((360, 450)) for p in outs]
    cols = min(5, len(th)); rows = (len(th) + cols - 1) // cols
    ov = Image.new("RGB", (cols * 370, rows * 460), (40, 40, 40))
    for i, t in enumerate(th): ov.paste(t, ((i % cols) * 370, (i // cols) * 460))
    ov.save(os.path.join(a.out, "overview.jpg"), quality=85)
    print("\n".join(outs + [os.path.join(a.out, "overview.jpg")]))


if __name__ == "__main__":
    main()
