# Decisions needed on the open questions

This tracks what's still needed from Luca on [`docs/open-questions.md`](docs/open-questions.md),
following the groups laid out in that page's ["Grouping and priority"](docs/open-questions.md#grouping-and-priority)
section. Group 1 there is already resolved in the spec text; everything below is open.

## 1. Validator story (group 2 — the real risk)

These are cases where every MUST can hold and the pixels/joins are still silently wrong.
Decide: commit to a documented validator layer (formalizing what
`scripts/check_sp_ops_zarr.py` already does as advisories), and which items become
spec-level MUST language vs. stay validator-only advisories?

Ranked by blast radius: **Q35** (raw tile footprint vs. per-image stage readout, up to
41 px), **Q19** (`library` has no unique key; `n:1` edge is really `n:5` for controls),
**Q46** (labels vs. source image physical extent, silently off by 2x), **Q30 / Q50**
(stacked-but-unregistered image indistinguishable from registered; `sp-ops:registration`
has no home in `raw`), **Q49** (`layout` vs. tile-to-well transforms can disagree by 82 px).
Lower blast radius, same family: Q37, Q32, Q27, Q22, Q51, Q15, Q5.

- [ ] Decide yes/no on the validator layer.
- [ ] For each item above, decide: promote to MUST language in the spec, or leave as a
      validator advisory.

## 2. Provenance: OME/Bio-Formats reuse vs. new sp-ops keys

**Q6** (raw instrument provenance), **Q10** (derived-element provenance), and the
layout-provenance half of **Q2** (measured vs. stage-readout layout) currently propose new
sp-ops-private keys or tables. The alternative: reuse the OME data model
(`Instrument`/`Objective`/`Detector`, per-image/per-plane metadata) and extend it only where
genuinely missing, since RFC-8 already invites this.

- [ ] Confirm this direction before Q6/Q10/Q2 get rewritten — it changes the shape of the
      fix compared to what's currently written in those entries.

## 3. Blank/background tile capability (carried over from the merged-spec PR, no Q id)

Converters currently drop blank/background fields of view used for illumination correction
and background subtraction — no home for them.

- [ ] Pick one: (a) a `kind` field on `sp-ops:tile` (`field` vs `background`), or (b) a
      sibling `calibration` collection.

## 4. Join/table model additions (group 4, additive — decide yes/no on each)

- [ ] **Q33**: let `on` take a list of column pairs (peak-to-read join needs `y, x, sigma`).
- [ ] **Q28**: add a `coverage` field to an edge, separate from `cardinality`.
- [ ] **Q11 / Q48**: require plain `label`/parent-label columns instead of parsing an id out
      of a string, or membership riding on a numbering convention.
- [ ] **Q12**: add a SHOULD for compartment membership recovered via spatial join at
      `status: suggested`.
- [ ] **Q23 / Q26 / Q34**: a read-length field, an edge type from feature definitions to the
      tables they describe, and naming the "fusion" merged-table encoding that
      `features.md` doesn't currently name.

## 5. Editorial batch (group 5) — go-ahead to just apply these?

Q38, Q1 / Q9, Q39, Q45 / Q42, Q32 (delete the false sentence), and smaller fixes: Q41, Q44,
Q47, Q24, Q21, Q20, Q40, Q36.

- [ ] Confirm I should apply these directly (default: yes), or flag any to review
      individually first.

## 6. Documentation-only notes (group 6) — confirm no spec change needed

Q3, Q18, Q16, Q25 — each needs at most one documentation sentence, not a spec change.

- [ ] Confirm (default: yes).

## 7. Housekeeping

`open-questions.md`'s own stated convention: "an entry that is resolved moves into the page
it fixes." Q7, Q8, Q14 are now resolved in the spec text but still sit in
`open-questions.md` as historical entries (including inline `<- Q8` / `<- Q14` / `<- Q7`
annotations in the dataset store trees).

- [ ] Decide: remove/migrate those three entries out of `open-questions.md` now, or leave
      them as a record until a broader resolved-entries cleanup.
