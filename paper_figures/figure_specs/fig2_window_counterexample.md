# Figure 2: Same marginal weather availability, different contiguous windows

## Scientific Question
Why does the count of individually calm slots fail to identify the number of
usable continuous starts?

## One-Sentence Takeaway
Fragmentation of high-wind slots destroys every three-slot start even when the
two paths contain the same six individually calm slots.

## Figure Archetype
constructed result synthesis

## Layout
Two aligned timeline rows, with the admissible start positions shown below each
path and the threshold legend at right.

## Panels
| Panel | Job | Elements | Evidence boundary | Visual priority |
|---|---|---|---|---|
| A | contiguous path | 8-slot sequence, calm/high-wind slots, four overlapping valid starts | constructed enumeration | primary |
| B | fragmented path | 8-slot sequence, calm/high-wind slots, zero valid starts | constructed enumeration | primary |

## Visual Semantics
- Teal: observed slot at or below start threshold (8 m/s).
- Coral: 25 m/s violation of continuation threshold.
- Dark outline: candidate start whose full 3-slot state-dependent window is valid.
- Gray: candidate start rejected by at least one continuation violation.

## Evidence Boundary
All values are transparent constructed paths used in `core.py` tests; no field
weather performance is encoded.

## Caption First Sentence
Constructed counterexample showing that equal counts of individually calm slots
do not imply equal counts of executable three-slot windows.

## Implementation
Matplotlib was selected for the aligned quantitative timeline and direct export
to SVG/PDF/PNG. The source CSV and plotting script are retained beside the
figure.
