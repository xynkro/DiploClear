# DiploClear

**Clearance at the speed of the mission.**

Enter a flight once. Get every country's diplomatic clearance form — correct, formatted,
ready to send.

Built by **Team GREENLIGHT (AND1)**, 57th GKSCSC — joint Technopreneurial Mindset (TM) +
Certified Professional Innovator (CPI) capstone.

**▶ Live demo: https://xynkro.github.io/diploclear-demo/**

---

## The problem

A planner filing a diplomatic clearance request re-types the same mission into 21 different
host-nation forms — each with its own layout, language, field names and file format. The
work is duplicated, and every re-keying is a chance to introduce an error into a document a
foreign government will act on.

DiploClear captures the mission **once** and fills all 21 in their native formats.

| Family | Count | Output |
|---|---|---|
| Word (DCR · EU-DIC · bespoke) | 15 | `.docx` |
| Excel (France) | 1 | `.xlsx` |
| PDF overlay (New Zealand, Jordan, Bahrain, Australia) | 4 | `.pdf` |
| Flat blank for hand completion (Canada) | 1 | `.pdf` |

### Format-in = format-out
The host gives a `.docx`, they get a `.docx` back. The template **is** the host nation's own
file, filled in place — never converted, never re-typeset. A form that arrives looking
unfamiliar is a form that gets rejected.

### Trust, not just speed
A clearance form that is fast and wrong is worse than a slow one, so the app is built to be
checkable:

- **Freshness** — each template carries when it was last verified against the host nation's
  current form, and by whom. The indicator degrades on its own: green under 6 months, amber
  under 18, red beyond. Stale beats silently-wrong.
- **Verify & sign** — every generated form opens an input-to-output table showing which
  mission value filled which field, then takes a **named** human sign-off.

## Running it

Nothing to install, no server, no network:

```
open index.html
```

Everything — the templating engines and all 21 templates — is bundled locally, so it also
runs straight from `file://`. That was a design constraint, not a flourish: it had to work
somewhere that will not host or buy cloud software.

The passcode screen is presentational; click **Open console**. Deep links: `#console`,
`#demo`, `#settings`, `#verify`, `?dark`.

## How it's built

```
index.html   the entire application
lib/         docxtemplater · pizzip · pdf-lib · templates_data.js (all 21 templates, base64)
assets/      hero imagery
```

**The XFA problem.** Australia and Canada publish their forms as Adobe LiveCycle **XFA**
PDFs, which render only in Adobe Reader — every other viewer shows *"Please wait…"*, and
current Adobe Reader itself fails them with *"STOP! Javascript is not enabled."* They are
flattened offline with **pdf.js** driven by headless Chrome: no Adobe, no network. Australia
then fills by coordinate overlay; Canada is a dynamic form nothing can auto-fill offline, so
it ships as a clean flat blank.

**Templates are sanitised.** The master forms are reduced to blank templates carrying only
placeholders and the scaffolding common to every request. A build gate fails if sample
mission data survives into a shipped template.

## Status

Working prototype. Remaining work is access-dependent rather than technical: a measured
before/after time-saved figure from a real mission, correctness diffing of the
highest-frequency countries against real filed forms, and a handover SOP naming the billet
that owns the templates once the team graduates.
