# Figure 1: Information boundary of the rolling weather-window evaluator

## Scientific Question
Which information is allowed to influence a dispatch decision, and where is the
realised weather path introduced?

## One-Sentence Takeaway
The controller commits an action using only the forecast snapshot available at
the decision time; the evaluator reads the realised path afterward and reports
completion, breach, missingness, or cutoff status.

## Figure Archetype
framework / evidence-chain

## Layout
Compact three-column layout: available inputs, committed start selection, and
the independent evaluator. English labels remain legible at manuscript width.

## Panels
| Panel | Job | Elements | Evidence boundary | Visual priority |
|---|---|---|---|---|
| A | observable inputs | available forecast, completed/active state, precedence and resources | implemented and unit-tested | primary |
| B | dispatch | blind baseline and window-probability selector | implemented; no truth input | primary |
| C | evaluation | realised observation, state transition, unresolved/cutoff accounting | implemented executor; empirical calibration pending | primary |

## Visual Semantics
- Blue: information available before the decision.
- Amber: irreversible controller action.
- Purple: realised path held by the independent evaluator.
- Gray: accounting and evidence boundary.
- Dashed clusters distinguish decision inputs and the independent evaluator;
  the footer specifies that realised weather is read only after the action log.

## Arrows And Relations
| From | To | Meaning | Evidence status |
|---|---|---|---|
| available forecast + project state | controller | permitted decision input | implemented |
| controller | action log | irrevocable dispatch record | implemented |
| realised observation | evaluator | post-decision truth input | implemented |
| action log + realised observation | status | breach/missing/censored/complete classification | implemented |

## Caption First Sentence
Information contract used by the event-level replay engine; realised interval
weather is held by the independent evaluator until current starts are recorded.

## Risks
- Unsupported schematic: forecast calibration and operational latency are not claimed.
- Clutter: keep the evaluator branch visually separate from the controller.
- Likely reviewer misunderstanding: this is a software/evidence contract, not a safety-control certification.

## Implementation
Graphviz DOT was selected because the figure is a typed flow with a hard
information boundary; SVG/PDF are the masters and PNG is a preview.
