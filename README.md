# DiploClear

**Clearance at the speed of the mission.**

Enter a flight once. Get every country's diplomatic clearance form — correct, formatted,
ready to send.

Built by **Team GREENLIGHT (AND1)**, 57th GKSCSC — joint Technopreneurial Mindset (TM) +
Certified Professional Innovator (CPI) capstone. Sponsor: **Hd Plans Hub, AOCG**.

**▶ Live: https://xynkro.github.io/DiploClear/** — opens in any browser, nothing to install.

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

### Itinerary, legs and the clock
Step 1 takes off-blocks in UTC, a ground speed, and a row per point with its leg and ground
time. Times run forward and roll the date themselves, so a sector crossing midnight prints
the next day. A leg is minutes, or nautical miles with the unit; left blank, it is derived
from the great-circle distance where both ends are airfields we hold a position for
(bundled from **SkyVector**, read 2026-10-08 — the app never calls out). A leg with neither
is flagged amber rather than counted as a silent zero.

An **overnight is two clearances**, so the return leg has its own panel — its own date,
off-blocks, captain and crew — and Generate produces both, foldered `OUTBOUND/` and
`INBOUND/` in the archive. Sign-offs are keyed per leg.

Several airframes on one request each get their own commander, and the crew list carries all
of them, because a form naming three tails and one captain is wrong.

### Hard rule: one frozen mission per batch
**Generate** freezes the flight. The strips, the verify table a planner signs, every
filename and all four engines read that freeze, so a strip, its sign-off and the document
it emits are the same mission by construction. Editing the flight afterwards does not
silently re-point a generated batch: a banner says the forms are behind and offers
*Regenerate*, which rebuilds and clears the sign-offs. `validate_all21.js` fails the build
if any engine reads a live input field again. The rule holds **per leg**: each clearance
freezes its own data and carries its own sign-off.

### Australia ships live, not flattened
Australia will not accept a flattened render of the AF179, so we send their own Adobe
LiveCycle form with the mission written into its XFA `datasets` packet. `/XFA`, `/AcroForm`
and `/NeedsRendering` are left intact, which means it opens in Adobe Reader and nowhere else
— every other viewer shows *"Please wait…"*, and that is the form being whole, not broken.
The packet must stay uncompressed for the runtime substitution to be safe; the engine refuses
outright if it is not plain XML.

### Gates
`node tools/xfa_flatten/validate_all21.js` runs seven, each with a positive control so a
blind check cannot pass: 21-of-21 generation, ARCHIVE, FROZEN-MISSION, NO-BAKED-DATES (no
template may carry another mission's dates or times), NO-AUTHOR-METADATA (docProps must name
nobody), AUSTRALIA-LIVE-XFA, AIRFIELD-POSITIONS (distances checked against SkyVector's own
published figures), and REFERENCE-AND-FRESHNESS (no fabricated clearance reference, and
verifications must be recordable).

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
  months, amber under 18, red beyond. Stale beats silently-wrong. A verification is
  **recordable**: the verify panel carries *"I checked it against the host's current form"*,
  which stamps today's date and the signed-in name over the bundled default and keeps it on
  the machine. It refuses if nobody is signed in, because an unattributed verification is
  worth nothing.
- **Clearance reference** — the `DCR` number the host tracks the request by is entered, not
  generated. It was hardcoded to the sample mission's `042-26 (1)`, so every form of every
  mission carried the same reference, and the stamp separately counted one off the list
  position. Left blank the forms read `TBC` and a notice says so. A return leg carries its
  own, because it is a separate request.
- **Verify & sign** — each generated form opens an input-to-output table showing exactly
  which mission value filled which field, then takes a **named** human sign-off. The form is
  marked *not reviewed* until a person puts their name to it.
- **Provenance** — every output carries its template's origin and verification date.
- **Preview** — runs the same engine as *Download* over the same frozen mission and shows
  the bytes that come out. PDFs render in the browser's own viewer. Word and Excel have no
  faithful in-browser renderer, so those show the values written into the host's template
  rather than an approximation of a document a host nation will act on.

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

> This repository is **public** and serves the live site above. The bundled templates carry
> RSAF Plans Hub contact details (unit address, office lines, point of contact) as they
> legitimately appear on a filed request — published deliberately, not by accident.
>
> The Australia scrub's leak-check list is the one thing held back: it names an officer and
> their personal mobile, so it lives in `tools/xfa_flatten/leakwords.local.txt`, gitignored.
> `patch_tpl.py` exits non-zero if it is missing, so a scrub cannot be reported clean
> without having been checked.

## Status

Working prototype, sponsor-facing. Outstanding items are access-dependent rather than
technical: a measured before/after time-saved figure from a real Plans Hub mission,
correctness diffing of the highest-frequency countries against real filed forms, and the
handover SOP naming the billet that owns the templates once the team graduates.
