#!/usr/bin/env python3
"""Australia AF179 XFA prep.

TWO jobs:
 1. template: flip subform presence so the script-gated form body renders without Adobe
    (FormPage->visible) and the STOP banners + dev metadata don't (subJavascriptCheck /
    subAcrobatCheck / subMetaData -> hidden).
 2. datasets: SCRUB. The vendor master is a real filed mission, so it ships another
    sortie's data — a named officer's name/email/phone, a dangerous-goods manifest
    (marine markers, aerial flares, cartridge impulse devices), ATS routes, aerodromes
    and Zulu times. We WHITELIST: every leaf value is cleared unless it is (a) one of our
    [[markers]], or (b) genuine static form scaffolding true of every RSAF request, or
    (c) a structural/control value. Anything new the vendor adds in a future revision is
    therefore cleared by default rather than silently leaking.
"""
import os, re, sys
import pikepdf
from lxml import etree

MARKER_RE = re.compile(r"\[\[\w+\]\]")

# (c) structural / control values — keep as-is
KEEP_TAGS_STRUCT = {
    "chkAmended", "chkAirOperator", "grpType", "grpRequestType",
    "fldCapLeg", "fldLEG", "fldCount", "ddlCrewDetailsType", "ddlPAXType",
    "fldSigningStatus", "fldIsSigned", "fldFormValidationPassed",
}
# (b) static scaffolding true for every RSAF request
KEEP_EXACT = {
    ("fldOpName", "RSAF"),
    ("fldOpNationality", "SINGAPORE"),
    ("ddlRequestingCountry", "Singapore"),
    ("fldOperator", "REPUBLIC OF SINGAPORE AIR FORCE"),
    ("fldClassificationHeader", "OFFICIAL"),
    ("fldClassificationFooter", "OFFICIAL"),
    ("ffFormNumber", "AF179"),
    ("ffVersionInformation", "Revised 07 Mar 24"),
    ("fflGroundHandling", "Ground Handling – Civilian Airfield"),
    ("fldETA", "ORIGINATE"), ("fldETD", "TERMINATE"),   # column labels, not times
    ("fldVIPDetails", "NIL"), ("fldWeapon", "NIL"), ("fldMed", "NIL"),
    ("fldGHAirField", "NIL"), ("fldGHAirFieldAgent", "NIL"),
}
# turn these baked sample values into overlay markers
TO_MARKER = {("fldCrewDetails", "15"): "crew_n", ("fldPAXNo", "00"): "pax"}

# AF179 fields DiploClear fills, as (tag, which occurrence) -> marker. Written only into a
# field the scrub emptied, so a column label such as <fldETA>ORIGINATE</fldETA> that the
# whitelist deliberately kept is never overwritten. These make the LIVE XFA form fillable:
# Australia will not take the flattened render, so the values have to go into the form's own
# datasets packet and the form has to stay a form.
SET_MARKERS = [
    ("fldPurpose", 0, "purpose"),      ("fldCallSign", 0, "callsign"),
    ("fldCapTitle", 0, "cap_title"),   ("fldCapLastName", 0, "cap_last"),
    ("fldCapGivenName", 0, "cap_given"),
    ("fldACRego", 0, "reg"),           ("fldACType", 0, "type"),
    ("fldACCallsign", 0, "callsign"),  ("fldACAltRego", 0, "alt_rego"),
    ("fldLPD", 0, "dep"),              ("fldLPETD", 0, "etd_full"),
    ("fldAAEP", 0, "fir_entry"),       ("fldAAETA", 0, "fir_entry_t"),
    ("fldPlace", 0, "p1_pt"), ("fldETA", 0, "p1_eta"), ("fldETD", 0, "p1_etd"),
    ("fldPlace", 1, "p2_pt"), ("fldETA", 1, "p2_eta"), ("fldETD", 1, "p2_etd"),
    ("fldPlace", 2, "p3_pt"), ("fldETA", 2, "p3_eta"), ("fldETD", 2, "p3_etd"),
]


def apply_markers(root):
    """Write [[markers]] into the AF179 fields DiploClear fills. Runs AFTER the scrub and
    only into fields the scrub emptied, so nothing the whitelist kept is clobbered."""
    want = {}
    for tag, occ, marker in SET_MARKERS: want.setdefault(tag, {})[occ] = marker
    seen, placed, skipped = {}, [], []
    for el, tag in leaf_elements(root):
        if tag not in want: continue
        i = seen.get(tag, 0); seen[tag] = i + 1
        marker = want[tag].get(i)
        if marker is None: continue
        if value_of(el).strip():
            skipped.append((tag, i, value_of(el)[:24])); continue   # whitelist kept it
        set_value(el, "[[%s]]" % marker); placed.append((tag, i, marker))
    return placed, skipped


def leaf_elements(root):
    """Yield elements whose content is a plain value (incl. xhtml rich text)."""
    for el in root.iter():
        tag = etree.QName(el).localname
        if tag in ("body", "p"):
            continue
        kids = [k for k in el if etree.QName(k).localname not in ("body", "p")]
        if kids:
            continue
        yield el, tag


