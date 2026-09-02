Dataset: `train_data.csv`, 10183 rows in the high-risk tail (risk >= -6).

Best hard-body radius: **9.0 m**, the single radius that best reproduces the whole tail.

Residual (log10 of ours over ESA's): median **+0.224** (a factor of 1.68 high), quartiles -0.20 to +0.86, 43% within a factor of two and 80% within a factor of ten.

| Risk bin | n | median | p05 | p95 | within x2 |
| --- | ---: | ---: | ---: | ---: | ---: |
| [-6, -5) | 6801 | +0.39 | -0.87 | +1.59 | 37% |
| [-5, -4) | 2666 | +0.22 | -0.44 | +1.55 | 53% |
| [-4, -3) | 664 | -0.17 | -0.45 | +0.93 | 58% |
| [-3, -2) | 44 | -0.12 | -0.57 | +0.77 | 36% |
| [-2, 0) | 8 | -0.52 | -0.61 | -0.23 | 12% |

Maximum probability and its scaling, against ESA's own columns:

- 2000 rows compared; the residual of the maximum has median +0.218 and 43% within a factor of two.
- Our scale factor over ESA's `max_risk_scaling`: median 0.9999 read as a factor on the covariance, 0.8249 read as a factor on the standard deviation. The first is one, so ESA's scaling is a factor on the covariance, as ours is.
