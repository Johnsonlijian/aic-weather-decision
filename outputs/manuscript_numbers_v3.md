## Table 1 - raw deterministic rule as a detector (TEST, 45 stations)
| Limit | claim rate | true rate | false alarms | missed | positives |
|---:|---:|---:|---:|---:|---:|
| 9 | 40.8% | 47.1% | 15.5% | 30.9% | 22,305 |
| 12 | 18.8% | 20.1% | 8.0% | 38.3% | 9,518 |
| 13 | 13.3% | 14.5% | 5.8% | 42.7% | 6,858 |
| 16.5 | 3.8% | 5.1% | 1.6% | 53.7% | 2,406 |
| 20 | 1.2% | 1.1% | 0.7% | 53.8% | 509 |

## Calibration skill (binned model, TEST)
| Limit | vs climatology | vs raw threshold | vs logistic gap |
|---:|---:|---:|---:|
| 9 | +0.407 | +0.348 | +0.007 |
| 12 | +0.412 | +0.316 | +0.002 |
| 13 | +0.407 | +0.321 | +0.001 |
| 16.5 | +0.374 | +0.255 | -0.003 |
| 20 | +0.271 | +0.366 | -0.015 |

## Cost-loss value (TEST): calibrated vs tuned raw vs documented limit
| Limit | calibrated peak | tuned-raw peak | fixed-limit peak | max disagreements |
|---:|---:|---:|---:|---:|
| 9 | +0.540 @ 0.488 | +0.540 @ 0.488 | +0.525 | 2608/47322 |
| 12 | +0.616 @ 0.190 | +0.618 @ 0.190 | +0.530 | 4071/47322 |
| 13 | +0.649 @ 0.150 | +0.649 @ 0.150 | +0.513 | 3644/47322 |
| 16.5 | +0.721 @ 0.052 | +0.721 @ 0.052 | +0.447 | 2199/47322 |
| 20 | +0.835 @ 0.010 | +0.791 @ 0.013 | +0.455 | 3656/47322 |

## Spatial transfer and lead (12 m/s)
- pooled held-out skill vs climatology: +0.399
- leave-one-station-out transfer median: +0.372 (min -1.703, negative on 2 stations)
- site-specific median: +0.396
- documented-limit raw threshold median: +0.121
- by lead: {'12': {'n': 23662, 'positives': 4604, 'brier': 0.09622336792068628, 'skill_vs_climatology': 0.3859965433652349, 'skill_vs_raw': 0.329750564692588}, '18': {'n': 23660, 'positives': 4914, 'brier': 0.09675488049994928, 'skill_vs_climatology': 0.41202535762346537, 'skill_vs_raw': 0.3010013824034199}}

## Event frequency (TEST)
- gust > 12 m/s: 20.1%