def value_of(el):
    return "".join(el.itertext()).strip()


def set_value(el, val):
    """Set a leaf's text, preserving an xhtml <body><p> wrapper if present."""
    ps = [d for d in el.iter() if etree.QName(d).localname == "p"]
    if ps:
        for p in ps:
            for c in list(p):
                p.remove(c)
            p.text = val
        return
    for c in list(el):
        el.remove(c)
    el.text = val


def scrub(datasets_bytes):
    root = etree.fromstring(datasets_bytes)
    kept, cleared, marked = [], [], []
    for el, tag in leaf_elements(root):
        val = value_of(el)
        if not val:
            continue
        if MARKER_RE.search(val):
            if val.strip() == MARKER_RE.search(val).group(0):
                set_value(el, val.strip())          # normalise padding
                kept.append((tag, val.strip()))
            else:
                set_value(el, "")                    # marker embedded in sample prose
                cleared.append((tag, val[:48] + " [marker in sample text]"))
            continue
        if (tag, val) in TO_MARKER:
            m = "[[%s]]" % TO_MARKER[(tag, val)]
            set_value(el, m); marked.append((tag, val, m)); continue
        if tag in KEEP_TAGS_STRUCT or (tag, val) in KEEP_EXACT:
            kept.append((tag, val)); continue
        set_value(el, ""); cleared.append((tag, val[:60]))
    placed, skipped = apply_markers(root)
    marked += [(t, "(emptied)", "[[%s]]" % m) for t, _, m in placed]
    for t, i, v in skipped:
        print("  !! marker for <%s>#%d skipped — field still holds %r" % (t, i, v))
    return etree.tostring(root, encoding="utf-8", xml_declaration=False), kept, cleared, marked


def set_presence(xml, name, val):
    pat = re.compile(r'(<subform\b[^>]*?\bname="' + re.escape(name) + r'"[^>]*?>)')
    n = [0]
    def repl(m):
        tag = m.group(1); n[0] += 1
        if 'presence="' in tag:
            return re.sub(r'presence="[^"]*"', 'presence="%s"' % val, tag)
        return tag[:-1] + ' presence="%s">' % val
    return pat.sub(repl, xml), n[0]


def main(src="australia.pdf", dst="australia_patched.pdf"):
    pdf = pikepdf.open(src)
    xfa = pdf.Root.AcroForm.XFA
    idx = {str(xfa[i]): i + 1 for i in range(0, len(xfa), 2)}

    t = bytes(xfa[idx["template"]].read_bytes()).decode("latin1")
    for nm, val in [("FormPage", "visible"), ("subJavascriptCheck", "hidden"),
                    ("subAcrobatCheck", "hidden"), ("subMetaData", "hidden")]:
        t, n = set_presence(t, nm, val)
        print("  tpl %-20s -> %-8s (%d)" % (nm, val, n))
    xfa[idx["template"]].write(t.encode("latin1"))

    out, kept, cleared, marked = scrub(bytes(xfa[idx["datasets"]].read_bytes()))
    # Write the datasets packet UNCOMPRESSED and keep it that way through save(). The runtime
    # injector swaps [[markers]] for the mission with a plain text substitution; if pikepdf
    # recompresses this stream the browser reads deflate bytes as UTF-8, silently destroys the
    # packet, and Adobe gets a form it cannot open.
    xfa[idx["datasets"]].write(out)
    pdf.save(dst, compress_streams=False); pdf.close()

    print("\n  MARKED (baked value -> overlay marker):")
    for tag, v, m in marked: print("    <%s> %r -> %s" % (tag, v, m))
    print("\n  KEPT (%d):" % len(kept))
    for tag, v in kept: print("    <%-22s> %r" % (tag, v[:52]))
    print("\n  CLEARED (%d):" % len(cleared))
    for tag, v in cleared: print("    <%-22s> %r" % (tag, v))

    # hard gate: nothing sensitive may survive
    # The token list lives in leakwords.local.txt, which is gitignored: it is itself a
    # named officer's details and another sortie's DG manifest. Keeping it out of the
    # repo means publishing this pipeline does not publish what it exists to remove.
    words_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "leakwords.local.txt")
    if not os.path.exists(words_file):
        print("\n  !! leakwords.local.txt missing — refusing to pass a scrub that was never checked")
        sys.exit(2)
    with open(words_file, encoding="utf-8") as fh:
        bads = [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]
    if not bads:
        print("\n  !! leakwords.local.txt is empty — refusing to pass an unchecked scrub"); sys.exit(2)
    leaked = []
    txt = out.decode("utf-8", "replace")
    for bad in bads:
        if bad in txt: leaked.append(bad)
    if leaked:
        print("\n  !! SCRUB FAILED, residue: %s" % leaked); sys.exit(1)
    print("\n  scrub gate: clean (no PII / DG / sample routing survived)")
    print("  wrote %s" % dst)


if __name__ == "__main__":
    main()
