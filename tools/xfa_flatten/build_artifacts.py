#!/usr/bin/env python3
"""Render the scrubbed XFA masters to flat PDFs and emit the overlay coordinate map.

Two passes off ONE scrubbed source:
  1. markers visible -> measure each value's position and the clear space on its line;
  2. markers cleared -> the SHIPPED template, so a submitted form has no [[marker]]
     residue in its text layer.
A gate then asserts pass 2 did not reflow (same page count, and every measured
coordinate lands on empty space), which is what makes reusing pass-1 coords safe.
"""
import json, os, re, subprocess, sys
import pikepdf

MK = ["purpose", "callsign", "aircraft", "reg", "captain", "dep", "dest", "crew_n", "pax"]
HERE = os.path.dirname(os.path.abspath(__file__))


def render(src, out, scale="1.3333333"):
    r = subprocess.run(["node", "capture.js", src, out, scale],
                       capture_output=True, text=True, cwd=HERE)
    if r.returncode != 0:
        print("  !! render failed for %s\n%s\n%s" % (src, r.stdout[-800:], r.stderr[-800:]))
        sys.exit(1)
    line = [l for l in r.stdout.splitlines() if l.startswith("WROTE")]
    print("    %-26s -> %-24s %s" % (src, out, line[0] if line else "?"))


def drop_page1(src, dst):
    pdf = pikepdf.open(src); del pdf.pages[0]; pdf.save(dst); pdf.close()


def coords_from(pdf_path, bbox_html):
    subprocess.run(["pdftotext", "-bbox", pdf_path, bbox_html], check=True, cwd=HERE)
    xml = open(os.path.join(HERE, bbox_html), encoding="latin1").read()
    pages = re.findall(r'<page width="([\d.]+)" height="([\d.]+)">(.*?)</page>', xml, re.S)
    coords = {k: [] for k in MK}
    WORD = re.compile(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>')
    for pnum, (pw, ph, body) in enumerate(pages, 1):
        ph = float(ph); pw = float(pw)
        allw = [(float(a), float(b), float(c), float(d), t)
                for a, b, c, d, t in WORD.findall(body)]
        for m in re.finditer(
            r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">\[\[(\w+)\]\]</word>',
            body):
            x0, y0, x1, y1, key = (float(m.group(1)), float(m.group(2)),
                                   float(m.group(3)), float(m.group(4)), m.group(5))
            if key not in coords:
                continue
            # room to draw before the next word on this baseline (else to the page margin)
            rights = [w[0] for w in allw
                      if abs(w[1] - y0) < 3 and w[0] > x0 + 0.5]
            maxw = round((min(rights) if rights else pw - 40) - x0 - 2, 1)
            coords[key].append({
                "page": pnum,
                "x": round(x0, 1),                       # left edge (draw origin)
                "y": round(ph - y1 + (y1 - y0) * 0.22, 1),  # baseline, bottom-left origin
                "wo": {"x": round(x0 - 1, 1), "y": round(ph - y1 - 1.5, 1),
                       "w": round(x1 - x0 + 2, 1), "h": round(y1 - y0 + 3, 1)},  # white-out box
                "maxw": maxw,
                "size": round((y1 - y0) * 0.86, 1),
            })
    return coords


def clear_markers(src, dst):
    pdf = pikepdf.open(src); xfa = pdf.Root.AcroForm.XFA
    idx = {str(xfa[i]): i + 1 for i in range(0, len(xfa), 2)}
    d = bytes(xfa[idx["datasets"]].read_bytes()).decode("utf-8")
    n = len(re.findall(r"\[\[\w+\]\]", d))
    xfa[idx["datasets"]].write(re.sub(r"\[\[\w+\]\]", "", d).encode("utf-8"))
    pdf.save(dst); pdf.close(); return n


def words_by_page(pdf_path, tmp_html):
    subprocess.run(["pdftotext", "-bbox", pdf_path, tmp_html], check=True, cwd=HERE)
    xml = open(os.path.join(HERE, tmp_html), encoding="latin1").read()
    out = {}
    for pn, (pw, ph, body) in enumerate(
            re.findall(r'<page width="([\d.]+)" height="([\d.]+)">(.*?)</page>', xml, re.S), 1):
        ph = float(ph)
        out[pn] = [(float(a), round(ph - float(d), 1), t) for a, b, c, d, t in re.findall(
            r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>', body)]
    return out


def main():
    os.chdir(HERE)
    print("AUSTRALIA:")
    # pass 1 — markers visible: measure where each value goes
    render("australia_patched.pdf", "australia_markers.pdf")
    coords = coords_from("australia_markers.pdf", "aus_bbox.html")
    json.dump(coords, open("aus_coords.json", "w"), indent=1)
    print("    markers found:", {k: len(v) for k, v in coords.items() if v})
    missing = [k for k in MK if not coords[k]]
    if missing:
        print("    !! no coords for: %s" % missing); sys.exit(1)
    pages = sorted({c["page"] for v in coords.values() for c in v})
    print("    marker pages:", pages)

    # pass 2 — markers cleared: this is the SHIPPED template (clean text layer, no
    # [[marker]] residue for anyone who copies text out of a submitted form).
    n = clear_markers("australia_patched.pdf", "australia_blank_src.pdf")
    render("australia_blank_src.pdf", "australia_blank.pdf")
    print("    cleared %d markers for the shipped blank" % n)

    # GATE: clearing must not reflow the page — every measured coord must be empty now.
    M, B = words_by_page("australia_markers.pdf", "m_.html"), words_by_page("australia_blank.pdf", "b_.html")
    if len(M) != len(B):
        print("    !! page count changed %d -> %d (reflow)" % (len(M), len(B))); sys.exit(1)
    occupied = []
    for k, v in coords.items():
        for c in v:
            hit = [t for (x, y, t) in B.get(c["page"], [])
                   if abs(y - c["y"]) < 4 and abs(x - c["x"]) < 14]
            if hit:
                occupied.append((k, c["page"], c["x"], c["y"], hit[:3]))
    if occupied:
        print("    !! REFLOW — coords land on text in the blank render:")
        for o in occupied: print("       ", o)
        sys.exit(1)
    print("    reflow gate: clean (all %d coords land on empty space)" %
          sum(len(v) for v in coords.values()))

    print("CANADA:")
    render("canada.pdf", "canada_full.pdf")
    drop_page1("canada_full.pdf", "canada_blank.pdf")
    print("    canada_blank.pdf pages:", len(pikepdf.open("canada_blank.pdf").pages))
    print("DONE — ship australia_blank.pdf + canada_blank.pdf; map = aus_coords.json")


if __name__ == "__main__":
    main()
