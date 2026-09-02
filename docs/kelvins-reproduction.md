Dataset: `train_data.csv`, 10183 rows in the high-risk tail (risk >= -6).

## The hard-body radius ESA used

It is in the data. The combined radius is half of each object's `span`, added: `(t_span + c_span) / 2`, and with it the reconstruction stops being an approximation: over the tail the median residual is **-0.0003** in log10, which is 0.07% in the probability, with quartiles -0.012 to +0.008. 87% of rows agree within a factor of two and 96% within a factor of ten. Nothing was fitted to get this: the multiplier on the span is one.

That settles the question the Phase 2 review left open. The probability code agrees with ESA's to a fraction of a percent for most conjunctions; what disagreement remains is not in the integration but in the rows described below.

**Restricted to the tail that matters** (risk above 1e-5, the yellow-flag threshold): 3382 rows, median residual **+0.0005**, 92% within a factor of two and 98% within a factor of ten, quartiles -0.003 to +0.005.

**The direction of the bias.** There is essentially none in the median: over the tail that matters the reconstruction is high by 0.11%, which is numerical noise rather than a bias. The residual is not symmetric, though. Its 5th percentile is -0.66 and its 95th is +0.13: the long tail is on the **low** side, so where this reconstruction disagrees it usually reads the encounter as *safer* than ESA did, by up to a factor of ten. That is the dangerous direction to be wrong in, and it is why the whole distribution is reported rather than its median. The rows in that tail are disproportionately payloads (13 % of them against 4 % of the tail), which is where the chaser-frame approximation below bites.

| Risk bin | n | median | p05 | p95 | within x2 |
| --- | ---: | ---: | ---: | ---: | ---: |
| [-6, -5) | 6801 | -0.0011 | -1.02 | +0.25 | 85% |
| [-5, -4) | 2666 | +0.0003 | -0.42 | +0.14 | 91% |
| [-4, -3) | 664 | +0.0008 | -0.81 | +0.06 | 94% |
| [-3, -2) | 44 | +0.0000 | -2.25 | +0.13 | 82% |
| [-2, 0) | 8 | -2.0063 | -2.26 | +0.00 | 38% |

The eight rows above 1e-2 are the exception: five of them come out two orders of magnitude low. At that risk the miss is comparable to the hard-body radius and the two-dimensional method is at the edge of its assumptions, so the disagreement is expected there. It is stated rather than tuned away.

## The residual against the risk

![Residual against ESA's risk](kelvins-reproduction.svg)

Density of the residual over the tail with the span radius: the median solid and the 5th and 95th percentiles dashed, per risk decade, with the band marking agreement within a factor of two. The grey line is the median of the older reconstruction, which fitted one radius for every conjunction. Two things to read from it: the median sits on zero once the radius is right, and the spread is one-sided, reaching down towards safer and barely up towards riskier.

## One radius for everything, as a fallback

Kept because a catalogue without a size column still needs a number, and because it is the honest picture of what a screening tool can do when it does not know how big the objects are.

Best single hard-body radius: **9.0 m**, the radius with the smallest median absolute residual over the tail.

Residual: median **+0.224** (a factor of 1.68 high), quartiles -0.20 to +0.86, 43% within a factor of two and 80% within a factor of ten.

Over the tail that matters (risk above 1e-5): 3382 rows, median **+0.210**, a factor of 1.62 high, 54% within a factor of two. The bias has an obvious cause: with one radius for every object the reconstruction over-calls the risk of small debris and under-calls the risk of large payloads, because it gives them the same size.

| Risk bin | n | median | p05 | p95 | within x2 |
| --- | ---: | ---: | ---: | ---: | ---: |
| [-6, -5) | 6801 | +0.39 | -0.87 | +1.59 | 37% |
| [-5, -4) | 2666 | +0.22 | -0.44 | +1.55 | 53% |
| [-4, -3) | 664 | -0.17 | -0.45 | +0.93 | 58% |
| [-3, -2) | 44 | -0.12 | -0.57 | +0.77 | 36% |
| [-2, 0) | 8 | -0.52 | -0.61 | -0.23 | 12% |

## The two size columns, scored against each other

The dataset carries two size columns per object: `*_span`, the largest dimension in metres, and `*_rcs_estimate`, the radar cross-section in square metres. Each is given one free multiplier, fitted the way the single radius is, so the comparison is of the shape of the per-object radius rather than of the units.

| Proxy | Rows | Median radius | Best multiplier | Median abs. residual | Within x2 | One radius, same rows |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `span` | 10183 | 7.00 m | 1x | 0.010 | 87% | 9.0 m: 0.431, 43% |
| `rcs` | 6758 | 1.11 m | 4.75x | 0.303 | 50% | 9.0 m: 0.447, 40% |

`span` wins at a multiplier of exactly one, which is what identifies it as ESA's own convention rather than a lucky fit. `rcs` needs a multiplier of nearly five and still does no better than a single radius: the radar cross-section is the area of the echo rather than of the object, it understates anything much larger than the radar wavelength, and it is missing on a third of the chaser rows. **This bears directly on driftwatch's own screening**: the secondary radii in `risk/scenario.py` fall back to `sqrt(RCS / pi)` for payloads, rocket bodies and debris, and this says that fallback is biased small and that a published dimension should be preferred wherever there is one.

## Maximum probability and its scaling, against ESA's own columns

- 2000 rows compared; the residual of the maximum has median +0.218 and 43% within a factor of two.
- Our scale factor over ESA's `max_risk_scaling`: median 0.9999 read as a factor on the covariance, 0.8249 read as a factor on the standard deviation. The first is one, so ESA's scaling is a factor on the covariance, as ours is.

Both are computed at the fitted single radius, so they carry that reconstruction's bias.

## What is still approximated

- The chaser's RTN frame is built from the target's and the relative velocity, with the target's velocity taken as circular. The data do not carry the target's velocity vector.
- Both covariances are used as position-only 3x3 matrices; the velocity terms play no part in the two-dimensional method.
- Rows at the risk floor of -30 are excluded from every figure here.
