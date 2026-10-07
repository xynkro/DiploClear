#!/usr/bin/env python3
"""Flatten page 1 of the New Zealand master so its sample mission can't be recovered.

The MFAT master DiploClear was given is a REAL FILED REQUEST, not a blank form: page 1
carries a named officer's contact details, a sample captain, callsign, alternate regs, the
full NZ itinerary with dates and the overflight routes. Painting white rectangles over
those at render time hides them visually but leaves every word in the PDF's text layer,
recoverable with copy-paste or `pdftotext` (audit, 2026-08-13).

So we bake the redaction in at build time instead:
    page 1  -> white out each sample region, RASTERISE (no text layer survives), re-wrap
    pages 2-4 -> left as vector text; they are MFAT's instructions and hold no mission data

The runtime overlay in index.html is unchanged — it draws the mission's values on top, and
its own white-out rectangles simply become no-ops over already-blank areas.

Usage:  python3 tools/flatten_nz.py        # writes Master Forms/NZ/nz_flat.pdf
Then rebundle (tools/build_templates.py) so lib/templates_data.js picks it up.
"""
import os, re, subprocess, sys, tempfile
import pikepdf
from PIL import Image, ImageDraw
from reportlab.pdfgen import canvas

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "Master Forms", "NZ", "nz.pdf")
DST = os.path.join(ROOT, "Master Forms", "NZ", "nz_flat.pdf")
INDEX = os.path.join(ROOT, "index.html")
DPI = 200


def rects_from_index():
    """Read PDFMAP.nz's blanks + field boxes so the redaction can never drift from the map."""
    s = open(INDEX, encoding="utf-8").read()
    nz = re.search(r'const PDFMAP = \{ nz:\{(.*?)\n  jordan:', s, re.S)
    if not nz:
        sys.exit("!! could not locate PDFMAP.nz in index.html")
    body = nz.group(1)
    out = [(float(a), float(b), float(c), float(d)) for a, b, c, d in
           re.findall(r'\{x:([\d.]+),\s*w:([\d.]+),\s*top:([\d.]+),\s*bot:([\d.]+)\}', body)]
    # field entries carry the same x/w/top/bot shape and also sit over sample values
    fields = re.findall(r'\{x:([\d.]+),\s*w:([\d.]+),\s*top:([\d.]+),\s*bot:([\d.]+),\s*key:', body)
    out += [(float(a), float(b), float(c), float(d)) for a, b, c, d in fields]
    return out


def main():
    if not os.path.exists(SRC):
        sys.exit("!! missing %s" % SRC)
    rects = rects_from_index()
    print("  redaction rects from PDFMAP.nz: %d" % len(rects))

    src = pikepdf.open(SRC)
    pw, ph = float(src.pages[0].MediaBox[2]), float(src.pages[0].MediaBox[3])
    print("  page 1: %.1f x %.1f pt, %d pages total" % (pw, ph, len(src.pages)))

    with tempfile.TemporaryDirectory() as td:
        subprocess.run(["pdftoppm", "-f", "1", "-l", "1", "-r", str(DPI), "-png",
                        SRC, os.path.join(td, "pg")], check=True)
        png = [f for f in os.listdir(td) if f.endswith(".png")]
        if not png:
            sys.exit("!! pdftoppm produced no image")
        img_path = os.path.join(td, png[0])
        img = Image.open(img_path).convert("RGB")
        sx, sy = img.width / pw, img.height / ph
        d = ImageDraw.Draw(img)
        for x, w, top, bot in rects:          # PDF pts, top-left origin -> pixels
            d.rectangle([x * sx, top * sy, (x + w) * sx, bot * sy], fill=(255, 255, 255))
        red = os.path.join(td, "redacted.png")
        img.save(red, "PNG")
        print("  rasterised %dx%d px and painted %d white rects" % (img.width, img.height, len(rects)))

        one = os.path.join(td, "page1.pdf")
        c = canvas.Canvas(one, pagesize=(pw, ph))
        c.drawImage(red, 0, 0, width=pw, height=ph)
        c.save()

        out = pikepdf.open(one)                       # rasterised page 1 ...
        for p in src.pages[1:]:                       # ... + the untouched instruction pages
            out.pages.append(p)
        out.save(DST)
        out.close()
    src.close()

    # GATE: no sample word may survive anywhere in the flattened file
    txt = subprocess.run(["pdftotext", DST, "-"], capture_output=True, text=True).stdout
    # The token list lives in xfa_flatten/leakwords.local.txt, which is gitignored: it names a
    # person and carries a phone number lifted from the master, so the guard must not be
    # published alongside the pipeline it guards.
    words_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "xfa_flatten", "leakwords.local.txt")
    if not os.path.exists(words_file):
        sys.exit("!! leakwords.local.txt missing — refusing to pass a scrub that was never checked")
    with open(words_file, encoding="utf-8") as fh:
        words = [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]
    if not words:
        sys.exit("!! leakwords.local.txt is empty — refusing to pass an unchecked scrub")
    bad = [w for w in words if w in txt]
    if bad:
        sys.exit("!! sample data still extractable: %s" % bad)
    print("  text-layer gate: clean (no sample values extractable)")
    print("  wrote %s (%d KB, %d pages)" %
          (os.path.relpath(DST, ROOT), os.path.getsize(DST) // 1024, len(pikepdf.open(DST).pages)))


if __name__ == "__main__":
    main()
