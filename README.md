# DiploClear

**Clearance at the speed of the mission.**

Enter a flight once. Get every country's diplomatic clearance form — correct, formatted,
ready to send.

Built by **Team GREENLIGHT (AND1)**, 57th GKSCSC — joint Technopreneurial Mindset (TM) +
Certified Professional Innovator (CPI) capstone. Sponsor: **Hd Plans Hub, AOCG**.

---

## What it does

A planner filing a diplomatic clearance request today re-types the same mission into 21
different host-nation forms — each with its own layout, language, field names and file
format. DiploClear captures the mission **once** and fills all 21 in their native formats.

| Family | Count | Output |
|---|---|---|
| Word (DCR · EU-DIC · bespoke) | 15 | `.docx` |
| Excel (France) | 1 | `.xlsx` |
| PDF overlay (New Zealand, Jordan, Bahrain, Australia) | 4 | `.pdf` |
| Flat blank for hand completion (Canada) | 1 | `.pdf` |

**21 / 21 generating** — verified end to end by `tools/xfa_flatten/validate_all21.js`.

### Hard rule: format-in = format-out
The host gives a `.docx`, they get a `.docx` back. The master template **is** the host
nation's own file, filled in place — never converted, never re-typeset. A form that arrives
looking unfamiliar is a form that gets rejected.

## Running it

No install, no build, no server, no network:

```
open index.html
```

Single file, runs from `file://`. Everything — the templating engines and all 21 templates —
is bundled locally. **Nothing leaves the machine**, which is the point: this had to work in a
place that will not buy or host cloud software.

The passcode screen is presentational; click **Open console**. Deep links: `#console`,
`#demo`, `#settings`, `#verify`, `?dark`.

## The trust layer

Speed is the easy half. A clearance form that is *fast and wrong* is worse than a slow one,
so the app is built to be checkable rather than merely quick:

- **Freshness** — every template is stamped with when it was last verified against the host
  nation's current form, and by whom. The indicator degrades on its own: green under 6
  months, amber under 18, red beyond. Stale beats silently-wrong.
- **Verify & sign** — each generated form opens an input-to-output table showing exactly
  which mission value filled which field, then takes a **named** human sign-off. The form is
  marked *not reviewed* until a person puts their name to it.
- **Provenance** — every output carries its template's origin and verification date.

## Repository layout

```
index.html                  the entire application
lib/                        docxtemplater · pizzip · pdf-lib · templates_data.js (all 21, base64)
assets/                     hero imagery
tools/build_templates.py    single source of truth — rebuilds every template
tools/flatten_nz.py         paints out + rasterises the NZ sample data
tools/xfa_flatten/          Adobe XFA → flat PDF pipeline (Australia, Canada)
config.json                 fields, fleet, airfields, purposes, POC, countries
docs/Field Map.xlsx         42 canonical "enter-once" fields × 21 forms
```

### The XFA problem (Australia · Canada)
Australia and Canada publish their forms as Adobe LiveCycle **XFA** PDFs, which render only
in Adobe Reader — every other viewer shows *"Please wait…"*, and current Adobe Reader itself
fails them with *"STOP! Javascript is not enabled."* We flatten them offline with **pdf.js**
driven by headless Chrome: no Adobe, no network. Australia then fills by coordinate overlay;
Canada is a dynamic form nothing can auto-fill offline, so it ships as a clean flat blank.
See `tools/xfa_flatten/README.md`.

## Data handling

The vendor master forms obtained for templating turned out to be **real filed missions**, not
blanks. A **2026-08-13 audit** found they carried a named officer's email and mobile number
and another sortie's dangerous-goods manifest. `patch_tpl.py` now whitelists: every data leaf
is cleared unless it is one of our own markers or static scaffolding true of every RSAF
request. Anything a future vendor revision introduces is cleared **by default** rather than
silently shipped, and a build gate fails if a known-sensitive token survives.

**The unscrubbed masters are excluded from this repository** (see `.gitignore`). Only scrubbed
derivatives ship, bundled into `lib/templates_data.js`.

> This repository is **private**. The bundled templates carry RSAF Plans Hub contact details
> (unit address, office lines, point of contact) as they legitimately appear on a filed
> request. Do not publish it, or a GitHub Pages site from it, without clearing that first.

## Status

Working prototype, sponsor-facing. Outstanding items are access-dependent rather than
technical: a measured before/after time-saved figure from a real Plans Hub mission,
correctness diffing of the highest-frequency countries against real filed forms, and the
handover SOP naming the billet that owns the templates once the team graduates.
