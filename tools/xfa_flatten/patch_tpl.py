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
import re, sys
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
    xfa[idx["datasets"]].write(out)
    pdf.save(dst); pdf.close()

    print("\n  MARKED (baked value -> overlay marker):")
    for tag, v, m in marked: print("    <%s> %r -> %s" % (tag, v, m))
    print("\n  KEPT (%d):" % len(kept))
    for tag, v in kept: print("    <%-22s> %r" % (tag, v[:52]))
    print("\n  CLEARED (%d):" % len(cleared))
    for tag, v in cleared: print("    <%-22s> %r" % (tag, v))

    # hard gate: nothing sensitive may survive
    leaked = []
    txt = out.decode("utf-8", "replace")
    for bad in ["REDACTED_NAME", "REDACTED_NAME", "REDACTED_PHONE", "Marine Marker", "Flares",
                "Cartridge", "Cart Power", "ROCKHAMPTON", "KIKEM", "ZNOV25", "NEO",
                "LUDPU", "TINDAL", "730, 731"]:
        if bad in txt: leaked.append(bad)
    if leaked:
        print("\n  !! SCRUB FAILED, residue: %s" % leaked); sys.exit(1)
    print("\n  scrub gate: clean (no PII / DG / sample routing survived)")
    print("  wrote %s" % dst)


if __name__ == "__main__":
    main()
