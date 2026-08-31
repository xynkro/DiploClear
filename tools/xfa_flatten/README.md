# XFA → flat-PDF pipeline (Australia AF179, Canada EXT2095)

Australia & Canada distribute their diplomatic-clearance forms as Adobe **LiveCycle XFA**
PDFs. These render **only** in Adobe Reader — every other viewer (Preview, Chrome, Quick
Look, poppler, mutool, pdf-lib) shows *"Please wait…"*, and current Adobe Reader itself
(2024/25) now fails them with *"STOP! Javascript is not enabled"* even with JS enabled.

We flatten them **offline** to normal multi-page PDFs using **pdf.js** (the same XFA engine
Firefox uses) driven by **headless Chrome via Puppeteer** — no Adobe, no network.

## Inputs (XFA masters)
- `../../Master Forms/Australia/australia.pdf`
- `../../Master Forms/Canada/canada.pdf`

## Steps (run in this dir, with the two masters copied in as `australia.pdf` / `canada.pdf`)
1. `python3 patch_tpl.py` — **Australia only**: scrubs the datasets (see "The scrub" below) and in the XFA `<template>` flips subform
   `presence`: `FormPage → visible` (reveal the whole script-gated body), and
   `subJavascriptCheck` + `subAcrobatCheck` + `subMetaData → hidden` (drop the two STOP
   banners, the dev "Designer note", and the debug status row). Writes `australia_patched.pdf`.
2. `python3 build_artifacts.py` — renders via pdf.js + Chrome (`capture.js` + `render.html`):
   - `australia_markers.pdf` (markers visible) → `pdftotext -bbox` → **`aus_coords.json`**
   - `australia_blank.pdf` (11 markers cleared) → the **shipped** template; a gate asserts
     clearing them caused no reflow, which is what makes the pass-1 coords valid
   - `canada_full.pdf` → drop page 1 (JS-warning splash) → `canada_blank.pdf`
   Then copy `australia_blank.pdf`→`Master Forms/Australia/australia_flat.pdf` and
   `canada_blank.pdf`→`Master Forms/Canada/canada_flat.pdf`.
3. `python3 tools/build_templates.py` — bundles the flat blanks into `lib/templates_data.js`.

## Runtime (index.html)
- **Australia**: `PDFMAP.australia` overlays `buildData()` values with pdf-lib onto the
  5-page `australia_flat.pdf` at `aus_coords.json` positions — 9 fields: purpose / callsign /
  type / reg / captain / crew / pax / dep / dest. Values shrink to `maxw` rather than overrun.
- **Canada**: `downloadFlatBlank` ships `canada_flat.pdf` — 2-page flat blank. It has NO form
  fields (no `/AcroForm`), so it is printed and completed by hand, not typed into.

## Deps
Node + `npm i pdfjs-dist@4.6.82 puppeteer pdf-lib` (Chrome = system
`/Applications/Google Chrome.app`); Python `pikepdf`; poppler `pdftotext`.

## The scrub (why this matters)
The vendor masters are **real filed missions**, not blank forms. Before the 2026-08-13 audit
the Australia template shipped, on every generated request:

* a named officer's given name, surname, **email and mobile number**;
* another sortie's **dangerous-goods manifest** (marine markers, aerial flares, cartridge
  impulse devices, with UN numbers and net explosive quantities);
* that mission's aerodromes, ATS routes and Zulu times.

`patch_tpl.py` therefore **whitelists**: every datasets leaf is cleared unless it is one of
our `[[markers]]`, static scaffolding true of every RSAF request (RSAF / SINGAPORE /
OFFICIAL / form number), or a structural control value. Anything a future vendor revision
adds is cleared by default rather than silently leaking. A gate fails the build if any
known-sensitive token survives.

New Zealand has the same problem and is handled by `tools/flatten_nz.py`, because its
master is a flat PDF with no XFA to scrub. `PDFMAP.nz.blanks` in `index.html` lists every
sample region — POC (a named officer + phone), callsign, alternate regs, the NZ itinerary
with dates, the overflight routes, the operator answers and the sample captain's name — and
`flatten_nz.py` reads that same list, paints it out and **rasterises page 1**, so the words
are gone from the text layer rather than merely covered. Pages 2-4 (MFAT's instructions,
no mission data) stay as vector text. `build_pdfs()` calls it, so a rebuild can't
reintroduce the leak, and a gate fails the build if any sample word is still extractable.

## Known limitations
1. **Page 1 of the NZ form is an image**, so its text isn't selectable or searchable (200 dpi,
   and the file is *smaller* than before: 718 KB vs 1418 KB). Pages 2-4 remain text. Australia
   needs no such treatment — its template is rendered from scrubbed data, so the sample values
   were never in the file. Sourcing genuinely blank masters from each host nation remains the
   real fix; the pipeline is a mitigation for masters that arrive pre-filled.
2. **Only nine fields are personalised** on Australia (purpose, callsign, type, reg, captain,
   crew, pax, dep, dest). Exact Zulu times, airspace entry/exit waypoints, alternate regs and
   the multi-leg itinerary ship **blank for the planner** — DiploClear captures a single leg
   and holds no ATS routing, so filling them would mean inventing data. To personalise more:
   add a marker in `patch_tpl.py`, rebuild, add a row to `PDFMAP.australia`.

## Verifying
`node validate_all21.js` generates all 21 forms from the bundled base64 using the app's own
libraries and the routing maps parsed out of `index.html`, and reports a size per country.
Needs `@xmldom/xmldom` (docxtemplater wants a DOM). Browser-side loops time out while the
preview pane is hidden, so use this harness rather than driving the page.
