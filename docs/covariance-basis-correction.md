# Covariance basis correction — 2026-09-08

Covariance is transported from predicted-state RIC into each residual's truth RIC basis before component scoring. Every cell is shown, including unchanged cells; differences are percentage points. Residuals, exclusions and horizons are unchanged. The September secondary tables use a dated amendment; the original frozen files, primary endpoint and audits remain preserved. Full precision sigma medians, counts and fractions are in [the CSV](assets/benchmark-v2-basis-corrections.csv).

| Population | Scope | Group | Window | Lead h | Component | Old → new n | Inside 1σ count | Inside 1σ share | Change pp | Inside 2σ count | Inside 2σ share | Change pp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| reference | by_band | 1000-1400 km | August 2024 held out | 6 | radial | 35 → 35 | 18 → 18 | 51.4% → 51.4% | 0.000000 | 23 → 23 | 65.7% → 65.7% | 0.000000 |
| reference | by_band | 1000-1400 km | August 2024 held out | 6 | in_track | 35 → 35 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_band | 1000-1400 km | August 2024 held out | 6 | cross | 35 → 35 | 5 → 5 | 14.3% → 14.3% | 0.000000 | 10 → 10 | 28.6% → 28.6% | 0.000000 |
| reference | by_band | 1000-1400 km | August 2024 held out | 12 | radial | 35 → 35 | 1 → 1 | 2.9% → 2.9% | 0.000000 | 7 → 7 | 20.0% → 20.0% | 0.000000 |
| reference | by_band | 1000-1400 km | August 2024 held out | 12 | in_track | 35 → 35 | 1 → 1 | 2.9% → 2.9% | 0.000000 | 2 → 2 | 5.7% → 5.7% | 0.000000 |
| reference | by_band | 1000-1400 km | August 2024 held out | 12 | cross | 35 → 35 | 2 → 2 | 5.7% → 5.7% | 0.000000 | 11 → 11 | 31.4% → 31.4% | 0.000000 |
| reference | by_band | 1000-1400 km | August 2024 held out | 24 | radial | 35 → 35 | 6 → 6 | 17.1% → 17.1% | 0.000000 | 32 → 32 | 91.4% → 91.4% | 0.000000 |
| reference | by_band | 1000-1400 km | August 2024 held out | 24 | in_track | 35 → 35 | 1 → 1 | 2.9% → 2.9% | 0.000000 | 3 → 3 | 8.6% → 8.6% | 0.000000 |
| reference | by_band | 1000-1400 km | August 2024 held out | 24 | cross | 35 → 35 | 4 → 4 | 11.4% → 11.4% | 0.000000 | 13 → 13 | 37.1% → 37.1% | 0.000000 |
| reference | by_band | 1000-1400 km | August 2024 held out | 36 | radial | 35 → 35 | 18 → 18 | 51.4% → 51.4% | 0.000000 | 35 → 35 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | August 2024 held out | 36 | in_track | 35 → 35 | 1 → 1 | 2.9% → 2.9% | 0.000000 | 1 → 1 | 2.9% → 2.9% | 0.000000 |
| reference | by_band | 1000-1400 km | August 2024 held out | 36 | cross | 35 → 35 | 10 → 10 | 28.6% → 28.6% | 0.000000 | 17 → 17 | 48.6% → 48.6% | 0.000000 |
| reference | by_band | 1000-1400 km | August 2024 held out | 48 | radial | 35 → 35 | 7 → 7 | 20.0% → 20.0% | 0.000000 | 35 → 35 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | August 2024 held out | 48 | in_track | 35 → 35 | 7 → 7 | 20.0% → 20.0% | 0.000000 | 15 → 15 | 42.9% → 42.9% | 0.000000 |
| reference | by_band | 1000-1400 km | August 2024 held out | 48 | cross | 35 → 35 | 14 → 14 | 40.0% → 40.0% | 0.000000 | 22 → 22 | 62.9% → 62.9% | 0.000000 |
| reference | by_band | 1000-1400 km | August 2024 held out | 72 | radial | 35 → 35 | 27 → 27 | 77.1% → 77.1% | 0.000000 | 35 → 35 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | August 2024 held out | 72 | in_track | 35 → 35 | 10 → 10 | 28.6% → 28.6% | 0.000000 | 16 → 16 | 45.7% → 45.7% | 0.000000 |
| reference | by_band | 1000-1400 km | August 2024 held out | 72 | cross | 35 → 35 | 24 → 24 | 68.6% → 68.6% | 0.000000 | 35 → 35 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | August 2024 held out | 96 | radial | 35 → 35 | 35 → 35 | 100.0% → 100.0% | 0.000000 | 35 → 35 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | August 2024 held out | 96 | in_track | 35 → 35 | 5 → 5 | 14.3% → 14.3% | 0.000000 | 9 → 9 | 25.7% → 25.7% | 0.000000 |
| reference | by_band | 1000-1400 km | August 2024 held out | 96 | cross | 35 → 35 | 18 → 18 | 51.4% → 51.4% | 0.000000 | 35 → 35 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | August 2024 held out | 120 | radial | 35 → 35 | 27 → 27 | 77.1% → 77.1% | 0.000000 | 35 → 35 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | August 2024 held out | 120 | in_track | 35 → 35 | 4 → 4 | 11.4% → 11.4% | 0.000000 | 14 → 14 | 40.0% → 40.0% | 0.000000 |
| reference | by_band | 1000-1400 km | August 2024 held out | 120 | cross | 35 → 35 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 35 → 35 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | August 2024 held out | 144 | radial | 35 → 35 | 35 → 35 | 100.0% → 100.0% | 0.000000 | 35 → 35 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | August 2024 held out | 144 | in_track | 35 → 35 | 12 → 12 | 34.3% → 34.3% | 0.000000 | 18 → 18 | 51.4% → 51.4% | 0.000000 |
| reference | by_band | 1000-1400 km | August 2024 held out | 144 | cross | 35 → 35 | 27 → 27 | 77.1% → 77.1% | 0.000000 | 35 → 35 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | August 2024 held out | 168 | radial | 35 → 35 | 35 → 35 | 100.0% → 100.0% | 0.000000 | 35 → 35 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | August 2024 held out | 168 | in_track | 35 → 35 | 13 → 13 | 37.1% → 37.1% | 0.000000 | 18 → 18 | 51.4% → 51.4% | 0.000000 |
| reference | by_band | 1000-1400 km | August 2024 held out | 168 | cross | 35 → 35 | 26 → 26 | 74.3% → 74.3% | 0.000000 | 35 → 35 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | October 2024 held out | 6 | radial | 32 → 32 | 14 → 14 | 43.8% → 43.8% | 0.000000 | 25 → 25 | 78.1% → 78.1% | 0.000000 |
| reference | by_band | 1000-1400 km | October 2024 held out | 6 | in_track | 32 → 32 | 16 → 16 | 50.0% → 50.0% | 0.000000 | 17 → 17 | 53.1% → 53.1% | 0.000000 |
| reference | by_band | 1000-1400 km | October 2024 held out | 6 | cross | 32 → 32 | 8 → 8 | 25.0% → 25.0% | 0.000000 | 16 → 16 | 50.0% → 50.0% | 0.000000 |
| reference | by_band | 1000-1400 km | October 2024 held out | 12 | radial | 32 → 32 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 2 → 2 | 6.2% → 6.2% | 0.000000 |
| reference | by_band | 1000-1400 km | October 2024 held out | 12 | in_track | 32 → 32 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 1 → 1 | 3.1% → 3.1% | 0.000000 |
| reference | by_band | 1000-1400 km | October 2024 held out | 12 | cross | 32 → 32 | 7 → 7 | 21.9% → 21.9% | 0.000000 | 17 → 17 | 53.1% → 53.1% | 0.000000 |
| reference | by_band | 1000-1400 km | October 2024 held out | 24 | radial | 32 → 32 | 18 → 18 | 56.2% → 56.2% | 0.000000 | 24 → 24 | 75.0% → 75.0% | 0.000000 |
| reference | by_band | 1000-1400 km | October 2024 held out | 24 | in_track | 32 → 32 | 13 → 13 | 40.6% → 40.6% | 0.000000 | 26 → 26 | 81.2% → 81.2% | 0.000000 |
| reference | by_band | 1000-1400 km | October 2024 held out | 24 | cross | 32 → 32 | 10 → 10 | 31.2% → 31.2% | 0.000000 | 25 → 25 | 78.1% → 78.1% | 0.000000 |
| reference | by_band | 1000-1400 km | October 2024 held out | 36 | radial | 32 → 32 | 30 → 30 | 93.8% → 93.8% | 0.000000 | 32 → 32 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | October 2024 held out | 36 | in_track | 32 → 32 | 11 → 11 | 34.4% → 34.4% | 0.000000 | 24 → 24 | 75.0% → 75.0% | 0.000000 |
| reference | by_band | 1000-1400 km | October 2024 held out | 36 | cross | 32 → 32 | 12 → 12 | 37.5% → 37.5% | 0.000000 | 21 → 21 | 65.6% → 65.6% | 0.000000 |
| reference | by_band | 1000-1400 km | October 2024 held out | 48 | radial | 32 → 32 | 16 → 16 | 50.0% → 50.0% | 0.000000 | 32 → 32 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | October 2024 held out | 48 | in_track | 32 → 32 | 27 → 27 | 84.4% → 84.4% | 0.000000 | 32 → 32 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | October 2024 held out | 48 | cross | 32 → 32 | 11 → 11 | 34.4% → 34.4% | 0.000000 | 32 → 32 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | October 2024 held out | 72 | radial | 32 → 32 | 16 → 16 | 50.0% → 50.0% | 0.000000 | 25 → 25 | 78.1% → 78.1% | 0.000000 |
| reference | by_band | 1000-1400 km | October 2024 held out | 72 | in_track | 32 → 32 | 31 → 31 | 96.9% → 96.9% | 0.000000 | 32 → 32 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | October 2024 held out | 72 | cross | 32 → 32 | 29 → 29 | 90.6% → 90.6% | 0.000000 | 32 → 32 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | October 2024 held out | 96 | radial | 32 → 32 | 32 → 32 | 100.0% → 100.0% | 0.000000 | 32 → 32 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | October 2024 held out | 96 | in_track | 32 → 32 | 32 → 32 | 100.0% → 100.0% | 0.000000 | 32 → 32 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | October 2024 held out | 96 | cross | 32 → 32 | 32 → 32 | 100.0% → 100.0% | 0.000000 | 32 → 32 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | October 2024 held out | 120 | radial | 32 → 32 | 6 → 6 | 18.8% → 18.8% | 0.000000 | 32 → 32 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | October 2024 held out | 120 | in_track | 32 → 32 | 32 → 32 | 100.0% → 100.0% | 0.000000 | 32 → 32 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | October 2024 held out | 120 | cross | 32 → 32 | 20 → 20 | 62.5% → 62.5% | 0.000000 | 32 → 32 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | October 2024 held out | 144 | radial | 32 → 32 | 19 → 19 | 59.4% → 59.4% | 0.000000 | 32 → 32 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | October 2024 held out | 144 | in_track | 32 → 32 | 32 → 32 | 100.0% → 100.0% | 0.000000 | 32 → 32 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | October 2024 held out | 144 | cross | 32 → 32 | 31 → 31 | 96.9% → 96.9% | 0.000000 | 32 → 32 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | October 2024 held out | 168 | radial | 32 → 32 | 32 → 32 | 100.0% → 100.0% | 0.000000 | 32 → 32 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | October 2024 held out | 168 | in_track | 32 → 32 | 32 → 32 | 100.0% → 100.0% | 0.000000 | 32 → 32 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | October 2024 held out | 168 | cross | 32 → 32 | 32 → 32 | 100.0% → 100.0% | 0.000000 | 32 → 32 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | April 2024 control | 6 | radial | 37 → 37 | 19 → 19 | 51.4% → 51.4% | 0.000000 | 26 → 26 | 70.3% → 70.3% | 0.000000 |
| reference | by_band | 1000-1400 km | April 2024 control | 6 | in_track | 37 → 37 | 6 → 6 | 16.2% → 16.2% | 0.000000 | 12 → 12 | 32.4% → 32.4% | 0.000000 |
| reference | by_band | 1000-1400 km | April 2024 control | 6 | cross | 37 → 37 | 10 → 10 | 27.0% → 27.0% | 0.000000 | 21 → 21 | 56.8% → 56.8% | 0.000000 |
| reference | by_band | 1000-1400 km | April 2024 control | 12 | radial | 37 → 37 | 2 → 2 | 5.4% → 5.4% | 0.000000 | 4 → 4 | 10.8% → 10.8% | 0.000000 |
| reference | by_band | 1000-1400 km | April 2024 control | 12 | in_track | 37 → 37 | 2 → 2 | 5.4% → 5.4% | 0.000000 | 5 → 5 | 13.5% → 13.5% | 0.000000 |
| reference | by_band | 1000-1400 km | April 2024 control | 12 | cross | 37 → 37 | 5 → 5 | 13.5% → 13.5% | 0.000000 | 10 → 10 | 27.0% → 27.0% | 0.000000 |
| reference | by_band | 1000-1400 km | April 2024 control | 24 | radial | 37 → 37 | 10 → 10 | 27.0% → 27.0% | 0.000000 | 29 → 29 | 78.4% → 78.4% | 0.000000 |
| reference | by_band | 1000-1400 km | April 2024 control | 24 | in_track | 37 → 37 | 11 → 11 | 29.7% → 29.7% | 0.000000 | 19 → 19 | 51.4% → 51.4% | 0.000000 |
| reference | by_band | 1000-1400 km | April 2024 control | 24 | cross | 37 → 37 | 13 → 13 | 35.1% → 35.1% | 0.000000 | 31 → 31 | 83.8% → 83.8% | 0.000000 |
| reference | by_band | 1000-1400 km | April 2024 control | 36 | radial | 37 → 37 | 28 → 28 | 75.7% → 75.7% | 0.000000 | 37 → 37 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | April 2024 control | 36 | in_track | 37 → 37 | 9 → 9 | 24.3% → 24.3% | 0.000000 | 18 → 18 | 48.6% → 48.6% | 0.000000 |
| reference | by_band | 1000-1400 km | April 2024 control | 36 | cross | 37 → 37 | 22 → 22 | 59.5% → 59.5% | 0.000000 | 36 → 36 | 97.3% → 97.3% | 0.000000 |
| reference | by_band | 1000-1400 km | April 2024 control | 48 | radial | 37 → 37 | 22 → 22 | 59.5% → 59.5% | 0.000000 | 37 → 37 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | April 2024 control | 48 | in_track | 37 → 37 | 21 → 21 | 56.8% → 56.8% | 0.000000 | 23 → 23 | 62.2% → 62.2% | 0.000000 |
| reference | by_band | 1000-1400 km | April 2024 control | 48 | cross | 37 → 37 | 29 → 29 | 78.4% → 78.4% | 0.000000 | 37 → 37 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | April 2024 control | 72 | radial | 37 → 37 | 36 → 36 | 97.3% → 97.3% | 0.000000 | 37 → 37 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | April 2024 control | 72 | in_track | 37 → 37 | 20 → 20 | 54.1% → 54.1% | 0.000000 | 22 → 22 | 59.5% → 59.5% | 0.000000 |
| reference | by_band | 1000-1400 km | April 2024 control | 72 | cross | 37 → 37 | 22 → 22 | 59.5% → 59.5% | 0.000000 | 37 → 37 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | April 2024 control | 96 | radial | 37 → 37 | 37 → 37 | 100.0% → 100.0% | 0.000000 | 37 → 37 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | April 2024 control | 96 | in_track | 37 → 37 | 21 → 21 | 56.8% → 56.8% | 0.000000 | 22 → 22 | 59.5% → 59.5% | 0.000000 |
| reference | by_band | 1000-1400 km | April 2024 control | 96 | cross | 37 → 37 | 37 → 37 | 100.0% → 100.0% | 0.000000 | 37 → 37 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | April 2024 control | 120 | radial | 37 → 37 | 34 → 34 | 91.9% → 91.9% | 0.000000 | 37 → 37 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | April 2024 control | 120 | in_track | 37 → 37 | 21 → 21 | 56.8% → 56.8% | 0.000000 | 26 → 26 | 70.3% → 70.3% | 0.000000 |
| reference | by_band | 1000-1400 km | April 2024 control | 120 | cross | 37 → 37 | 4 → 4 | 10.8% → 10.8% | 0.000000 | 37 → 37 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | April 2024 control | 144 | radial | 37 → 37 | 37 → 37 | 100.0% → 100.0% | 0.000000 | 37 → 37 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | April 2024 control | 144 | in_track | 37 → 37 | 26 → 26 | 70.3% → 70.3% | 0.000000 | 32 → 32 | 86.5% → 86.5% | 0.000000 |
| reference | by_band | 1000-1400 km | April 2024 control | 144 | cross | 37 → 37 | 33 → 33 | 89.2% → 89.2% | 0.000000 | 37 → 37 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | April 2024 control | 168 | radial | 37 → 37 | 37 → 37 | 100.0% → 100.0% | 0.000000 | 37 → 37 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | April 2024 control | 168 | in_track | 37 → 37 | 25 → 25 | 67.6% → 67.6% | 0.000000 | 27 → 27 | 73.0% → 73.0% | 0.000000 |
| reference | by_band | 1000-1400 km | April 2024 control | 168 | cross | 37 → 37 | 37 → 37 | 100.0% → 100.0% | 0.000000 | 37 → 37 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | May 2024 | 6 | radial | 30 → 30 | 6 → 6 | 20.0% → 20.0% | 0.000000 | 17 → 17 | 56.7% → 56.7% | 0.000000 |
| reference | by_band | 1000-1400 km | May 2024 | 6 | in_track | 30 → 30 | 4 → 4 | 13.3% → 13.3% | 0.000000 | 4 → 4 | 13.3% → 13.3% | 0.000000 |
| reference | by_band | 1000-1400 km | May 2024 | 6 | cross | 30 → 30 | 6 → 6 | 20.0% → 20.0% | 0.000000 | 12 → 12 | 40.0% → 40.0% | 0.000000 |
| reference | by_band | 1000-1400 km | May 2024 | 12 | radial | 29 → 29 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 1 → 1 | 3.4% → 3.4% | 0.000000 |
| reference | by_band | 1000-1400 km | May 2024 | 12 | in_track | 29 → 29 | 2 → 2 | 6.9% → 6.9% | 0.000000 | 5 → 5 | 17.2% → 17.2% | 0.000000 |
| reference | by_band | 1000-1400 km | May 2024 | 12 | cross | 29 → 29 | 9 → 9 | 31.0% → 31.0% | 0.000000 | 18 → 18 | 62.1% → 62.1% | 0.000000 |
| reference | by_band | 1000-1400 km | May 2024 | 24 | radial | 28 → 28 | 16 → 16 | 57.1% → 57.1% | 0.000000 | 25 → 25 | 89.3% → 89.3% | 0.000000 |
| reference | by_band | 1000-1400 km | May 2024 | 24 | in_track | 28 → 28 | 2 → 2 | 7.1% → 7.1% | 0.000000 | 2 → 2 | 7.1% → 7.1% | 0.000000 |
| reference | by_band | 1000-1400 km | May 2024 | 24 | cross | 28 → 28 | 17 → 17 | 60.7% → 60.7% | 0.000000 | 25 → 25 | 89.3% → 89.3% | 0.000000 |
| reference | by_band | 1000-1400 km | May 2024 | 36 | radial | 26 → 26 | 25 → 25 | 96.2% → 96.2% | 0.000000 | 26 → 26 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | May 2024 | 36 | in_track | 26 → 26 | 3 → 3 | 11.5% → 11.5% | 0.000000 | 6 → 6 | 23.1% → 23.1% | 0.000000 |
| reference | by_band | 1000-1400 km | May 2024 | 36 | cross | 26 → 26 | 13 → 13 | 50.0% → 50.0% | 0.000000 | 22 → 22 | 84.6% → 84.6% | 0.000000 |
| reference | by_band | 1000-1400 km | May 2024 | 48 | radial | 25 → 25 | 22 → 22 | 88.0% → 88.0% | 0.000000 | 25 → 25 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | May 2024 | 48 | in_track | 25 → 25 | 6 → 6 | 24.0% → 24.0% | 0.000000 | 9 → 9 | 36.0% → 36.0% | 0.000000 |
| reference | by_band | 1000-1400 km | May 2024 | 48 | cross | 25 → 25 | 2 → 2 | 8.0% → 8.0% | 0.000000 | 20 → 20 | 80.0% → 80.0% | 0.000000 |
| reference | by_band | 1000-1400 km | May 2024 | 72 | radial | 23 → 23 | 21 → 21 | 91.3% → 91.3% | 0.000000 | 23 → 23 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | May 2024 | 72 | in_track | 23 → 23 | 6 → 6 | 26.1% → 26.1% | 0.000000 | 6 → 6 | 26.1% → 26.1% | 0.000000 |
| reference | by_band | 1000-1400 km | May 2024 | 72 | cross | 23 → 23 | 16 → 16 | 69.6% → 69.6% | 0.000000 | 23 → 23 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | May 2024 | 96 | radial | 20 → 20 | 20 → 20 | 100.0% → 100.0% | 0.000000 | 20 → 20 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | May 2024 | 96 | in_track | 20 → 20 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 3 → 3 | 15.0% → 15.0% | 0.000000 |
| reference | by_band | 1000-1400 km | May 2024 | 96 | cross | 20 → 20 | 18 → 18 | 90.0% → 90.0% | 0.000000 | 20 → 20 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | May 2024 | 120 | radial | 20 → 20 | 19 → 19 | 95.0% → 95.0% | 0.000000 | 20 → 20 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | May 2024 | 120 | in_track | 20 → 20 | 2 → 2 | 10.0% → 10.0% | 0.000000 | 6 → 6 | 30.0% → 30.0% | 0.000000 |
| reference | by_band | 1000-1400 km | May 2024 | 120 | cross | 20 → 20 | 9 → 9 | 45.0% → 45.0% | 0.000000 | 20 → 20 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | May 2024 | 144 | radial | 20 → 20 | 19 → 19 | 95.0% → 95.0% | 0.000000 | 20 → 20 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | May 2024 | 144 | in_track | 20 → 20 | 4 → 4 | 20.0% → 20.0% | 0.000000 | 9 → 9 | 45.0% → 45.0% | 0.000000 |
| reference | by_band | 1000-1400 km | May 2024 | 144 | cross | 20 → 20 | 20 → 20 | 100.0% → 100.0% | 0.000000 | 20 → 20 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | May 2024 | 168 | radial | 20 → 20 | 20 → 20 | 100.0% → 100.0% | 0.000000 | 20 → 20 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 1000-1400 km | May 2024 | 168 | in_track | 20 → 20 | 1 → 1 | 5.0% → 5.0% | 0.000000 | 8 → 8 | 40.0% → 40.0% | 0.000000 |
| reference | by_band | 1000-1400 km | May 2024 | 168 | cross | 20 → 20 | 19 → 19 | 95.0% → 95.0% | 0.000000 | 20 → 20 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 400-600 km | August 2024 held out | 6 | radial | 93 → 93 | 17 → 17 | 18.3% → 18.3% | 0.000000 | 61 → 61 | 65.6% → 65.6% | 0.000000 |
| reference | by_band | 400-600 km | August 2024 held out | 6 | in_track | 93 → 93 | 22 → 22 | 23.7% → 23.7% | 0.000000 | 40 → 40 | 43.0% → 43.0% | 0.000000 |
| reference | by_band | 400-600 km | August 2024 held out | 6 | cross | 93 → 93 | 1 → 1 | 1.1% → 1.1% | 0.000000 | 1 → 1 | 1.1% → 1.1% | 0.000000 |
| reference | by_band | 400-600 km | August 2024 held out | 12 | radial | 93 → 93 | 51 → 51 | 54.8% → 54.8% | 0.000000 | 77 → 77 | 82.8% → 82.8% | 0.000000 |
| reference | by_band | 400-600 km | August 2024 held out | 12 | in_track | 93 → 93 | 20 → 20 | 21.5% → 21.5% | 0.000000 | 39 → 39 | 41.9% → 41.9% | 0.000000 |
| reference | by_band | 400-600 km | August 2024 held out | 12 | cross | 93 → 93 | 6 → 6 | 6.5% → 6.5% | 0.000000 | 13 → 13 | 14.0% → 14.0% | 0.000000 |
| reference | by_band | 400-600 km | August 2024 held out | 24 | radial | 93 → 93 | 86 → 86 | 92.5% → 92.5% | 0.000000 | 92 → 92 | 98.9% → 98.9% | 0.000000 |
| reference | by_band | 400-600 km | August 2024 held out | 24 | in_track | 93 → 93 | 53 → 53 | 57.0% → 57.0% | 0.000000 | 75 → 75 | 80.6% → 80.6% | 0.000000 |
| reference | by_band | 400-600 km | August 2024 held out | 24 | cross | 93 → 93 | 5 → 5 | 5.4% → 5.4% | 0.000000 | 9 → 9 | 9.7% → 9.7% | 0.000000 |
| reference | by_band | 400-600 km | August 2024 held out | 36 | radial | 93 → 93 | 67 → 67 | 72.0% → 72.0% | 0.000000 | 92 → 92 | 98.9% → 98.9% | 0.000000 |
| reference | by_band | 400-600 km | August 2024 held out | 36 | in_track | 93 → 93 | 44 → 44 | 47.3% → 47.3% | 0.000000 | 64 → 64 | 68.8% → 68.8% | 0.000000 |
| reference | by_band | 400-600 km | August 2024 held out | 36 | cross | 93 → 93 | 13 → 13 | 14.0% → 14.0% | 0.000000 | 25 → 25 | 26.9% → 26.9% | 0.000000 |
| reference | by_band | 400-600 km | August 2024 held out | 48 | radial | 93 → 93 | 53 → 53 | 57.0% → 57.0% | 0.000000 | 93 → 93 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 400-600 km | August 2024 held out | 48 | in_track | 93 → 93 | 40 → 40 | 43.0% → 43.0% | 0.000000 | 55 → 55 | 59.1% → 59.1% | 0.000000 |
| reference | by_band | 400-600 km | August 2024 held out | 48 | cross | 93 → 93 | 19 → 19 | 20.4% → 20.4% | 0.000000 | 26 → 26 | 28.0% → 28.0% | 0.000000 |
| reference | by_band | 400-600 km | August 2024 held out | 72 | radial | 93 → 93 | 70 → 70 | 75.3% → 75.3% | 0.000000 | 89 → 89 | 95.7% → 95.7% | 0.000000 |
| reference | by_band | 400-600 km | August 2024 held out | 72 | in_track | 93 → 93 | 27 → 27 | 29.0% → 29.0% | 0.000000 | 47 → 47 | 50.5% → 50.5% | 0.000000 |
| reference | by_band | 400-600 km | August 2024 held out | 72 | cross | 93 → 93 | 15 → 15 | 16.1% → 16.1% | 0.000000 | 34 → 34 | 36.6% → 36.6% | 0.000000 |
| reference | by_band | 400-600 km | August 2024 held out | 96 | radial | 93 → 93 | 82 → 82 | 88.2% → 88.2% | 0.000000 | 89 → 89 | 95.7% → 95.7% | 0.000000 |
| reference | by_band | 400-600 km | August 2024 held out | 96 | in_track | 93 → 93 | 20 → 20 | 21.5% → 21.5% | 0.000000 | 41 → 41 | 44.1% → 44.1% | 0.000000 |
| reference | by_band | 400-600 km | August 2024 held out | 96 | cross | 93 → 93 | 21 → 21 | 22.6% → 22.6% | 0.000000 | 37 → 37 | 39.8% → 39.8% | 0.000000 |
| reference | by_band | 400-600 km | August 2024 held out | 120 | radial | 93 → 93 | 60 → 60 | 64.5% → 64.5% | 0.000000 | 88 → 88 | 94.6% → 94.6% | 0.000000 |
| reference | by_band | 400-600 km | August 2024 held out | 120 | in_track | 93 → 93 | 22 → 22 | 23.7% → 23.7% | 0.000000 | 35 → 35 | 37.6% → 37.6% | 0.000000 |
| reference | by_band | 400-600 km | August 2024 held out | 120 | cross | 93 → 93 | 21 → 21 | 22.6% → 22.6% | 0.000000 | 50 → 50 | 53.8% → 53.8% | 0.000000 |
| reference | by_band | 400-600 km | August 2024 held out | 144 | radial | 93 → 93 | 62 → 62 | 66.7% → 66.7% | 0.000000 | 85 → 86 | 91.4% → 92.5% | 1.075269 |
| reference | by_band | 400-600 km | August 2024 held out | 144 | in_track | 93 → 93 | 24 → 24 | 25.8% → 25.8% | 0.000000 | 33 → 33 | 35.5% → 35.5% | 0.000000 |
| reference | by_band | 400-600 km | August 2024 held out | 144 | cross | 93 → 93 | 31 → 31 | 33.3% → 33.3% | 0.000000 | 62 → 62 | 66.7% → 66.7% | 0.000000 |
| reference | by_band | 400-600 km | August 2024 held out | 168 | radial | 93 → 93 | 66 → 68 | 71.0% → 73.1% | 2.150538 | 80 → 80 | 86.0% → 86.0% | 0.000000 |
| reference | by_band | 400-600 km | August 2024 held out | 168 | in_track | 93 → 93 | 27 → 27 | 29.0% → 29.0% | 0.000000 | 31 → 31 | 33.3% → 33.3% | 0.000000 |
| reference | by_band | 400-600 km | August 2024 held out | 168 | cross | 93 → 93 | 25 → 25 | 26.9% → 26.9% | 0.000000 | 61 → 61 | 65.6% → 65.6% | 0.000000 |
| reference | by_band | 400-600 km | October 2024 held out | 6 | radial | 100 → 100 | 58 → 58 | 58.0% → 58.0% | 0.000000 | 86 → 86 | 86.0% → 86.0% | 0.000000 |
| reference | by_band | 400-600 km | October 2024 held out | 6 | in_track | 100 → 100 | 31 → 31 | 31.0% → 31.0% | 0.000000 | 77 → 77 | 77.0% → 77.0% | 0.000000 |
| reference | by_band | 400-600 km | October 2024 held out | 6 | cross | 100 → 100 | 2 → 2 | 2.0% → 2.0% | 0.000000 | 7 → 7 | 7.0% → 7.0% | 0.000000 |
| reference | by_band | 400-600 km | October 2024 held out | 12 | radial | 100 → 100 | 20 → 20 | 20.0% → 20.0% | 0.000000 | 42 → 42 | 42.0% → 42.0% | 0.000000 |
| reference | by_band | 400-600 km | October 2024 held out | 12 | in_track | 100 → 100 | 33 → 33 | 33.0% → 33.0% | 0.000000 | 58 → 58 | 58.0% → 58.0% | 0.000000 |
| reference | by_band | 400-600 km | October 2024 held out | 12 | cross | 100 → 100 | 4 → 4 | 4.0% → 4.0% | 0.000000 | 9 → 9 | 9.0% → 9.0% | 0.000000 |
| reference | by_band | 400-600 km | October 2024 held out | 24 | radial | 100 → 100 | 67 → 67 | 67.0% → 67.0% | 0.000000 | 97 → 97 | 97.0% → 97.0% | 0.000000 |
| reference | by_band | 400-600 km | October 2024 held out | 24 | in_track | 100 → 100 | 53 → 53 | 53.0% → 53.0% | 0.000000 | 71 → 71 | 71.0% → 71.0% | 0.000000 |
| reference | by_band | 400-600 km | October 2024 held out | 24 | cross | 100 → 100 | 8 → 8 | 8.0% → 8.0% | 0.000000 | 16 → 16 | 16.0% → 16.0% | 0.000000 |
| reference | by_band | 400-600 km | October 2024 held out | 36 | radial | 100 → 100 | 30 → 30 | 30.0% → 30.0% | 0.000000 | 83 → 83 | 83.0% → 83.0% | 0.000000 |
| reference | by_band | 400-600 km | October 2024 held out | 36 | in_track | 100 → 100 | 49 → 49 | 49.0% → 49.0% | 0.000000 | 65 → 65 | 65.0% → 65.0% | 0.000000 |
| reference | by_band | 400-600 km | October 2024 held out | 36 | cross | 100 → 100 | 13 → 13 | 13.0% → 13.0% | 0.000000 | 19 → 19 | 19.0% → 19.0% | 0.000000 |
| reference | by_band | 400-600 km | October 2024 held out | 48 | radial | 100 → 100 | 80 → 80 | 80.0% → 80.0% | 0.000000 | 96 → 97 | 96.0% → 97.0% | 1.000000 |
| reference | by_band | 400-600 km | October 2024 held out | 48 | in_track | 100 → 100 | 48 → 48 | 48.0% → 48.0% | 0.000000 | 68 → 68 | 68.0% → 68.0% | 0.000000 |
| reference | by_band | 400-600 km | October 2024 held out | 48 | cross | 100 → 100 | 20 → 20 | 20.0% → 20.0% | 0.000000 | 29 → 29 | 29.0% → 29.0% | 0.000000 |
| reference | by_band | 400-600 km | October 2024 held out | 72 | radial | 100 → 100 | 63 → 63 | 63.0% → 63.0% | 0.000000 | 85 → 85 | 85.0% → 85.0% | 0.000000 |
| reference | by_band | 400-600 km | October 2024 held out | 72 | in_track | 100 → 100 | 47 → 47 | 47.0% → 47.0% | 0.000000 | 65 → 65 | 65.0% → 65.0% | 0.000000 |
| reference | by_band | 400-600 km | October 2024 held out | 72 | cross | 100 → 100 | 28 → 28 | 28.0% → 28.0% | 0.000000 | 43 → 43 | 43.0% → 43.0% | 0.000000 |
| reference | by_band | 400-600 km | October 2024 held out | 96 | radial | 97 → 97 | 71 → 75 | 73.2% → 77.3% | 4.123711 | 89 → 89 | 91.8% → 91.8% | 0.000000 |
| reference | by_band | 400-600 km | October 2024 held out | 96 | in_track | 97 → 97 | 53 → 53 | 54.6% → 54.6% | 0.000000 | 62 → 62 | 63.9% → 63.9% | 0.000000 |
| reference | by_band | 400-600 km | October 2024 held out | 96 | cross | 97 → 97 | 17 → 17 | 17.5% → 17.5% | 0.000000 | 37 → 37 | 38.1% → 38.1% | 0.000000 |
| reference | by_band | 400-600 km | October 2024 held out | 120 | radial | 93 → 93 | 67 → 68 | 72.0% → 73.1% | 1.075269 | 74 → 78 | 79.6% → 83.9% | 4.301075 |
| reference | by_band | 400-600 km | October 2024 held out | 120 | in_track | 93 → 93 | 56 → 56 | 60.2% → 60.2% | 0.000000 | 62 → 62 | 66.7% → 66.7% | 0.000000 |
| reference | by_band | 400-600 km | October 2024 held out | 120 | cross | 93 → 93 | 29 → 29 | 31.2% → 31.2% | 0.000000 | 44 → 44 | 47.3% → 47.3% | 0.000000 |
| reference | by_band | 400-600 km | October 2024 held out | 144 | radial | 89 → 89 | 58 → 58 | 65.2% → 65.2% | 0.000000 | 63 → 68 | 70.8% → 76.4% | 5.617978 |
| reference | by_band | 400-600 km | October 2024 held out | 144 | in_track | 89 → 89 | 50 → 50 | 56.2% → 56.2% | 0.000000 | 59 → 59 | 66.3% → 66.3% | 0.000000 |
| reference | by_band | 400-600 km | October 2024 held out | 144 | cross | 89 → 89 | 34 → 34 | 38.2% → 38.2% | 0.000000 | 53 → 53 | 59.6% → 59.6% | 0.000000 |
| reference | by_band | 400-600 km | October 2024 held out | 168 | radial | 85 → 85 | 58 → 58 | 68.2% → 68.2% | 0.000000 | 59 → 63 | 69.4% → 74.1% | 4.705882 |
| reference | by_band | 400-600 km | October 2024 held out | 168 | in_track | 85 → 85 | 46 → 46 | 54.1% → 54.1% | 0.000000 | 57 → 57 | 67.1% → 67.1% | 0.000000 |
| reference | by_band | 400-600 km | October 2024 held out | 168 | cross | 85 → 85 | 33 → 33 | 38.8% → 38.8% | 0.000000 | 60 → 60 | 70.6% → 70.6% | 0.000000 |
| reference | by_band | 400-600 km | April 2024 control | 6 | radial | 95 → 95 | 47 → 47 | 49.5% → 49.5% | 0.000000 | 93 → 93 | 97.9% → 97.9% | 0.000000 |
| reference | by_band | 400-600 km | April 2024 control | 6 | in_track | 95 → 95 | 30 → 30 | 31.6% → 31.6% | 0.000000 | 54 → 54 | 56.8% → 56.8% | 0.000000 |
| reference | by_band | 400-600 km | April 2024 control | 6 | cross | 95 → 95 | 2 → 2 | 2.1% → 2.1% | 0.000000 | 2 → 2 | 2.1% → 2.1% | 0.000000 |
| reference | by_band | 400-600 km | April 2024 control | 12 | radial | 95 → 95 | 54 → 54 | 56.8% → 56.8% | 0.000000 | 77 → 77 | 81.1% → 81.1% | 0.000000 |
| reference | by_band | 400-600 km | April 2024 control | 12 | in_track | 95 → 95 | 25 → 25 | 26.3% → 26.3% | 0.000000 | 39 → 39 | 41.1% → 41.1% | 0.000000 |
| reference | by_band | 400-600 km | April 2024 control | 12 | cross | 95 → 95 | 1 → 1 | 1.1% → 1.1% | 0.000000 | 3 → 3 | 3.2% → 3.2% | 0.000000 |
| reference | by_band | 400-600 km | April 2024 control | 24 | radial | 95 → 95 | 91 → 91 | 95.8% → 95.8% | 0.000000 | 95 → 95 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 400-600 km | April 2024 control | 24 | in_track | 95 → 95 | 81 → 81 | 85.3% → 85.3% | 0.000000 | 93 → 93 | 97.9% → 97.9% | 0.000000 |
| reference | by_band | 400-600 km | April 2024 control | 24 | cross | 95 → 95 | 1 → 1 | 1.1% → 1.1% | 0.000000 | 5 → 5 | 5.3% → 5.3% | 0.000000 |
| reference | by_band | 400-600 km | April 2024 control | 36 | radial | 95 → 95 | 65 → 65 | 68.4% → 68.4% | 0.000000 | 95 → 95 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 400-600 km | April 2024 control | 36 | in_track | 95 → 95 | 78 → 78 | 82.1% → 82.1% | 0.000000 | 94 → 94 | 98.9% → 98.9% | 0.000000 |
| reference | by_band | 400-600 km | April 2024 control | 36 | cross | 95 → 95 | 23 → 23 | 24.2% → 24.2% | 0.000000 | 34 → 34 | 35.8% → 35.8% | 0.000000 |
| reference | by_band | 400-600 km | April 2024 control | 48 | radial | 95 → 95 | 61 → 61 | 64.2% → 64.2% | 0.000000 | 95 → 95 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 400-600 km | April 2024 control | 48 | in_track | 95 → 95 | 89 → 89 | 93.7% → 93.7% | 0.000000 | 95 → 95 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 400-600 km | April 2024 control | 48 | cross | 95 → 95 | 10 → 10 | 10.5% → 10.5% | 0.000000 | 28 → 28 | 29.5% → 29.5% | 0.000000 |
| reference | by_band | 400-600 km | April 2024 control | 72 | radial | 95 → 95 | 73 → 73 | 76.8% → 76.8% | 0.000000 | 95 → 95 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 400-600 km | April 2024 control | 72 | in_track | 95 → 95 | 91 → 91 | 95.8% → 95.8% | 0.000000 | 95 → 95 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 400-600 km | April 2024 control | 72 | cross | 95 → 95 | 39 → 39 | 41.1% → 41.1% | 0.000000 | 61 → 61 | 64.2% → 64.2% | 0.000000 |
| reference | by_band | 400-600 km | April 2024 control | 96 | radial | 95 → 95 | 95 → 95 | 100.0% → 100.0% | 0.000000 | 95 → 95 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 400-600 km | April 2024 control | 96 | in_track | 95 → 95 | 91 → 91 | 95.8% → 95.8% | 0.000000 | 95 → 95 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 400-600 km | April 2024 control | 96 | cross | 95 → 95 | 20 → 20 | 21.1% → 21.1% | 0.000000 | 37 → 37 | 38.9% → 38.9% | 0.000000 |
| reference | by_band | 400-600 km | April 2024 control | 120 | radial | 95 → 95 | 88 → 88 | 92.6% → 92.6% | 0.000000 | 95 → 95 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 400-600 km | April 2024 control | 120 | in_track | 95 → 95 | 88 → 88 | 92.6% → 92.6% | 0.000000 | 94 → 94 | 98.9% → 98.9% | 0.000000 |
| reference | by_band | 400-600 km | April 2024 control | 120 | cross | 95 → 95 | 41 → 41 | 43.2% → 43.2% | 0.000000 | 81 → 81 | 85.3% → 85.3% | 0.000000 |
| reference | by_band | 400-600 km | April 2024 control | 144 | radial | 95 → 95 | 92 → 92 | 96.8% → 96.8% | 0.000000 | 95 → 95 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 400-600 km | April 2024 control | 144 | in_track | 95 → 95 | 84 → 84 | 88.4% → 88.4% | 0.000000 | 94 → 94 | 98.9% → 98.9% | 0.000000 |
| reference | by_band | 400-600 km | April 2024 control | 144 | cross | 95 → 95 | 42 → 42 | 44.2% → 44.2% | 0.000000 | 76 → 76 | 80.0% → 80.0% | 0.000000 |
| reference | by_band | 400-600 km | April 2024 control | 168 | radial | 95 → 95 | 75 → 75 | 78.9% → 78.9% | 0.000000 | 95 → 95 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 400-600 km | April 2024 control | 168 | in_track | 95 → 95 | 76 → 76 | 80.0% → 80.0% | 0.000000 | 93 → 93 | 97.9% → 97.9% | 0.000000 |
| reference | by_band | 400-600 km | April 2024 control | 168 | cross | 95 → 95 | 45 → 45 | 47.4% → 47.4% | 0.000000 | 76 → 76 | 80.0% → 80.0% | 0.000000 |
| reference | by_band | 400-600 km | May 2024 | 6 | radial | 91 → 91 | 36 → 36 | 39.6% → 39.6% | 0.000000 | 85 → 85 | 93.4% → 93.4% | 0.000000 |
| reference | by_band | 400-600 km | May 2024 | 6 | in_track | 91 → 91 | 19 → 19 | 20.9% → 20.9% | 0.000000 | 42 → 42 | 46.2% → 46.2% | 0.000000 |
| reference | by_band | 400-600 km | May 2024 | 6 | cross | 91 → 91 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 2 → 2 | 2.2% → 2.2% | 0.000000 |
| reference | by_band | 400-600 km | May 2024 | 12 | radial | 91 → 91 | 55 → 55 | 60.4% → 60.4% | 0.000000 | 79 → 79 | 86.8% → 86.8% | 0.000000 |
| reference | by_band | 400-600 km | May 2024 | 12 | in_track | 91 → 91 | 25 → 25 | 27.5% → 27.5% | 0.000000 | 47 → 47 | 51.6% → 51.6% | 0.000000 |
| reference | by_band | 400-600 km | May 2024 | 12 | cross | 91 → 91 | 6 → 6 | 6.6% → 6.6% | 0.000000 | 8 → 8 | 8.8% → 8.8% | 0.000000 |
| reference | by_band | 400-600 km | May 2024 | 24 | radial | 91 → 91 | 84 → 84 | 92.3% → 92.3% | 0.000000 | 91 → 91 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 400-600 km | May 2024 | 24 | in_track | 91 → 91 | 52 → 52 | 57.1% → 57.1% | 0.000000 | 76 → 76 | 83.5% → 83.5% | 0.000000 |
| reference | by_band | 400-600 km | May 2024 | 24 | cross | 91 → 91 | 3 → 3 | 3.3% → 3.3% | 0.000000 | 7 → 7 | 7.7% → 7.7% | 0.000000 |
| reference | by_band | 400-600 km | May 2024 | 36 | radial | 91 → 91 | 64 → 64 | 70.3% → 70.3% | 0.000000 | 89 → 89 | 97.8% → 97.8% | 0.000000 |
| reference | by_band | 400-600 km | May 2024 | 36 | in_track | 91 → 91 | 68 → 68 | 74.7% → 74.7% | 0.000000 | 70 → 70 | 76.9% → 76.9% | 0.000000 |
| reference | by_band | 400-600 km | May 2024 | 36 | cross | 91 → 91 | 22 → 22 | 24.2% → 24.2% | 0.000000 | 36 → 36 | 39.6% → 39.6% | 0.000000 |
| reference | by_band | 400-600 km | May 2024 | 48 | radial | 91 → 91 | 52 → 52 | 57.1% → 57.1% | 0.000000 | 91 → 91 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 400-600 km | May 2024 | 48 | in_track | 91 → 91 | 60 → 60 | 65.9% → 65.9% | 0.000000 | 68 → 68 | 74.7% → 74.7% | 0.000000 |
| reference | by_band | 400-600 km | May 2024 | 48 | cross | 91 → 91 | 14 → 14 | 15.4% → 15.4% | 0.000000 | 30 → 30 | 33.0% → 33.0% | 0.000000 |
| reference | by_band | 400-600 km | May 2024 | 72 | radial | 88 → 88 | 70 → 70 | 79.5% → 79.5% | 0.000000 | 88 → 88 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 400-600 km | May 2024 | 72 | in_track | 88 → 88 | 44 → 44 | 50.0% → 50.0% | 0.000000 | 60 → 60 | 68.2% → 68.2% | 0.000000 |
| reference | by_band | 400-600 km | May 2024 | 72 | cross | 88 → 88 | 45 → 45 | 51.1% → 51.1% | 0.000000 | 70 → 70 | 79.5% → 79.5% | 0.000000 |
| reference | by_band | 400-600 km | May 2024 | 96 | radial | 86 → 86 | 82 → 82 | 95.3% → 95.3% | 0.000000 | 86 → 86 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 400-600 km | May 2024 | 96 | in_track | 86 → 86 | 40 → 40 | 46.5% → 46.5% | 0.000000 | 61 → 61 | 70.9% → 70.9% | 0.000000 |
| reference | by_band | 400-600 km | May 2024 | 96 | cross | 86 → 86 | 21 → 21 | 24.4% → 24.4% | 0.000000 | 43 → 43 | 50.0% → 50.0% | 0.000000 |
| reference | by_band | 400-600 km | May 2024 | 120 | radial | 84 → 84 | 70 → 70 | 83.3% → 83.3% | 0.000000 | 82 → 84 | 97.6% → 100.0% | 2.380952 |
| reference | by_band | 400-600 km | May 2024 | 120 | in_track | 84 → 84 | 29 → 29 | 34.5% → 34.5% | 0.000000 | 63 → 63 | 75.0% → 75.0% | 0.000000 |
| reference | by_band | 400-600 km | May 2024 | 120 | cross | 84 → 84 | 53 → 53 | 63.1% → 63.1% | 0.000000 | 81 → 81 | 96.4% → 96.4% | 0.000000 |
| reference | by_band | 400-600 km | May 2024 | 144 | radial | 81 → 81 | 72 → 75 | 88.9% → 92.6% | 3.703704 | 75 → 79 | 92.6% → 97.5% | 4.938272 |
| reference | by_band | 400-600 km | May 2024 | 144 | in_track | 81 → 81 | 29 → 29 | 35.8% → 35.8% | 0.000000 | 58 → 58 | 71.6% → 71.6% | 0.000000 |
| reference | by_band | 400-600 km | May 2024 | 144 | cross | 81 → 81 | 64 → 64 | 79.0% → 79.0% | 0.000000 | 74 → 74 | 91.4% → 91.4% | 0.000000 |
| reference | by_band | 400-600 km | May 2024 | 168 | radial | 78 → 78 | 63 → 64 | 80.8% → 82.1% | 1.282051 | 70 → 75 | 89.7% → 96.2% | 6.410256 |
| reference | by_band | 400-600 km | May 2024 | 168 | in_track | 78 → 78 | 30 → 30 | 38.5% → 38.5% | 0.000000 | 65 → 65 | 83.3% → 83.3% | 0.000000 |
| reference | by_band | 400-600 km | May 2024 | 168 | cross | 78 → 78 | 33 → 33 | 42.3% → 42.3% | 0.000000 | 69 → 69 | 88.5% → 88.5% | 0.000000 |
| reference | by_band | 600-750 km | August 2024 held out | 6 | radial | 39 → 39 | 14 → 14 | 35.9% → 35.9% | 0.000000 | 17 → 17 | 43.6% → 43.6% | 0.000000 |
| reference | by_band | 600-750 km | August 2024 held out | 6 | in_track | 39 → 39 | 14 → 14 | 35.9% → 35.9% | 0.000000 | 23 → 23 | 59.0% → 59.0% | 0.000000 |
| reference | by_band | 600-750 km | August 2024 held out | 6 | cross | 39 → 39 | 3 → 3 | 7.7% → 7.7% | 0.000000 | 5 → 5 | 12.8% → 12.8% | 0.000000 |
| reference | by_band | 600-750 km | August 2024 held out | 12 | radial | 37 → 37 | 13 → 13 | 35.1% → 35.1% | 0.000000 | 25 → 25 | 67.6% → 67.6% | 0.000000 |
| reference | by_band | 600-750 km | August 2024 held out | 12 | in_track | 37 → 37 | 18 → 18 | 48.6% → 48.6% | 0.000000 | 25 → 25 | 67.6% → 67.6% | 0.000000 |
| reference | by_band | 600-750 km | August 2024 held out | 12 | cross | 37 → 37 | 1 → 1 | 2.7% → 2.7% | 0.000000 | 3 → 3 | 8.1% → 8.1% | 0.000000 |
| reference | by_band | 600-750 km | August 2024 held out | 24 | radial | 34 → 34 | 7 → 7 | 20.6% → 20.6% | 0.000000 | 17 → 17 | 50.0% → 50.0% | 0.000000 |
| reference | by_band | 600-750 km | August 2024 held out | 24 | in_track | 34 → 34 | 21 → 21 | 61.8% → 61.8% | 0.000000 | 28 → 28 | 82.4% → 82.4% | 0.000000 |
| reference | by_band | 600-750 km | August 2024 held out | 24 | cross | 34 → 34 | 2 → 2 | 5.9% → 5.9% | 0.000000 | 8 → 8 | 23.5% → 23.5% | 0.000000 |
| reference | by_band | 600-750 km | August 2024 held out | 36 | radial | 29 → 29 | 19 → 19 | 65.5% → 65.5% | 0.000000 | 29 → 29 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 600-750 km | August 2024 held out | 36 | in_track | 29 → 29 | 21 → 21 | 72.4% → 72.4% | 0.000000 | 24 → 24 | 82.8% → 82.8% | 0.000000 |
| reference | by_band | 600-750 km | August 2024 held out | 36 | cross | 29 → 29 | 11 → 11 | 37.9% → 37.9% | 0.000000 | 15 → 15 | 51.7% → 51.7% | 0.000000 |
| reference | by_band | 600-750 km | August 2024 held out | 48 | radial | 25 → 25 | 13 → 13 | 52.0% → 52.0% | 0.000000 | 24 → 24 | 96.0% → 96.0% | 0.000000 |
| reference | by_band | 600-750 km | August 2024 held out | 48 | in_track | 25 → 25 | 14 → 14 | 56.0% → 56.0% | 0.000000 | 20 → 20 | 80.0% → 80.0% | 0.000000 |
| reference | by_band | 600-750 km | August 2024 held out | 48 | cross | 25 → 25 | 5 → 5 | 20.0% → 20.0% | 0.000000 | 13 → 13 | 52.0% → 52.0% | 0.000000 |
| reference | by_band | 600-750 km | August 2024 held out | 72 | radial | 19 → 19 | 15 → 15 | 78.9% → 78.9% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 600-750 km | August 2024 held out | 72 | in_track | 19 → 19 | 10 → 10 | 52.6% → 52.6% | 0.000000 | 18 → 18 | 94.7% → 94.7% | 0.000000 |
| reference | by_band | 600-750 km | August 2024 held out | 72 | cross | 19 → 19 | 7 → 7 | 36.8% → 36.8% | 0.000000 | 14 → 14 | 73.7% → 73.7% | 0.000000 |
| reference | by_band | 600-750 km | August 2024 held out | 96 | radial | 12 → 12 | 8 → 8 | 66.7% → 66.7% | 0.000000 | 12 → 12 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 600-750 km | August 2024 held out | 96 | in_track | 12 → 12 | 5 → 5 | 41.7% → 41.7% | 0.000000 | 12 → 12 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 600-750 km | August 2024 held out | 96 | cross | 12 → 12 | 6 → 6 | 50.0% → 50.0% | 0.000000 | 9 → 9 | 75.0% → 75.0% | 0.000000 |
| reference | by_band | 600-750 km | August 2024 held out | 120 | radial | 4 → 4 | 1 → 1 | 25.0% → 25.0% | 0.000000 | 4 → 4 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 600-750 km | August 2024 held out | 120 | in_track | 4 → 4 | 4 → 4 | 100.0% → 100.0% | 0.000000 | 4 → 4 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 600-750 km | August 2024 held out | 120 | cross | 4 → 4 | 2 → 2 | 50.0% → 50.0% | 0.000000 | 2 → 2 | 50.0% → 50.0% | 0.000000 |
| reference | by_band | 600-750 km | August 2024 held out | 144 | radial | 0 → 0 | 0 → 0 | — → — | — | 0 → 0 | — → — | — |
| reference | by_band | 600-750 km | August 2024 held out | 144 | in_track | 0 → 0 | 0 → 0 | — → — | — | 0 → 0 | — → — | — |
| reference | by_band | 600-750 km | August 2024 held out | 144 | cross | 0 → 0 | 0 → 0 | — → — | — | 0 → 0 | — → — | — |
| reference | by_band | 600-750 km | August 2024 held out | 168 | radial | 0 → 0 | 0 → 0 | — → — | — | 0 → 0 | — → — | — |
| reference | by_band | 600-750 km | August 2024 held out | 168 | in_track | 0 → 0 | 0 → 0 | — → — | — | 0 → 0 | — → — | — |
| reference | by_band | 600-750 km | August 2024 held out | 168 | cross | 0 → 0 | 0 → 0 | — → — | — | 0 → 0 | — → — | — |
| reference | by_band | 600-750 km | October 2024 held out | 6 | radial | 42 → 42 | 18 → 18 | 42.9% → 42.9% | 0.000000 | 25 → 25 | 59.5% → 59.5% | 0.000000 |
| reference | by_band | 600-750 km | October 2024 held out | 6 | in_track | 42 → 42 | 17 → 17 | 40.5% → 40.5% | 0.000000 | 31 → 31 | 73.8% → 73.8% | 0.000000 |
| reference | by_band | 600-750 km | October 2024 held out | 6 | cross | 42 → 42 | 1 → 1 | 2.4% → 2.4% | 0.000000 | 5 → 5 | 11.9% → 11.9% | 0.000000 |
| reference | by_band | 600-750 km | October 2024 held out | 12 | radial | 41 → 41 | 15 → 15 | 36.6% → 36.6% | 0.000000 | 28 → 28 | 68.3% → 68.3% | 0.000000 |
| reference | by_band | 600-750 km | October 2024 held out | 12 | in_track | 41 → 41 | 22 → 22 | 53.7% → 53.7% | 0.000000 | 29 → 29 | 70.7% → 70.7% | 0.000000 |
| reference | by_band | 600-750 km | October 2024 held out | 12 | cross | 41 → 41 | 2 → 2 | 4.9% → 4.9% | 0.000000 | 4 → 4 | 9.8% → 9.8% | 0.000000 |
| reference | by_band | 600-750 km | October 2024 held out | 24 | radial | 39 → 39 | 10 → 10 | 25.6% → 25.6% | 0.000000 | 22 → 22 | 56.4% → 56.4% | 0.000000 |
| reference | by_band | 600-750 km | October 2024 held out | 24 | in_track | 39 → 39 | 29 → 29 | 74.4% → 74.4% | 0.000000 | 33 → 33 | 84.6% → 84.6% | 0.000000 |
| reference | by_band | 600-750 km | October 2024 held out | 24 | cross | 39 → 39 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 3 → 3 | 7.7% → 7.7% | 0.000000 |
| reference | by_band | 600-750 km | October 2024 held out | 36 | radial | 37 → 37 | 23 → 23 | 62.2% → 62.2% | 0.000000 | 36 → 36 | 97.3% → 97.3% | 0.000000 |
| reference | by_band | 600-750 km | October 2024 held out | 36 | in_track | 37 → 37 | 27 → 27 | 73.0% → 73.0% | 0.000000 | 32 → 32 | 86.5% → 86.5% | 0.000000 |
| reference | by_band | 600-750 km | October 2024 held out | 36 | cross | 37 → 37 | 11 → 11 | 29.7% → 29.7% | 0.000000 | 14 → 14 | 37.8% → 37.8% | 0.000000 |
| reference | by_band | 600-750 km | October 2024 held out | 48 | radial | 33 → 33 | 21 → 21 | 63.6% → 63.6% | 0.000000 | 30 → 30 | 90.9% → 90.9% | 0.000000 |
| reference | by_band | 600-750 km | October 2024 held out | 48 | in_track | 33 → 33 | 25 → 25 | 75.8% → 75.8% | 0.000000 | 30 → 30 | 90.9% → 90.9% | 0.000000 |
| reference | by_band | 600-750 km | October 2024 held out | 48 | cross | 33 → 33 | 3 → 3 | 9.1% → 9.1% | 0.000000 | 15 → 15 | 45.5% → 45.5% | 0.000000 |
| reference | by_band | 600-750 km | October 2024 held out | 72 | radial | 27 → 27 | 22 → 22 | 81.5% → 81.5% | 0.000000 | 27 → 27 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 600-750 km | October 2024 held out | 72 | in_track | 27 → 27 | 25 → 25 | 92.6% → 92.6% | 0.000000 | 25 → 25 | 92.6% → 92.6% | 0.000000 |
| reference | by_band | 600-750 km | October 2024 held out | 72 | cross | 27 → 27 | 4 → 4 | 14.8% → 14.8% | 0.000000 | 8 → 8 | 29.6% → 29.6% | 0.000000 |
| reference | by_band | 600-750 km | October 2024 held out | 96 | radial | 22 → 22 | 15 → 15 | 68.2% → 68.2% | 0.000000 | 22 → 22 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 600-750 km | October 2024 held out | 96 | in_track | 22 → 22 | 18 → 18 | 81.8% → 81.8% | 0.000000 | 21 → 21 | 95.5% → 95.5% | 0.000000 |
| reference | by_band | 600-750 km | October 2024 held out | 96 | cross | 22 → 22 | 6 → 6 | 27.3% → 27.3% | 0.000000 | 16 → 16 | 72.7% → 72.7% | 0.000000 |
| reference | by_band | 600-750 km | October 2024 held out | 120 | radial | 18 → 18 | 7 → 7 | 38.9% → 38.9% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 600-750 km | October 2024 held out | 120 | in_track | 18 → 18 | 14 → 14 | 77.8% → 77.8% | 0.000000 | 17 → 17 | 94.4% → 94.4% | 0.000000 |
| reference | by_band | 600-750 km | October 2024 held out | 120 | cross | 18 → 18 | 4 → 4 | 22.2% → 22.2% | 0.000000 | 12 → 12 | 66.7% → 66.7% | 0.000000 |
| reference | by_band | 600-750 km | October 2024 held out | 144 | radial | 13 → 13 | 12 → 12 | 92.3% → 92.3% | 0.000000 | 13 → 13 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 600-750 km | October 2024 held out | 144 | in_track | 13 → 13 | 12 → 12 | 92.3% → 92.3% | 0.000000 | 13 → 13 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 600-750 km | October 2024 held out | 144 | cross | 13 → 13 | 4 → 4 | 30.8% → 30.8% | 0.000000 | 8 → 8 | 61.5% → 61.5% | 0.000000 |
| reference | by_band | 600-750 km | October 2024 held out | 168 | radial | 8 → 8 | 7 → 7 | 87.5% → 87.5% | 0.000000 | 8 → 8 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 600-750 km | October 2024 held out | 168 | in_track | 8 → 8 | 8 → 8 | 100.0% → 100.0% | 0.000000 | 8 → 8 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 600-750 km | October 2024 held out | 168 | cross | 8 → 8 | 1 → 1 | 12.5% → 12.5% | 0.000000 | 2 → 2 | 25.0% → 25.0% | 0.000000 |
| reference | by_band | 600-750 km | April 2024 control | 6 | radial | 45 → 45 | 15 → 15 | 33.3% → 33.3% | 0.000000 | 26 → 26 | 57.8% → 57.8% | 0.000000 |
| reference | by_band | 600-750 km | April 2024 control | 6 | in_track | 45 → 45 | 27 → 27 | 60.0% → 60.0% | 0.000000 | 41 → 41 | 91.1% → 91.1% | 0.000000 |
| reference | by_band | 600-750 km | April 2024 control | 6 | cross | 45 → 45 | 2 → 2 | 4.4% → 4.4% | 0.000000 | 4 → 4 | 8.9% → 8.9% | 0.000000 |
| reference | by_band | 600-750 km | April 2024 control | 12 | radial | 45 → 45 | 16 → 16 | 35.6% → 35.6% | 0.000000 | 32 → 32 | 71.1% → 71.1% | 0.000000 |
| reference | by_band | 600-750 km | April 2024 control | 12 | in_track | 45 → 45 | 36 → 36 | 80.0% → 80.0% | 0.000000 | 44 → 44 | 97.8% → 97.8% | 0.000000 |
| reference | by_band | 600-750 km | April 2024 control | 12 | cross | 45 → 45 | 3 → 3 | 6.7% → 6.7% | 0.000000 | 4 → 4 | 8.9% → 8.9% | 0.000000 |
| reference | by_band | 600-750 km | April 2024 control | 24 | radial | 44 → 44 | 11 → 11 | 25.0% → 25.0% | 0.000000 | 26 → 26 | 59.1% → 59.1% | 0.000000 |
| reference | by_band | 600-750 km | April 2024 control | 24 | in_track | 44 → 44 | 36 → 36 | 81.8% → 81.8% | 0.000000 | 44 → 44 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 600-750 km | April 2024 control | 24 | cross | 44 → 44 | 4 → 4 | 9.1% → 9.1% | 0.000000 | 8 → 8 | 18.2% → 18.2% | 0.000000 |
| reference | by_band | 600-750 km | April 2024 control | 36 | radial | 42 → 42 | 26 → 26 | 61.9% → 61.9% | 0.000000 | 41 → 41 | 97.6% → 97.6% | 0.000000 |
| reference | by_band | 600-750 km | April 2024 control | 36 | in_track | 42 → 42 | 37 → 37 | 88.1% → 88.1% | 0.000000 | 40 → 40 | 95.2% → 95.2% | 0.000000 |
| reference | by_band | 600-750 km | April 2024 control | 36 | cross | 42 → 42 | 9 → 9 | 21.4% → 21.4% | 0.000000 | 20 → 20 | 47.6% → 47.6% | 0.000000 |
| reference | by_band | 600-750 km | April 2024 control | 48 | radial | 41 → 41 | 20 → 20 | 48.8% → 48.8% | 0.000000 | 40 → 40 | 97.6% → 97.6% | 0.000000 |
| reference | by_band | 600-750 km | April 2024 control | 48 | in_track | 41 → 41 | 36 → 36 | 87.8% → 87.8% | 0.000000 | 38 → 38 | 92.7% → 92.7% | 0.000000 |
| reference | by_band | 600-750 km | April 2024 control | 48 | cross | 41 → 41 | 11 → 11 | 26.8% → 26.8% | 0.000000 | 15 → 15 | 36.6% → 36.6% | 0.000000 |
| reference | by_band | 600-750 km | April 2024 control | 72 | radial | 38 → 38 | 35 → 35 | 92.1% → 92.1% | 0.000000 | 38 → 38 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 600-750 km | April 2024 control | 72 | in_track | 38 → 38 | 33 → 33 | 86.8% → 86.8% | 0.000000 | 36 → 36 | 94.7% → 94.7% | 0.000000 |
| reference | by_band | 600-750 km | April 2024 control | 72 | cross | 38 → 38 | 8 → 8 | 21.1% → 21.1% | 0.000000 | 18 → 18 | 47.4% → 47.4% | 0.000000 |
| reference | by_band | 600-750 km | April 2024 control | 96 | radial | 36 → 36 | 27 → 27 | 75.0% → 75.0% | 0.000000 | 36 → 36 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 600-750 km | April 2024 control | 96 | in_track | 36 → 36 | 29 → 29 | 80.6% → 80.6% | 0.000000 | 33 → 33 | 91.7% → 91.7% | 0.000000 |
| reference | by_band | 600-750 km | April 2024 control | 96 | cross | 36 → 36 | 20 → 20 | 55.6% → 55.6% | 0.000000 | 28 → 28 | 77.8% → 77.8% | 0.000000 |
| reference | by_band | 600-750 km | April 2024 control | 120 | radial | 35 → 35 | 12 → 12 | 34.3% → 34.3% | 0.000000 | 35 → 35 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 600-750 km | April 2024 control | 120 | in_track | 35 → 35 | 28 → 28 | 80.0% → 80.0% | 0.000000 | 33 → 33 | 94.3% → 94.3% | 0.000000 |
| reference | by_band | 600-750 km | April 2024 control | 120 | cross | 35 → 35 | 15 → 15 | 42.9% → 42.9% | 0.000000 | 28 → 28 | 80.0% → 80.0% | 0.000000 |
| reference | by_band | 600-750 km | April 2024 control | 144 | radial | 35 → 35 | 22 → 22 | 62.9% → 62.9% | 0.000000 | 35 → 35 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 600-750 km | April 2024 control | 144 | in_track | 35 → 35 | 27 → 27 | 77.1% → 77.1% | 0.000000 | 32 → 32 | 91.4% → 91.4% | 0.000000 |
| reference | by_band | 600-750 km | April 2024 control | 144 | cross | 35 → 35 | 7 → 7 | 20.0% → 20.0% | 0.000000 | 27 → 27 | 77.1% → 77.1% | 0.000000 |
| reference | by_band | 600-750 km | April 2024 control | 168 | radial | 35 → 35 | 21 → 21 | 60.0% → 60.0% | 0.000000 | 35 → 35 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 600-750 km | April 2024 control | 168 | in_track | 35 → 35 | 25 → 25 | 71.4% → 71.4% | 0.000000 | 31 → 31 | 88.6% → 88.6% | 0.000000 |
| reference | by_band | 600-750 km | April 2024 control | 168 | cross | 35 → 35 | 5 → 5 | 14.3% → 14.3% | 0.000000 | 28 → 28 | 80.0% → 80.0% | 0.000000 |
| reference | by_band | 600-750 km | May 2024 | 6 | radial | 41 → 41 | 14 → 14 | 34.1% → 34.1% | 0.000000 | 23 → 23 | 56.1% → 56.1% | 0.000000 |
| reference | by_band | 600-750 km | May 2024 | 6 | in_track | 41 → 41 | 17 → 17 | 41.5% → 41.5% | 0.000000 | 34 → 34 | 82.9% → 82.9% | 0.000000 |
| reference | by_band | 600-750 km | May 2024 | 6 | cross | 41 → 41 | 2 → 2 | 4.9% → 4.9% | 0.000000 | 4 → 4 | 9.8% → 9.8% | 0.000000 |
| reference | by_band | 600-750 km | May 2024 | 12 | radial | 39 → 39 | 8 → 8 | 20.5% → 20.5% | 0.000000 | 27 → 27 | 69.2% → 69.2% | 0.000000 |
| reference | by_band | 600-750 km | May 2024 | 12 | in_track | 39 → 39 | 16 → 16 | 41.0% → 41.0% | 0.000000 | 34 → 34 | 87.2% → 87.2% | 0.000000 |
| reference | by_band | 600-750 km | May 2024 | 12 | cross | 39 → 39 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 1 → 1 | 2.6% → 2.6% | 0.000000 |
| reference | by_band | 600-750 km | May 2024 | 24 | radial | 34 → 34 | 12 → 12 | 35.3% → 35.3% | 0.000000 | 22 → 22 | 64.7% → 64.7% | 0.000000 |
| reference | by_band | 600-750 km | May 2024 | 24 | in_track | 34 → 34 | 28 → 28 | 82.4% → 82.4% | 0.000000 | 34 → 34 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 600-750 km | May 2024 | 24 | cross | 34 → 34 | 1 → 1 | 2.9% → 2.9% | 0.000000 | 4 → 4 | 11.8% → 11.8% | 0.000000 |
| reference | by_band | 600-750 km | May 2024 | 36 | radial | 32 → 32 | 21 → 21 | 65.6% → 65.6% | 0.000000 | 32 → 32 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 600-750 km | May 2024 | 36 | in_track | 32 → 32 | 31 → 31 | 96.9% → 96.9% | 0.000000 | 32 → 32 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 600-750 km | May 2024 | 36 | cross | 32 → 32 | 10 → 10 | 31.2% → 31.2% | 0.000000 | 12 → 12 | 37.5% → 37.5% | 0.000000 |
| reference | by_band | 600-750 km | May 2024 | 48 | radial | 29 → 29 | 19 → 19 | 65.5% → 65.5% | 0.000000 | 28 → 28 | 96.6% → 96.6% | 0.000000 |
| reference | by_band | 600-750 km | May 2024 | 48 | in_track | 29 → 29 | 29 → 29 | 100.0% → 100.0% | 0.000000 | 29 → 29 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 600-750 km | May 2024 | 48 | cross | 29 → 29 | 6 → 6 | 20.7% → 20.7% | 0.000000 | 7 → 7 | 24.1% → 24.1% | 0.000000 |
| reference | by_band | 600-750 km | May 2024 | 72 | radial | 24 → 24 | 23 → 23 | 95.8% → 95.8% | 0.000000 | 24 → 24 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 600-750 km | May 2024 | 72 | in_track | 24 → 24 | 24 → 24 | 100.0% → 100.0% | 0.000000 | 24 → 24 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 600-750 km | May 2024 | 72 | cross | 24 → 24 | 3 → 3 | 12.5% → 12.5% | 0.000000 | 9 → 9 | 37.5% → 37.5% | 0.000000 |
| reference | by_band | 600-750 km | May 2024 | 96 | radial | 20 → 20 | 18 → 18 | 90.0% → 90.0% | 0.000000 | 20 → 20 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 600-750 km | May 2024 | 96 | in_track | 20 → 20 | 20 → 20 | 100.0% → 100.0% | 0.000000 | 20 → 20 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 600-750 km | May 2024 | 96 | cross | 20 → 20 | 6 → 6 | 30.0% → 30.0% | 0.000000 | 11 → 11 | 55.0% → 55.0% | 0.000000 |
| reference | by_band | 600-750 km | May 2024 | 120 | radial | 15 → 15 | 13 → 13 | 86.7% → 86.7% | 0.000000 | 15 → 15 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 600-750 km | May 2024 | 120 | in_track | 15 → 15 | 15 → 15 | 100.0% → 100.0% | 0.000000 | 15 → 15 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 600-750 km | May 2024 | 120 | cross | 15 → 15 | 4 → 4 | 26.7% → 26.7% | 0.000000 | 9 → 9 | 60.0% → 60.0% | 0.000000 |
| reference | by_band | 600-750 km | May 2024 | 144 | radial | 12 → 12 | 12 → 12 | 100.0% → 100.0% | 0.000000 | 12 → 12 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 600-750 km | May 2024 | 144 | in_track | 12 → 12 | 12 → 12 | 100.0% → 100.0% | 0.000000 | 12 → 12 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 600-750 km | May 2024 | 144 | cross | 12 → 12 | 3 → 3 | 25.0% → 25.0% | 0.000000 | 6 → 6 | 50.0% → 50.0% | 0.000000 |
| reference | by_band | 600-750 km | May 2024 | 168 | radial | 12 → 12 | 12 → 12 | 100.0% → 100.0% | 0.000000 | 12 → 12 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 600-750 km | May 2024 | 168 | in_track | 12 → 12 | 12 → 12 | 100.0% → 100.0% | 0.000000 | 12 → 12 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 600-750 km | May 2024 | 168 | cross | 12 → 12 | 2 → 2 | 16.7% → 16.7% | 0.000000 | 6 → 6 | 50.0% → 50.0% | 0.000000 |
| reference | by_band | 750-850 km | August 2024 held out | 6 | radial | 60 → 60 | 5 → 5 | 8.3% → 8.3% | 0.000000 | 14 → 14 | 23.3% → 23.3% | 0.000000 |
| reference | by_band | 750-850 km | August 2024 held out | 6 | in_track | 60 → 60 | 15 → 15 | 25.0% → 25.0% | 0.000000 | 24 → 24 | 40.0% → 40.0% | 0.000000 |
| reference | by_band | 750-850 km | August 2024 held out | 6 | cross | 60 → 60 | 6 → 6 | 10.0% → 10.0% | 0.000000 | 13 → 13 | 21.7% → 21.7% | 0.000000 |
| reference | by_band | 750-850 km | August 2024 held out | 12 | radial | 58 → 58 | 7 → 7 | 12.1% → 12.1% | 0.000000 | 10 → 10 | 17.2% → 17.2% | 0.000000 |
| reference | by_band | 750-850 km | August 2024 held out | 12 | in_track | 58 → 58 | 21 → 21 | 36.2% → 36.2% | 0.000000 | 33 → 33 | 56.9% → 56.9% | 0.000000 |
| reference | by_band | 750-850 km | August 2024 held out | 12 | cross | 58 → 58 | 5 → 5 | 8.6% → 8.6% | 0.000000 | 12 → 12 | 20.7% → 20.7% | 0.000000 |
| reference | by_band | 750-850 km | August 2024 held out | 24 | radial | 53 → 53 | 35 → 35 | 66.0% → 66.0% | 0.000000 | 44 → 44 | 83.0% → 83.0% | 0.000000 |
| reference | by_band | 750-850 km | August 2024 held out | 24 | in_track | 53 → 53 | 27 → 27 | 50.9% → 50.9% | 0.000000 | 38 → 38 | 71.7% → 71.7% | 0.000000 |
| reference | by_band | 750-850 km | August 2024 held out | 24 | cross | 53 → 53 | 3 → 3 | 5.7% → 5.7% | 0.000000 | 8 → 8 | 15.1% → 15.1% | 0.000000 |
| reference | by_band | 750-850 km | August 2024 held out | 36 | radial | 50 → 50 | 28 → 28 | 56.0% → 56.0% | 0.000000 | 34 → 34 | 68.0% → 68.0% | 0.000000 |
| reference | by_band | 750-850 km | August 2024 held out | 36 | in_track | 50 → 50 | 34 → 34 | 68.0% → 68.0% | 0.000000 | 39 → 39 | 78.0% → 78.0% | 0.000000 |
| reference | by_band | 750-850 km | August 2024 held out | 36 | cross | 50 → 50 | 16 → 16 | 32.0% → 32.0% | 0.000000 | 32 → 32 | 64.0% → 64.0% | 0.000000 |
| reference | by_band | 750-850 km | August 2024 held out | 48 | radial | 46 → 46 | 19 → 19 | 41.3% → 41.3% | 0.000000 | 39 → 39 | 84.8% → 84.8% | 0.000000 |
| reference | by_band | 750-850 km | August 2024 held out | 48 | in_track | 46 → 46 | 33 → 33 | 71.7% → 71.7% | 0.000000 | 33 → 33 | 71.7% → 71.7% | 0.000000 |
| reference | by_band | 750-850 km | August 2024 held out | 48 | cross | 46 → 46 | 18 → 18 | 39.1% → 39.1% | 0.000000 | 24 → 24 | 52.2% → 52.2% | 0.000000 |
| reference | by_band | 750-850 km | August 2024 held out | 72 | radial | 40 → 40 | 31 → 31 | 77.5% → 77.5% | 0.000000 | 40 → 40 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 750-850 km | August 2024 held out | 72 | in_track | 40 → 40 | 25 → 25 | 62.5% → 62.5% | 0.000000 | 29 → 29 | 72.5% → 72.5% | 0.000000 |
| reference | by_band | 750-850 km | August 2024 held out | 72 | cross | 40 → 40 | 10 → 10 | 25.0% → 25.0% | 0.000000 | 23 → 23 | 57.5% → 57.5% | 0.000000 |
| reference | by_band | 750-850 km | August 2024 held out | 96 | radial | 34 → 34 | 29 → 29 | 85.3% → 85.3% | 0.000000 | 34 → 34 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 750-850 km | August 2024 held out | 96 | in_track | 34 → 34 | 20 → 20 | 58.8% → 58.8% | 0.000000 | 26 → 26 | 76.5% → 76.5% | 0.000000 |
| reference | by_band | 750-850 km | August 2024 held out | 96 | cross | 34 → 34 | 14 → 14 | 41.2% → 41.2% | 0.000000 | 17 → 17 | 50.0% → 50.0% | 0.000000 |
| reference | by_band | 750-850 km | August 2024 held out | 120 | radial | 25 → 25 | 25 → 25 | 100.0% → 100.0% | 0.000000 | 25 → 25 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 750-850 km | August 2024 held out | 120 | in_track | 25 → 25 | 8 → 8 | 32.0% → 32.0% | 0.000000 | 10 → 10 | 40.0% → 40.0% | 0.000000 |
| reference | by_band | 750-850 km | August 2024 held out | 120 | cross | 25 → 25 | 7 → 7 | 28.0% → 28.0% | 0.000000 | 10 → 10 | 40.0% → 40.0% | 0.000000 |
| reference | by_band | 750-850 km | August 2024 held out | 144 | radial | 19 → 19 | 14 → 14 | 73.7% → 73.7% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 750-850 km | August 2024 held out | 144 | in_track | 19 → 19 | 2 → 2 | 10.5% → 10.5% | 0.000000 | 7 → 7 | 36.8% → 36.8% | 0.000000 |
| reference | by_band | 750-850 km | August 2024 held out | 144 | cross | 19 → 19 | 11 → 11 | 57.9% → 57.9% | 0.000000 | 14 → 14 | 73.7% → 73.7% | 0.000000 |
| reference | by_band | 750-850 km | August 2024 held out | 168 | radial | 18 → 18 | 18 → 18 | 100.0% → 100.0% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 750-850 km | August 2024 held out | 168 | in_track | 18 → 18 | 4 → 4 | 22.2% → 22.2% | 0.000000 | 7 → 7 | 38.9% → 38.9% | 0.000000 |
| reference | by_band | 750-850 km | August 2024 held out | 168 | cross | 18 → 18 | 1 → 1 | 5.6% → 5.6% | 0.000000 | 3 → 3 | 16.7% → 16.7% | 0.000000 |
| reference | by_band | 750-850 km | October 2024 held out | 6 | radial | 51 → 51 | 3 → 4 | 5.9% → 7.8% | 1.960784 | 11 → 11 | 21.6% → 21.6% | 0.000000 |
| reference | by_band | 750-850 km | October 2024 held out | 6 | in_track | 51 → 51 | 15 → 15 | 29.4% → 29.4% | 0.000000 | 33 → 33 | 64.7% → 64.7% | 0.000000 |
| reference | by_band | 750-850 km | October 2024 held out | 6 | cross | 51 → 51 | 5 → 5 | 9.8% → 9.8% | 0.000000 | 10 → 10 | 19.6% → 19.6% | 0.000000 |
| reference | by_band | 750-850 km | October 2024 held out | 12 | radial | 50 → 50 | 11 → 11 | 22.0% → 22.0% | 0.000000 | 17 → 17 | 34.0% → 34.0% | 0.000000 |
| reference | by_band | 750-850 km | October 2024 held out | 12 | in_track | 50 → 50 | 27 → 27 | 54.0% → 54.0% | 0.000000 | 35 → 35 | 70.0% → 70.0% | 0.000000 |
| reference | by_band | 750-850 km | October 2024 held out | 12 | cross | 50 → 50 | 5 → 5 | 10.0% → 10.0% | 0.000000 | 6 → 6 | 12.0% → 12.0% | 0.000000 |
| reference | by_band | 750-850 km | October 2024 held out | 24 | radial | 50 → 50 | 39 → 39 | 78.0% → 78.0% | 0.000000 | 46 → 46 | 92.0% → 92.0% | 0.000000 |
| reference | by_band | 750-850 km | October 2024 held out | 24 | in_track | 50 → 50 | 35 → 35 | 70.0% → 70.0% | 0.000000 | 40 → 40 | 80.0% → 80.0% | 0.000000 |
| reference | by_band | 750-850 km | October 2024 held out | 24 | cross | 50 → 50 | 3 → 3 | 6.0% → 6.0% | 0.000000 | 6 → 6 | 12.0% → 12.0% | 0.000000 |
| reference | by_band | 750-850 km | October 2024 held out | 36 | radial | 48 → 48 | 20 → 20 | 41.7% → 41.7% | 0.000000 | 23 → 23 | 47.9% → 47.9% | 0.000000 |
| reference | by_band | 750-850 km | October 2024 held out | 36 | in_track | 48 → 48 | 33 → 33 | 68.8% → 68.8% | 0.000000 | 41 → 41 | 85.4% → 85.4% | 0.000000 |
| reference | by_band | 750-850 km | October 2024 held out | 36 | cross | 48 → 48 | 17 → 17 | 35.4% → 35.4% | 0.000000 | 35 → 35 | 72.9% → 72.9% | 0.000000 |
| reference | by_band | 750-850 km | October 2024 held out | 48 | radial | 47 → 47 | 19 → 19 | 40.4% → 40.4% | 0.000000 | 43 → 43 | 91.5% → 91.5% | 0.000000 |
| reference | by_band | 750-850 km | October 2024 held out | 48 | in_track | 47 → 47 | 35 → 35 | 74.5% → 74.5% | 0.000000 | 41 → 41 | 87.2% → 87.2% | 0.000000 |
| reference | by_band | 750-850 km | October 2024 held out | 48 | cross | 47 → 47 | 24 → 24 | 51.1% → 51.1% | 0.000000 | 34 → 34 | 72.3% → 72.3% | 0.000000 |
| reference | by_band | 750-850 km | October 2024 held out | 72 | radial | 45 → 45 | 39 → 39 | 86.7% → 86.7% | 0.000000 | 43 → 43 | 95.6% → 95.6% | 0.000000 |
| reference | by_band | 750-850 km | October 2024 held out | 72 | in_track | 45 → 45 | 34 → 34 | 75.6% → 75.6% | 0.000000 | 40 → 40 | 88.9% → 88.9% | 0.000000 |
| reference | by_band | 750-850 km | October 2024 held out | 72 | cross | 45 → 45 | 16 → 16 | 35.6% → 35.6% | 0.000000 | 29 → 29 | 64.4% → 64.4% | 0.000000 |
| reference | by_band | 750-850 km | October 2024 held out | 96 | radial | 43 → 43 | 29 → 29 | 67.4% → 67.4% | 0.000000 | 42 → 42 | 97.7% → 97.7% | 0.000000 |
| reference | by_band | 750-850 km | October 2024 held out | 96 | in_track | 43 → 43 | 32 → 32 | 74.4% → 74.4% | 0.000000 | 37 → 37 | 86.0% → 86.0% | 0.000000 |
| reference | by_band | 750-850 km | October 2024 held out | 96 | cross | 43 → 43 | 30 → 30 | 69.8% → 69.8% | 0.000000 | 37 → 37 | 86.0% → 86.0% | 0.000000 |
| reference | by_band | 750-850 km | October 2024 held out | 120 | radial | 41 → 41 | 39 → 39 | 95.1% → 95.1% | 0.000000 | 40 → 41 | 97.6% → 100.0% | 2.439024 |
| reference | by_band | 750-850 km | October 2024 held out | 120 | in_track | 41 → 41 | 28 → 28 | 68.3% → 68.3% | 0.000000 | 35 → 35 | 85.4% → 85.4% | 0.000000 |
| reference | by_band | 750-850 km | October 2024 held out | 120 | cross | 41 → 41 | 23 → 23 | 56.1% → 56.1% | 0.000000 | 33 → 33 | 80.5% → 80.5% | 0.000000 |
| reference | by_band | 750-850 km | October 2024 held out | 144 | radial | 38 → 38 | 26 → 26 | 68.4% → 68.4% | 0.000000 | 36 → 37 | 94.7% → 97.4% | 2.631579 |
| reference | by_band | 750-850 km | October 2024 held out | 144 | in_track | 38 → 38 | 25 → 25 | 65.8% → 65.8% | 0.000000 | 31 → 31 | 81.6% → 81.6% | 0.000000 |
| reference | by_band | 750-850 km | October 2024 held out | 144 | cross | 38 → 38 | 33 → 33 | 86.8% → 86.8% | 0.000000 | 38 → 38 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 750-850 km | October 2024 held out | 168 | radial | 33 → 33 | 32 → 32 | 97.0% → 97.0% | 0.000000 | 32 → 32 | 97.0% → 97.0% | 0.000000 |
| reference | by_band | 750-850 km | October 2024 held out | 168 | in_track | 33 → 33 | 24 → 24 | 72.7% → 72.7% | 0.000000 | 25 → 25 | 75.8% → 75.8% | 0.000000 |
| reference | by_band | 750-850 km | October 2024 held out | 168 | cross | 33 → 33 | 23 → 23 | 69.7% → 69.7% | 0.000000 | 25 → 25 | 75.8% → 75.8% | 0.000000 |
| reference | by_band | 750-850 km | April 2024 control | 6 | radial | 57 → 57 | 3 → 3 | 5.3% → 5.3% | 0.000000 | 10 → 10 | 17.5% → 17.5% | 0.000000 |
| reference | by_band | 750-850 km | April 2024 control | 6 | in_track | 57 → 57 | 13 → 13 | 22.8% → 22.8% | 0.000000 | 29 → 29 | 50.9% → 50.9% | 0.000000 |
| reference | by_band | 750-850 km | April 2024 control | 6 | cross | 57 → 57 | 17 → 17 | 29.8% → 29.8% | 0.000000 | 27 → 27 | 47.4% → 47.4% | 0.000000 |
| reference | by_band | 750-850 km | April 2024 control | 12 | radial | 56 → 56 | 6 → 6 | 10.7% → 10.7% | 0.000000 | 11 → 11 | 19.6% → 19.6% | 0.000000 |
| reference | by_band | 750-850 km | April 2024 control | 12 | in_track | 56 → 56 | 31 → 31 | 55.4% → 55.4% | 0.000000 | 46 → 46 | 82.1% → 82.1% | 0.000000 |
| reference | by_band | 750-850 km | April 2024 control | 12 | cross | 56 → 56 | 6 → 6 | 10.7% → 10.7% | 0.000000 | 13 → 13 | 23.2% → 23.2% | 0.000000 |
| reference | by_band | 750-850 km | April 2024 control | 24 | radial | 52 → 52 | 33 → 33 | 63.5% → 63.5% | 0.000000 | 48 → 48 | 92.3% → 92.3% | 0.000000 |
| reference | by_band | 750-850 km | April 2024 control | 24 | in_track | 52 → 52 | 37 → 37 | 71.2% → 71.2% | 0.000000 | 46 → 46 | 88.5% → 88.5% | 0.000000 |
| reference | by_band | 750-850 km | April 2024 control | 24 | cross | 52 → 52 | 9 → 9 | 17.3% → 17.3% | 0.000000 | 21 → 21 | 40.4% → 40.4% | 0.000000 |
| reference | by_band | 750-850 km | April 2024 control | 36 | radial | 49 → 49 | 27 → 27 | 55.1% → 55.1% | 0.000000 | 30 → 30 | 61.2% → 61.2% | 0.000000 |
| reference | by_band | 750-850 km | April 2024 control | 36 | in_track | 49 → 49 | 38 → 38 | 77.6% → 77.6% | 0.000000 | 47 → 47 | 95.9% → 95.9% | 0.000000 |
| reference | by_band | 750-850 km | April 2024 control | 36 | cross | 49 → 49 | 20 → 20 | 40.8% → 40.8% | 0.000000 | 41 → 41 | 83.7% → 83.7% | 0.000000 |
| reference | by_band | 750-850 km | April 2024 control | 48 | radial | 46 → 46 | 18 → 18 | 39.1% → 39.1% | 0.000000 | 40 → 40 | 87.0% → 87.0% | 0.000000 |
| reference | by_band | 750-850 km | April 2024 control | 48 | in_track | 46 → 46 | 38 → 38 | 82.6% → 82.6% | 0.000000 | 44 → 44 | 95.7% → 95.7% | 0.000000 |
| reference | by_band | 750-850 km | April 2024 control | 48 | cross | 46 → 46 | 25 → 25 | 54.3% → 54.3% | 0.000000 | 34 → 34 | 73.9% → 73.9% | 0.000000 |
| reference | by_band | 750-850 km | April 2024 control | 72 | radial | 40 → 40 | 30 → 30 | 75.0% → 75.0% | 0.000000 | 40 → 40 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 750-850 km | April 2024 control | 72 | in_track | 40 → 40 | 37 → 37 | 92.5% → 92.5% | 0.000000 | 40 → 40 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 750-850 km | April 2024 control | 72 | cross | 40 → 40 | 24 → 24 | 60.0% → 60.0% | 0.000000 | 39 → 39 | 97.5% → 97.5% | 0.000000 |
| reference | by_band | 750-850 km | April 2024 control | 96 | radial | 33 → 33 | 23 → 23 | 69.7% → 69.7% | 0.000000 | 33 → 33 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 750-850 km | April 2024 control | 96 | in_track | 33 → 33 | 32 → 32 | 97.0% → 97.0% | 0.000000 | 33 → 33 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 750-850 km | April 2024 control | 96 | cross | 33 → 33 | 20 → 20 | 60.6% → 60.6% | 0.000000 | 28 → 28 | 84.8% → 84.8% | 0.000000 |
| reference | by_band | 750-850 km | April 2024 control | 120 | radial | 30 → 30 | 28 → 28 | 93.3% → 93.3% | 0.000000 | 30 → 30 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 750-850 km | April 2024 control | 120 | in_track | 30 → 30 | 27 → 27 | 90.0% → 90.0% | 0.000000 | 30 → 30 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 750-850 km | April 2024 control | 120 | cross | 30 → 30 | 20 → 20 | 66.7% → 66.7% | 0.000000 | 27 → 27 | 90.0% → 90.0% | 0.000000 |
| reference | by_band | 750-850 km | April 2024 control | 144 | radial | 29 → 29 | 17 → 17 | 58.6% → 58.6% | 0.000000 | 29 → 29 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 750-850 km | April 2024 control | 144 | in_track | 29 → 29 | 25 → 25 | 86.2% → 86.2% | 0.000000 | 29 → 29 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 750-850 km | April 2024 control | 144 | cross | 29 → 29 | 25 → 25 | 86.2% → 86.2% | 0.000000 | 29 → 29 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 750-850 km | April 2024 control | 168 | radial | 29 → 29 | 28 → 28 | 96.6% → 96.6% | 0.000000 | 29 → 29 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 750-850 km | April 2024 control | 168 | in_track | 29 → 29 | 23 → 23 | 79.3% → 79.3% | 0.000000 | 27 → 27 | 93.1% → 93.1% | 0.000000 |
| reference | by_band | 750-850 km | April 2024 control | 168 | cross | 29 → 29 | 25 → 25 | 86.2% → 86.2% | 0.000000 | 29 → 29 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 750-850 km | May 2024 | 6 | radial | 65 → 65 | 6 → 6 | 9.2% → 9.2% | 0.000000 | 18 → 18 | 27.7% → 27.7% | 0.000000 |
| reference | by_band | 750-850 km | May 2024 | 6 | in_track | 65 → 65 | 18 → 18 | 27.7% → 27.7% | 0.000000 | 40 → 40 | 61.5% → 61.5% | 0.000000 |
| reference | by_band | 750-850 km | May 2024 | 6 | cross | 65 → 65 | 6 → 6 | 9.2% → 9.2% | 0.000000 | 16 → 16 | 24.6% → 24.6% | 0.000000 |
| reference | by_band | 750-850 km | May 2024 | 12 | radial | 63 → 63 | 7 → 7 | 11.1% → 11.1% | 0.000000 | 14 → 14 | 22.2% → 22.2% | 0.000000 |
| reference | by_band | 750-850 km | May 2024 | 12 | in_track | 63 → 63 | 37 → 37 | 58.7% → 58.7% | 0.000000 | 44 → 44 | 69.8% → 69.8% | 0.000000 |
| reference | by_band | 750-850 km | May 2024 | 12 | cross | 63 → 63 | 8 → 8 | 12.7% → 12.7% | 0.000000 | 16 → 16 | 25.4% → 25.4% | 0.000000 |
| reference | by_band | 750-850 km | May 2024 | 24 | radial | 61 → 61 | 40 → 40 | 65.6% → 65.6% | 0.000000 | 51 → 51 | 83.6% → 83.6% | 0.000000 |
| reference | by_band | 750-850 km | May 2024 | 24 | in_track | 61 → 61 | 44 → 44 | 72.1% → 72.1% | 0.000000 | 56 → 56 | 91.8% → 91.8% | 0.000000 |
| reference | by_band | 750-850 km | May 2024 | 24 | cross | 61 → 61 | 9 → 9 | 14.8% → 14.8% | 0.000000 | 22 → 22 | 36.1% → 36.1% | 0.000000 |
| reference | by_band | 750-850 km | May 2024 | 36 | radial | 58 → 58 | 30 → 30 | 51.7% → 51.7% | 0.000000 | 35 → 35 | 60.3% → 60.3% | 0.000000 |
| reference | by_band | 750-850 km | May 2024 | 36 | in_track | 58 → 58 | 45 → 45 | 77.6% → 77.6% | 0.000000 | 53 → 53 | 91.4% → 91.4% | 0.000000 |
| reference | by_band | 750-850 km | May 2024 | 36 | cross | 58 → 58 | 22 → 22 | 37.9% → 37.9% | 0.000000 | 36 → 36 | 62.1% → 62.1% | 0.000000 |
| reference | by_band | 750-850 km | May 2024 | 48 | radial | 56 → 56 | 23 → 23 | 41.1% → 41.1% | 0.000000 | 47 → 47 | 83.9% → 83.9% | 0.000000 |
| reference | by_band | 750-850 km | May 2024 | 48 | in_track | 56 → 56 | 46 → 46 | 82.1% → 82.1% | 0.000000 | 53 → 53 | 94.6% → 94.6% | 0.000000 |
| reference | by_band | 750-850 km | May 2024 | 48 | cross | 56 → 56 | 25 → 25 | 44.6% → 44.6% | 0.000000 | 39 → 39 | 69.6% → 69.6% | 0.000000 |
| reference | by_band | 750-850 km | May 2024 | 72 | radial | 53 → 53 | 42 → 42 | 79.2% → 79.2% | 0.000000 | 53 → 53 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 750-850 km | May 2024 | 72 | in_track | 53 → 53 | 45 → 45 | 84.9% → 84.9% | 0.000000 | 49 → 49 | 92.5% → 92.5% | 0.000000 |
| reference | by_band | 750-850 km | May 2024 | 72 | cross | 53 → 53 | 27 → 27 | 50.9% → 50.9% | 0.000000 | 47 → 47 | 88.7% → 88.7% | 0.000000 |
| reference | by_band | 750-850 km | May 2024 | 96 | radial | 46 → 46 | 33 → 33 | 71.7% → 71.7% | 0.000000 | 46 → 46 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 750-850 km | May 2024 | 96 | in_track | 46 → 46 | 35 → 35 | 76.1% → 76.1% | 0.000000 | 43 → 43 | 93.5% → 93.5% | 0.000000 |
| reference | by_band | 750-850 km | May 2024 | 96 | cross | 46 → 46 | 23 → 23 | 50.0% → 50.0% | 0.000000 | 38 → 38 | 82.6% → 82.6% | 0.000000 |
| reference | by_band | 750-850 km | May 2024 | 120 | radial | 40 → 40 | 36 → 36 | 90.0% → 90.0% | 0.000000 | 40 → 40 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 750-850 km | May 2024 | 120 | in_track | 40 → 40 | 27 → 27 | 67.5% → 67.5% | 0.000000 | 32 → 32 | 80.0% → 80.0% | 0.000000 |
| reference | by_band | 750-850 km | May 2024 | 120 | cross | 40 → 40 | 27 → 27 | 67.5% → 67.5% | 0.000000 | 40 → 40 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 750-850 km | May 2024 | 144 | radial | 33 → 33 | 17 → 17 | 51.5% → 51.5% | 0.000000 | 33 → 33 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 750-850 km | May 2024 | 144 | in_track | 33 → 33 | 19 → 19 | 57.6% → 57.6% | 0.000000 | 24 → 24 | 72.7% → 72.7% | 0.000000 |
| reference | by_band | 750-850 km | May 2024 | 144 | cross | 33 → 33 | 25 → 25 | 75.8% → 75.8% | 0.000000 | 33 → 33 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 750-850 km | May 2024 | 168 | radial | 25 → 25 | 25 → 25 | 100.0% → 100.0% | 0.000000 | 25 → 25 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 750-850 km | May 2024 | 168 | in_track | 25 → 25 | 10 → 10 | 40.0% → 40.0% | 0.000000 | 15 → 15 | 60.0% → 60.0% | 0.000000 |
| reference | by_band | 750-850 km | May 2024 | 168 | cross | 25 → 25 | 15 → 15 | 60.0% → 60.0% | 0.000000 | 24 → 24 | 96.0% → 96.0% | 0.000000 |
| reference | by_band | 850-1000 km | August 2024 held out | 6 | radial | 65 → 65 | 3 → 3 | 4.6% → 4.6% | 0.000000 | 6 → 6 | 9.2% → 9.2% | 0.000000 |
| reference | by_band | 850-1000 km | August 2024 held out | 6 | in_track | 65 → 65 | 6 → 6 | 9.2% → 9.2% | 0.000000 | 11 → 11 | 16.9% → 16.9% | 0.000000 |
| reference | by_band | 850-1000 km | August 2024 held out | 6 | cross | 65 → 65 | 18 → 18 | 27.7% → 27.7% | 0.000000 | 37 → 37 | 56.9% → 56.9% | 0.000000 |
| reference | by_band | 850-1000 km | August 2024 held out | 12 | radial | 65 → 65 | 14 → 14 | 21.5% → 21.5% | 0.000000 | 22 → 22 | 33.8% → 33.8% | 0.000000 |
| reference | by_band | 850-1000 km | August 2024 held out | 12 | in_track | 65 → 65 | 9 → 9 | 13.8% → 13.8% | 0.000000 | 23 → 23 | 35.4% → 35.4% | 0.000000 |
| reference | by_band | 850-1000 km | August 2024 held out | 12 | cross | 65 → 65 | 14 → 14 | 21.5% → 21.5% | 0.000000 | 27 → 27 | 41.5% → 41.5% | 0.000000 |
| reference | by_band | 850-1000 km | August 2024 held out | 24 | radial | 65 → 65 | 21 → 21 | 32.3% → 32.3% | 0.000000 | 33 → 33 | 50.8% → 50.8% | 0.000000 |
| reference | by_band | 850-1000 km | August 2024 held out | 24 | in_track | 65 → 65 | 32 → 32 | 49.2% → 49.2% | 0.000000 | 45 → 45 | 69.2% → 69.2% | 0.000000 |
| reference | by_band | 850-1000 km | August 2024 held out | 24 | cross | 65 → 65 | 21 → 21 | 32.3% → 32.3% | 0.000000 | 45 → 45 | 69.2% → 69.2% | 0.000000 |
| reference | by_band | 850-1000 km | August 2024 held out | 36 | radial | 64 → 64 | 40 → 40 | 62.5% → 62.5% | 0.000000 | 51 → 51 | 79.7% → 79.7% | 0.000000 |
| reference | by_band | 850-1000 km | August 2024 held out | 36 | in_track | 64 → 64 | 41 → 41 | 64.1% → 64.1% | 0.000000 | 56 → 56 | 87.5% → 87.5% | 0.000000 |
| reference | by_band | 850-1000 km | August 2024 held out | 36 | cross | 64 → 64 | 31 → 31 | 48.4% → 48.4% | 0.000000 | 50 → 50 | 78.1% → 78.1% | 0.000000 |
| reference | by_band | 850-1000 km | August 2024 held out | 48 | radial | 62 → 62 | 25 → 25 | 40.3% → 40.3% | 0.000000 | 45 → 45 | 72.6% → 72.6% | 0.000000 |
| reference | by_band | 850-1000 km | August 2024 held out | 48 | in_track | 62 → 62 | 51 → 51 | 82.3% → 82.3% | 0.000000 | 60 → 60 | 96.8% → 96.8% | 0.000000 |
| reference | by_band | 850-1000 km | August 2024 held out | 48 | cross | 62 → 62 | 29 → 29 | 46.8% → 46.8% | 0.000000 | 50 → 50 | 80.6% → 80.6% | 0.000000 |
| reference | by_band | 850-1000 km | August 2024 held out | 72 | radial | 57 → 57 | 20 → 20 | 35.1% → 35.1% | 0.000000 | 40 → 40 | 70.2% → 70.2% | 0.000000 |
| reference | by_band | 850-1000 km | August 2024 held out | 72 | in_track | 57 → 57 | 57 → 57 | 100.0% → 100.0% | 0.000000 | 57 → 57 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 850-1000 km | August 2024 held out | 72 | cross | 57 → 57 | 27 → 27 | 47.4% → 47.4% | 0.000000 | 51 → 51 | 89.5% → 89.5% | 0.000000 |
| reference | by_band | 850-1000 km | August 2024 held out | 96 | radial | 53 → 53 | 36 → 36 | 67.9% → 67.9% | 0.000000 | 37 → 37 | 69.8% → 69.8% | 0.000000 |
| reference | by_band | 850-1000 km | August 2024 held out | 96 | in_track | 53 → 53 | 53 → 53 | 100.0% → 100.0% | 0.000000 | 53 → 53 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 850-1000 km | August 2024 held out | 96 | cross | 53 → 53 | 45 → 45 | 84.9% → 84.9% | 0.000000 | 53 → 53 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 850-1000 km | August 2024 held out | 120 | radial | 49 → 49 | 32 → 32 | 65.3% → 65.3% | 0.000000 | 34 → 34 | 69.4% → 69.4% | 0.000000 |
| reference | by_band | 850-1000 km | August 2024 held out | 120 | in_track | 49 → 49 | 49 → 49 | 100.0% → 100.0% | 0.000000 | 49 → 49 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 850-1000 km | August 2024 held out | 120 | cross | 49 → 49 | 31 → 31 | 63.3% → 63.3% | 0.000000 | 49 → 49 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 850-1000 km | August 2024 held out | 144 | radial | 46 → 46 | 21 → 21 | 45.7% → 45.7% | 0.000000 | 30 → 30 | 65.2% → 65.2% | 0.000000 |
| reference | by_band | 850-1000 km | August 2024 held out | 144 | in_track | 46 → 46 | 46 → 46 | 100.0% → 100.0% | 0.000000 | 46 → 46 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 850-1000 km | August 2024 held out | 144 | cross | 46 → 46 | 15 → 15 | 32.6% → 32.6% | 0.000000 | 46 → 46 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 850-1000 km | August 2024 held out | 168 | radial | 39 → 39 | 22 → 22 | 56.4% → 56.4% | 0.000000 | 25 → 25 | 64.1% → 64.1% | 0.000000 |
| reference | by_band | 850-1000 km | August 2024 held out | 168 | in_track | 39 → 39 | 39 → 39 | 100.0% → 100.0% | 0.000000 | 39 → 39 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 850-1000 km | August 2024 held out | 168 | cross | 39 → 39 | 32 → 32 | 82.1% → 82.1% | 0.000000 | 39 → 39 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 850-1000 km | October 2024 held out | 6 | radial | 60 → 60 | 8 → 8 | 13.3% → 13.3% | 0.000000 | 14 → 14 | 23.3% → 23.3% | 0.000000 |
| reference | by_band | 850-1000 km | October 2024 held out | 6 | in_track | 60 → 60 | 8 → 8 | 13.3% → 13.3% | 0.000000 | 19 → 19 | 31.7% → 31.7% | 0.000000 |
| reference | by_band | 850-1000 km | October 2024 held out | 6 | cross | 60 → 60 | 14 → 14 | 23.3% → 23.3% | 0.000000 | 29 → 29 | 48.3% → 48.3% | 0.000000 |
| reference | by_band | 850-1000 km | October 2024 held out | 12 | radial | 59 → 59 | 16 → 16 | 27.1% → 27.1% | 0.000000 | 21 → 21 | 35.6% → 35.6% | 0.000000 |
| reference | by_band | 850-1000 km | October 2024 held out | 12 | in_track | 59 → 59 | 7 → 7 | 11.9% → 11.9% | 0.000000 | 13 → 13 | 22.0% → 22.0% | 0.000000 |
| reference | by_band | 850-1000 km | October 2024 held out | 12 | cross | 59 → 59 | 15 → 15 | 25.4% → 25.4% | 0.000000 | 23 → 23 | 39.0% → 39.0% | 0.000000 |
| reference | by_band | 850-1000 km | October 2024 held out | 24 | radial | 55 → 55 | 19 → 19 | 34.5% → 34.5% | 0.000000 | 29 → 29 | 52.7% → 52.7% | 0.000000 |
| reference | by_band | 850-1000 km | October 2024 held out | 24 | in_track | 55 → 55 | 22 → 22 | 40.0% → 40.0% | 0.000000 | 37 → 37 | 67.3% → 67.3% | 0.000000 |
| reference | by_band | 850-1000 km | October 2024 held out | 24 | cross | 55 → 55 | 17 → 17 | 30.9% → 30.9% | 0.000000 | 30 → 30 | 54.5% → 54.5% | 0.000000 |
| reference | by_band | 850-1000 km | October 2024 held out | 36 | radial | 52 → 52 | 25 → 25 | 48.1% → 48.1% | 0.000000 | 39 → 39 | 75.0% → 75.0% | 0.000000 |
| reference | by_band | 850-1000 km | October 2024 held out | 36 | in_track | 52 → 52 | 35 → 35 | 67.3% → 67.3% | 0.000000 | 40 → 40 | 76.9% → 76.9% | 0.000000 |
| reference | by_band | 850-1000 km | October 2024 held out | 36 | cross | 52 → 52 | 26 → 26 | 50.0% → 50.0% | 0.000000 | 44 → 44 | 84.6% → 84.6% | 0.000000 |
| reference | by_band | 850-1000 km | October 2024 held out | 48 | radial | 49 → 49 | 31 → 31 | 63.3% → 63.3% | 0.000000 | 38 → 38 | 77.6% → 77.6% | 0.000000 |
| reference | by_band | 850-1000 km | October 2024 held out | 48 | in_track | 49 → 49 | 37 → 37 | 75.5% → 75.5% | 0.000000 | 44 → 44 | 89.8% → 89.8% | 0.000000 |
| reference | by_band | 850-1000 km | October 2024 held out | 48 | cross | 49 → 49 | 19 → 19 | 38.8% → 38.8% | 0.000000 | 42 → 42 | 85.7% → 85.7% | 0.000000 |
| reference | by_band | 850-1000 km | October 2024 held out | 72 | radial | 42 → 42 | 14 → 14 | 33.3% → 33.3% | 0.000000 | 35 → 35 | 83.3% → 83.3% | 0.000000 |
| reference | by_band | 850-1000 km | October 2024 held out | 72 | in_track | 42 → 42 | 35 → 35 | 83.3% → 83.3% | 0.000000 | 39 → 39 | 92.9% → 92.9% | 0.000000 |
| reference | by_band | 850-1000 km | October 2024 held out | 72 | cross | 42 → 42 | 26 → 26 | 61.9% → 61.9% | 0.000000 | 39 → 39 | 92.9% → 92.9% | 0.000000 |
| reference | by_band | 850-1000 km | October 2024 held out | 96 | radial | 32 → 32 | 25 → 25 | 78.1% → 78.1% | 0.000000 | 29 → 29 | 90.6% → 90.6% | 0.000000 |
| reference | by_band | 850-1000 km | October 2024 held out | 96 | in_track | 32 → 32 | 30 → 30 | 93.8% → 93.8% | 0.000000 | 31 → 31 | 96.9% → 96.9% | 0.000000 |
| reference | by_band | 850-1000 km | October 2024 held out | 96 | cross | 32 → 32 | 29 → 29 | 90.6% → 90.6% | 0.000000 | 30 → 30 | 93.8% → 93.8% | 0.000000 |
| reference | by_band | 850-1000 km | October 2024 held out | 120 | radial | 25 → 25 | 22 → 22 | 88.0% → 88.0% | 0.000000 | 23 → 23 | 92.0% → 92.0% | 0.000000 |
| reference | by_band | 850-1000 km | October 2024 held out | 120 | in_track | 25 → 25 | 23 → 23 | 92.0% → 92.0% | 0.000000 | 24 → 24 | 96.0% → 96.0% | 0.000000 |
| reference | by_band | 850-1000 km | October 2024 held out | 120 | cross | 25 → 25 | 21 → 21 | 84.0% → 84.0% | 0.000000 | 24 → 24 | 96.0% → 96.0% | 0.000000 |
| reference | by_band | 850-1000 km | October 2024 held out | 144 | radial | 19 → 19 | 6 → 6 | 31.6% → 31.6% | 0.000000 | 18 → 18 | 94.7% → 94.7% | 0.000000 |
| reference | by_band | 850-1000 km | October 2024 held out | 144 | in_track | 19 → 19 | 17 → 17 | 89.5% → 89.5% | 0.000000 | 18 → 18 | 94.7% → 94.7% | 0.000000 |
| reference | by_band | 850-1000 km | October 2024 held out | 144 | cross | 19 → 19 | 8 → 8 | 42.1% → 42.1% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 850-1000 km | October 2024 held out | 168 | radial | 15 → 15 | 14 → 14 | 93.3% → 93.3% | 0.000000 | 14 → 14 | 93.3% → 93.3% | 0.000000 |
| reference | by_band | 850-1000 km | October 2024 held out | 168 | in_track | 15 → 15 | 12 → 12 | 80.0% → 80.0% | 0.000000 | 13 → 13 | 86.7% → 86.7% | 0.000000 |
| reference | by_band | 850-1000 km | October 2024 held out | 168 | cross | 15 → 15 | 14 → 14 | 93.3% → 93.3% | 0.000000 | 15 → 15 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 850-1000 km | April 2024 control | 6 | radial | 78 → 78 | 5 → 5 | 6.4% → 6.4% | 0.000000 | 13 → 13 | 16.7% → 16.7% | 0.000000 |
| reference | by_band | 850-1000 km | April 2024 control | 6 | in_track | 78 → 78 | 15 → 15 | 19.2% → 19.2% | 0.000000 | 43 → 43 | 55.1% → 55.1% | 0.000000 |
| reference | by_band | 850-1000 km | April 2024 control | 6 | cross | 78 → 78 | 17 → 17 | 21.8% → 21.8% | 0.000000 | 37 → 37 | 47.4% → 47.4% | 0.000000 |
| reference | by_band | 850-1000 km | April 2024 control | 12 | radial | 78 → 78 | 16 → 16 | 20.5% → 20.5% | 0.000000 | 23 → 23 | 29.5% → 29.5% | 0.000000 |
| reference | by_band | 850-1000 km | April 2024 control | 12 | in_track | 78 → 78 | 26 → 26 | 33.3% → 33.3% | 0.000000 | 57 → 57 | 73.1% → 73.1% | 0.000000 |
| reference | by_band | 850-1000 km | April 2024 control | 12 | cross | 78 → 78 | 21 → 21 | 26.9% → 26.9% | 0.000000 | 36 → 36 | 46.2% → 46.2% | 0.000000 |
| reference | by_band | 850-1000 km | April 2024 control | 24 | radial | 78 → 78 | 31 → 31 | 39.7% → 39.7% | 0.000000 | 56 → 56 | 71.8% → 71.8% | 0.000000 |
| reference | by_band | 850-1000 km | April 2024 control | 24 | in_track | 78 → 78 | 64 → 64 | 82.1% → 82.1% | 0.000000 | 78 → 78 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 850-1000 km | April 2024 control | 24 | cross | 78 → 78 | 26 → 26 | 33.3% → 33.3% | 0.000000 | 60 → 60 | 76.9% → 76.9% | 0.000000 |
| reference | by_band | 850-1000 km | April 2024 control | 36 | radial | 78 → 78 | 44 → 44 | 56.4% → 56.4% | 0.000000 | 57 → 57 | 73.1% → 73.1% | 0.000000 |
| reference | by_band | 850-1000 km | April 2024 control | 36 | in_track | 78 → 78 | 76 → 76 | 97.4% → 97.4% | 0.000000 | 78 → 78 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 850-1000 km | April 2024 control | 36 | cross | 78 → 78 | 34 → 34 | 43.6% → 43.6% | 0.000000 | 67 → 67 | 85.9% → 85.9% | 0.000000 |
| reference | by_band | 850-1000 km | April 2024 control | 48 | radial | 78 → 78 | 45 → 45 | 57.7% → 57.7% | 0.000000 | 63 → 63 | 80.8% → 80.8% | 0.000000 |
| reference | by_band | 850-1000 km | April 2024 control | 48 | in_track | 78 → 78 | 78 → 78 | 100.0% → 100.0% | 0.000000 | 78 → 78 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 850-1000 km | April 2024 control | 48 | cross | 78 → 78 | 38 → 38 | 48.7% → 48.7% | 0.000000 | 69 → 69 | 88.5% → 88.5% | 0.000000 |
| reference | by_band | 850-1000 km | April 2024 control | 72 | radial | 78 → 78 | 30 → 30 | 38.5% → 38.5% | 0.000000 | 62 → 62 | 79.5% → 79.5% | 0.000000 |
| reference | by_band | 850-1000 km | April 2024 control | 72 | in_track | 78 → 78 | 78 → 78 | 100.0% → 100.0% | 0.000000 | 78 → 78 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 850-1000 km | April 2024 control | 72 | cross | 78 → 78 | 41 → 41 | 52.6% → 52.6% | 0.000000 | 78 → 78 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 850-1000 km | April 2024 control | 96 | radial | 78 → 78 | 61 → 61 | 78.2% → 78.2% | 0.000000 | 65 → 65 | 83.3% → 83.3% | 0.000000 |
| reference | by_band | 850-1000 km | April 2024 control | 96 | in_track | 78 → 78 | 78 → 78 | 100.0% → 100.0% | 0.000000 | 78 → 78 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 850-1000 km | April 2024 control | 96 | cross | 78 → 78 | 66 → 66 | 84.6% → 84.6% | 0.000000 | 78 → 78 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 850-1000 km | April 2024 control | 120 | radial | 78 → 78 | 62 → 62 | 79.5% → 79.5% | 0.000000 | 70 → 70 | 89.7% → 89.7% | 0.000000 |
| reference | by_band | 850-1000 km | April 2024 control | 120 | in_track | 78 → 78 | 78 → 78 | 100.0% → 100.0% | 0.000000 | 78 → 78 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 850-1000 km | April 2024 control | 120 | cross | 78 → 78 | 40 → 40 | 51.3% → 51.3% | 0.000000 | 78 → 78 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 850-1000 km | April 2024 control | 144 | radial | 78 → 78 | 42 → 42 | 53.8% → 53.8% | 0.000000 | 71 → 71 | 91.0% → 91.0% | 0.000000 |
| reference | by_band | 850-1000 km | April 2024 control | 144 | in_track | 78 → 78 | 78 → 78 | 100.0% → 100.0% | 0.000000 | 78 → 78 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 850-1000 km | April 2024 control | 144 | cross | 78 → 78 | 18 → 18 | 23.1% → 23.1% | 0.000000 | 78 → 78 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 850-1000 km | April 2024 control | 168 | radial | 77 → 77 | 65 → 65 | 84.4% → 84.4% | 0.000000 | 75 → 75 | 97.4% → 97.4% | 0.000000 |
| reference | by_band | 850-1000 km | April 2024 control | 168 | in_track | 77 → 77 | 77 → 77 | 100.0% → 100.0% | 0.000000 | 77 → 77 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 850-1000 km | April 2024 control | 168 | cross | 77 → 77 | 60 → 60 | 77.9% → 77.9% | 0.000000 | 77 → 77 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 850-1000 km | May 2024 | 6 | radial | 77 → 77 | 2 → 2 | 2.6% → 2.6% | 0.000000 | 10 → 10 | 13.0% → 13.0% | 0.000000 |
| reference | by_band | 850-1000 km | May 2024 | 6 | in_track | 77 → 77 | 18 → 18 | 23.4% → 23.4% | 0.000000 | 32 → 32 | 41.6% → 41.6% | 0.000000 |
| reference | by_band | 850-1000 km | May 2024 | 6 | cross | 77 → 77 | 19 → 19 | 24.7% → 24.7% | 0.000000 | 33 → 33 | 42.9% → 42.9% | 0.000000 |
| reference | by_band | 850-1000 km | May 2024 | 12 | radial | 75 → 75 | 15 → 15 | 20.0% → 20.0% | 0.000000 | 25 → 25 | 33.3% → 33.3% | 0.000000 |
| reference | by_band | 850-1000 km | May 2024 | 12 | in_track | 75 → 75 | 19 → 19 | 25.3% → 25.3% | 0.000000 | 30 → 30 | 40.0% → 40.0% | 0.000000 |
| reference | by_band | 850-1000 km | May 2024 | 12 | cross | 75 → 75 | 17 → 17 | 22.7% → 22.7% | 0.000000 | 38 → 38 | 50.7% → 50.7% | 0.000000 |
| reference | by_band | 850-1000 km | May 2024 | 24 | radial | 73 → 73 | 24 → 24 | 32.9% → 32.9% | 0.000000 | 36 → 36 | 49.3% → 49.3% | 0.000000 |
| reference | by_band | 850-1000 km | May 2024 | 24 | in_track | 73 → 73 | 42 → 42 | 57.5% → 57.5% | 0.000000 | 62 → 62 | 84.9% → 84.9% | 0.000000 |
| reference | by_band | 850-1000 km | May 2024 | 24 | cross | 73 → 73 | 26 → 26 | 35.6% → 35.6% | 0.000000 | 54 → 54 | 74.0% → 74.0% | 0.000000 |
| reference | by_band | 850-1000 km | May 2024 | 36 | radial | 72 → 72 | 50 → 50 | 69.4% → 69.4% | 0.000000 | 57 → 57 | 79.2% → 79.2% | 0.000000 |
| reference | by_band | 850-1000 km | May 2024 | 36 | in_track | 72 → 72 | 60 → 60 | 83.3% → 83.3% | 0.000000 | 71 → 71 | 98.6% → 98.6% | 0.000000 |
| reference | by_band | 850-1000 km | May 2024 | 36 | cross | 72 → 72 | 41 → 41 | 56.9% → 56.9% | 0.000000 | 61 → 61 | 84.7% → 84.7% | 0.000000 |
| reference | by_band | 850-1000 km | May 2024 | 48 | radial | 72 → 72 | 41 → 41 | 56.9% → 56.9% | 0.000000 | 53 → 53 | 73.6% → 73.6% | 0.000000 |
| reference | by_band | 850-1000 km | May 2024 | 48 | in_track | 72 → 72 | 69 → 69 | 95.8% → 95.8% | 0.000000 | 72 → 72 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 850-1000 km | May 2024 | 48 | cross | 72 → 72 | 30 → 30 | 41.7% → 41.7% | 0.000000 | 61 → 61 | 84.7% → 84.7% | 0.000000 |
| reference | by_band | 850-1000 km | May 2024 | 72 | radial | 67 → 67 | 31 → 31 | 46.3% → 46.3% | 0.000000 | 48 → 48 | 71.6% → 71.6% | 0.000000 |
| reference | by_band | 850-1000 km | May 2024 | 72 | in_track | 67 → 67 | 65 → 65 | 97.0% → 97.0% | 0.000000 | 67 → 67 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 850-1000 km | May 2024 | 72 | cross | 67 → 67 | 36 → 36 | 53.7% → 53.7% | 0.000000 | 62 → 62 | 92.5% → 92.5% | 0.000000 |
| reference | by_band | 850-1000 km | May 2024 | 96 | radial | 63 → 63 | 44 → 44 | 69.8% → 69.8% | 0.000000 | 44 → 44 | 69.8% → 69.8% | 0.000000 |
| reference | by_band | 850-1000 km | May 2024 | 96 | in_track | 63 → 63 | 60 → 60 | 95.2% → 95.2% | 0.000000 | 63 → 63 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 850-1000 km | May 2024 | 96 | cross | 63 → 63 | 49 → 49 | 77.8% → 77.8% | 0.000000 | 60 → 60 | 95.2% → 95.2% | 0.000000 |
| reference | by_band | 850-1000 km | May 2024 | 120 | radial | 58 → 58 | 38 → 38 | 65.5% → 65.5% | 0.000000 | 39 → 39 | 67.2% → 67.2% | 0.000000 |
| reference | by_band | 850-1000 km | May 2024 | 120 | in_track | 58 → 58 | 57 → 57 | 98.3% → 98.3% | 0.000000 | 58 → 58 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 850-1000 km | May 2024 | 120 | cross | 58 → 58 | 28 → 28 | 48.3% → 48.3% | 0.000000 | 58 → 58 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 850-1000 km | May 2024 | 144 | radial | 53 → 53 | 23 → 23 | 43.4% → 43.4% | 0.000000 | 34 → 34 | 64.2% → 64.2% | 0.000000 |
| reference | by_band | 850-1000 km | May 2024 | 144 | in_track | 53 → 53 | 53 → 53 | 100.0% → 100.0% | 0.000000 | 53 → 53 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 850-1000 km | May 2024 | 144 | cross | 53 → 53 | 15 → 15 | 28.3% → 28.3% | 0.000000 | 53 → 53 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 850-1000 km | May 2024 | 168 | radial | 48 → 48 | 29 → 29 | 60.4% → 60.4% | 0.000000 | 29 → 29 | 60.4% → 60.4% | 0.000000 |
| reference | by_band | 850-1000 km | May 2024 | 168 | in_track | 48 → 48 | 48 → 48 | 100.0% → 100.0% | 0.000000 | 48 → 48 | 100.0% → 100.0% | 0.000000 |
| reference | by_band | 850-1000 km | May 2024 | 168 | cross | 48 → 48 | 34 → 34 | 70.8% → 70.8% | 0.000000 | 48 → 48 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | August 2024 held out | 6 | radial | 14 → 14 | 8 → 8 | 57.1% → 57.1% | 0.000000 | 9 → 9 | 64.3% → 64.3% | 0.000000 |
| reference | by_mission | cryosat-2 | August 2024 held out | 6 | in_track | 14 → 14 | 6 → 6 | 42.9% → 42.9% | 0.000000 | 11 → 11 | 78.6% → 78.6% | 0.000000 |
| reference | by_mission | cryosat-2 | August 2024 held out | 6 | cross | 14 → 14 | 1 → 1 | 7.1% → 7.1% | 0.000000 | 1 → 1 | 7.1% → 7.1% | 0.000000 |
| reference | by_mission | cryosat-2 | August 2024 held out | 12 | radial | 14 → 14 | 2 → 2 | 14.3% → 14.3% | 0.000000 | 7 → 7 | 50.0% → 50.0% | 0.000000 |
| reference | by_mission | cryosat-2 | August 2024 held out | 12 | in_track | 14 → 14 | 8 → 8 | 57.1% → 57.1% | 0.000000 | 12 → 12 | 85.7% → 85.7% | 0.000000 |
| reference | by_mission | cryosat-2 | August 2024 held out | 12 | cross | 14 → 14 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | cryosat-2 | August 2024 held out | 24 | radial | 13 → 13 | 6 → 6 | 46.2% → 46.2% | 0.000000 | 8 → 8 | 61.5% → 61.5% | 0.000000 |
| reference | by_mission | cryosat-2 | August 2024 held out | 24 | in_track | 13 → 13 | 10 → 10 | 76.9% → 76.9% | 0.000000 | 13 → 13 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | August 2024 held out | 24 | cross | 13 → 13 | 1 → 1 | 7.7% → 7.7% | 0.000000 | 1 → 1 | 7.7% → 7.7% | 0.000000 |
| reference | by_mission | cryosat-2 | August 2024 held out | 36 | radial | 11 → 11 | 11 → 11 | 100.0% → 100.0% | 0.000000 | 11 → 11 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | August 2024 held out | 36 | in_track | 11 → 11 | 9 → 9 | 81.8% → 81.8% | 0.000000 | 11 → 11 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | August 2024 held out | 36 | cross | 11 → 11 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 2 → 2 | 18.2% → 18.2% | 0.000000 |
| reference | by_mission | cryosat-2 | August 2024 held out | 48 | radial | 10 → 10 | 6 → 6 | 60.0% → 60.0% | 0.000000 | 10 → 10 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | August 2024 held out | 48 | in_track | 10 → 10 | 8 → 8 | 80.0% → 80.0% | 0.000000 | 10 → 10 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | August 2024 held out | 48 | cross | 10 → 10 | 1 → 1 | 10.0% → 10.0% | 0.000000 | 2 → 2 | 20.0% → 20.0% | 0.000000 |
| reference | by_mission | cryosat-2 | August 2024 held out | 72 | radial | 7 → 7 | 3 → 3 | 42.9% → 42.9% | 0.000000 | 7 → 7 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | August 2024 held out | 72 | in_track | 7 → 7 | 7 → 7 | 100.0% → 100.0% | 0.000000 | 7 → 7 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | August 2024 held out | 72 | cross | 7 → 7 | 2 → 2 | 28.6% → 28.6% | 0.000000 | 5 → 5 | 71.4% → 71.4% | 0.000000 |
| reference | by_mission | cryosat-2 | August 2024 held out | 96 | radial | 5 → 5 | 3 → 3 | 60.0% → 60.0% | 0.000000 | 5 → 5 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | August 2024 held out | 96 | in_track | 5 → 5 | 5 → 5 | 100.0% → 100.0% | 0.000000 | 5 → 5 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | August 2024 held out | 96 | cross | 5 → 5 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 2 → 2 | 40.0% → 40.0% | 0.000000 |
| reference | by_mission | cryosat-2 | August 2024 held out | 120 | radial | 3 → 3 | 1 → 1 | 33.3% → 33.3% | 0.000000 | 3 → 3 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | August 2024 held out | 120 | in_track | 3 → 3 | 3 → 3 | 100.0% → 100.0% | 0.000000 | 3 → 3 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | August 2024 held out | 120 | cross | 3 → 3 | 1 → 1 | 33.3% → 33.3% | 0.000000 | 1 → 1 | 33.3% → 33.3% | 0.000000 |
| reference | by_mission | cryosat-2 | August 2024 held out | 144 | radial | 0 → 0 | 0 → 0 | — → — | — | 0 → 0 | — → — | — |
| reference | by_mission | cryosat-2 | August 2024 held out | 144 | in_track | 0 → 0 | 0 → 0 | — → — | — | 0 → 0 | — → — | — |
| reference | by_mission | cryosat-2 | August 2024 held out | 144 | cross | 0 → 0 | 0 → 0 | — → — | — | 0 → 0 | — → — | — |
| reference | by_mission | cryosat-2 | August 2024 held out | 168 | radial | 0 → 0 | 0 → 0 | — → — | — | 0 → 0 | — → — | — |
| reference | by_mission | cryosat-2 | August 2024 held out | 168 | in_track | 0 → 0 | 0 → 0 | — → — | — | 0 → 0 | — → — | — |
| reference | by_mission | cryosat-2 | August 2024 held out | 168 | cross | 0 → 0 | 0 → 0 | — → — | — | 0 → 0 | — → — | — |
| reference | by_mission | cryosat-2 | October 2024 held out | 6 | radial | 15 → 15 | 11 → 11 | 73.3% → 73.3% | 0.000000 | 14 → 14 | 93.3% → 93.3% | 0.000000 |
| reference | by_mission | cryosat-2 | October 2024 held out | 6 | in_track | 15 → 15 | 8 → 8 | 53.3% → 53.3% | 0.000000 | 13 → 13 | 86.7% → 86.7% | 0.000000 |
| reference | by_mission | cryosat-2 | October 2024 held out | 6 | cross | 15 → 15 | 1 → 1 | 6.7% → 6.7% | 0.000000 | 2 → 2 | 13.3% → 13.3% | 0.000000 |
| reference | by_mission | cryosat-2 | October 2024 held out | 12 | radial | 14 → 14 | 3 → 3 | 21.4% → 21.4% | 0.000000 | 6 → 6 | 42.9% → 42.9% | 0.000000 |
| reference | by_mission | cryosat-2 | October 2024 held out | 12 | in_track | 14 → 14 | 9 → 9 | 64.3% → 64.3% | 0.000000 | 12 → 12 | 85.7% → 85.7% | 0.000000 |
| reference | by_mission | cryosat-2 | October 2024 held out | 12 | cross | 14 → 14 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | cryosat-2 | October 2024 held out | 24 | radial | 12 → 12 | 7 → 7 | 58.3% → 58.3% | 0.000000 | 11 → 11 | 91.7% → 91.7% | 0.000000 |
| reference | by_mission | cryosat-2 | October 2024 held out | 24 | in_track | 12 → 12 | 11 → 11 | 91.7% → 91.7% | 0.000000 | 12 → 12 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | October 2024 held out | 24 | cross | 12 → 12 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | cryosat-2 | October 2024 held out | 36 | radial | 11 → 11 | 11 → 11 | 100.0% → 100.0% | 0.000000 | 11 → 11 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | October 2024 held out | 36 | in_track | 11 → 11 | 10 → 10 | 90.9% → 90.9% | 0.000000 | 11 → 11 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | October 2024 held out | 36 | cross | 11 → 11 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | cryosat-2 | October 2024 held out | 48 | radial | 9 → 9 | 7 → 7 | 77.8% → 77.8% | 0.000000 | 9 → 9 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | October 2024 held out | 48 | in_track | 9 → 9 | 9 → 9 | 100.0% → 100.0% | 0.000000 | 9 → 9 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | October 2024 held out | 48 | cross | 9 → 9 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 2 → 2 | 22.2% → 22.2% | 0.000000 |
| reference | by_mission | cryosat-2 | October 2024 held out | 72 | radial | 6 → 6 | 2 → 2 | 33.3% → 33.3% | 0.000000 | 6 → 6 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | October 2024 held out | 72 | in_track | 6 → 6 | 6 → 6 | 100.0% → 100.0% | 0.000000 | 6 → 6 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | October 2024 held out | 72 | cross | 6 → 6 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | cryosat-2 | October 2024 held out | 96 | radial | 6 → 6 | 5 → 5 | 83.3% → 83.3% | 0.000000 | 6 → 6 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | October 2024 held out | 96 | in_track | 6 → 6 | 6 → 6 | 100.0% → 100.0% | 0.000000 | 6 → 6 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | October 2024 held out | 96 | cross | 6 → 6 | 1 → 1 | 16.7% → 16.7% | 0.000000 | 1 → 1 | 16.7% → 16.7% | 0.000000 |
| reference | by_mission | cryosat-2 | October 2024 held out | 120 | radial | 6 → 6 | 5 → 5 | 83.3% → 83.3% | 0.000000 | 6 → 6 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | October 2024 held out | 120 | in_track | 6 → 6 | 6 → 6 | 100.0% → 100.0% | 0.000000 | 6 → 6 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | October 2024 held out | 120 | cross | 6 → 6 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | cryosat-2 | October 2024 held out | 144 | radial | 6 → 6 | 6 → 6 | 100.0% → 100.0% | 0.000000 | 6 → 6 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | October 2024 held out | 144 | in_track | 6 → 6 | 6 → 6 | 100.0% → 100.0% | 0.000000 | 6 → 6 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | October 2024 held out | 144 | cross | 6 → 6 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 1 → 1 | 16.7% → 16.7% | 0.000000 |
| reference | by_mission | cryosat-2 | October 2024 held out | 168 | radial | 6 → 6 | 6 → 6 | 100.0% → 100.0% | 0.000000 | 6 → 6 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | October 2024 held out | 168 | in_track | 6 → 6 | 6 → 6 | 100.0% → 100.0% | 0.000000 | 6 → 6 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | October 2024 held out | 168 | cross | 6 → 6 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | cryosat-2 | April 2024 control | 6 | radial | 14 → 14 | 8 → 8 | 57.1% → 57.1% | 0.000000 | 12 → 12 | 85.7% → 85.7% | 0.000000 |
| reference | by_mission | cryosat-2 | April 2024 control | 6 | in_track | 14 → 14 | 7 → 7 | 50.0% → 50.0% | 0.000000 | 10 → 10 | 71.4% → 71.4% | 0.000000 |
| reference | by_mission | cryosat-2 | April 2024 control | 6 | cross | 14 → 14 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 1 → 1 | 7.1% → 7.1% | 0.000000 |
| reference | by_mission | cryosat-2 | April 2024 control | 12 | radial | 14 → 14 | 2 → 2 | 14.3% → 14.3% | 0.000000 | 7 → 7 | 50.0% → 50.0% | 0.000000 |
| reference | by_mission | cryosat-2 | April 2024 control | 12 | in_track | 14 → 14 | 12 → 12 | 85.7% → 85.7% | 0.000000 | 14 → 14 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | April 2024 control | 12 | cross | 14 → 14 | 2 → 2 | 14.3% → 14.3% | 0.000000 | 2 → 2 | 14.3% → 14.3% | 0.000000 |
| reference | by_mission | cryosat-2 | April 2024 control | 24 | radial | 13 → 13 | 8 → 8 | 61.5% → 61.5% | 0.000000 | 13 → 13 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | April 2024 control | 24 | in_track | 13 → 13 | 13 → 13 | 100.0% → 100.0% | 0.000000 | 13 → 13 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | April 2024 control | 24 | cross | 13 → 13 | 1 → 1 | 7.7% → 7.7% | 0.000000 | 2 → 2 | 15.4% → 15.4% | 0.000000 |
| reference | by_mission | cryosat-2 | April 2024 control | 36 | radial | 11 → 11 | 10 → 10 | 90.9% → 90.9% | 0.000000 | 11 → 11 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | April 2024 control | 36 | in_track | 11 → 11 | 11 → 11 | 100.0% → 100.0% | 0.000000 | 11 → 11 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | April 2024 control | 36 | cross | 11 → 11 | 1 → 1 | 9.1% → 9.1% | 0.000000 | 1 → 1 | 9.1% → 9.1% | 0.000000 |
| reference | by_mission | cryosat-2 | April 2024 control | 48 | radial | 10 → 10 | 6 → 6 | 60.0% → 60.0% | 0.000000 | 10 → 10 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | April 2024 control | 48 | in_track | 10 → 10 | 10 → 10 | 100.0% → 100.0% | 0.000000 | 10 → 10 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | April 2024 control | 48 | cross | 10 → 10 | 1 → 1 | 10.0% → 10.0% | 0.000000 | 2 → 2 | 20.0% → 20.0% | 0.000000 |
| reference | by_mission | cryosat-2 | April 2024 control | 72 | radial | 7 → 7 | 4 → 4 | 57.1% → 57.1% | 0.000000 | 7 → 7 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | April 2024 control | 72 | in_track | 7 → 7 | 7 → 7 | 100.0% → 100.0% | 0.000000 | 7 → 7 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | April 2024 control | 72 | cross | 7 → 7 | 2 → 2 | 28.6% → 28.6% | 0.000000 | 2 → 2 | 28.6% → 28.6% | 0.000000 |
| reference | by_mission | cryosat-2 | April 2024 control | 96 | radial | 5 → 5 | 3 → 3 | 60.0% → 60.0% | 0.000000 | 5 → 5 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | April 2024 control | 96 | in_track | 5 → 5 | 5 → 5 | 100.0% → 100.0% | 0.000000 | 5 → 5 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | April 2024 control | 96 | cross | 5 → 5 | 1 → 1 | 20.0% → 20.0% | 0.000000 | 1 → 1 | 20.0% → 20.0% | 0.000000 |
| reference | by_mission | cryosat-2 | April 2024 control | 120 | radial | 4 → 4 | 4 → 4 | 100.0% → 100.0% | 0.000000 | 4 → 4 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | April 2024 control | 120 | in_track | 4 → 4 | 4 → 4 | 100.0% → 100.0% | 0.000000 | 4 → 4 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | April 2024 control | 120 | cross | 4 → 4 | 1 → 1 | 25.0% → 25.0% | 0.000000 | 2 → 2 | 50.0% → 50.0% | 0.000000 |
| reference | by_mission | cryosat-2 | April 2024 control | 144 | radial | 4 → 4 | 4 → 4 | 100.0% → 100.0% | 0.000000 | 4 → 4 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | April 2024 control | 144 | in_track | 4 → 4 | 4 → 4 | 100.0% → 100.0% | 0.000000 | 4 → 4 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | April 2024 control | 144 | cross | 4 → 4 | 1 → 1 | 25.0% → 25.0% | 0.000000 | 2 → 2 | 50.0% → 50.0% | 0.000000 |
| reference | by_mission | cryosat-2 | April 2024 control | 168 | radial | 4 → 4 | 4 → 4 | 100.0% → 100.0% | 0.000000 | 4 → 4 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | April 2024 control | 168 | in_track | 4 → 4 | 4 → 4 | 100.0% → 100.0% | 0.000000 | 4 → 4 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | April 2024 control | 168 | cross | 4 → 4 | 1 → 1 | 25.0% → 25.0% | 0.000000 | 2 → 2 | 50.0% → 50.0% | 0.000000 |
| reference | by_mission | cryosat-2 | May 2024 | 6 | radial | 15 → 15 | 8 → 8 | 53.3% → 53.3% | 0.000000 | 13 → 13 | 86.7% → 86.7% | 0.000000 |
| reference | by_mission | cryosat-2 | May 2024 | 6 | in_track | 15 → 15 | 6 → 6 | 40.0% → 40.0% | 0.000000 | 11 → 11 | 73.3% → 73.3% | 0.000000 |
| reference | by_mission | cryosat-2 | May 2024 | 6 | cross | 15 → 15 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | cryosat-2 | May 2024 | 12 | radial | 14 → 14 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 8 → 8 | 57.1% → 57.1% | 0.000000 |
| reference | by_mission | cryosat-2 | May 2024 | 12 | in_track | 14 → 14 | 4 → 4 | 28.6% → 28.6% | 0.000000 | 11 → 11 | 78.6% → 78.6% | 0.000000 |
| reference | by_mission | cryosat-2 | May 2024 | 12 | cross | 14 → 14 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | cryosat-2 | May 2024 | 24 | radial | 12 → 12 | 11 → 11 | 91.7% → 91.7% | 0.000000 | 12 → 12 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | May 2024 | 24 | in_track | 12 → 12 | 11 → 11 | 91.7% → 91.7% | 0.000000 | 12 → 12 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | May 2024 | 24 | cross | 12 → 12 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | cryosat-2 | May 2024 | 36 | radial | 12 → 12 | 12 → 12 | 100.0% → 100.0% | 0.000000 | 12 → 12 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | May 2024 | 36 | in_track | 12 → 12 | 12 → 12 | 100.0% → 100.0% | 0.000000 | 12 → 12 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | May 2024 | 36 | cross | 12 → 12 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | cryosat-2 | May 2024 | 48 | radial | 12 → 12 | 10 → 10 | 83.3% → 83.3% | 0.000000 | 12 → 12 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | May 2024 | 48 | in_track | 12 → 12 | 12 → 12 | 100.0% → 100.0% | 0.000000 | 12 → 12 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | May 2024 | 48 | cross | 12 → 12 | 1 → 1 | 8.3% → 8.3% | 0.000000 | 1 → 1 | 8.3% → 8.3% | 0.000000 |
| reference | by_mission | cryosat-2 | May 2024 | 72 | radial | 12 → 12 | 11 → 11 | 91.7% → 91.7% | 0.000000 | 12 → 12 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | May 2024 | 72 | in_track | 12 → 12 | 12 → 12 | 100.0% → 100.0% | 0.000000 | 12 → 12 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | May 2024 | 72 | cross | 12 → 12 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 3 → 3 | 25.0% → 25.0% | 0.000000 |
| reference | by_mission | cryosat-2 | May 2024 | 96 | radial | 12 → 12 | 11 → 11 | 91.7% → 91.7% | 0.000000 | 12 → 12 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | May 2024 | 96 | in_track | 12 → 12 | 12 → 12 | 100.0% → 100.0% | 0.000000 | 12 → 12 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | May 2024 | 96 | cross | 12 → 12 | 1 → 1 | 8.3% → 8.3% | 0.000000 | 3 → 3 | 25.0% → 25.0% | 0.000000 |
| reference | by_mission | cryosat-2 | May 2024 | 120 | radial | 12 → 12 | 11 → 11 | 91.7% → 91.7% | 0.000000 | 12 → 12 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | May 2024 | 120 | in_track | 12 → 12 | 12 → 12 | 100.0% → 100.0% | 0.000000 | 12 → 12 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | May 2024 | 120 | cross | 12 → 12 | 2 → 2 | 16.7% → 16.7% | 0.000000 | 6 → 6 | 50.0% → 50.0% | 0.000000 |
| reference | by_mission | cryosat-2 | May 2024 | 144 | radial | 12 → 12 | 12 → 12 | 100.0% → 100.0% | 0.000000 | 12 → 12 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | May 2024 | 144 | in_track | 12 → 12 | 12 → 12 | 100.0% → 100.0% | 0.000000 | 12 → 12 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | May 2024 | 144 | cross | 12 → 12 | 3 → 3 | 25.0% → 25.0% | 0.000000 | 6 → 6 | 50.0% → 50.0% | 0.000000 |
| reference | by_mission | cryosat-2 | May 2024 | 168 | radial | 12 → 12 | 12 → 12 | 100.0% → 100.0% | 0.000000 | 12 → 12 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | May 2024 | 168 | in_track | 12 → 12 | 12 → 12 | 100.0% → 100.0% | 0.000000 | 12 → 12 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | cryosat-2 | May 2024 | 168 | cross | 12 → 12 | 2 → 2 | 16.7% → 16.7% | 0.000000 | 6 → 6 | 50.0% → 50.0% | 0.000000 |
| reference | by_mission | gracefo-c | August 2024 held out | 6 | radial | 18 → 18 | 3 → 3 | 16.7% → 16.7% | 0.000000 | 11 → 11 | 61.1% → 61.1% | 0.000000 |
| reference | by_mission | gracefo-c | August 2024 held out | 6 | in_track | 18 → 18 | 5 → 5 | 27.8% → 27.8% | 0.000000 | 8 → 8 | 44.4% → 44.4% | 0.000000 |
| reference | by_mission | gracefo-c | August 2024 held out | 6 | cross | 18 → 18 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | gracefo-c | August 2024 held out | 12 | radial | 18 → 18 | 8 → 8 | 44.4% → 44.4% | 0.000000 | 11 → 11 | 61.1% → 61.1% | 0.000000 |
| reference | by_mission | gracefo-c | August 2024 held out | 12 | in_track | 18 → 18 | 3 → 3 | 16.7% → 16.7% | 0.000000 | 7 → 7 | 38.9% → 38.9% | 0.000000 |
| reference | by_mission | gracefo-c | August 2024 held out | 12 | cross | 18 → 18 | 1 → 1 | 5.6% → 5.6% | 0.000000 | 1 → 1 | 5.6% → 5.6% | 0.000000 |
| reference | by_mission | gracefo-c | August 2024 held out | 24 | radial | 18 → 18 | 17 → 17 | 94.4% → 94.4% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-c | August 2024 held out | 24 | in_track | 18 → 18 | 12 → 12 | 66.7% → 66.7% | 0.000000 | 16 → 16 | 88.9% → 88.9% | 0.000000 |
| reference | by_mission | gracefo-c | August 2024 held out | 24 | cross | 18 → 18 | 3 → 3 | 16.7% → 16.7% | 0.000000 | 3 → 3 | 16.7% → 16.7% | 0.000000 |
| reference | by_mission | gracefo-c | August 2024 held out | 36 | radial | 18 → 18 | 11 → 11 | 61.1% → 61.1% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-c | August 2024 held out | 36 | in_track | 18 → 18 | 9 → 9 | 50.0% → 50.0% | 0.000000 | 14 → 14 | 77.8% → 77.8% | 0.000000 |
| reference | by_mission | gracefo-c | August 2024 held out | 36 | cross | 18 → 18 | 2 → 2 | 11.1% → 11.1% | 0.000000 | 4 → 4 | 22.2% → 22.2% | 0.000000 |
| reference | by_mission | gracefo-c | August 2024 held out | 48 | radial | 18 → 18 | 10 → 10 | 55.6% → 55.6% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-c | August 2024 held out | 48 | in_track | 18 → 18 | 9 → 9 | 50.0% → 50.0% | 0.000000 | 12 → 12 | 66.7% → 66.7% | 0.000000 |
| reference | by_mission | gracefo-c | August 2024 held out | 48 | cross | 18 → 18 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | gracefo-c | August 2024 held out | 72 | radial | 18 → 18 | 15 → 15 | 83.3% → 83.3% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-c | August 2024 held out | 72 | in_track | 18 → 18 | 6 → 6 | 33.3% → 33.3% | 0.000000 | 10 → 10 | 55.6% → 55.6% | 0.000000 |
| reference | by_mission | gracefo-c | August 2024 held out | 72 | cross | 18 → 18 | 1 → 1 | 5.6% → 5.6% | 0.000000 | 4 → 4 | 22.2% → 22.2% | 0.000000 |
| reference | by_mission | gracefo-c | August 2024 held out | 96 | radial | 18 → 18 | 15 → 15 | 83.3% → 83.3% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-c | August 2024 held out | 96 | in_track | 18 → 18 | 5 → 5 | 27.8% → 27.8% | 0.000000 | 10 → 10 | 55.6% → 55.6% | 0.000000 |
| reference | by_mission | gracefo-c | August 2024 held out | 96 | cross | 18 → 18 | 3 → 3 | 16.7% → 16.7% | 0.000000 | 4 → 4 | 22.2% → 22.2% | 0.000000 |
| reference | by_mission | gracefo-c | August 2024 held out | 120 | radial | 18 → 18 | 10 → 10 | 55.6% → 55.6% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-c | August 2024 held out | 120 | in_track | 18 → 18 | 5 → 5 | 27.8% → 27.8% | 0.000000 | 8 → 8 | 44.4% → 44.4% | 0.000000 |
| reference | by_mission | gracefo-c | August 2024 held out | 120 | cross | 18 → 18 | 4 → 4 | 22.2% → 22.2% | 0.000000 | 12 → 12 | 66.7% → 66.7% | 0.000000 |
| reference | by_mission | gracefo-c | August 2024 held out | 144 | radial | 18 → 18 | 16 → 16 | 88.9% → 88.9% | 0.000000 | 17 → 18 | 94.4% → 100.0% | 5.555556 |
| reference | by_mission | gracefo-c | August 2024 held out | 144 | in_track | 18 → 18 | 5 → 5 | 27.8% → 27.8% | 0.000000 | 7 → 7 | 38.9% → 38.9% | 0.000000 |
| reference | by_mission | gracefo-c | August 2024 held out | 144 | cross | 18 → 18 | 2 → 2 | 11.1% → 11.1% | 0.000000 | 7 → 7 | 38.9% → 38.9% | 0.000000 |
| reference | by_mission | gracefo-c | August 2024 held out | 168 | radial | 18 → 18 | 9 → 9 | 50.0% → 50.0% | 0.000000 | 15 → 15 | 83.3% → 83.3% | 0.000000 |
| reference | by_mission | gracefo-c | August 2024 held out | 168 | in_track | 18 → 18 | 6 → 6 | 33.3% → 33.3% | 0.000000 | 6 → 6 | 33.3% → 33.3% | 0.000000 |
| reference | by_mission | gracefo-c | August 2024 held out | 168 | cross | 18 → 18 | 5 → 5 | 27.8% → 27.8% | 0.000000 | 10 → 10 | 55.6% → 55.6% | 0.000000 |
| reference | by_mission | gracefo-c | October 2024 held out | 6 | radial | 19 → 19 | 15 → 15 | 78.9% → 78.9% | 0.000000 | 17 → 17 | 89.5% → 89.5% | 0.000000 |
| reference | by_mission | gracefo-c | October 2024 held out | 6 | in_track | 19 → 19 | 6 → 6 | 31.6% → 31.6% | 0.000000 | 16 → 16 | 84.2% → 84.2% | 0.000000 |
| reference | by_mission | gracefo-c | October 2024 held out | 6 | cross | 19 → 19 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | gracefo-c | October 2024 held out | 12 | radial | 19 → 19 | 3 → 3 | 15.8% → 15.8% | 0.000000 | 11 → 11 | 57.9% → 57.9% | 0.000000 |
| reference | by_mission | gracefo-c | October 2024 held out | 12 | in_track | 19 → 19 | 6 → 6 | 31.6% → 31.6% | 0.000000 | 11 → 11 | 57.9% → 57.9% | 0.000000 |
| reference | by_mission | gracefo-c | October 2024 held out | 12 | cross | 19 → 19 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 1 → 1 | 5.3% → 5.3% | 0.000000 |
| reference | by_mission | gracefo-c | October 2024 held out | 24 | radial | 19 → 19 | 14 → 14 | 73.7% → 73.7% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-c | October 2024 held out | 24 | in_track | 19 → 19 | 11 → 11 | 57.9% → 57.9% | 0.000000 | 14 → 14 | 73.7% → 73.7% | 0.000000 |
| reference | by_mission | gracefo-c | October 2024 held out | 24 | cross | 19 → 19 | 1 → 1 | 5.3% → 5.3% | 0.000000 | 2 → 2 | 10.5% → 10.5% | 0.000000 |
| reference | by_mission | gracefo-c | October 2024 held out | 36 | radial | 19 → 19 | 5 → 5 | 26.3% → 26.3% | 0.000000 | 17 → 17 | 89.5% → 89.5% | 0.000000 |
| reference | by_mission | gracefo-c | October 2024 held out | 36 | in_track | 19 → 19 | 9 → 9 | 47.4% → 47.4% | 0.000000 | 13 → 13 | 68.4% → 68.4% | 0.000000 |
| reference | by_mission | gracefo-c | October 2024 held out | 36 | cross | 19 → 19 | 1 → 1 | 5.3% → 5.3% | 0.000000 | 2 → 2 | 10.5% → 10.5% | 0.000000 |
| reference | by_mission | gracefo-c | October 2024 held out | 48 | radial | 19 → 19 | 15 → 15 | 78.9% → 78.9% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-c | October 2024 held out | 48 | in_track | 19 → 19 | 9 → 9 | 47.4% → 47.4% | 0.000000 | 13 → 13 | 68.4% → 68.4% | 0.000000 |
| reference | by_mission | gracefo-c | October 2024 held out | 48 | cross | 19 → 19 | 4 → 4 | 21.1% → 21.1% | 0.000000 | 6 → 6 | 31.6% → 31.6% | 0.000000 |
| reference | by_mission | gracefo-c | October 2024 held out | 72 | radial | 19 → 19 | 10 → 10 | 52.6% → 52.6% | 0.000000 | 16 → 16 | 84.2% → 84.2% | 0.000000 |
| reference | by_mission | gracefo-c | October 2024 held out | 72 | in_track | 19 → 19 | 8 → 8 | 42.1% → 42.1% | 0.000000 | 12 → 12 | 63.2% → 63.2% | 0.000000 |
| reference | by_mission | gracefo-c | October 2024 held out | 72 | cross | 19 → 19 | 2 → 2 | 10.5% → 10.5% | 0.000000 | 2 → 2 | 10.5% → 10.5% | 0.000000 |
| reference | by_mission | gracefo-c | October 2024 held out | 96 | radial | 19 → 19 | 13 → 13 | 68.4% → 68.4% | 0.000000 | 17 → 17 | 89.5% → 89.5% | 0.000000 |
| reference | by_mission | gracefo-c | October 2024 held out | 96 | in_track | 19 → 19 | 10 → 10 | 52.6% → 52.6% | 0.000000 | 12 → 12 | 63.2% → 63.2% | 0.000000 |
| reference | by_mission | gracefo-c | October 2024 held out | 96 | cross | 19 → 19 | 5 → 5 | 26.3% → 26.3% | 0.000000 | 10 → 10 | 52.6% → 52.6% | 0.000000 |
| reference | by_mission | gracefo-c | October 2024 held out | 120 | radial | 19 → 19 | 14 → 14 | 73.7% → 73.7% | 0.000000 | 17 → 17 | 89.5% → 89.5% | 0.000000 |
| reference | by_mission | gracefo-c | October 2024 held out | 120 | in_track | 19 → 19 | 10 → 10 | 52.6% → 52.6% | 0.000000 | 12 → 12 | 63.2% → 63.2% | 0.000000 |
| reference | by_mission | gracefo-c | October 2024 held out | 120 | cross | 19 → 19 | 5 → 5 | 26.3% → 26.3% | 0.000000 | 9 → 9 | 47.4% → 47.4% | 0.000000 |
| reference | by_mission | gracefo-c | October 2024 held out | 144 | radial | 19 → 19 | 12 → 12 | 63.2% → 63.2% | 0.000000 | 13 → 13 | 68.4% → 68.4% | 0.000000 |
| reference | by_mission | gracefo-c | October 2024 held out | 144 | in_track | 19 → 19 | 9 → 9 | 47.4% → 47.4% | 0.000000 | 12 → 12 | 63.2% → 63.2% | 0.000000 |
| reference | by_mission | gracefo-c | October 2024 held out | 144 | cross | 19 → 19 | 3 → 3 | 15.8% → 15.8% | 0.000000 | 6 → 6 | 31.6% → 31.6% | 0.000000 |
| reference | by_mission | gracefo-c | October 2024 held out | 168 | radial | 19 → 19 | 12 → 12 | 63.2% → 63.2% | 0.000000 | 12 → 13 | 63.2% → 68.4% | 5.263158 |
| reference | by_mission | gracefo-c | October 2024 held out | 168 | in_track | 19 → 19 | 8 → 8 | 42.1% → 42.1% | 0.000000 | 12 → 12 | 63.2% → 63.2% | 0.000000 |
| reference | by_mission | gracefo-c | October 2024 held out | 168 | cross | 19 → 19 | 10 → 10 | 52.6% → 52.6% | 0.000000 | 16 → 16 | 84.2% → 84.2% | 0.000000 |
| reference | by_mission | gracefo-c | April 2024 control | 6 | radial | 19 → 19 | 3 → 3 | 15.8% → 15.8% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-c | April 2024 control | 6 | in_track | 19 → 19 | 2 → 2 | 10.5% → 10.5% | 0.000000 | 7 → 7 | 36.8% → 36.8% | 0.000000 |
| reference | by_mission | gracefo-c | April 2024 control | 6 | cross | 19 → 19 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | gracefo-c | April 2024 control | 12 | radial | 19 → 19 | 9 → 9 | 47.4% → 47.4% | 0.000000 | 15 → 15 | 78.9% → 78.9% | 0.000000 |
| reference | by_mission | gracefo-c | April 2024 control | 12 | in_track | 19 → 19 | 2 → 2 | 10.5% → 10.5% | 0.000000 | 3 → 3 | 15.8% → 15.8% | 0.000000 |
| reference | by_mission | gracefo-c | April 2024 control | 12 | cross | 19 → 19 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 1 → 1 | 5.3% → 5.3% | 0.000000 |
| reference | by_mission | gracefo-c | April 2024 control | 24 | radial | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-c | April 2024 control | 24 | in_track | 19 → 19 | 18 → 18 | 94.7% → 94.7% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-c | April 2024 control | 24 | cross | 19 → 19 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 1 → 1 | 5.3% → 5.3% | 0.000000 |
| reference | by_mission | gracefo-c | April 2024 control | 36 | radial | 19 → 19 | 13 → 13 | 68.4% → 68.4% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-c | April 2024 control | 36 | in_track | 19 → 19 | 17 → 17 | 89.5% → 89.5% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-c | April 2024 control | 36 | cross | 19 → 19 | 2 → 2 | 10.5% → 10.5% | 0.000000 | 4 → 4 | 21.1% → 21.1% | 0.000000 |
| reference | by_mission | gracefo-c | April 2024 control | 48 | radial | 19 → 19 | 9 → 9 | 47.4% → 47.4% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-c | April 2024 control | 48 | in_track | 19 → 19 | 18 → 18 | 94.7% → 94.7% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-c | April 2024 control | 48 | cross | 19 → 19 | 3 → 3 | 15.8% → 15.8% | 0.000000 | 8 → 8 | 42.1% → 42.1% | 0.000000 |
| reference | by_mission | gracefo-c | April 2024 control | 72 | radial | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-c | April 2024 control | 72 | in_track | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-c | April 2024 control | 72 | cross | 19 → 19 | 6 → 6 | 31.6% → 31.6% | 0.000000 | 9 → 9 | 47.4% → 47.4% | 0.000000 |
| reference | by_mission | gracefo-c | April 2024 control | 96 | radial | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-c | April 2024 control | 96 | in_track | 19 → 19 | 18 → 18 | 94.7% → 94.7% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-c | April 2024 control | 96 | cross | 19 → 19 | 3 → 3 | 15.8% → 15.8% | 0.000000 | 6 → 6 | 31.6% → 31.6% | 0.000000 |
| reference | by_mission | gracefo-c | April 2024 control | 120 | radial | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-c | April 2024 control | 120 | in_track | 19 → 19 | 18 → 18 | 94.7% → 94.7% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-c | April 2024 control | 120 | cross | 19 → 19 | 8 → 8 | 42.1% → 42.1% | 0.000000 | 16 → 16 | 84.2% → 84.2% | 0.000000 |
| reference | by_mission | gracefo-c | April 2024 control | 144 | radial | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-c | April 2024 control | 144 | in_track | 19 → 19 | 18 → 18 | 94.7% → 94.7% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-c | April 2024 control | 144 | cross | 19 → 19 | 8 → 8 | 42.1% → 42.1% | 0.000000 | 17 → 17 | 89.5% → 89.5% | 0.000000 |
| reference | by_mission | gracefo-c | April 2024 control | 168 | radial | 19 → 19 | 11 → 11 | 57.9% → 57.9% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-c | April 2024 control | 168 | in_track | 19 → 19 | 18 → 18 | 94.7% → 94.7% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-c | April 2024 control | 168 | cross | 19 → 19 | 14 → 14 | 73.7% → 73.7% | 0.000000 | 18 → 18 | 94.7% → 94.7% | 0.000000 |
| reference | by_mission | gracefo-c | May 2024 | 6 | radial | 18 → 18 | 8 → 8 | 44.4% → 44.4% | 0.000000 | 17 → 17 | 94.4% → 94.4% | 0.000000 |
| reference | by_mission | gracefo-c | May 2024 | 6 | in_track | 18 → 18 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 1 → 1 | 5.6% → 5.6% | 0.000000 |
| reference | by_mission | gracefo-c | May 2024 | 6 | cross | 18 → 18 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 1 → 1 | 5.6% → 5.6% | 0.000000 |
| reference | by_mission | gracefo-c | May 2024 | 12 | radial | 18 → 18 | 9 → 9 | 50.0% → 50.0% | 0.000000 | 13 → 13 | 72.2% → 72.2% | 0.000000 |
| reference | by_mission | gracefo-c | May 2024 | 12 | in_track | 18 → 18 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 2 → 2 | 11.1% → 11.1% | 0.000000 |
| reference | by_mission | gracefo-c | May 2024 | 12 | cross | 18 → 18 | 2 → 2 | 11.1% → 11.1% | 0.000000 | 2 → 2 | 11.1% → 11.1% | 0.000000 |
| reference | by_mission | gracefo-c | May 2024 | 24 | radial | 18 → 18 | 17 → 17 | 94.4% → 94.4% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-c | May 2024 | 24 | in_track | 18 → 18 | 7 → 7 | 38.9% → 38.9% | 0.000000 | 15 → 15 | 83.3% → 83.3% | 0.000000 |
| reference | by_mission | gracefo-c | May 2024 | 24 | cross | 18 → 18 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 2 → 2 | 11.1% → 11.1% | 0.000000 |
| reference | by_mission | gracefo-c | May 2024 | 36 | radial | 18 → 18 | 8 → 8 | 44.4% → 44.4% | 0.000000 | 17 → 17 | 94.4% → 94.4% | 0.000000 |
| reference | by_mission | gracefo-c | May 2024 | 36 | in_track | 18 → 18 | 13 → 13 | 72.2% → 72.2% | 0.000000 | 13 → 13 | 72.2% → 72.2% | 0.000000 |
| reference | by_mission | gracefo-c | May 2024 | 36 | cross | 18 → 18 | 6 → 6 | 33.3% → 33.3% | 0.000000 | 9 → 9 | 50.0% → 50.0% | 0.000000 |
| reference | by_mission | gracefo-c | May 2024 | 48 | radial | 18 → 18 | 8 → 8 | 44.4% → 44.4% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-c | May 2024 | 48 | in_track | 18 → 18 | 11 → 11 | 61.1% → 61.1% | 0.000000 | 13 → 13 | 72.2% → 72.2% | 0.000000 |
| reference | by_mission | gracefo-c | May 2024 | 48 | cross | 18 → 18 | 5 → 5 | 27.8% → 27.8% | 0.000000 | 9 → 9 | 50.0% → 50.0% | 0.000000 |
| reference | by_mission | gracefo-c | May 2024 | 72 | radial | 18 → 18 | 17 → 17 | 94.4% → 94.4% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-c | May 2024 | 72 | in_track | 18 → 18 | 9 → 9 | 50.0% → 50.0% | 0.000000 | 13 → 13 | 72.2% → 72.2% | 0.000000 |
| reference | by_mission | gracefo-c | May 2024 | 72 | cross | 18 → 18 | 10 → 10 | 55.6% → 55.6% | 0.000000 | 13 → 13 | 72.2% → 72.2% | 0.000000 |
| reference | by_mission | gracefo-c | May 2024 | 96 | radial | 18 → 18 | 16 → 16 | 88.9% → 88.9% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-c | May 2024 | 96 | in_track | 18 → 18 | 9 → 9 | 50.0% → 50.0% | 0.000000 | 14 → 14 | 77.8% → 77.8% | 0.000000 |
| reference | by_mission | gracefo-c | May 2024 | 96 | cross | 18 → 18 | 7 → 7 | 38.9% → 38.9% | 0.000000 | 15 → 15 | 83.3% → 83.3% | 0.000000 |
| reference | by_mission | gracefo-c | May 2024 | 120 | radial | 18 → 18 | 16 → 16 | 88.9% → 88.9% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-c | May 2024 | 120 | in_track | 18 → 18 | 7 → 7 | 38.9% → 38.9% | 0.000000 | 15 → 15 | 83.3% → 83.3% | 0.000000 |
| reference | by_mission | gracefo-c | May 2024 | 120 | cross | 18 → 18 | 12 → 12 | 66.7% → 66.7% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-c | May 2024 | 144 | radial | 18 → 18 | 17 → 18 | 94.4% → 100.0% | 5.555556 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-c | May 2024 | 144 | in_track | 18 → 18 | 7 → 7 | 38.9% → 38.9% | 0.000000 | 14 → 14 | 77.8% → 77.8% | 0.000000 |
| reference | by_mission | gracefo-c | May 2024 | 144 | cross | 18 → 18 | 13 → 13 | 72.2% → 72.2% | 0.000000 | 15 → 15 | 83.3% → 83.3% | 0.000000 |
| reference | by_mission | gracefo-c | May 2024 | 168 | radial | 18 → 18 | 11 → 11 | 61.1% → 61.1% | 0.000000 | 16 → 16 | 88.9% → 88.9% | 0.000000 |
| reference | by_mission | gracefo-c | May 2024 | 168 | in_track | 18 → 18 | 8 → 8 | 44.4% → 44.4% | 0.000000 | 16 → 16 | 88.9% → 88.9% | 0.000000 |
| reference | by_mission | gracefo-c | May 2024 | 168 | cross | 18 → 18 | 12 → 12 | 66.7% → 66.7% | 0.000000 | 17 → 17 | 94.4% → 94.4% | 0.000000 |
| reference | by_mission | gracefo-d | August 2024 held out | 6 | radial | 18 → 18 | 3 → 3 | 16.7% → 16.7% | 0.000000 | 11 → 11 | 61.1% → 61.1% | 0.000000 |
| reference | by_mission | gracefo-d | August 2024 held out | 6 | in_track | 18 → 18 | 6 → 6 | 33.3% → 33.3% | 0.000000 | 8 → 8 | 44.4% → 44.4% | 0.000000 |
| reference | by_mission | gracefo-d | August 2024 held out | 6 | cross | 18 → 18 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | gracefo-d | August 2024 held out | 12 | radial | 18 → 18 | 8 → 8 | 44.4% → 44.4% | 0.000000 | 12 → 12 | 66.7% → 66.7% | 0.000000 |
| reference | by_mission | gracefo-d | August 2024 held out | 12 | in_track | 18 → 18 | 4 → 4 | 22.2% → 22.2% | 0.000000 | 8 → 8 | 44.4% → 44.4% | 0.000000 |
| reference | by_mission | gracefo-d | August 2024 held out | 12 | cross | 18 → 18 | 1 → 1 | 5.6% → 5.6% | 0.000000 | 2 → 2 | 11.1% → 11.1% | 0.000000 |
| reference | by_mission | gracefo-d | August 2024 held out | 24 | radial | 18 → 18 | 17 → 17 | 94.4% → 94.4% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-d | August 2024 held out | 24 | in_track | 18 → 18 | 12 → 12 | 66.7% → 66.7% | 0.000000 | 16 → 16 | 88.9% → 88.9% | 0.000000 |
| reference | by_mission | gracefo-d | August 2024 held out | 24 | cross | 18 → 18 | 2 → 2 | 11.1% → 11.1% | 0.000000 | 3 → 3 | 16.7% → 16.7% | 0.000000 |
| reference | by_mission | gracefo-d | August 2024 held out | 36 | radial | 18 → 18 | 11 → 11 | 61.1% → 61.1% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-d | August 2024 held out | 36 | in_track | 18 → 18 | 10 → 10 | 55.6% → 55.6% | 0.000000 | 14 → 14 | 77.8% → 77.8% | 0.000000 |
| reference | by_mission | gracefo-d | August 2024 held out | 36 | cross | 18 → 18 | 2 → 2 | 11.1% → 11.1% | 0.000000 | 5 → 5 | 27.8% → 27.8% | 0.000000 |
| reference | by_mission | gracefo-d | August 2024 held out | 48 | radial | 18 → 18 | 10 → 10 | 55.6% → 55.6% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-d | August 2024 held out | 48 | in_track | 18 → 18 | 9 → 9 | 50.0% → 50.0% | 0.000000 | 13 → 13 | 72.2% → 72.2% | 0.000000 |
| reference | by_mission | gracefo-d | August 2024 held out | 48 | cross | 18 → 18 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | gracefo-d | August 2024 held out | 72 | radial | 18 → 18 | 15 → 15 | 83.3% → 83.3% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-d | August 2024 held out | 72 | in_track | 18 → 18 | 8 → 8 | 44.4% → 44.4% | 0.000000 | 11 → 11 | 61.1% → 61.1% | 0.000000 |
| reference | by_mission | gracefo-d | August 2024 held out | 72 | cross | 18 → 18 | 1 → 1 | 5.6% → 5.6% | 0.000000 | 3 → 3 | 16.7% → 16.7% | 0.000000 |
| reference | by_mission | gracefo-d | August 2024 held out | 96 | radial | 18 → 18 | 15 → 15 | 83.3% → 83.3% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-d | August 2024 held out | 96 | in_track | 18 → 18 | 5 → 5 | 27.8% → 27.8% | 0.000000 | 10 → 10 | 55.6% → 55.6% | 0.000000 |
| reference | by_mission | gracefo-d | August 2024 held out | 96 | cross | 18 → 18 | 3 → 3 | 16.7% → 16.7% | 0.000000 | 4 → 4 | 22.2% → 22.2% | 0.000000 |
| reference | by_mission | gracefo-d | August 2024 held out | 120 | radial | 18 → 18 | 10 → 10 | 55.6% → 55.6% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-d | August 2024 held out | 120 | in_track | 18 → 18 | 5 → 5 | 27.8% → 27.8% | 0.000000 | 9 → 9 | 50.0% → 50.0% | 0.000000 |
| reference | by_mission | gracefo-d | August 2024 held out | 120 | cross | 18 → 18 | 3 → 3 | 16.7% → 16.7% | 0.000000 | 13 → 13 | 72.2% → 72.2% | 0.000000 |
| reference | by_mission | gracefo-d | August 2024 held out | 144 | radial | 18 → 18 | 16 → 16 | 88.9% → 88.9% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-d | August 2024 held out | 144 | in_track | 18 → 18 | 6 → 6 | 33.3% → 33.3% | 0.000000 | 7 → 7 | 38.9% → 38.9% | 0.000000 |
| reference | by_mission | gracefo-d | August 2024 held out | 144 | cross | 18 → 18 | 2 → 2 | 11.1% → 11.1% | 0.000000 | 6 → 6 | 33.3% → 33.3% | 0.000000 |
| reference | by_mission | gracefo-d | August 2024 held out | 168 | radial | 18 → 18 | 9 → 9 | 50.0% → 50.0% | 0.000000 | 15 → 15 | 83.3% → 83.3% | 0.000000 |
| reference | by_mission | gracefo-d | August 2024 held out | 168 | in_track | 18 → 18 | 6 → 6 | 33.3% → 33.3% | 0.000000 | 6 → 6 | 33.3% → 33.3% | 0.000000 |
| reference | by_mission | gracefo-d | August 2024 held out | 168 | cross | 18 → 18 | 4 → 4 | 22.2% → 22.2% | 0.000000 | 10 → 10 | 55.6% → 55.6% | 0.000000 |
| reference | by_mission | gracefo-d | October 2024 held out | 6 | radial | 20 → 20 | 14 → 14 | 70.0% → 70.0% | 0.000000 | 18 → 18 | 90.0% → 90.0% | 0.000000 |
| reference | by_mission | gracefo-d | October 2024 held out | 6 | in_track | 20 → 20 | 6 → 6 | 30.0% → 30.0% | 0.000000 | 15 → 15 | 75.0% → 75.0% | 0.000000 |
| reference | by_mission | gracefo-d | October 2024 held out | 6 | cross | 20 → 20 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | gracefo-d | October 2024 held out | 12 | radial | 20 → 20 | 4 → 4 | 20.0% → 20.0% | 0.000000 | 11 → 11 | 55.0% → 55.0% | 0.000000 |
| reference | by_mission | gracefo-d | October 2024 held out | 12 | in_track | 20 → 20 | 7 → 7 | 35.0% → 35.0% | 0.000000 | 9 → 9 | 45.0% → 45.0% | 0.000000 |
| reference | by_mission | gracefo-d | October 2024 held out | 12 | cross | 20 → 20 | 1 → 1 | 5.0% → 5.0% | 0.000000 | 2 → 2 | 10.0% → 10.0% | 0.000000 |
| reference | by_mission | gracefo-d | October 2024 held out | 24 | radial | 20 → 20 | 15 → 15 | 75.0% → 75.0% | 0.000000 | 20 → 20 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-d | October 2024 held out | 24 | in_track | 20 → 20 | 11 → 11 | 55.0% → 55.0% | 0.000000 | 15 → 15 | 75.0% → 75.0% | 0.000000 |
| reference | by_mission | gracefo-d | October 2024 held out | 24 | cross | 20 → 20 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 3 → 3 | 15.0% → 15.0% | 0.000000 |
| reference | by_mission | gracefo-d | October 2024 held out | 36 | radial | 20 → 20 | 5 → 5 | 25.0% → 25.0% | 0.000000 | 18 → 18 | 90.0% → 90.0% | 0.000000 |
| reference | by_mission | gracefo-d | October 2024 held out | 36 | in_track | 20 → 20 | 10 → 10 | 50.0% → 50.0% | 0.000000 | 14 → 14 | 70.0% → 70.0% | 0.000000 |
| reference | by_mission | gracefo-d | October 2024 held out | 36 | cross | 20 → 20 | 1 → 1 | 5.0% → 5.0% | 0.000000 | 1 → 1 | 5.0% → 5.0% | 0.000000 |
| reference | by_mission | gracefo-d | October 2024 held out | 48 | radial | 20 → 20 | 14 → 14 | 70.0% → 70.0% | 0.000000 | 20 → 20 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-d | October 2024 held out | 48 | in_track | 20 → 20 | 10 → 10 | 50.0% → 50.0% | 0.000000 | 14 → 14 | 70.0% → 70.0% | 0.000000 |
| reference | by_mission | gracefo-d | October 2024 held out | 48 | cross | 20 → 20 | 4 → 4 | 20.0% → 20.0% | 0.000000 | 8 → 8 | 40.0% → 40.0% | 0.000000 |
| reference | by_mission | gracefo-d | October 2024 held out | 72 | radial | 20 → 20 | 10 → 10 | 50.0% → 50.0% | 0.000000 | 17 → 17 | 85.0% → 85.0% | 0.000000 |
| reference | by_mission | gracefo-d | October 2024 held out | 72 | in_track | 20 → 20 | 12 → 12 | 60.0% → 60.0% | 0.000000 | 13 → 13 | 65.0% → 65.0% | 0.000000 |
| reference | by_mission | gracefo-d | October 2024 held out | 72 | cross | 20 → 20 | 2 → 2 | 10.0% → 10.0% | 0.000000 | 2 → 2 | 10.0% → 10.0% | 0.000000 |
| reference | by_mission | gracefo-d | October 2024 held out | 96 | radial | 20 → 20 | 15 → 15 | 75.0% → 75.0% | 0.000000 | 18 → 18 | 90.0% → 90.0% | 0.000000 |
| reference | by_mission | gracefo-d | October 2024 held out | 96 | in_track | 20 → 20 | 11 → 11 | 55.0% → 55.0% | 0.000000 | 13 → 13 | 65.0% → 65.0% | 0.000000 |
| reference | by_mission | gracefo-d | October 2024 held out | 96 | cross | 20 → 20 | 5 → 5 | 25.0% → 25.0% | 0.000000 | 10 → 10 | 50.0% → 50.0% | 0.000000 |
| reference | by_mission | gracefo-d | October 2024 held out | 120 | radial | 20 → 20 | 15 → 16 | 75.0% → 80.0% | 5.000000 | 18 → 18 | 90.0% → 90.0% | 0.000000 |
| reference | by_mission | gracefo-d | October 2024 held out | 120 | in_track | 20 → 20 | 12 → 12 | 60.0% → 60.0% | 0.000000 | 13 → 13 | 65.0% → 65.0% | 0.000000 |
| reference | by_mission | gracefo-d | October 2024 held out | 120 | cross | 20 → 20 | 5 → 5 | 25.0% → 25.0% | 0.000000 | 9 → 9 | 45.0% → 45.0% | 0.000000 |
| reference | by_mission | gracefo-d | October 2024 held out | 144 | radial | 20 → 20 | 13 → 13 | 65.0% → 65.0% | 0.000000 | 14 → 17 | 70.0% → 85.0% | 15.000000 |
| reference | by_mission | gracefo-d | October 2024 held out | 144 | in_track | 20 → 20 | 10 → 10 | 50.0% → 50.0% | 0.000000 | 13 → 13 | 65.0% → 65.0% | 0.000000 |
| reference | by_mission | gracefo-d | October 2024 held out | 144 | cross | 20 → 20 | 2 → 2 | 10.0% → 10.0% | 0.000000 | 6 → 6 | 30.0% → 30.0% | 0.000000 |
| reference | by_mission | gracefo-d | October 2024 held out | 168 | radial | 20 → 20 | 13 → 13 | 65.0% → 65.0% | 0.000000 | 14 → 14 | 70.0% → 70.0% | 0.000000 |
| reference | by_mission | gracefo-d | October 2024 held out | 168 | in_track | 20 → 20 | 10 → 10 | 50.0% → 50.0% | 0.000000 | 13 → 13 | 65.0% → 65.0% | 0.000000 |
| reference | by_mission | gracefo-d | October 2024 held out | 168 | cross | 20 → 20 | 12 → 12 | 60.0% → 60.0% | 0.000000 | 17 → 17 | 85.0% → 85.0% | 0.000000 |
| reference | by_mission | gracefo-d | April 2024 control | 6 | radial | 19 → 19 | 3 → 3 | 15.8% → 15.8% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-d | April 2024 control | 6 | in_track | 19 → 19 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 4 → 4 | 21.1% → 21.1% | 0.000000 |
| reference | by_mission | gracefo-d | April 2024 control | 6 | cross | 19 → 19 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | gracefo-d | April 2024 control | 12 | radial | 19 → 19 | 9 → 9 | 47.4% → 47.4% | 0.000000 | 13 → 13 | 68.4% → 68.4% | 0.000000 |
| reference | by_mission | gracefo-d | April 2024 control | 12 | in_track | 19 → 19 | 2 → 2 | 10.5% → 10.5% | 0.000000 | 2 → 2 | 10.5% → 10.5% | 0.000000 |
| reference | by_mission | gracefo-d | April 2024 control | 12 | cross | 19 → 19 | 1 → 1 | 5.3% → 5.3% | 0.000000 | 1 → 1 | 5.3% → 5.3% | 0.000000 |
| reference | by_mission | gracefo-d | April 2024 control | 24 | radial | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-d | April 2024 control | 24 | in_track | 19 → 19 | 16 → 16 | 84.2% → 84.2% | 0.000000 | 18 → 18 | 94.7% → 94.7% | 0.000000 |
| reference | by_mission | gracefo-d | April 2024 control | 24 | cross | 19 → 19 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | gracefo-d | April 2024 control | 36 | radial | 19 → 19 | 12 → 12 | 63.2% → 63.2% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-d | April 2024 control | 36 | in_track | 19 → 19 | 13 → 13 | 68.4% → 68.4% | 0.000000 | 18 → 18 | 94.7% → 94.7% | 0.000000 |
| reference | by_mission | gracefo-d | April 2024 control | 36 | cross | 19 → 19 | 3 → 3 | 15.8% → 15.8% | 0.000000 | 5 → 5 | 26.3% → 26.3% | 0.000000 |
| reference | by_mission | gracefo-d | April 2024 control | 48 | radial | 19 → 19 | 9 → 9 | 47.4% → 47.4% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-d | April 2024 control | 48 | in_track | 19 → 19 | 18 → 18 | 94.7% → 94.7% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-d | April 2024 control | 48 | cross | 19 → 19 | 1 → 1 | 5.3% → 5.3% | 0.000000 | 7 → 7 | 36.8% → 36.8% | 0.000000 |
| reference | by_mission | gracefo-d | April 2024 control | 72 | radial | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-d | April 2024 control | 72 | in_track | 19 → 19 | 18 → 18 | 94.7% → 94.7% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-d | April 2024 control | 72 | cross | 19 → 19 | 6 → 6 | 31.6% → 31.6% | 0.000000 | 10 → 10 | 52.6% → 52.6% | 0.000000 |
| reference | by_mission | gracefo-d | April 2024 control | 96 | radial | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-d | April 2024 control | 96 | in_track | 19 → 19 | 18 → 18 | 94.7% → 94.7% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-d | April 2024 control | 96 | cross | 19 → 19 | 3 → 3 | 15.8% → 15.8% | 0.000000 | 6 → 6 | 31.6% → 31.6% | 0.000000 |
| reference | by_mission | gracefo-d | April 2024 control | 120 | radial | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-d | April 2024 control | 120 | in_track | 19 → 19 | 18 → 18 | 94.7% → 94.7% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-d | April 2024 control | 120 | cross | 19 → 19 | 10 → 10 | 52.6% → 52.6% | 0.000000 | 16 → 16 | 84.2% → 84.2% | 0.000000 |
| reference | by_mission | gracefo-d | April 2024 control | 144 | radial | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-d | April 2024 control | 144 | in_track | 19 → 19 | 18 → 18 | 94.7% → 94.7% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-d | April 2024 control | 144 | cross | 19 → 19 | 9 → 9 | 47.4% → 47.4% | 0.000000 | 17 → 17 | 89.5% → 89.5% | 0.000000 |
| reference | by_mission | gracefo-d | April 2024 control | 168 | radial | 19 → 19 | 9 → 9 | 47.4% → 47.4% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-d | April 2024 control | 168 | in_track | 19 → 19 | 18 → 18 | 94.7% → 94.7% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-d | April 2024 control | 168 | cross | 19 → 19 | 15 → 15 | 78.9% → 78.9% | 0.000000 | 18 → 18 | 94.7% → 94.7% | 0.000000 |
| reference | by_mission | gracefo-d | May 2024 | 6 | radial | 19 → 19 | 8 → 8 | 42.1% → 42.1% | 0.000000 | 18 → 18 | 94.7% → 94.7% | 0.000000 |
| reference | by_mission | gracefo-d | May 2024 | 6 | in_track | 19 → 19 | 1 → 1 | 5.3% → 5.3% | 0.000000 | 5 → 5 | 26.3% → 26.3% | 0.000000 |
| reference | by_mission | gracefo-d | May 2024 | 6 | cross | 19 → 19 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | gracefo-d | May 2024 | 12 | radial | 19 → 19 | 12 → 12 | 63.2% → 63.2% | 0.000000 | 16 → 16 | 84.2% → 84.2% | 0.000000 |
| reference | by_mission | gracefo-d | May 2024 | 12 | in_track | 19 → 19 | 1 → 1 | 5.3% → 5.3% | 0.000000 | 4 → 4 | 21.1% → 21.1% | 0.000000 |
| reference | by_mission | gracefo-d | May 2024 | 12 | cross | 19 → 19 | 3 → 3 | 15.8% → 15.8% | 0.000000 | 3 → 3 | 15.8% → 15.8% | 0.000000 |
| reference | by_mission | gracefo-d | May 2024 | 24 | radial | 19 → 19 | 18 → 18 | 94.7% → 94.7% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-d | May 2024 | 24 | in_track | 19 → 19 | 9 → 9 | 47.4% → 47.4% | 0.000000 | 18 → 18 | 94.7% → 94.7% | 0.000000 |
| reference | by_mission | gracefo-d | May 2024 | 24 | cross | 19 → 19 | 1 → 1 | 5.3% → 5.3% | 0.000000 | 3 → 3 | 15.8% → 15.8% | 0.000000 |
| reference | by_mission | gracefo-d | May 2024 | 36 | radial | 19 → 19 | 8 → 8 | 42.1% → 42.1% | 0.000000 | 18 → 18 | 94.7% → 94.7% | 0.000000 |
| reference | by_mission | gracefo-d | May 2024 | 36 | in_track | 19 → 19 | 14 → 14 | 73.7% → 73.7% | 0.000000 | 16 → 16 | 84.2% → 84.2% | 0.000000 |
| reference | by_mission | gracefo-d | May 2024 | 36 | cross | 19 → 19 | 4 → 4 | 21.1% → 21.1% | 0.000000 | 7 → 7 | 36.8% → 36.8% | 0.000000 |
| reference | by_mission | gracefo-d | May 2024 | 48 | radial | 19 → 19 | 11 → 11 | 57.9% → 57.9% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-d | May 2024 | 48 | in_track | 19 → 19 | 13 → 13 | 68.4% → 68.4% | 0.000000 | 14 → 14 | 73.7% → 73.7% | 0.000000 |
| reference | by_mission | gracefo-d | May 2024 | 48 | cross | 19 → 19 | 3 → 3 | 15.8% → 15.8% | 0.000000 | 9 → 9 | 47.4% → 47.4% | 0.000000 |
| reference | by_mission | gracefo-d | May 2024 | 72 | radial | 16 → 16 | 15 → 15 | 93.8% → 93.8% | 0.000000 | 16 → 16 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-d | May 2024 | 72 | in_track | 16 → 16 | 7 → 7 | 43.8% → 43.8% | 0.000000 | 12 → 12 | 75.0% → 75.0% | 0.000000 |
| reference | by_mission | gracefo-d | May 2024 | 72 | cross | 16 → 16 | 6 → 6 | 37.5% → 37.5% | 0.000000 | 9 → 9 | 56.2% → 56.2% | 0.000000 |
| reference | by_mission | gracefo-d | May 2024 | 96 | radial | 14 → 14 | 14 → 14 | 100.0% → 100.0% | 0.000000 | 14 → 14 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-d | May 2024 | 96 | in_track | 14 → 14 | 7 → 7 | 50.0% → 50.0% | 0.000000 | 12 → 12 | 85.7% → 85.7% | 0.000000 |
| reference | by_mission | gracefo-d | May 2024 | 96 | cross | 14 → 14 | 6 → 6 | 42.9% → 42.9% | 0.000000 | 10 → 10 | 71.4% → 71.4% | 0.000000 |
| reference | by_mission | gracefo-d | May 2024 | 120 | radial | 12 → 12 | 9 → 9 | 75.0% → 75.0% | 0.000000 | 12 → 12 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-d | May 2024 | 120 | in_track | 12 → 12 | 4 → 4 | 33.3% → 33.3% | 0.000000 | 12 → 12 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-d | May 2024 | 120 | cross | 12 → 12 | 7 → 7 | 58.3% → 58.3% | 0.000000 | 12 → 12 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-d | May 2024 | 144 | radial | 9 → 9 | 9 → 9 | 100.0% → 100.0% | 0.000000 | 9 → 9 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-d | May 2024 | 144 | in_track | 9 → 9 | 3 → 3 | 33.3% → 33.3% | 0.000000 | 8 → 8 | 88.9% → 88.9% | 0.000000 |
| reference | by_mission | gracefo-d | May 2024 | 144 | cross | 9 → 9 | 8 → 8 | 88.9% → 88.9% | 0.000000 | 9 → 9 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-d | May 2024 | 168 | radial | 6 → 6 | 4 → 5 | 66.7% → 83.3% | 16.666667 | 6 → 6 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-d | May 2024 | 168 | in_track | 6 → 6 | 3 → 3 | 50.0% → 50.0% | 0.000000 | 6 → 6 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | gracefo-d | May 2024 | 168 | cross | 6 → 6 | 6 → 6 | 100.0% → 100.0% | 0.000000 | 6 → 6 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | August 2024 held out | 6 | radial | 25 → 25 | 2 → 2 | 8.0% → 8.0% | 0.000000 | 4 → 4 | 16.0% → 16.0% | 0.000000 |
| reference | by_mission | hy-2c | August 2024 held out | 6 | in_track | 25 → 25 | 4 → 4 | 16.0% → 16.0% | 0.000000 | 6 → 6 | 24.0% → 24.0% | 0.000000 |
| reference | by_mission | hy-2c | August 2024 held out | 6 | cross | 25 → 25 | 5 → 5 | 20.0% → 20.0% | 0.000000 | 10 → 10 | 40.0% → 40.0% | 0.000000 |
| reference | by_mission | hy-2c | August 2024 held out | 12 | radial | 25 → 25 | 7 → 7 | 28.0% → 28.0% | 0.000000 | 11 → 11 | 44.0% → 44.0% | 0.000000 |
| reference | by_mission | hy-2c | August 2024 held out | 12 | in_track | 25 → 25 | 5 → 5 | 20.0% → 20.0% | 0.000000 | 13 → 13 | 52.0% → 52.0% | 0.000000 |
| reference | by_mission | hy-2c | August 2024 held out | 12 | cross | 25 → 25 | 4 → 4 | 16.0% → 16.0% | 0.000000 | 10 → 10 | 40.0% → 40.0% | 0.000000 |
| reference | by_mission | hy-2c | August 2024 held out | 24 | radial | 25 → 25 | 15 → 15 | 60.0% → 60.0% | 0.000000 | 21 → 21 | 84.0% → 84.0% | 0.000000 |
| reference | by_mission | hy-2c | August 2024 held out | 24 | in_track | 25 → 25 | 17 → 17 | 68.0% → 68.0% | 0.000000 | 24 → 24 | 96.0% → 96.0% | 0.000000 |
| reference | by_mission | hy-2c | August 2024 held out | 24 | cross | 25 → 25 | 5 → 5 | 20.0% → 20.0% | 0.000000 | 17 → 17 | 68.0% → 68.0% | 0.000000 |
| reference | by_mission | hy-2c | August 2024 held out | 36 | radial | 25 → 25 | 19 → 19 | 76.0% → 76.0% | 0.000000 | 25 → 25 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | August 2024 held out | 36 | in_track | 25 → 25 | 22 → 22 | 88.0% → 88.0% | 0.000000 | 25 → 25 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | August 2024 held out | 36 | cross | 25 → 25 | 7 → 7 | 28.0% → 28.0% | 0.000000 | 15 → 15 | 60.0% → 60.0% | 0.000000 |
| reference | by_mission | hy-2c | August 2024 held out | 48 | radial | 25 → 25 | 17 → 17 | 68.0% → 68.0% | 0.000000 | 25 → 25 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | August 2024 held out | 48 | in_track | 25 → 25 | 24 → 24 | 96.0% → 96.0% | 0.000000 | 25 → 25 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | August 2024 held out | 48 | cross | 25 → 25 | 9 → 9 | 36.0% → 36.0% | 0.000000 | 20 → 20 | 80.0% → 80.0% | 0.000000 |
| reference | by_mission | hy-2c | August 2024 held out | 72 | radial | 25 → 25 | 12 → 12 | 48.0% → 48.0% | 0.000000 | 25 → 25 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | August 2024 held out | 72 | in_track | 25 → 25 | 25 → 25 | 100.0% → 100.0% | 0.000000 | 25 → 25 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | August 2024 held out | 72 | cross | 25 → 25 | 10 → 10 | 40.0% → 40.0% | 0.000000 | 25 → 25 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | August 2024 held out | 96 | radial | 25 → 25 | 25 → 25 | 100.0% → 100.0% | 0.000000 | 25 → 25 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | August 2024 held out | 96 | in_track | 25 → 25 | 25 → 25 | 100.0% → 100.0% | 0.000000 | 25 → 25 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | August 2024 held out | 96 | cross | 25 → 25 | 24 → 24 | 96.0% → 96.0% | 0.000000 | 25 → 25 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | August 2024 held out | 120 | radial | 25 → 25 | 25 → 25 | 100.0% → 100.0% | 0.000000 | 25 → 25 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | August 2024 held out | 120 | in_track | 25 → 25 | 25 → 25 | 100.0% → 100.0% | 0.000000 | 25 → 25 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | August 2024 held out | 120 | cross | 25 → 25 | 14 → 14 | 56.0% → 56.0% | 0.000000 | 25 → 25 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | August 2024 held out | 144 | radial | 25 → 25 | 17 → 17 | 68.0% → 68.0% | 0.000000 | 25 → 25 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | August 2024 held out | 144 | in_track | 25 → 25 | 25 → 25 | 100.0% → 100.0% | 0.000000 | 25 → 25 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | August 2024 held out | 144 | cross | 25 → 25 | 2 → 2 | 8.0% → 8.0% | 0.000000 | 25 → 25 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | August 2024 held out | 168 | radial | 22 → 22 | 22 → 22 | 100.0% → 100.0% | 0.000000 | 22 → 22 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | August 2024 held out | 168 | in_track | 22 → 22 | 22 → 22 | 100.0% → 100.0% | 0.000000 | 22 → 22 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | August 2024 held out | 168 | cross | 22 → 22 | 22 → 22 | 100.0% → 100.0% | 0.000000 | 22 → 22 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | October 2024 held out | 6 | radial | 26 → 26 | 4 → 4 | 15.4% → 15.4% | 0.000000 | 9 → 9 | 34.6% → 34.6% | 0.000000 |
| reference | by_mission | hy-2c | October 2024 held out | 6 | in_track | 26 → 26 | 6 → 6 | 23.1% → 23.1% | 0.000000 | 11 → 11 | 42.3% → 42.3% | 0.000000 |
| reference | by_mission | hy-2c | October 2024 held out | 6 | cross | 26 → 26 | 7 → 7 | 26.9% → 26.9% | 0.000000 | 14 → 14 | 53.8% → 53.8% | 0.000000 |
| reference | by_mission | hy-2c | October 2024 held out | 12 | radial | 26 → 26 | 11 → 11 | 42.3% → 42.3% | 0.000000 | 16 → 16 | 61.5% → 61.5% | 0.000000 |
| reference | by_mission | hy-2c | October 2024 held out | 12 | in_track | 26 → 26 | 3 → 3 | 11.5% → 11.5% | 0.000000 | 5 → 5 | 19.2% → 19.2% | 0.000000 |
| reference | by_mission | hy-2c | October 2024 held out | 12 | cross | 26 → 26 | 9 → 9 | 34.6% → 34.6% | 0.000000 | 13 → 13 | 50.0% → 50.0% | 0.000000 |
| reference | by_mission | hy-2c | October 2024 held out | 24 | radial | 26 → 26 | 12 → 12 | 46.2% → 46.2% | 0.000000 | 17 → 17 | 65.4% → 65.4% | 0.000000 |
| reference | by_mission | hy-2c | October 2024 held out | 24 | in_track | 26 → 26 | 11 → 11 | 42.3% → 42.3% | 0.000000 | 17 → 17 | 65.4% → 65.4% | 0.000000 |
| reference | by_mission | hy-2c | October 2024 held out | 24 | cross | 26 → 26 | 11 → 11 | 42.3% → 42.3% | 0.000000 | 17 → 17 | 65.4% → 65.4% | 0.000000 |
| reference | by_mission | hy-2c | October 2024 held out | 36 | radial | 26 → 26 | 15 → 15 | 57.7% → 57.7% | 0.000000 | 26 → 26 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | October 2024 held out | 36 | in_track | 26 → 26 | 19 → 19 | 73.1% → 73.1% | 0.000000 | 24 → 24 | 92.3% → 92.3% | 0.000000 |
| reference | by_mission | hy-2c | October 2024 held out | 36 | cross | 26 → 26 | 15 → 15 | 57.7% → 57.7% | 0.000000 | 24 → 24 | 92.3% → 92.3% | 0.000000 |
| reference | by_mission | hy-2c | October 2024 held out | 48 | radial | 26 → 26 | 23 → 23 | 88.5% → 88.5% | 0.000000 | 26 → 26 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | October 2024 held out | 48 | in_track | 26 → 26 | 21 → 21 | 80.8% → 80.8% | 0.000000 | 24 → 24 | 92.3% → 92.3% | 0.000000 |
| reference | by_mission | hy-2c | October 2024 held out | 48 | cross | 26 → 26 | 9 → 9 | 34.6% → 34.6% | 0.000000 | 26 → 26 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | October 2024 held out | 72 | radial | 26 → 26 | 11 → 11 | 42.3% → 42.3% | 0.000000 | 26 → 26 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | October 2024 held out | 72 | in_track | 26 → 26 | 24 → 24 | 92.3% → 92.3% | 0.000000 | 24 → 24 | 92.3% → 92.3% | 0.000000 |
| reference | by_mission | hy-2c | October 2024 held out | 72 | cross | 26 → 26 | 16 → 16 | 61.5% → 61.5% | 0.000000 | 26 → 26 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | October 2024 held out | 96 | radial | 24 → 24 | 24 → 24 | 100.0% → 100.0% | 0.000000 | 24 → 24 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | October 2024 held out | 96 | in_track | 24 → 24 | 22 → 22 | 91.7% → 91.7% | 0.000000 | 23 → 23 | 95.8% → 95.8% | 0.000000 |
| reference | by_mission | hy-2c | October 2024 held out | 96 | cross | 24 → 24 | 24 → 24 | 100.0% → 100.0% | 0.000000 | 24 → 24 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | October 2024 held out | 120 | radial | 20 → 20 | 20 → 20 | 100.0% → 100.0% | 0.000000 | 20 → 20 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | October 2024 held out | 120 | in_track | 20 → 20 | 18 → 18 | 90.0% → 90.0% | 0.000000 | 19 → 19 | 95.0% → 95.0% | 0.000000 |
| reference | by_mission | hy-2c | October 2024 held out | 120 | cross | 20 → 20 | 20 → 20 | 100.0% → 100.0% | 0.000000 | 20 → 20 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | October 2024 held out | 144 | radial | 16 → 16 | 5 → 5 | 31.2% → 31.2% | 0.000000 | 16 → 16 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | October 2024 held out | 144 | in_track | 16 → 16 | 15 → 15 | 93.8% → 93.8% | 0.000000 | 16 → 16 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | October 2024 held out | 144 | cross | 16 → 16 | 7 → 7 | 43.8% → 43.8% | 0.000000 | 16 → 16 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | October 2024 held out | 168 | radial | 12 → 12 | 12 → 12 | 100.0% → 100.0% | 0.000000 | 12 → 12 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | October 2024 held out | 168 | in_track | 12 → 12 | 11 → 11 | 91.7% → 91.7% | 0.000000 | 12 → 12 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | October 2024 held out | 168 | cross | 12 → 12 | 12 → 12 | 100.0% → 100.0% | 0.000000 | 12 → 12 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | April 2024 control | 6 | radial | 30 → 30 | 2 → 2 | 6.7% → 6.7% | 0.000000 | 5 → 5 | 16.7% → 16.7% | 0.000000 |
| reference | by_mission | hy-2c | April 2024 control | 6 | in_track | 30 → 30 | 10 → 10 | 33.3% → 33.3% | 0.000000 | 20 → 20 | 66.7% → 66.7% | 0.000000 |
| reference | by_mission | hy-2c | April 2024 control | 6 | cross | 30 → 30 | 5 → 5 | 16.7% → 16.7% | 0.000000 | 11 → 11 | 36.7% → 36.7% | 0.000000 |
| reference | by_mission | hy-2c | April 2024 control | 12 | radial | 30 → 30 | 8 → 8 | 26.7% → 26.7% | 0.000000 | 14 → 14 | 46.7% → 46.7% | 0.000000 |
| reference | by_mission | hy-2c | April 2024 control | 12 | in_track | 30 → 30 | 9 → 9 | 30.0% → 30.0% | 0.000000 | 28 → 28 | 93.3% → 93.3% | 0.000000 |
| reference | by_mission | hy-2c | April 2024 control | 12 | cross | 30 → 30 | 13 → 13 | 43.3% → 43.3% | 0.000000 | 18 → 18 | 60.0% → 60.0% | 0.000000 |
| reference | by_mission | hy-2c | April 2024 control | 24 | radial | 30 → 30 | 15 → 15 | 50.0% → 50.0% | 0.000000 | 24 → 24 | 80.0% → 80.0% | 0.000000 |
| reference | by_mission | hy-2c | April 2024 control | 24 | in_track | 30 → 30 | 29 → 29 | 96.7% → 96.7% | 0.000000 | 30 → 30 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | April 2024 control | 24 | cross | 30 → 30 | 8 → 8 | 26.7% → 26.7% | 0.000000 | 19 → 19 | 63.3% → 63.3% | 0.000000 |
| reference | by_mission | hy-2c | April 2024 control | 36 | radial | 30 → 30 | 24 → 24 | 80.0% → 80.0% | 0.000000 | 30 → 30 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | April 2024 control | 36 | in_track | 30 → 30 | 30 → 30 | 100.0% → 100.0% | 0.000000 | 30 → 30 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | April 2024 control | 36 | cross | 30 → 30 | 11 → 11 | 36.7% → 36.7% | 0.000000 | 27 → 27 | 90.0% → 90.0% | 0.000000 |
| reference | by_mission | hy-2c | April 2024 control | 48 | radial | 30 → 30 | 27 → 27 | 90.0% → 90.0% | 0.000000 | 30 → 30 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | April 2024 control | 48 | in_track | 30 → 30 | 30 → 30 | 100.0% → 100.0% | 0.000000 | 30 → 30 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | April 2024 control | 48 | cross | 30 → 30 | 13 → 13 | 43.3% → 43.3% | 0.000000 | 30 → 30 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | April 2024 control | 72 | radial | 30 → 30 | 16 → 16 | 53.3% → 53.3% | 0.000000 | 30 → 30 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | April 2024 control | 72 | in_track | 30 → 30 | 30 → 30 | 100.0% → 100.0% | 0.000000 | 30 → 30 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | April 2024 control | 72 | cross | 30 → 30 | 21 → 21 | 70.0% → 70.0% | 0.000000 | 30 → 30 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | April 2024 control | 96 | radial | 30 → 30 | 30 → 30 | 100.0% → 100.0% | 0.000000 | 30 → 30 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | April 2024 control | 96 | in_track | 30 → 30 | 30 → 30 | 100.0% → 100.0% | 0.000000 | 30 → 30 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | April 2024 control | 96 | cross | 30 → 30 | 29 → 29 | 96.7% → 96.7% | 0.000000 | 30 → 30 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | April 2024 control | 120 | radial | 30 → 30 | 30 → 30 | 100.0% → 100.0% | 0.000000 | 30 → 30 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | April 2024 control | 120 | in_track | 30 → 30 | 30 → 30 | 100.0% → 100.0% | 0.000000 | 30 → 30 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | April 2024 control | 120 | cross | 30 → 30 | 21 → 21 | 70.0% → 70.0% | 0.000000 | 30 → 30 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | April 2024 control | 144 | radial | 30 → 30 | 22 → 22 | 73.3% → 73.3% | 0.000000 | 30 → 30 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | April 2024 control | 144 | in_track | 30 → 30 | 30 → 30 | 100.0% → 100.0% | 0.000000 | 30 → 30 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | April 2024 control | 144 | cross | 30 → 30 | 6 → 6 | 20.0% → 20.0% | 0.000000 | 30 → 30 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | April 2024 control | 168 | radial | 30 → 30 | 30 → 30 | 100.0% → 100.0% | 0.000000 | 30 → 30 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | April 2024 control | 168 | in_track | 30 → 30 | 30 → 30 | 100.0% → 100.0% | 0.000000 | 30 → 30 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | April 2024 control | 168 | cross | 30 → 30 | 30 → 30 | 100.0% → 100.0% | 0.000000 | 30 → 30 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | May 2024 | 6 | radial | 34 → 34 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | hy-2c | May 2024 | 6 | in_track | 34 → 34 | 9 → 9 | 26.5% → 26.5% | 0.000000 | 19 → 19 | 55.9% → 55.9% | 0.000000 |
| reference | by_mission | hy-2c | May 2024 | 6 | cross | 34 → 34 | 12 → 12 | 35.3% → 35.3% | 0.000000 | 17 → 17 | 50.0% → 50.0% | 0.000000 |
| reference | by_mission | hy-2c | May 2024 | 12 | radial | 34 → 34 | 9 → 9 | 26.5% → 26.5% | 0.000000 | 12 → 12 | 35.3% → 35.3% | 0.000000 |
| reference | by_mission | hy-2c | May 2024 | 12 | in_track | 34 → 34 | 11 → 11 | 32.4% → 32.4% | 0.000000 | 16 → 16 | 47.1% → 47.1% | 0.000000 |
| reference | by_mission | hy-2c | May 2024 | 12 | cross | 34 → 34 | 8 → 8 | 23.5% → 23.5% | 0.000000 | 15 → 15 | 44.1% → 44.1% | 0.000000 |
| reference | by_mission | hy-2c | May 2024 | 24 | radial | 34 → 34 | 15 → 15 | 44.1% → 44.1% | 0.000000 | 24 → 24 | 70.6% → 70.6% | 0.000000 |
| reference | by_mission | hy-2c | May 2024 | 24 | in_track | 34 → 34 | 23 → 23 | 67.6% → 67.6% | 0.000000 | 34 → 34 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | May 2024 | 24 | cross | 34 → 34 | 11 → 11 | 32.4% → 32.4% | 0.000000 | 32 → 32 | 94.1% → 94.1% | 0.000000 |
| reference | by_mission | hy-2c | May 2024 | 36 | radial | 34 → 34 | 34 → 34 | 100.0% → 100.0% | 0.000000 | 34 → 34 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | May 2024 | 36 | in_track | 34 → 34 | 34 → 34 | 100.0% → 100.0% | 0.000000 | 34 → 34 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | May 2024 | 36 | cross | 34 → 34 | 21 → 21 | 61.8% → 61.8% | 0.000000 | 30 → 30 | 88.2% → 88.2% | 0.000000 |
| reference | by_mission | hy-2c | May 2024 | 48 | radial | 34 → 34 | 26 → 26 | 76.5% → 76.5% | 0.000000 | 34 → 34 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | May 2024 | 48 | in_track | 34 → 34 | 34 → 34 | 100.0% → 100.0% | 0.000000 | 34 → 34 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | May 2024 | 48 | cross | 34 → 34 | 17 → 17 | 50.0% → 50.0% | 0.000000 | 34 → 34 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | May 2024 | 72 | radial | 29 → 29 | 20 → 20 | 69.0% → 69.0% | 0.000000 | 29 → 29 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | May 2024 | 72 | in_track | 29 → 29 | 29 → 29 | 100.0% → 100.0% | 0.000000 | 29 → 29 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | May 2024 | 72 | cross | 29 → 29 | 12 → 12 | 41.4% → 41.4% | 0.000000 | 29 → 29 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | May 2024 | 96 | radial | 25 → 25 | 25 → 25 | 100.0% → 100.0% | 0.000000 | 25 → 25 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | May 2024 | 96 | in_track | 25 → 25 | 25 → 25 | 100.0% → 100.0% | 0.000000 | 25 → 25 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | May 2024 | 96 | cross | 25 → 25 | 24 → 24 | 96.0% → 96.0% | 0.000000 | 25 → 25 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | May 2024 | 120 | radial | 20 → 20 | 20 → 20 | 100.0% → 100.0% | 0.000000 | 20 → 20 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | May 2024 | 120 | in_track | 20 → 20 | 20 → 20 | 100.0% → 100.0% | 0.000000 | 20 → 20 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | May 2024 | 120 | cross | 20 → 20 | 19 → 19 | 95.0% → 95.0% | 0.000000 | 20 → 20 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | May 2024 | 144 | radial | 15 → 15 | 12 → 12 | 80.0% → 80.0% | 0.000000 | 15 → 15 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | May 2024 | 144 | in_track | 15 → 15 | 15 → 15 | 100.0% → 100.0% | 0.000000 | 15 → 15 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | May 2024 | 144 | cross | 15 → 15 | 1 → 1 | 6.7% → 6.7% | 0.000000 | 15 → 15 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | May 2024 | 168 | radial | 10 → 10 | 10 → 10 | 100.0% → 100.0% | 0.000000 | 10 → 10 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | May 2024 | 168 | in_track | 10 → 10 | 10 → 10 | 100.0% → 100.0% | 0.000000 | 10 → 10 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2c | May 2024 | 168 | cross | 10 → 10 | 10 → 10 | 100.0% → 100.0% | 0.000000 | 10 → 10 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | August 2024 held out | 6 | radial | 23 → 23 | 1 → 1 | 4.3% → 4.3% | 0.000000 | 2 → 2 | 8.7% → 8.7% | 0.000000 |
| reference | by_mission | hy-2d | August 2024 held out | 6 | in_track | 23 → 23 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | hy-2d | August 2024 held out | 6 | cross | 23 → 23 | 3 → 3 | 13.0% → 13.0% | 0.000000 | 11 → 11 | 47.8% → 47.8% | 0.000000 |
| reference | by_mission | hy-2d | August 2024 held out | 12 | radial | 23 → 23 | 6 → 6 | 26.1% → 26.1% | 0.000000 | 10 → 10 | 43.5% → 43.5% | 0.000000 |
| reference | by_mission | hy-2d | August 2024 held out | 12 | in_track | 23 → 23 | 2 → 2 | 8.7% → 8.7% | 0.000000 | 2 → 2 | 8.7% → 8.7% | 0.000000 |
| reference | by_mission | hy-2d | August 2024 held out | 12 | cross | 23 → 23 | 6 → 6 | 26.1% → 26.1% | 0.000000 | 11 → 11 | 47.8% → 47.8% | 0.000000 |
| reference | by_mission | hy-2d | August 2024 held out | 24 | radial | 23 → 23 | 6 → 6 | 26.1% → 26.1% | 0.000000 | 12 → 12 | 52.2% → 52.2% | 0.000000 |
| reference | by_mission | hy-2d | August 2024 held out | 24 | in_track | 23 → 23 | 2 → 2 | 8.7% → 8.7% | 0.000000 | 4 → 4 | 17.4% → 17.4% | 0.000000 |
| reference | by_mission | hy-2d | August 2024 held out | 24 | cross | 23 → 23 | 10 → 10 | 43.5% → 43.5% | 0.000000 | 18 → 18 | 78.3% → 78.3% | 0.000000 |
| reference | by_mission | hy-2d | August 2024 held out | 36 | radial | 22 → 22 | 20 → 20 | 90.9% → 90.9% | 0.000000 | 22 → 22 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | August 2024 held out | 36 | in_track | 22 → 22 | 5 → 5 | 22.7% → 22.7% | 0.000000 | 14 → 14 | 63.6% → 63.6% | 0.000000 |
| reference | by_mission | hy-2d | August 2024 held out | 36 | cross | 22 → 22 | 11 → 11 | 50.0% → 50.0% | 0.000000 | 19 → 19 | 86.4% → 86.4% | 0.000000 |
| reference | by_mission | hy-2d | August 2024 held out | 48 | radial | 20 → 20 | 8 → 8 | 40.0% → 40.0% | 0.000000 | 20 → 20 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | August 2024 held out | 48 | in_track | 20 → 20 | 10 → 10 | 50.0% → 50.0% | 0.000000 | 18 → 18 | 90.0% → 90.0% | 0.000000 |
| reference | by_mission | hy-2d | August 2024 held out | 48 | cross | 20 → 20 | 11 → 11 | 55.0% → 55.0% | 0.000000 | 20 → 20 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | August 2024 held out | 72 | radial | 15 → 15 | 8 → 8 | 53.3% → 53.3% | 0.000000 | 15 → 15 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | August 2024 held out | 72 | in_track | 15 → 15 | 15 → 15 | 100.0% → 100.0% | 0.000000 | 15 → 15 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | August 2024 held out | 72 | cross | 15 → 15 | 7 → 7 | 46.7% → 46.7% | 0.000000 | 15 → 15 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | August 2024 held out | 96 | radial | 11 → 11 | 11 → 11 | 100.0% → 100.0% | 0.000000 | 11 → 11 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | August 2024 held out | 96 | in_track | 11 → 11 | 11 → 11 | 100.0% → 100.0% | 0.000000 | 11 → 11 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | August 2024 held out | 96 | cross | 11 → 11 | 11 → 11 | 100.0% → 100.0% | 0.000000 | 11 → 11 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | August 2024 held out | 120 | radial | 7 → 7 | 7 → 7 | 100.0% → 100.0% | 0.000000 | 7 → 7 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | August 2024 held out | 120 | in_track | 7 → 7 | 7 → 7 | 100.0% → 100.0% | 0.000000 | 7 → 7 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | August 2024 held out | 120 | cross | 7 → 7 | 7 → 7 | 100.0% → 100.0% | 0.000000 | 7 → 7 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | August 2024 held out | 144 | radial | 4 → 4 | 3 → 3 | 75.0% → 75.0% | 0.000000 | 4 → 4 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | August 2024 held out | 144 | in_track | 4 → 4 | 4 → 4 | 100.0% → 100.0% | 0.000000 | 4 → 4 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | August 2024 held out | 144 | cross | 4 → 4 | 3 → 3 | 75.0% → 75.0% | 0.000000 | 4 → 4 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | August 2024 held out | 168 | radial | 0 → 0 | 0 → 0 | — → — | — | 0 → 0 | — → — | — |
| reference | by_mission | hy-2d | August 2024 held out | 168 | in_track | 0 → 0 | 0 → 0 | — → — | — | 0 → 0 | — → — | — |
| reference | by_mission | hy-2d | August 2024 held out | 168 | cross | 0 → 0 | 0 → 0 | — → — | — | 0 → 0 | — → — | — |
| reference | by_mission | hy-2d | October 2024 held out | 6 | radial | 17 → 17 | 4 → 4 | 23.5% → 23.5% | 0.000000 | 5 → 5 | 29.4% → 29.4% | 0.000000 |
| reference | by_mission | hy-2d | October 2024 held out | 6 | in_track | 17 → 17 | 1 → 1 | 5.9% → 5.9% | 0.000000 | 2 → 2 | 11.8% → 11.8% | 0.000000 |
| reference | by_mission | hy-2d | October 2024 held out | 6 | cross | 17 → 17 | 4 → 4 | 23.5% → 23.5% | 0.000000 | 8 → 8 | 47.1% → 47.1% | 0.000000 |
| reference | by_mission | hy-2d | October 2024 held out | 12 | radial | 17 → 17 | 5 → 5 | 29.4% → 29.4% | 0.000000 | 5 → 5 | 29.4% → 29.4% | 0.000000 |
| reference | by_mission | hy-2d | October 2024 held out | 12 | in_track | 17 → 17 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 2 → 2 | 11.8% → 11.8% | 0.000000 |
| reference | by_mission | hy-2d | October 2024 held out | 12 | cross | 17 → 17 | 4 → 4 | 23.5% → 23.5% | 0.000000 | 7 → 7 | 41.2% → 41.2% | 0.000000 |
| reference | by_mission | hy-2d | October 2024 held out | 24 | radial | 14 → 14 | 6 → 6 | 42.9% → 42.9% | 0.000000 | 11 → 11 | 78.6% → 78.6% | 0.000000 |
| reference | by_mission | hy-2d | October 2024 held out | 24 | in_track | 14 → 14 | 3 → 3 | 21.4% → 21.4% | 0.000000 | 6 → 6 | 42.9% → 42.9% | 0.000000 |
| reference | by_mission | hy-2d | October 2024 held out | 24 | cross | 14 → 14 | 3 → 3 | 21.4% → 21.4% | 0.000000 | 6 → 6 | 42.9% → 42.9% | 0.000000 |
| reference | by_mission | hy-2d | October 2024 held out | 36 | radial | 13 → 13 | 10 → 10 | 76.9% → 76.9% | 0.000000 | 13 → 13 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | October 2024 held out | 36 | in_track | 13 → 13 | 4 → 4 | 30.8% → 30.8% | 0.000000 | 4 → 4 | 30.8% → 30.8% | 0.000000 |
| reference | by_mission | hy-2d | October 2024 held out | 36 | cross | 13 → 13 | 4 → 4 | 30.8% → 30.8% | 0.000000 | 8 → 8 | 61.5% → 61.5% | 0.000000 |
| reference | by_mission | hy-2d | October 2024 held out | 48 | radial | 11 → 11 | 8 → 8 | 72.7% → 72.7% | 0.000000 | 11 → 11 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | October 2024 held out | 48 | in_track | 11 → 11 | 5 → 5 | 45.5% → 45.5% | 0.000000 | 9 → 9 | 81.8% → 81.8% | 0.000000 |
| reference | by_mission | hy-2d | October 2024 held out | 48 | cross | 11 → 11 | 3 → 3 | 27.3% → 27.3% | 0.000000 | 8 → 8 | 72.7% → 72.7% | 0.000000 |
| reference | by_mission | hy-2d | October 2024 held out | 72 | radial | 7 → 7 | 3 → 3 | 42.9% → 42.9% | 0.000000 | 7 → 7 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | October 2024 held out | 72 | in_track | 7 → 7 | 3 → 3 | 42.9% → 42.9% | 0.000000 | 7 → 7 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | October 2024 held out | 72 | cross | 7 → 7 | 5 → 5 | 71.4% → 71.4% | 0.000000 | 7 → 7 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | October 2024 held out | 96 | radial | 2 → 2 | 1 → 1 | 50.0% → 50.0% | 0.000000 | 2 → 2 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | October 2024 held out | 96 | in_track | 2 → 2 | 2 → 2 | 100.0% → 100.0% | 0.000000 | 2 → 2 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | October 2024 held out | 96 | cross | 2 → 2 | 2 → 2 | 100.0% → 100.0% | 0.000000 | 2 → 2 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | October 2024 held out | 120 | radial | 2 → 2 | 2 → 2 | 100.0% → 100.0% | 0.000000 | 2 → 2 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | October 2024 held out | 120 | in_track | 2 → 2 | 2 → 2 | 100.0% → 100.0% | 0.000000 | 2 → 2 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | October 2024 held out | 120 | cross | 2 → 2 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 2 → 2 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | October 2024 held out | 144 | radial | 2 → 2 | 1 → 1 | 50.0% → 50.0% | 0.000000 | 2 → 2 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | October 2024 held out | 144 | in_track | 2 → 2 | 1 → 1 | 50.0% → 50.0% | 0.000000 | 1 → 1 | 50.0% → 50.0% | 0.000000 |
| reference | by_mission | hy-2d | October 2024 held out | 144 | cross | 2 → 2 | 1 → 1 | 50.0% → 50.0% | 0.000000 | 2 → 2 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | October 2024 held out | 168 | radial | 2 → 2 | 2 → 2 | 100.0% → 100.0% | 0.000000 | 2 → 2 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | October 2024 held out | 168 | in_track | 2 → 2 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | hy-2d | October 2024 held out | 168 | cross | 2 → 2 | 2 → 2 | 100.0% → 100.0% | 0.000000 | 2 → 2 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | April 2024 control | 6 | radial | 27 → 27 | 2 → 2 | 7.4% → 7.4% | 0.000000 | 7 → 7 | 25.9% → 25.9% | 0.000000 |
| reference | by_mission | hy-2d | April 2024 control | 6 | in_track | 27 → 27 | 3 → 3 | 11.1% → 11.1% | 0.000000 | 14 → 14 | 51.9% → 51.9% | 0.000000 |
| reference | by_mission | hy-2d | April 2024 control | 6 | cross | 27 → 27 | 8 → 8 | 29.6% → 29.6% | 0.000000 | 13 → 13 | 48.1% → 48.1% | 0.000000 |
| reference | by_mission | hy-2d | April 2024 control | 12 | radial | 27 → 27 | 8 → 8 | 29.6% → 29.6% | 0.000000 | 9 → 9 | 33.3% → 33.3% | 0.000000 |
| reference | by_mission | hy-2d | April 2024 control | 12 | in_track | 27 → 27 | 6 → 6 | 22.2% → 22.2% | 0.000000 | 15 → 15 | 55.6% → 55.6% | 0.000000 |
| reference | by_mission | hy-2d | April 2024 control | 12 | cross | 27 → 27 | 5 → 5 | 18.5% → 18.5% | 0.000000 | 13 → 13 | 48.1% → 48.1% | 0.000000 |
| reference | by_mission | hy-2d | April 2024 control | 24 | radial | 27 → 27 | 13 → 13 | 48.1% → 48.1% | 0.000000 | 26 → 26 | 96.3% → 96.3% | 0.000000 |
| reference | by_mission | hy-2d | April 2024 control | 24 | in_track | 27 → 27 | 25 → 25 | 92.6% → 92.6% | 0.000000 | 27 → 27 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | April 2024 control | 24 | cross | 27 → 27 | 5 → 5 | 18.5% → 18.5% | 0.000000 | 20 → 20 | 74.1% → 74.1% | 0.000000 |
| reference | by_mission | hy-2d | April 2024 control | 36 | radial | 27 → 27 | 20 → 20 | 74.1% → 74.1% | 0.000000 | 27 → 27 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | April 2024 control | 36 | in_track | 27 → 27 | 26 → 26 | 96.3% → 96.3% | 0.000000 | 27 → 27 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | April 2024 control | 36 | cross | 27 → 27 | 9 → 9 | 33.3% → 33.3% | 0.000000 | 20 → 20 | 74.1% → 74.1% | 0.000000 |
| reference | by_mission | hy-2d | April 2024 control | 48 | radial | 27 → 27 | 13 → 13 | 48.1% → 48.1% | 0.000000 | 27 → 27 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | April 2024 control | 48 | in_track | 27 → 27 | 27 → 27 | 100.0% → 100.0% | 0.000000 | 27 → 27 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | April 2024 control | 48 | cross | 27 → 27 | 11 → 11 | 40.7% → 40.7% | 0.000000 | 18 → 18 | 66.7% → 66.7% | 0.000000 |
| reference | by_mission | hy-2d | April 2024 control | 72 | radial | 27 → 27 | 9 → 9 | 33.3% → 33.3% | 0.000000 | 27 → 27 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | April 2024 control | 72 | in_track | 27 → 27 | 27 → 27 | 100.0% → 100.0% | 0.000000 | 27 → 27 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | April 2024 control | 72 | cross | 27 → 27 | 7 → 7 | 25.9% → 25.9% | 0.000000 | 27 → 27 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | April 2024 control | 96 | radial | 27 → 27 | 27 → 27 | 100.0% → 100.0% | 0.000000 | 27 → 27 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | April 2024 control | 96 | in_track | 27 → 27 | 27 → 27 | 100.0% → 100.0% | 0.000000 | 27 → 27 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | April 2024 control | 96 | cross | 27 → 27 | 27 → 27 | 100.0% → 100.0% | 0.000000 | 27 → 27 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | April 2024 control | 120 | radial | 27 → 27 | 27 → 27 | 100.0% → 100.0% | 0.000000 | 27 → 27 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | April 2024 control | 120 | in_track | 27 → 27 | 27 → 27 | 100.0% → 100.0% | 0.000000 | 27 → 27 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | April 2024 control | 120 | cross | 27 → 27 | 10 → 10 | 37.0% → 37.0% | 0.000000 | 27 → 27 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | April 2024 control | 144 | radial | 27 → 27 | 14 → 14 | 51.9% → 51.9% | 0.000000 | 27 → 27 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | April 2024 control | 144 | in_track | 27 → 27 | 27 → 27 | 100.0% → 100.0% | 0.000000 | 27 → 27 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | April 2024 control | 144 | cross | 27 → 27 | 6 → 6 | 22.2% → 22.2% | 0.000000 | 27 → 27 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | April 2024 control | 168 | radial | 27 → 27 | 27 → 27 | 100.0% → 100.0% | 0.000000 | 27 → 27 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | April 2024 control | 168 | in_track | 27 → 27 | 27 → 27 | 100.0% → 100.0% | 0.000000 | 27 → 27 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | April 2024 control | 168 | cross | 27 → 27 | 27 → 27 | 100.0% → 100.0% | 0.000000 | 27 → 27 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | May 2024 | 6 | radial | 24 → 24 | 2 → 2 | 8.3% → 8.3% | 0.000000 | 10 → 10 | 41.7% → 41.7% | 0.000000 |
| reference | by_mission | hy-2d | May 2024 | 6 | in_track | 24 → 24 | 5 → 5 | 20.8% → 20.8% | 0.000000 | 7 → 7 | 29.2% → 29.2% | 0.000000 |
| reference | by_mission | hy-2d | May 2024 | 6 | cross | 24 → 24 | 6 → 6 | 25.0% → 25.0% | 0.000000 | 9 → 9 | 37.5% → 37.5% | 0.000000 |
| reference | by_mission | hy-2d | May 2024 | 12 | radial | 22 → 22 | 5 → 5 | 22.7% → 22.7% | 0.000000 | 11 → 11 | 50.0% → 50.0% | 0.000000 |
| reference | by_mission | hy-2d | May 2024 | 12 | in_track | 22 → 22 | 1 → 1 | 4.5% → 4.5% | 0.000000 | 3 → 3 | 13.6% → 13.6% | 0.000000 |
| reference | by_mission | hy-2d | May 2024 | 12 | cross | 22 → 22 | 4 → 4 | 18.2% → 18.2% | 0.000000 | 11 → 11 | 50.0% → 50.0% | 0.000000 |
| reference | by_mission | hy-2d | May 2024 | 24 | radial | 20 → 20 | 9 → 9 | 45.0% → 45.0% | 0.000000 | 12 → 12 | 60.0% → 60.0% | 0.000000 |
| reference | by_mission | hy-2d | May 2024 | 24 | in_track | 20 → 20 | 5 → 5 | 25.0% → 25.0% | 0.000000 | 9 → 9 | 45.0% → 45.0% | 0.000000 |
| reference | by_mission | hy-2d | May 2024 | 24 | cross | 20 → 20 | 5 → 5 | 25.0% → 25.0% | 0.000000 | 8 → 8 | 40.0% → 40.0% | 0.000000 |
| reference | by_mission | hy-2d | May 2024 | 36 | radial | 19 → 19 | 13 → 13 | 68.4% → 68.4% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | May 2024 | 36 | in_track | 19 → 19 | 12 → 12 | 63.2% → 63.2% | 0.000000 | 18 → 18 | 94.7% → 94.7% | 0.000000 |
| reference | by_mission | hy-2d | May 2024 | 36 | cross | 19 → 19 | 7 → 7 | 36.8% → 36.8% | 0.000000 | 13 → 13 | 68.4% → 68.4% | 0.000000 |
| reference | by_mission | hy-2d | May 2024 | 48 | radial | 19 → 19 | 15 → 15 | 78.9% → 78.9% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | May 2024 | 48 | in_track | 19 → 19 | 17 → 17 | 89.5% → 89.5% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | May 2024 | 48 | cross | 19 → 19 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 13 → 13 | 68.4% → 68.4% | 0.000000 |
| reference | by_mission | hy-2d | May 2024 | 72 | radial | 19 → 19 | 11 → 11 | 57.9% → 57.9% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | May 2024 | 72 | in_track | 19 → 19 | 18 → 18 | 94.7% → 94.7% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | May 2024 | 72 | cross | 19 → 19 | 12 → 12 | 63.2% → 63.2% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | May 2024 | 96 | radial | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | May 2024 | 96 | in_track | 19 → 19 | 16 → 16 | 84.2% → 84.2% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | May 2024 | 96 | cross | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | May 2024 | 120 | radial | 19 → 19 | 18 → 18 | 94.7% → 94.7% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | May 2024 | 120 | in_track | 19 → 19 | 18 → 18 | 94.7% → 94.7% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | May 2024 | 120 | cross | 19 → 19 | 5 → 5 | 26.3% → 26.3% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | May 2024 | 144 | radial | 19 → 19 | 11 → 11 | 57.9% → 57.9% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | May 2024 | 144 | in_track | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | May 2024 | 144 | cross | 19 → 19 | 10 → 10 | 52.6% → 52.6% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | May 2024 | 168 | radial | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | May 2024 | 168 | in_track | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | hy-2d | May 2024 | 168 | cross | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | August 2024 held out | 6 | radial | 17 → 17 | 12 → 12 | 70.6% → 70.6% | 0.000000 | 14 → 14 | 82.4% → 82.4% | 0.000000 |
| reference | by_mission | jason-3 | August 2024 held out | 6 | in_track | 17 → 17 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | jason-3 | August 2024 held out | 6 | cross | 17 → 17 | 3 → 3 | 17.6% → 17.6% | 0.000000 | 5 → 5 | 29.4% → 29.4% | 0.000000 |
| reference | by_mission | jason-3 | August 2024 held out | 12 | radial | 17 → 17 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 3 → 3 | 17.6% → 17.6% | 0.000000 |
| reference | by_mission | jason-3 | August 2024 held out | 12 | in_track | 17 → 17 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 1 → 1 | 5.9% → 5.9% | 0.000000 |
| reference | by_mission | jason-3 | August 2024 held out | 12 | cross | 17 → 17 | 1 → 1 | 5.9% → 5.9% | 0.000000 | 5 → 5 | 29.4% → 29.4% | 0.000000 |
| reference | by_mission | jason-3 | August 2024 held out | 24 | radial | 17 → 17 | 2 → 2 | 11.8% → 11.8% | 0.000000 | 16 → 16 | 94.1% → 94.1% | 0.000000 |
| reference | by_mission | jason-3 | August 2024 held out | 24 | in_track | 17 → 17 | 1 → 1 | 5.9% → 5.9% | 0.000000 | 2 → 2 | 11.8% → 11.8% | 0.000000 |
| reference | by_mission | jason-3 | August 2024 held out | 24 | cross | 17 → 17 | 3 → 3 | 17.6% → 17.6% | 0.000000 | 6 → 6 | 35.3% → 35.3% | 0.000000 |
| reference | by_mission | jason-3 | August 2024 held out | 36 | radial | 17 → 17 | 4 → 4 | 23.5% → 23.5% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | August 2024 held out | 36 | in_track | 17 → 17 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | jason-3 | August 2024 held out | 36 | cross | 17 → 17 | 7 → 7 | 41.2% → 41.2% | 0.000000 | 10 → 10 | 58.8% → 58.8% | 0.000000 |
| reference | by_mission | jason-3 | August 2024 held out | 48 | radial | 17 → 17 | 3 → 3 | 17.6% → 17.6% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | August 2024 held out | 48 | in_track | 17 → 17 | 2 → 2 | 11.8% → 11.8% | 0.000000 | 8 → 8 | 47.1% → 47.1% | 0.000000 |
| reference | by_mission | jason-3 | August 2024 held out | 48 | cross | 17 → 17 | 8 → 8 | 47.1% → 47.1% | 0.000000 | 13 → 13 | 76.5% → 76.5% | 0.000000 |
| reference | by_mission | jason-3 | August 2024 held out | 72 | radial | 17 → 17 | 15 → 15 | 88.2% → 88.2% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | August 2024 held out | 72 | in_track | 17 → 17 | 5 → 5 | 29.4% → 29.4% | 0.000000 | 7 → 7 | 41.2% → 41.2% | 0.000000 |
| reference | by_mission | jason-3 | August 2024 held out | 72 | cross | 17 → 17 | 11 → 11 | 64.7% → 64.7% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | August 2024 held out | 96 | radial | 17 → 17 | 17 → 17 | 100.0% → 100.0% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | August 2024 held out | 96 | in_track | 17 → 17 | 3 → 3 | 17.6% → 17.6% | 0.000000 | 6 → 6 | 35.3% → 35.3% | 0.000000 |
| reference | by_mission | jason-3 | August 2024 held out | 96 | cross | 17 → 17 | 9 → 9 | 52.9% → 52.9% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | August 2024 held out | 120 | radial | 17 → 17 | 16 → 16 | 94.1% → 94.1% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | August 2024 held out | 120 | in_track | 17 → 17 | 3 → 3 | 17.6% → 17.6% | 0.000000 | 9 → 9 | 52.9% → 52.9% | 0.000000 |
| reference | by_mission | jason-3 | August 2024 held out | 120 | cross | 17 → 17 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | August 2024 held out | 144 | radial | 17 → 17 | 17 → 17 | 100.0% → 100.0% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | August 2024 held out | 144 | in_track | 17 → 17 | 4 → 4 | 23.5% → 23.5% | 0.000000 | 9 → 9 | 52.9% → 52.9% | 0.000000 |
| reference | by_mission | jason-3 | August 2024 held out | 144 | cross | 17 → 17 | 13 → 13 | 76.5% → 76.5% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | August 2024 held out | 168 | radial | 17 → 17 | 17 → 17 | 100.0% → 100.0% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | August 2024 held out | 168 | in_track | 17 → 17 | 6 → 6 | 35.3% → 35.3% | 0.000000 | 10 → 10 | 58.8% → 58.8% | 0.000000 |
| reference | by_mission | jason-3 | August 2024 held out | 168 | cross | 17 → 17 | 16 → 16 | 94.1% → 94.1% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | October 2024 held out | 6 | radial | 17 → 17 | 7 → 7 | 41.2% → 41.2% | 0.000000 | 10 → 10 | 58.8% → 58.8% | 0.000000 |
| reference | by_mission | jason-3 | October 2024 held out | 6 | in_track | 17 → 17 | 11 → 11 | 64.7% → 64.7% | 0.000000 | 12 → 12 | 70.6% → 70.6% | 0.000000 |
| reference | by_mission | jason-3 | October 2024 held out | 6 | cross | 17 → 17 | 4 → 4 | 23.5% → 23.5% | 0.000000 | 9 → 9 | 52.9% → 52.9% | 0.000000 |
| reference | by_mission | jason-3 | October 2024 held out | 12 | radial | 17 → 17 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | jason-3 | October 2024 held out | 12 | in_track | 17 → 17 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 1 → 1 | 5.9% → 5.9% | 0.000000 |
| reference | by_mission | jason-3 | October 2024 held out | 12 | cross | 17 → 17 | 4 → 4 | 23.5% → 23.5% | 0.000000 | 9 → 9 | 52.9% → 52.9% | 0.000000 |
| reference | by_mission | jason-3 | October 2024 held out | 24 | radial | 17 → 17 | 9 → 9 | 52.9% → 52.9% | 0.000000 | 9 → 9 | 52.9% → 52.9% | 0.000000 |
| reference | by_mission | jason-3 | October 2024 held out | 24 | in_track | 17 → 17 | 9 → 9 | 52.9% → 52.9% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | October 2024 held out | 24 | cross | 17 → 17 | 4 → 4 | 23.5% → 23.5% | 0.000000 | 12 → 12 | 70.6% → 70.6% | 0.000000 |
| reference | by_mission | jason-3 | October 2024 held out | 36 | radial | 17 → 17 | 16 → 16 | 94.1% → 94.1% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | October 2024 held out | 36 | in_track | 17 → 17 | 9 → 9 | 52.9% → 52.9% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | October 2024 held out | 36 | cross | 17 → 17 | 7 → 7 | 41.2% → 41.2% | 0.000000 | 10 → 10 | 58.8% → 58.8% | 0.000000 |
| reference | by_mission | jason-3 | October 2024 held out | 48 | radial | 17 → 17 | 9 → 9 | 52.9% → 52.9% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | October 2024 held out | 48 | in_track | 17 → 17 | 17 → 17 | 100.0% → 100.0% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | October 2024 held out | 48 | cross | 17 → 17 | 5 → 5 | 29.4% → 29.4% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | October 2024 held out | 72 | radial | 17 → 17 | 9 → 9 | 52.9% → 52.9% | 0.000000 | 10 → 10 | 58.8% → 58.8% | 0.000000 |
| reference | by_mission | jason-3 | October 2024 held out | 72 | in_track | 17 → 17 | 17 → 17 | 100.0% → 100.0% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | October 2024 held out | 72 | cross | 17 → 17 | 17 → 17 | 100.0% → 100.0% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | October 2024 held out | 96 | radial | 17 → 17 | 17 → 17 | 100.0% → 100.0% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | October 2024 held out | 96 | in_track | 17 → 17 | 17 → 17 | 100.0% → 100.0% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | October 2024 held out | 96 | cross | 17 → 17 | 17 → 17 | 100.0% → 100.0% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | October 2024 held out | 120 | radial | 17 → 17 | 1 → 1 | 5.9% → 5.9% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | October 2024 held out | 120 | in_track | 17 → 17 | 17 → 17 | 100.0% → 100.0% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | October 2024 held out | 120 | cross | 17 → 17 | 13 → 13 | 76.5% → 76.5% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | October 2024 held out | 144 | radial | 17 → 17 | 9 → 9 | 52.9% → 52.9% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | October 2024 held out | 144 | in_track | 17 → 17 | 17 → 17 | 100.0% → 100.0% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | October 2024 held out | 144 | cross | 17 → 17 | 17 → 17 | 100.0% → 100.0% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | October 2024 held out | 168 | radial | 17 → 17 | 17 → 17 | 100.0% → 100.0% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | October 2024 held out | 168 | in_track | 17 → 17 | 17 → 17 | 100.0% → 100.0% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | October 2024 held out | 168 | cross | 17 → 17 | 17 → 17 | 100.0% → 100.0% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | April 2024 control | 6 | radial | 19 → 19 | 13 → 13 | 68.4% → 68.4% | 0.000000 | 16 → 16 | 84.2% → 84.2% | 0.000000 |
| reference | by_mission | jason-3 | April 2024 control | 6 | in_track | 19 → 19 | 4 → 4 | 21.1% → 21.1% | 0.000000 | 8 → 8 | 42.1% → 42.1% | 0.000000 |
| reference | by_mission | jason-3 | April 2024 control | 6 | cross | 19 → 19 | 5 → 5 | 26.3% → 26.3% | 0.000000 | 11 → 11 | 57.9% → 57.9% | 0.000000 |
| reference | by_mission | jason-3 | April 2024 control | 12 | radial | 19 → 19 | 2 → 2 | 10.5% → 10.5% | 0.000000 | 3 → 3 | 15.8% → 15.8% | 0.000000 |
| reference | by_mission | jason-3 | April 2024 control | 12 | in_track | 19 → 19 | 1 → 1 | 5.3% → 5.3% | 0.000000 | 4 → 4 | 21.1% → 21.1% | 0.000000 |
| reference | by_mission | jason-3 | April 2024 control | 12 | cross | 19 → 19 | 1 → 1 | 5.3% → 5.3% | 0.000000 | 4 → 4 | 21.1% → 21.1% | 0.000000 |
| reference | by_mission | jason-3 | April 2024 control | 24 | radial | 19 → 19 | 4 → 4 | 21.1% → 21.1% | 0.000000 | 14 → 14 | 73.7% → 73.7% | 0.000000 |
| reference | by_mission | jason-3 | April 2024 control | 24 | in_track | 19 → 19 | 11 → 11 | 57.9% → 57.9% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | April 2024 control | 24 | cross | 19 → 19 | 2 → 2 | 10.5% → 10.5% | 0.000000 | 15 → 15 | 78.9% → 78.9% | 0.000000 |
| reference | by_mission | jason-3 | April 2024 control | 36 | radial | 19 → 19 | 12 → 12 | 63.2% → 63.2% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | April 2024 control | 36 | in_track | 19 → 19 | 9 → 9 | 47.4% → 47.4% | 0.000000 | 18 → 18 | 94.7% → 94.7% | 0.000000 |
| reference | by_mission | jason-3 | April 2024 control | 36 | cross | 19 → 19 | 9 → 9 | 47.4% → 47.4% | 0.000000 | 18 → 18 | 94.7% → 94.7% | 0.000000 |
| reference | by_mission | jason-3 | April 2024 control | 48 | radial | 19 → 19 | 8 → 8 | 42.1% → 42.1% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | April 2024 control | 48 | in_track | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | April 2024 control | 48 | cross | 19 → 19 | 15 → 15 | 78.9% → 78.9% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | April 2024 control | 72 | radial | 19 → 19 | 18 → 18 | 94.7% → 94.7% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | April 2024 control | 72 | in_track | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | April 2024 control | 72 | cross | 19 → 19 | 12 → 12 | 63.2% → 63.2% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | April 2024 control | 96 | radial | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | April 2024 control | 96 | in_track | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | April 2024 control | 96 | cross | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | April 2024 control | 120 | radial | 19 → 19 | 18 → 18 | 94.7% → 94.7% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | April 2024 control | 120 | in_track | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | April 2024 control | 120 | cross | 19 → 19 | 3 → 3 | 15.8% → 15.8% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | April 2024 control | 144 | radial | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | April 2024 control | 144 | in_track | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | April 2024 control | 144 | cross | 19 → 19 | 16 → 16 | 84.2% → 84.2% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | April 2024 control | 168 | radial | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | April 2024 control | 168 | in_track | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | April 2024 control | 168 | cross | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | May 2024 | 6 | radial | 15 → 15 | 1 → 1 | 6.7% → 6.7% | 0.000000 | 6 → 6 | 40.0% → 40.0% | 0.000000 |
| reference | by_mission | jason-3 | May 2024 | 6 | in_track | 15 → 15 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | jason-3 | May 2024 | 6 | cross | 15 → 15 | 3 → 3 | 20.0% → 20.0% | 0.000000 | 7 → 7 | 46.7% → 46.7% | 0.000000 |
| reference | by_mission | jason-3 | May 2024 | 12 | radial | 14 → 14 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 1 → 1 | 7.1% → 7.1% | 0.000000 |
| reference | by_mission | jason-3 | May 2024 | 12 | in_track | 14 → 14 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 1 → 1 | 7.1% → 7.1% | 0.000000 |
| reference | by_mission | jason-3 | May 2024 | 12 | cross | 14 → 14 | 6 → 6 | 42.9% → 42.9% | 0.000000 | 9 → 9 | 64.3% → 64.3% | 0.000000 |
| reference | by_mission | jason-3 | May 2024 | 24 | radial | 13 → 13 | 6 → 6 | 46.2% → 46.2% | 0.000000 | 11 → 11 | 84.6% → 84.6% | 0.000000 |
| reference | by_mission | jason-3 | May 2024 | 24 | in_track | 13 → 13 | 2 → 2 | 15.4% → 15.4% | 0.000000 | 2 → 2 | 15.4% → 15.4% | 0.000000 |
| reference | by_mission | jason-3 | May 2024 | 24 | cross | 13 → 13 | 8 → 8 | 61.5% → 61.5% | 0.000000 | 10 → 10 | 76.9% → 76.9% | 0.000000 |
| reference | by_mission | jason-3 | May 2024 | 36 | radial | 11 → 11 | 10 → 10 | 90.9% → 90.9% | 0.000000 | 11 → 11 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | May 2024 | 36 | in_track | 11 → 11 | 3 → 3 | 27.3% → 27.3% | 0.000000 | 3 → 3 | 27.3% → 27.3% | 0.000000 |
| reference | by_mission | jason-3 | May 2024 | 36 | cross | 11 → 11 | 5 → 5 | 45.5% → 45.5% | 0.000000 | 8 → 8 | 72.7% → 72.7% | 0.000000 |
| reference | by_mission | jason-3 | May 2024 | 48 | radial | 10 → 10 | 7 → 7 | 70.0% → 70.0% | 0.000000 | 10 → 10 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | May 2024 | 48 | in_track | 10 → 10 | 5 → 5 | 50.0% → 50.0% | 0.000000 | 8 → 8 | 80.0% → 80.0% | 0.000000 |
| reference | by_mission | jason-3 | May 2024 | 48 | cross | 10 → 10 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 7 → 7 | 70.0% → 70.0% | 0.000000 |
| reference | by_mission | jason-3 | May 2024 | 72 | radial | 8 → 8 | 6 → 6 | 75.0% → 75.0% | 0.000000 | 8 → 8 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | May 2024 | 72 | in_track | 8 → 8 | 6 → 6 | 75.0% → 75.0% | 0.000000 | 6 → 6 | 75.0% → 75.0% | 0.000000 |
| reference | by_mission | jason-3 | May 2024 | 72 | cross | 8 → 8 | 7 → 7 | 87.5% → 87.5% | 0.000000 | 8 → 8 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | May 2024 | 96 | radial | 5 → 5 | 5 → 5 | 100.0% → 100.0% | 0.000000 | 5 → 5 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | May 2024 | 96 | in_track | 5 → 5 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 3 → 3 | 60.0% → 60.0% | 0.000000 |
| reference | by_mission | jason-3 | May 2024 | 96 | cross | 5 → 5 | 3 → 3 | 60.0% → 60.0% | 0.000000 | 5 → 5 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | May 2024 | 120 | radial | 5 → 5 | 4 → 4 | 80.0% → 80.0% | 0.000000 | 5 → 5 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | May 2024 | 120 | in_track | 5 → 5 | 1 → 1 | 20.0% → 20.0% | 0.000000 | 3 → 3 | 60.0% → 60.0% | 0.000000 |
| reference | by_mission | jason-3 | May 2024 | 120 | cross | 5 → 5 | 3 → 3 | 60.0% → 60.0% | 0.000000 | 5 → 5 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | May 2024 | 144 | radial | 5 → 5 | 4 → 4 | 80.0% → 80.0% | 0.000000 | 5 → 5 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | May 2024 | 144 | in_track | 5 → 5 | 1 → 1 | 20.0% → 20.0% | 0.000000 | 3 → 3 | 60.0% → 60.0% | 0.000000 |
| reference | by_mission | jason-3 | May 2024 | 144 | cross | 5 → 5 | 5 → 5 | 100.0% → 100.0% | 0.000000 | 5 → 5 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | May 2024 | 168 | radial | 5 → 5 | 5 → 5 | 100.0% → 100.0% | 0.000000 | 5 → 5 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | jason-3 | May 2024 | 168 | in_track | 5 → 5 | 1 → 1 | 20.0% → 20.0% | 0.000000 | 3 → 3 | 60.0% → 60.0% | 0.000000 |
| reference | by_mission | jason-3 | May 2024 | 168 | cross | 5 → 5 | 4 → 4 | 80.0% → 80.0% | 0.000000 | 5 → 5 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | saral | August 2024 held out | 6 | radial | 18 → 18 | 1 → 1 | 5.6% → 5.6% | 0.000000 | 6 → 6 | 33.3% → 33.3% | 0.000000 |
| reference | by_mission | saral | August 2024 held out | 6 | in_track | 18 → 18 | 1 → 1 | 5.6% → 5.6% | 0.000000 | 2 → 2 | 11.1% → 11.1% | 0.000000 |
| reference | by_mission | saral | August 2024 held out | 6 | cross | 18 → 18 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | saral | August 2024 held out | 12 | radial | 18 → 18 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 1 → 1 | 5.6% → 5.6% | 0.000000 |
| reference | by_mission | saral | August 2024 held out | 12 | in_track | 18 → 18 | 1 → 1 | 5.6% → 5.6% | 0.000000 | 1 → 1 | 5.6% → 5.6% | 0.000000 |
| reference | by_mission | saral | August 2024 held out | 12 | cross | 18 → 18 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | saral | August 2024 held out | 24 | radial | 18 → 18 | 14 → 14 | 77.8% → 77.8% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | saral | August 2024 held out | 24 | in_track | 18 → 18 | 4 → 4 | 22.2% → 22.2% | 0.000000 | 6 → 6 | 33.3% → 33.3% | 0.000000 |
| reference | by_mission | saral | August 2024 held out | 24 | cross | 18 → 18 | 1 → 1 | 5.6% → 5.6% | 0.000000 | 2 → 2 | 11.1% → 11.1% | 0.000000 |
| reference | by_mission | saral | August 2024 held out | 36 | radial | 18 → 18 | 8 → 8 | 44.4% → 44.4% | 0.000000 | 11 → 11 | 61.1% → 61.1% | 0.000000 |
| reference | by_mission | saral | August 2024 held out | 36 | in_track | 18 → 18 | 3 → 3 | 16.7% → 16.7% | 0.000000 | 7 → 7 | 38.9% → 38.9% | 0.000000 |
| reference | by_mission | saral | August 2024 held out | 36 | cross | 18 → 18 | 6 → 6 | 33.3% → 33.3% | 0.000000 | 9 → 9 | 50.0% → 50.0% | 0.000000 |
| reference | by_mission | saral | August 2024 held out | 48 | radial | 18 → 18 | 10 → 10 | 55.6% → 55.6% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | saral | August 2024 held out | 48 | in_track | 18 → 18 | 5 → 5 | 27.8% → 27.8% | 0.000000 | 5 → 5 | 27.8% → 27.8% | 0.000000 |
| reference | by_mission | saral | August 2024 held out | 48 | cross | 18 → 18 | 1 → 1 | 5.6% → 5.6% | 0.000000 | 1 → 1 | 5.6% → 5.6% | 0.000000 |
| reference | by_mission | saral | August 2024 held out | 72 | radial | 18 → 18 | 9 → 9 | 50.0% → 50.0% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | saral | August 2024 held out | 72 | in_track | 18 → 18 | 3 → 3 | 16.7% → 16.7% | 0.000000 | 7 → 7 | 38.9% → 38.9% | 0.000000 |
| reference | by_mission | saral | August 2024 held out | 72 | cross | 18 → 18 | 2 → 2 | 11.1% → 11.1% | 0.000000 | 4 → 4 | 22.2% → 22.2% | 0.000000 |
| reference | by_mission | saral | August 2024 held out | 96 | radial | 18 → 18 | 18 → 18 | 100.0% → 100.0% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | saral | August 2024 held out | 96 | in_track | 18 → 18 | 4 → 4 | 22.2% → 22.2% | 0.000000 | 10 → 10 | 55.6% → 55.6% | 0.000000 |
| reference | by_mission | saral | August 2024 held out | 96 | cross | 18 → 18 | 1 → 1 | 5.6% → 5.6% | 0.000000 | 2 → 2 | 11.1% → 11.1% | 0.000000 |
| reference | by_mission | saral | August 2024 held out | 120 | radial | 18 → 18 | 18 → 18 | 100.0% → 100.0% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | saral | August 2024 held out | 120 | in_track | 18 → 18 | 1 → 1 | 5.6% → 5.6% | 0.000000 | 3 → 3 | 16.7% → 16.7% | 0.000000 |
| reference | by_mission | saral | August 2024 held out | 120 | cross | 18 → 18 | 2 → 2 | 11.1% → 11.1% | 0.000000 | 3 → 3 | 16.7% → 16.7% | 0.000000 |
| reference | by_mission | saral | August 2024 held out | 144 | radial | 18 → 18 | 13 → 13 | 72.2% → 72.2% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | saral | August 2024 held out | 144 | in_track | 18 → 18 | 1 → 1 | 5.6% → 5.6% | 0.000000 | 6 → 6 | 33.3% → 33.3% | 0.000000 |
| reference | by_mission | saral | August 2024 held out | 144 | cross | 18 → 18 | 10 → 10 | 55.6% → 55.6% | 0.000000 | 13 → 13 | 72.2% → 72.2% | 0.000000 |
| reference | by_mission | saral | August 2024 held out | 168 | radial | 18 → 18 | 18 → 18 | 100.0% → 100.0% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | saral | August 2024 held out | 168 | in_track | 18 → 18 | 4 → 4 | 22.2% → 22.2% | 0.000000 | 7 → 7 | 38.9% → 38.9% | 0.000000 |
| reference | by_mission | saral | August 2024 held out | 168 | cross | 18 → 18 | 1 → 1 | 5.6% → 5.6% | 0.000000 | 3 → 3 | 16.7% → 16.7% | 0.000000 |
| reference | by_mission | saral | October 2024 held out | 6 | radial | 17 → 17 | 1 → 1 | 5.9% → 5.9% | 0.000000 | 5 → 5 | 29.4% → 29.4% | 0.000000 |
| reference | by_mission | saral | October 2024 held out | 6 | in_track | 17 → 17 | 2 → 2 | 11.8% → 11.8% | 0.000000 | 6 → 6 | 35.3% → 35.3% | 0.000000 |
| reference | by_mission | saral | October 2024 held out | 6 | cross | 17 → 17 | 1 → 1 | 5.9% → 5.9% | 0.000000 | 5 → 5 | 29.4% → 29.4% | 0.000000 |
| reference | by_mission | saral | October 2024 held out | 12 | radial | 17 → 17 | 3 → 3 | 17.6% → 17.6% | 0.000000 | 4 → 4 | 23.5% → 23.5% | 0.000000 |
| reference | by_mission | saral | October 2024 held out | 12 | in_track | 17 → 17 | 5 → 5 | 29.4% → 29.4% | 0.000000 | 9 → 9 | 52.9% → 52.9% | 0.000000 |
| reference | by_mission | saral | October 2024 held out | 12 | cross | 17 → 17 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | saral | October 2024 held out | 24 | radial | 17 → 17 | 15 → 15 | 88.2% → 88.2% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | saral | October 2024 held out | 24 | in_track | 17 → 17 | 9 → 9 | 52.9% → 52.9% | 0.000000 | 12 → 12 | 70.6% → 70.6% | 0.000000 |
| reference | by_mission | saral | October 2024 held out | 24 | cross | 17 → 17 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | saral | October 2024 held out | 36 | radial | 17 → 17 | 8 → 8 | 47.1% → 47.1% | 0.000000 | 8 → 8 | 47.1% → 47.1% | 0.000000 |
| reference | by_mission | saral | October 2024 held out | 36 | in_track | 17 → 17 | 7 → 7 | 41.2% → 41.2% | 0.000000 | 13 → 13 | 76.5% → 76.5% | 0.000000 |
| reference | by_mission | saral | October 2024 held out | 36 | cross | 17 → 17 | 10 → 10 | 58.8% → 58.8% | 0.000000 | 16 → 16 | 94.1% → 94.1% | 0.000000 |
| reference | by_mission | saral | October 2024 held out | 48 | radial | 17 → 17 | 5 → 5 | 29.4% → 29.4% | 0.000000 | 16 → 16 | 94.1% → 94.1% | 0.000000 |
| reference | by_mission | saral | October 2024 held out | 48 | in_track | 17 → 17 | 9 → 9 | 52.9% → 52.9% | 0.000000 | 13 → 13 | 76.5% → 76.5% | 0.000000 |
| reference | by_mission | saral | October 2024 held out | 48 | cross | 17 → 17 | 9 → 9 | 52.9% → 52.9% | 0.000000 | 9 → 9 | 52.9% → 52.9% | 0.000000 |
| reference | by_mission | saral | October 2024 held out | 72 | radial | 17 → 17 | 14 → 14 | 82.4% → 82.4% | 0.000000 | 16 → 16 | 94.1% → 94.1% | 0.000000 |
| reference | by_mission | saral | October 2024 held out | 72 | in_track | 17 → 17 | 9 → 9 | 52.9% → 52.9% | 0.000000 | 13 → 13 | 76.5% → 76.5% | 0.000000 |
| reference | by_mission | saral | October 2024 held out | 72 | cross | 17 → 17 | 2 → 2 | 11.8% → 11.8% | 0.000000 | 7 → 7 | 41.2% → 41.2% | 0.000000 |
| reference | by_mission | saral | October 2024 held out | 96 | radial | 17 → 17 | 16 → 16 | 94.1% → 94.1% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | saral | October 2024 held out | 96 | in_track | 17 → 17 | 9 → 9 | 52.9% → 52.9% | 0.000000 | 12 → 12 | 70.6% → 70.6% | 0.000000 |
| reference | by_mission | saral | October 2024 held out | 96 | cross | 17 → 17 | 6 → 6 | 35.3% → 35.3% | 0.000000 | 11 → 11 | 64.7% → 64.7% | 0.000000 |
| reference | by_mission | saral | October 2024 held out | 120 | radial | 17 → 17 | 16 → 16 | 94.1% → 94.1% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | saral | October 2024 held out | 120 | in_track | 17 → 17 | 7 → 7 | 41.2% → 41.2% | 0.000000 | 12 → 12 | 70.6% → 70.6% | 0.000000 |
| reference | by_mission | saral | October 2024 held out | 120 | cross | 17 → 17 | 4 → 4 | 23.5% → 23.5% | 0.000000 | 9 → 9 | 52.9% → 52.9% | 0.000000 |
| reference | by_mission | saral | October 2024 held out | 144 | radial | 17 → 17 | 12 → 12 | 70.6% → 70.6% | 0.000000 | 16 → 16 | 94.1% → 94.1% | 0.000000 |
| reference | by_mission | saral | October 2024 held out | 144 | in_track | 17 → 17 | 7 → 7 | 41.2% → 41.2% | 0.000000 | 11 → 11 | 64.7% → 64.7% | 0.000000 |
| reference | by_mission | saral | October 2024 held out | 144 | cross | 17 → 17 | 13 → 13 | 76.5% → 76.5% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | saral | October 2024 held out | 168 | radial | 17 → 17 | 16 → 16 | 94.1% → 94.1% | 0.000000 | 16 → 16 | 94.1% → 94.1% | 0.000000 |
| reference | by_mission | saral | October 2024 held out | 168 | in_track | 17 → 17 | 8 → 8 | 47.1% → 47.1% | 0.000000 | 9 → 9 | 52.9% → 52.9% | 0.000000 |
| reference | by_mission | saral | October 2024 held out | 168 | cross | 17 → 17 | 9 → 9 | 52.9% → 52.9% | 0.000000 | 10 → 10 | 58.8% → 58.8% | 0.000000 |
| reference | by_mission | saral | April 2024 control | 6 | radial | 19 → 19 | 2 → 2 | 10.5% → 10.5% | 0.000000 | 5 → 5 | 26.3% → 26.3% | 0.000000 |
| reference | by_mission | saral | April 2024 control | 6 | in_track | 19 → 19 | 1 → 1 | 5.3% → 5.3% | 0.000000 | 5 → 5 | 26.3% → 26.3% | 0.000000 |
| reference | by_mission | saral | April 2024 control | 6 | cross | 19 → 19 | 4 → 4 | 21.1% → 21.1% | 0.000000 | 9 → 9 | 47.4% → 47.4% | 0.000000 |
| reference | by_mission | saral | April 2024 control | 12 | radial | 19 → 19 | 1 → 1 | 5.3% → 5.3% | 0.000000 | 4 → 4 | 21.1% → 21.1% | 0.000000 |
| reference | by_mission | saral | April 2024 control | 12 | in_track | 19 → 19 | 3 → 3 | 15.8% → 15.8% | 0.000000 | 10 → 10 | 52.6% → 52.6% | 0.000000 |
| reference | by_mission | saral | April 2024 control | 12 | cross | 19 → 19 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 4 → 4 | 21.1% → 21.1% | 0.000000 |
| reference | by_mission | saral | April 2024 control | 24 | radial | 19 → 19 | 11 → 11 | 57.9% → 57.9% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | saral | April 2024 control | 24 | in_track | 19 → 19 | 9 → 9 | 47.4% → 47.4% | 0.000000 | 13 → 13 | 68.4% → 68.4% | 0.000000 |
| reference | by_mission | saral | April 2024 control | 24 | cross | 19 → 19 | 2 → 2 | 10.5% → 10.5% | 0.000000 | 3 → 3 | 15.8% → 15.8% | 0.000000 |
| reference | by_mission | saral | April 2024 control | 36 | radial | 19 → 19 | 7 → 7 | 36.8% → 36.8% | 0.000000 | 10 → 10 | 52.6% → 52.6% | 0.000000 |
| reference | by_mission | saral | April 2024 control | 36 | in_track | 19 → 19 | 8 → 8 | 42.1% → 42.1% | 0.000000 | 17 → 17 | 89.5% → 89.5% | 0.000000 |
| reference | by_mission | saral | April 2024 control | 36 | cross | 19 → 19 | 6 → 6 | 31.6% → 31.6% | 0.000000 | 13 → 13 | 68.4% → 68.4% | 0.000000 |
| reference | by_mission | saral | April 2024 control | 48 | radial | 19 → 19 | 10 → 10 | 52.6% → 52.6% | 0.000000 | 16 → 16 | 84.2% → 84.2% | 0.000000 |
| reference | by_mission | saral | April 2024 control | 48 | in_track | 19 → 19 | 11 → 11 | 57.9% → 57.9% | 0.000000 | 17 → 17 | 89.5% → 89.5% | 0.000000 |
| reference | by_mission | saral | April 2024 control | 48 | cross | 19 → 19 | 4 → 4 | 21.1% → 21.1% | 0.000000 | 7 → 7 | 36.8% → 36.8% | 0.000000 |
| reference | by_mission | saral | April 2024 control | 72 | radial | 19 → 19 | 11 → 11 | 57.9% → 57.9% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | saral | April 2024 control | 72 | in_track | 19 → 19 | 16 → 16 | 84.2% → 84.2% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | saral | April 2024 control | 72 | cross | 19 → 19 | 12 → 12 | 63.2% → 63.2% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | saral | April 2024 control | 96 | radial | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | saral | April 2024 control | 96 | in_track | 19 → 19 | 18 → 18 | 94.7% → 94.7% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | saral | April 2024 control | 96 | cross | 19 → 19 | 9 → 9 | 47.4% → 47.4% | 0.000000 | 14 → 14 | 73.7% → 73.7% | 0.000000 |
| reference | by_mission | saral | April 2024 control | 120 | radial | 19 → 19 | 17 → 17 | 89.5% → 89.5% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | saral | April 2024 control | 120 | in_track | 19 → 19 | 16 → 16 | 84.2% → 84.2% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | saral | April 2024 control | 120 | cross | 19 → 19 | 11 → 11 | 57.9% → 57.9% | 0.000000 | 16 → 16 | 84.2% → 84.2% | 0.000000 |
| reference | by_mission | saral | April 2024 control | 144 | radial | 19 → 19 | 11 → 11 | 57.9% → 57.9% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | saral | April 2024 control | 144 | in_track | 19 → 19 | 15 → 15 | 78.9% → 78.9% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | saral | April 2024 control | 144 | cross | 19 → 19 | 17 → 17 | 89.5% → 89.5% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | saral | April 2024 control | 168 | radial | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | saral | April 2024 control | 168 | in_track | 19 → 19 | 13 → 13 | 68.4% → 68.4% | 0.000000 | 17 → 17 | 89.5% → 89.5% | 0.000000 |
| reference | by_mission | saral | April 2024 control | 168 | cross | 19 → 19 | 15 → 15 | 78.9% → 78.9% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | saral | May 2024 | 6 | radial | 19 → 19 | 1 → 1 | 5.3% → 5.3% | 0.000000 | 7 → 7 | 36.8% → 36.8% | 0.000000 |
| reference | by_mission | saral | May 2024 | 6 | in_track | 19 → 19 | 1 → 1 | 5.3% → 5.3% | 0.000000 | 5 → 5 | 26.3% → 26.3% | 0.000000 |
| reference | by_mission | saral | May 2024 | 6 | cross | 19 → 19 | 1 → 1 | 5.3% → 5.3% | 0.000000 | 2 → 2 | 10.5% → 10.5% | 0.000000 |
| reference | by_mission | saral | May 2024 | 12 | radial | 19 → 19 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 2 → 2 | 10.5% → 10.5% | 0.000000 |
| reference | by_mission | saral | May 2024 | 12 | in_track | 19 → 19 | 3 → 3 | 15.8% → 15.8% | 0.000000 | 6 → 6 | 31.6% → 31.6% | 0.000000 |
| reference | by_mission | saral | May 2024 | 12 | cross | 19 → 19 | 2 → 2 | 10.5% → 10.5% | 0.000000 | 5 → 5 | 26.3% → 26.3% | 0.000000 |
| reference | by_mission | saral | May 2024 | 24 | radial | 19 → 19 | 11 → 11 | 57.9% → 57.9% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | saral | May 2024 | 24 | in_track | 19 → 19 | 8 → 8 | 42.1% → 42.1% | 0.000000 | 15 → 15 | 78.9% → 78.9% | 0.000000 |
| reference | by_mission | saral | May 2024 | 24 | cross | 19 → 19 | 1 → 1 | 5.3% → 5.3% | 0.000000 | 3 → 3 | 15.8% → 15.8% | 0.000000 |
| reference | by_mission | saral | May 2024 | 36 | radial | 19 → 19 | 7 → 7 | 36.8% → 36.8% | 0.000000 | 9 → 9 | 47.4% → 47.4% | 0.000000 |
| reference | by_mission | saral | May 2024 | 36 | in_track | 19 → 19 | 7 → 7 | 36.8% → 36.8% | 0.000000 | 15 → 15 | 78.9% → 78.9% | 0.000000 |
| reference | by_mission | saral | May 2024 | 36 | cross | 19 → 19 | 1 → 1 | 5.3% → 5.3% | 0.000000 | 5 → 5 | 26.3% → 26.3% | 0.000000 |
| reference | by_mission | saral | May 2024 | 48 | radial | 19 → 19 | 10 → 10 | 52.6% → 52.6% | 0.000000 | 17 → 17 | 89.5% → 89.5% | 0.000000 |
| reference | by_mission | saral | May 2024 | 48 | in_track | 19 → 19 | 10 → 10 | 52.6% → 52.6% | 0.000000 | 17 → 17 | 89.5% → 89.5% | 0.000000 |
| reference | by_mission | saral | May 2024 | 48 | cross | 19 → 19 | 3 → 3 | 15.8% → 15.8% | 0.000000 | 6 → 6 | 31.6% → 31.6% | 0.000000 |
| reference | by_mission | saral | May 2024 | 72 | radial | 19 → 19 | 10 → 10 | 52.6% → 52.6% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | saral | May 2024 | 72 | in_track | 19 → 19 | 12 → 12 | 63.2% → 63.2% | 0.000000 | 16 → 16 | 84.2% → 84.2% | 0.000000 |
| reference | by_mission | saral | May 2024 | 72 | cross | 19 → 19 | 9 → 9 | 47.4% → 47.4% | 0.000000 | 16 → 16 | 84.2% → 84.2% | 0.000000 |
| reference | by_mission | saral | May 2024 | 96 | radial | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | saral | May 2024 | 96 | in_track | 19 → 19 | 8 → 8 | 42.1% → 42.1% | 0.000000 | 16 → 16 | 84.2% → 84.2% | 0.000000 |
| reference | by_mission | saral | May 2024 | 96 | cross | 19 → 19 | 7 → 7 | 36.8% → 36.8% | 0.000000 | 14 → 14 | 73.7% → 73.7% | 0.000000 |
| reference | by_mission | saral | May 2024 | 120 | radial | 19 → 19 | 16 → 16 | 84.2% → 84.2% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | saral | May 2024 | 120 | in_track | 19 → 19 | 6 → 6 | 31.6% → 31.6% | 0.000000 | 11 → 11 | 57.9% → 57.9% | 0.000000 |
| reference | by_mission | saral | May 2024 | 120 | cross | 19 → 19 | 9 → 9 | 47.4% → 47.4% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | saral | May 2024 | 144 | radial | 19 → 19 | 12 → 12 | 63.2% → 63.2% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | saral | May 2024 | 144 | in_track | 19 → 19 | 5 → 5 | 26.3% → 26.3% | 0.000000 | 10 → 10 | 52.6% → 52.6% | 0.000000 |
| reference | by_mission | saral | May 2024 | 144 | cross | 19 → 19 | 16 → 16 | 84.2% → 84.2% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | saral | May 2024 | 168 | radial | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | saral | May 2024 | 168 | in_track | 19 → 19 | 4 → 4 | 21.1% → 21.1% | 0.000000 | 9 → 9 | 47.4% → 47.4% | 0.000000 |
| reference | by_mission | saral | May 2024 | 168 | cross | 19 → 19 | 9 → 9 | 47.4% → 47.4% | 0.000000 | 18 → 18 | 94.7% → 94.7% | 0.000000 |
| reference | by_mission | sentinel-1a | August 2024 held out | 6 | radial | 25 → 25 | 6 → 6 | 24.0% → 24.0% | 0.000000 | 8 → 8 | 32.0% → 32.0% | 0.000000 |
| reference | by_mission | sentinel-1a | August 2024 held out | 6 | in_track | 25 → 25 | 8 → 8 | 32.0% → 32.0% | 0.000000 | 12 → 12 | 48.0% → 48.0% | 0.000000 |
| reference | by_mission | sentinel-1a | August 2024 held out | 6 | cross | 25 → 25 | 2 → 2 | 8.0% → 8.0% | 0.000000 | 4 → 4 | 16.0% → 16.0% | 0.000000 |
| reference | by_mission | sentinel-1a | August 2024 held out | 12 | radial | 23 → 23 | 11 → 11 | 47.8% → 47.8% | 0.000000 | 18 → 18 | 78.3% → 78.3% | 0.000000 |
| reference | by_mission | sentinel-1a | August 2024 held out | 12 | in_track | 23 → 23 | 10 → 10 | 43.5% → 43.5% | 0.000000 | 13 → 13 | 56.5% → 56.5% | 0.000000 |
| reference | by_mission | sentinel-1a | August 2024 held out | 12 | cross | 23 → 23 | 1 → 1 | 4.3% → 4.3% | 0.000000 | 3 → 3 | 13.0% → 13.0% | 0.000000 |
| reference | by_mission | sentinel-1a | August 2024 held out | 24 | radial | 21 → 21 | 1 → 1 | 4.8% → 4.8% | 0.000000 | 9 → 9 | 42.9% → 42.9% | 0.000000 |
| reference | by_mission | sentinel-1a | August 2024 held out | 24 | in_track | 21 → 21 | 11 → 11 | 52.4% → 52.4% | 0.000000 | 15 → 15 | 71.4% → 71.4% | 0.000000 |
| reference | by_mission | sentinel-1a | August 2024 held out | 24 | cross | 21 → 21 | 1 → 1 | 4.8% → 4.8% | 0.000000 | 7 → 7 | 33.3% → 33.3% | 0.000000 |
| reference | by_mission | sentinel-1a | August 2024 held out | 36 | radial | 18 → 18 | 8 → 8 | 44.4% → 44.4% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-1a | August 2024 held out | 36 | in_track | 18 → 18 | 12 → 12 | 66.7% → 66.7% | 0.000000 | 13 → 13 | 72.2% → 72.2% | 0.000000 |
| reference | by_mission | sentinel-1a | August 2024 held out | 36 | cross | 18 → 18 | 11 → 11 | 61.1% → 61.1% | 0.000000 | 13 → 13 | 72.2% → 72.2% | 0.000000 |
| reference | by_mission | sentinel-1a | August 2024 held out | 48 | radial | 15 → 15 | 7 → 7 | 46.7% → 46.7% | 0.000000 | 14 → 14 | 93.3% → 93.3% | 0.000000 |
| reference | by_mission | sentinel-1a | August 2024 held out | 48 | in_track | 15 → 15 | 6 → 6 | 40.0% → 40.0% | 0.000000 | 10 → 10 | 66.7% → 66.7% | 0.000000 |
| reference | by_mission | sentinel-1a | August 2024 held out | 48 | cross | 15 → 15 | 4 → 4 | 26.7% → 26.7% | 0.000000 | 11 → 11 | 73.3% → 73.3% | 0.000000 |
| reference | by_mission | sentinel-1a | August 2024 held out | 72 | radial | 12 → 12 | 12 → 12 | 100.0% → 100.0% | 0.000000 | 12 → 12 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-1a | August 2024 held out | 72 | in_track | 12 → 12 | 3 → 3 | 25.0% → 25.0% | 0.000000 | 11 → 11 | 91.7% → 91.7% | 0.000000 |
| reference | by_mission | sentinel-1a | August 2024 held out | 72 | cross | 12 → 12 | 5 → 5 | 41.7% → 41.7% | 0.000000 | 9 → 9 | 75.0% → 75.0% | 0.000000 |
| reference | by_mission | sentinel-1a | August 2024 held out | 96 | radial | 7 → 7 | 5 → 5 | 71.4% → 71.4% | 0.000000 | 7 → 7 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-1a | August 2024 held out | 96 | in_track | 7 → 7 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 7 → 7 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-1a | August 2024 held out | 96 | cross | 7 → 7 | 6 → 6 | 85.7% → 85.7% | 0.000000 | 7 → 7 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-1a | August 2024 held out | 120 | radial | 1 → 1 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 1 → 1 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-1a | August 2024 held out | 120 | in_track | 1 → 1 | 1 → 1 | 100.0% → 100.0% | 0.000000 | 1 → 1 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-1a | August 2024 held out | 120 | cross | 1 → 1 | 1 → 1 | 100.0% → 100.0% | 0.000000 | 1 → 1 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-1a | August 2024 held out | 144 | radial | 0 → 0 | 0 → 0 | — → — | — | 0 → 0 | — → — | — |
| reference | by_mission | sentinel-1a | August 2024 held out | 144 | in_track | 0 → 0 | 0 → 0 | — → — | — | 0 → 0 | — → — | — |
| reference | by_mission | sentinel-1a | August 2024 held out | 144 | cross | 0 → 0 | 0 → 0 | — → — | — | 0 → 0 | — → — | — |
| reference | by_mission | sentinel-1a | August 2024 held out | 168 | radial | 0 → 0 | 0 → 0 | — → — | — | 0 → 0 | — → — | — |
| reference | by_mission | sentinel-1a | August 2024 held out | 168 | in_track | 0 → 0 | 0 → 0 | — → — | — | 0 → 0 | — → — | — |
| reference | by_mission | sentinel-1a | August 2024 held out | 168 | cross | 0 → 0 | 0 → 0 | — → — | — | 0 → 0 | — → — | — |
| reference | by_mission | sentinel-1a | October 2024 held out | 6 | radial | 27 → 27 | 7 → 7 | 25.9% → 25.9% | 0.000000 | 11 → 11 | 40.7% → 40.7% | 0.000000 |
| reference | by_mission | sentinel-1a | October 2024 held out | 6 | in_track | 27 → 27 | 9 → 9 | 33.3% → 33.3% | 0.000000 | 18 → 18 | 66.7% → 66.7% | 0.000000 |
| reference | by_mission | sentinel-1a | October 2024 held out | 6 | cross | 27 → 27 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 3 → 3 | 11.1% → 11.1% | 0.000000 |
| reference | by_mission | sentinel-1a | October 2024 held out | 12 | radial | 27 → 27 | 12 → 12 | 44.4% → 44.4% | 0.000000 | 22 → 22 | 81.5% → 81.5% | 0.000000 |
| reference | by_mission | sentinel-1a | October 2024 held out | 12 | in_track | 27 → 27 | 13 → 13 | 48.1% → 48.1% | 0.000000 | 17 → 17 | 63.0% → 63.0% | 0.000000 |
| reference | by_mission | sentinel-1a | October 2024 held out | 12 | cross | 27 → 27 | 2 → 2 | 7.4% → 7.4% | 0.000000 | 4 → 4 | 14.8% → 14.8% | 0.000000 |
| reference | by_mission | sentinel-1a | October 2024 held out | 24 | radial | 27 → 27 | 3 → 3 | 11.1% → 11.1% | 0.000000 | 11 → 11 | 40.7% → 40.7% | 0.000000 |
| reference | by_mission | sentinel-1a | October 2024 held out | 24 | in_track | 27 → 27 | 18 → 18 | 66.7% → 66.7% | 0.000000 | 21 → 21 | 77.8% → 77.8% | 0.000000 |
| reference | by_mission | sentinel-1a | October 2024 held out | 24 | cross | 27 → 27 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 3 → 3 | 11.1% → 11.1% | 0.000000 |
| reference | by_mission | sentinel-1a | October 2024 held out | 36 | radial | 26 → 26 | 12 → 12 | 46.2% → 46.2% | 0.000000 | 25 → 25 | 96.2% → 96.2% | 0.000000 |
| reference | by_mission | sentinel-1a | October 2024 held out | 36 | in_track | 26 → 26 | 17 → 17 | 65.4% → 65.4% | 0.000000 | 21 → 21 | 80.8% → 80.8% | 0.000000 |
| reference | by_mission | sentinel-1a | October 2024 held out | 36 | cross | 26 → 26 | 11 → 11 | 42.3% → 42.3% | 0.000000 | 14 → 14 | 53.8% → 53.8% | 0.000000 |
| reference | by_mission | sentinel-1a | October 2024 held out | 48 | radial | 24 → 24 | 14 → 14 | 58.3% → 58.3% | 0.000000 | 21 → 21 | 87.5% → 87.5% | 0.000000 |
| reference | by_mission | sentinel-1a | October 2024 held out | 48 | in_track | 24 → 24 | 16 → 16 | 66.7% → 66.7% | 0.000000 | 21 → 21 | 87.5% → 87.5% | 0.000000 |
| reference | by_mission | sentinel-1a | October 2024 held out | 48 | cross | 24 → 24 | 3 → 3 | 12.5% → 12.5% | 0.000000 | 13 → 13 | 54.2% → 54.2% | 0.000000 |
| reference | by_mission | sentinel-1a | October 2024 held out | 72 | radial | 21 → 21 | 20 → 20 | 95.2% → 95.2% | 0.000000 | 21 → 21 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-1a | October 2024 held out | 72 | in_track | 21 → 21 | 19 → 19 | 90.5% → 90.5% | 0.000000 | 19 → 19 | 90.5% → 90.5% | 0.000000 |
| reference | by_mission | sentinel-1a | October 2024 held out | 72 | cross | 21 → 21 | 4 → 4 | 19.0% → 19.0% | 0.000000 | 8 → 8 | 38.1% → 38.1% | 0.000000 |
| reference | by_mission | sentinel-1a | October 2024 held out | 96 | radial | 16 → 16 | 10 → 10 | 62.5% → 62.5% | 0.000000 | 16 → 16 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-1a | October 2024 held out | 96 | in_track | 16 → 16 | 12 → 12 | 75.0% → 75.0% | 0.000000 | 15 → 15 | 93.8% → 93.8% | 0.000000 |
| reference | by_mission | sentinel-1a | October 2024 held out | 96 | cross | 16 → 16 | 5 → 5 | 31.2% → 31.2% | 0.000000 | 15 → 15 | 93.8% → 93.8% | 0.000000 |
| reference | by_mission | sentinel-1a | October 2024 held out | 120 | radial | 12 → 12 | 2 → 2 | 16.7% → 16.7% | 0.000000 | 12 → 12 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-1a | October 2024 held out | 120 | in_track | 12 → 12 | 8 → 8 | 66.7% → 66.7% | 0.000000 | 11 → 11 | 91.7% → 91.7% | 0.000000 |
| reference | by_mission | sentinel-1a | October 2024 held out | 120 | cross | 12 → 12 | 4 → 4 | 33.3% → 33.3% | 0.000000 | 12 → 12 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-1a | October 2024 held out | 144 | radial | 7 → 7 | 6 → 6 | 85.7% → 85.7% | 0.000000 | 7 → 7 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-1a | October 2024 held out | 144 | in_track | 7 → 7 | 6 → 6 | 85.7% → 85.7% | 0.000000 | 7 → 7 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-1a | October 2024 held out | 144 | cross | 7 → 7 | 4 → 4 | 57.1% → 57.1% | 0.000000 | 7 → 7 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-1a | October 2024 held out | 168 | radial | 2 → 2 | 1 → 1 | 50.0% → 50.0% | 0.000000 | 2 → 2 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-1a | October 2024 held out | 168 | in_track | 2 → 2 | 2 → 2 | 100.0% → 100.0% | 0.000000 | 2 → 2 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-1a | October 2024 held out | 168 | cross | 2 → 2 | 1 → 1 | 50.0% → 50.0% | 0.000000 | 2 → 2 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-1a | April 2024 control | 6 | radial | 31 → 31 | 7 → 7 | 22.6% → 22.6% | 0.000000 | 14 → 14 | 45.2% → 45.2% | 0.000000 |
| reference | by_mission | sentinel-1a | April 2024 control | 6 | in_track | 31 → 31 | 20 → 20 | 64.5% → 64.5% | 0.000000 | 31 → 31 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-1a | April 2024 control | 6 | cross | 31 → 31 | 2 → 2 | 6.5% → 6.5% | 0.000000 | 3 → 3 | 9.7% → 9.7% | 0.000000 |
| reference | by_mission | sentinel-1a | April 2024 control | 12 | radial | 31 → 31 | 14 → 14 | 45.2% → 45.2% | 0.000000 | 25 → 25 | 80.6% → 80.6% | 0.000000 |
| reference | by_mission | sentinel-1a | April 2024 control | 12 | in_track | 31 → 31 | 24 → 24 | 77.4% → 77.4% | 0.000000 | 30 → 30 | 96.8% → 96.8% | 0.000000 |
| reference | by_mission | sentinel-1a | April 2024 control | 12 | cross | 31 → 31 | 1 → 1 | 3.2% → 3.2% | 0.000000 | 2 → 2 | 6.5% → 6.5% | 0.000000 |
| reference | by_mission | sentinel-1a | April 2024 control | 24 | radial | 31 → 31 | 3 → 3 | 9.7% → 9.7% | 0.000000 | 13 → 13 | 41.9% → 41.9% | 0.000000 |
| reference | by_mission | sentinel-1a | April 2024 control | 24 | in_track | 31 → 31 | 23 → 23 | 74.2% → 74.2% | 0.000000 | 31 → 31 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-1a | April 2024 control | 24 | cross | 31 → 31 | 3 → 3 | 9.7% → 9.7% | 0.000000 | 6 → 6 | 19.4% → 19.4% | 0.000000 |
| reference | by_mission | sentinel-1a | April 2024 control | 36 | radial | 31 → 31 | 16 → 16 | 51.6% → 51.6% | 0.000000 | 30 → 30 | 96.8% → 96.8% | 0.000000 |
| reference | by_mission | sentinel-1a | April 2024 control | 36 | in_track | 31 → 31 | 26 → 26 | 83.9% → 83.9% | 0.000000 | 29 → 29 | 93.5% → 93.5% | 0.000000 |
| reference | by_mission | sentinel-1a | April 2024 control | 36 | cross | 31 → 31 | 8 → 8 | 25.8% → 25.8% | 0.000000 | 19 → 19 | 61.3% → 61.3% | 0.000000 |
| reference | by_mission | sentinel-1a | April 2024 control | 48 | radial | 31 → 31 | 14 → 14 | 45.2% → 45.2% | 0.000000 | 30 → 30 | 96.8% → 96.8% | 0.000000 |
| reference | by_mission | sentinel-1a | April 2024 control | 48 | in_track | 31 → 31 | 26 → 26 | 83.9% → 83.9% | 0.000000 | 28 → 28 | 90.3% → 90.3% | 0.000000 |
| reference | by_mission | sentinel-1a | April 2024 control | 48 | cross | 31 → 31 | 10 → 10 | 32.3% → 32.3% | 0.000000 | 13 → 13 | 41.9% → 41.9% | 0.000000 |
| reference | by_mission | sentinel-1a | April 2024 control | 72 | radial | 31 → 31 | 31 → 31 | 100.0% → 100.0% | 0.000000 | 31 → 31 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-1a | April 2024 control | 72 | in_track | 31 → 31 | 26 → 26 | 83.9% → 83.9% | 0.000000 | 29 → 29 | 93.5% → 93.5% | 0.000000 |
| reference | by_mission | sentinel-1a | April 2024 control | 72 | cross | 31 → 31 | 6 → 6 | 19.4% → 19.4% | 0.000000 | 16 → 16 | 51.6% → 51.6% | 0.000000 |
| reference | by_mission | sentinel-1a | April 2024 control | 96 | radial | 31 → 31 | 24 → 24 | 77.4% → 77.4% | 0.000000 | 31 → 31 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-1a | April 2024 control | 96 | in_track | 31 → 31 | 24 → 24 | 77.4% → 77.4% | 0.000000 | 28 → 28 | 90.3% → 90.3% | 0.000000 |
| reference | by_mission | sentinel-1a | April 2024 control | 96 | cross | 31 → 31 | 19 → 19 | 61.3% → 61.3% | 0.000000 | 27 → 27 | 87.1% → 87.1% | 0.000000 |
| reference | by_mission | sentinel-1a | April 2024 control | 120 | radial | 31 → 31 | 8 → 8 | 25.8% → 25.8% | 0.000000 | 31 → 31 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-1a | April 2024 control | 120 | in_track | 31 → 31 | 24 → 24 | 77.4% → 77.4% | 0.000000 | 29 → 29 | 93.5% → 93.5% | 0.000000 |
| reference | by_mission | sentinel-1a | April 2024 control | 120 | cross | 31 → 31 | 14 → 14 | 45.2% → 45.2% | 0.000000 | 26 → 26 | 83.9% → 83.9% | 0.000000 |
| reference | by_mission | sentinel-1a | April 2024 control | 144 | radial | 31 → 31 | 18 → 18 | 58.1% → 58.1% | 0.000000 | 31 → 31 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-1a | April 2024 control | 144 | in_track | 31 → 31 | 23 → 23 | 74.2% → 74.2% | 0.000000 | 28 → 28 | 90.3% → 90.3% | 0.000000 |
| reference | by_mission | sentinel-1a | April 2024 control | 144 | cross | 31 → 31 | 6 → 6 | 19.4% → 19.4% | 0.000000 | 25 → 25 | 80.6% → 80.6% | 0.000000 |
| reference | by_mission | sentinel-1a | April 2024 control | 168 | radial | 31 → 31 | 17 → 17 | 54.8% → 54.8% | 0.000000 | 31 → 31 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-1a | April 2024 control | 168 | in_track | 31 → 31 | 21 → 21 | 67.7% → 67.7% | 0.000000 | 27 → 27 | 87.1% → 87.1% | 0.000000 |
| reference | by_mission | sentinel-1a | April 2024 control | 168 | cross | 31 → 31 | 4 → 4 | 12.9% → 12.9% | 0.000000 | 26 → 26 | 83.9% → 83.9% | 0.000000 |
| reference | by_mission | sentinel-1a | May 2024 | 6 | radial | 26 → 26 | 6 → 6 | 23.1% → 23.1% | 0.000000 | 10 → 10 | 38.5% → 38.5% | 0.000000 |
| reference | by_mission | sentinel-1a | May 2024 | 6 | in_track | 26 → 26 | 11 → 11 | 42.3% → 42.3% | 0.000000 | 23 → 23 | 88.5% → 88.5% | 0.000000 |
| reference | by_mission | sentinel-1a | May 2024 | 6 | cross | 26 → 26 | 2 → 2 | 7.7% → 7.7% | 0.000000 | 4 → 4 | 15.4% → 15.4% | 0.000000 |
| reference | by_mission | sentinel-1a | May 2024 | 12 | radial | 25 → 25 | 8 → 8 | 32.0% → 32.0% | 0.000000 | 19 → 19 | 76.0% → 76.0% | 0.000000 |
| reference | by_mission | sentinel-1a | May 2024 | 12 | in_track | 25 → 25 | 12 → 12 | 48.0% → 48.0% | 0.000000 | 23 → 23 | 92.0% → 92.0% | 0.000000 |
| reference | by_mission | sentinel-1a | May 2024 | 12 | cross | 25 → 25 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 1 → 1 | 4.0% → 4.0% | 0.000000 |
| reference | by_mission | sentinel-1a | May 2024 | 24 | radial | 22 → 22 | 1 → 1 | 4.5% → 4.5% | 0.000000 | 10 → 10 | 45.5% → 45.5% | 0.000000 |
| reference | by_mission | sentinel-1a | May 2024 | 24 | in_track | 22 → 22 | 17 → 17 | 77.3% → 77.3% | 0.000000 | 22 → 22 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-1a | May 2024 | 24 | cross | 22 → 22 | 1 → 1 | 4.5% → 4.5% | 0.000000 | 4 → 4 | 18.2% → 18.2% | 0.000000 |
| reference | by_mission | sentinel-1a | May 2024 | 36 | radial | 20 → 20 | 9 → 9 | 45.0% → 45.0% | 0.000000 | 20 → 20 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-1a | May 2024 | 36 | in_track | 20 → 20 | 19 → 19 | 95.0% → 95.0% | 0.000000 | 20 → 20 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-1a | May 2024 | 36 | cross | 20 → 20 | 10 → 10 | 50.0% → 50.0% | 0.000000 | 12 → 12 | 60.0% → 60.0% | 0.000000 |
| reference | by_mission | sentinel-1a | May 2024 | 48 | radial | 17 → 17 | 9 → 9 | 52.9% → 52.9% | 0.000000 | 16 → 16 | 94.1% → 94.1% | 0.000000 |
| reference | by_mission | sentinel-1a | May 2024 | 48 | in_track | 17 → 17 | 17 → 17 | 100.0% → 100.0% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-1a | May 2024 | 48 | cross | 17 → 17 | 5 → 5 | 29.4% → 29.4% | 0.000000 | 6 → 6 | 35.3% → 35.3% | 0.000000 |
| reference | by_mission | sentinel-1a | May 2024 | 72 | radial | 12 → 12 | 12 → 12 | 100.0% → 100.0% | 0.000000 | 12 → 12 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-1a | May 2024 | 72 | in_track | 12 → 12 | 12 → 12 | 100.0% → 100.0% | 0.000000 | 12 → 12 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-1a | May 2024 | 72 | cross | 12 → 12 | 3 → 3 | 25.0% → 25.0% | 0.000000 | 6 → 6 | 50.0% → 50.0% | 0.000000 |
| reference | by_mission | sentinel-1a | May 2024 | 96 | radial | 8 → 8 | 7 → 7 | 87.5% → 87.5% | 0.000000 | 8 → 8 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-1a | May 2024 | 96 | in_track | 8 → 8 | 8 → 8 | 100.0% → 100.0% | 0.000000 | 8 → 8 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-1a | May 2024 | 96 | cross | 8 → 8 | 5 → 5 | 62.5% → 62.5% | 0.000000 | 8 → 8 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-1a | May 2024 | 120 | radial | 3 → 3 | 2 → 2 | 66.7% → 66.7% | 0.000000 | 3 → 3 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-1a | May 2024 | 120 | in_track | 3 → 3 | 3 → 3 | 100.0% → 100.0% | 0.000000 | 3 → 3 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-1a | May 2024 | 120 | cross | 3 → 3 | 2 → 2 | 66.7% → 66.7% | 0.000000 | 3 → 3 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-1a | May 2024 | 144 | radial | 0 → 0 | 0 → 0 | — → — | — | 0 → 0 | — → — | — |
| reference | by_mission | sentinel-1a | May 2024 | 144 | in_track | 0 → 0 | 0 → 0 | — → — | — | 0 → 0 | — → — | — |
| reference | by_mission | sentinel-1a | May 2024 | 144 | cross | 0 → 0 | 0 → 0 | — → — | — | 0 → 0 | — → — | — |
| reference | by_mission | sentinel-1a | May 2024 | 168 | radial | 0 → 0 | 0 → 0 | — → — | — | 0 → 0 | — → — | — |
| reference | by_mission | sentinel-1a | May 2024 | 168 | in_track | 0 → 0 | 0 → 0 | — → — | — | 0 → 0 | — → — | — |
| reference | by_mission | sentinel-1a | May 2024 | 168 | cross | 0 → 0 | 0 → 0 | — → — | — | 0 → 0 | — → — | — |
| reference | by_mission | sentinel-3a | August 2024 held out | 6 | radial | 29 → 29 | 1 → 1 | 3.4% → 3.4% | 0.000000 | 4 → 4 | 13.8% → 13.8% | 0.000000 |
| reference | by_mission | sentinel-3a | August 2024 held out | 6 | in_track | 29 → 29 | 9 → 9 | 31.0% → 31.0% | 0.000000 | 13 → 13 | 44.8% → 44.8% | 0.000000 |
| reference | by_mission | sentinel-3a | August 2024 held out | 6 | cross | 29 → 29 | 5 → 5 | 17.2% → 17.2% | 0.000000 | 9 → 9 | 31.0% → 31.0% | 0.000000 |
| reference | by_mission | sentinel-3a | August 2024 held out | 12 | radial | 27 → 27 | 4 → 4 | 14.8% → 14.8% | 0.000000 | 6 → 6 | 22.2% → 22.2% | 0.000000 |
| reference | by_mission | sentinel-3a | August 2024 held out | 12 | in_track | 27 → 27 | 10 → 10 | 37.0% → 37.0% | 0.000000 | 20 → 20 | 74.1% → 74.1% | 0.000000 |
| reference | by_mission | sentinel-3a | August 2024 held out | 12 | cross | 27 → 27 | 2 → 2 | 7.4% → 7.4% | 0.000000 | 8 → 8 | 29.6% → 29.6% | 0.000000 |
| reference | by_mission | sentinel-3a | August 2024 held out | 24 | radial | 24 → 24 | 16 → 16 | 66.7% → 66.7% | 0.000000 | 18 → 18 | 75.0% → 75.0% | 0.000000 |
| reference | by_mission | sentinel-3a | August 2024 held out | 24 | in_track | 24 → 24 | 14 → 14 | 58.3% → 58.3% | 0.000000 | 21 → 21 | 87.5% → 87.5% | 0.000000 |
| reference | by_mission | sentinel-3a | August 2024 held out | 24 | cross | 24 → 24 | 2 → 2 | 8.3% → 8.3% | 0.000000 | 4 → 4 | 16.7% → 16.7% | 0.000000 |
| reference | by_mission | sentinel-3a | August 2024 held out | 36 | radial | 22 → 22 | 12 → 12 | 54.5% → 54.5% | 0.000000 | 15 → 15 | 68.2% → 68.2% | 0.000000 |
| reference | by_mission | sentinel-3a | August 2024 held out | 36 | in_track | 22 → 22 | 21 → 21 | 95.5% → 95.5% | 0.000000 | 22 → 22 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | August 2024 held out | 36 | cross | 22 → 22 | 7 → 7 | 31.8% → 31.8% | 0.000000 | 14 → 14 | 63.6% → 63.6% | 0.000000 |
| reference | by_mission | sentinel-3a | August 2024 held out | 48 | radial | 19 → 19 | 5 → 5 | 26.3% → 26.3% | 0.000000 | 14 → 14 | 73.7% → 73.7% | 0.000000 |
| reference | by_mission | sentinel-3a | August 2024 held out | 48 | in_track | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | August 2024 held out | 48 | cross | 19 → 19 | 11 → 11 | 57.9% → 57.9% | 0.000000 | 15 → 15 | 78.9% → 78.9% | 0.000000 |
| reference | by_mission | sentinel-3a | August 2024 held out | 72 | radial | 15 → 15 | 15 → 15 | 100.0% → 100.0% | 0.000000 | 15 → 15 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | August 2024 held out | 72 | in_track | 15 → 15 | 15 → 15 | 100.0% → 100.0% | 0.000000 | 15 → 15 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | August 2024 held out | 72 | cross | 15 → 15 | 7 → 7 | 46.7% → 46.7% | 0.000000 | 13 → 13 | 86.7% → 86.7% | 0.000000 |
| reference | by_mission | sentinel-3a | August 2024 held out | 96 | radial | 11 → 11 | 7 → 7 | 63.6% → 63.6% | 0.000000 | 11 → 11 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | August 2024 held out | 96 | in_track | 11 → 11 | 11 → 11 | 100.0% → 100.0% | 0.000000 | 11 → 11 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | August 2024 held out | 96 | cross | 11 → 11 | 9 → 9 | 81.8% → 81.8% | 0.000000 | 10 → 10 | 90.9% → 90.9% | 0.000000 |
| reference | by_mission | sentinel-3a | August 2024 held out | 120 | radial | 5 → 5 | 5 → 5 | 100.0% → 100.0% | 0.000000 | 5 → 5 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | August 2024 held out | 120 | in_track | 5 → 5 | 5 → 5 | 100.0% → 100.0% | 0.000000 | 5 → 5 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | August 2024 held out | 120 | cross | 5 → 5 | 4 → 4 | 80.0% → 80.0% | 0.000000 | 5 → 5 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | August 2024 held out | 144 | radial | 1 → 1 | 1 → 1 | 100.0% → 100.0% | 0.000000 | 1 → 1 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | August 2024 held out | 144 | in_track | 1 → 1 | 1 → 1 | 100.0% → 100.0% | 0.000000 | 1 → 1 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | August 2024 held out | 144 | cross | 1 → 1 | 1 → 1 | 100.0% → 100.0% | 0.000000 | 1 → 1 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | August 2024 held out | 168 | radial | 0 → 0 | 0 → 0 | — → — | — | 0 → 0 | — → — | — |
| reference | by_mission | sentinel-3a | August 2024 held out | 168 | in_track | 0 → 0 | 0 → 0 | — → — | — | 0 → 0 | — → — | — |
| reference | by_mission | sentinel-3a | August 2024 held out | 168 | cross | 0 → 0 | 0 → 0 | — → — | — | 0 → 0 | — → — | — |
| reference | by_mission | sentinel-3a | October 2024 held out | 6 | radial | 22 → 22 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 2 → 2 | 9.1% → 9.1% | 0.000000 |
| reference | by_mission | sentinel-3a | October 2024 held out | 6 | in_track | 22 → 22 | 6 → 6 | 27.3% → 27.3% | 0.000000 | 17 → 17 | 77.3% → 77.3% | 0.000000 |
| reference | by_mission | sentinel-3a | October 2024 held out | 6 | cross | 22 → 22 | 2 → 2 | 9.1% → 9.1% | 0.000000 | 3 → 3 | 13.6% → 13.6% | 0.000000 |
| reference | by_mission | sentinel-3a | October 2024 held out | 12 | radial | 22 → 22 | 5 → 5 | 22.7% → 22.7% | 0.000000 | 8 → 8 | 36.4% → 36.4% | 0.000000 |
| reference | by_mission | sentinel-3a | October 2024 held out | 12 | in_track | 22 → 22 | 15 → 15 | 68.2% → 68.2% | 0.000000 | 17 → 17 | 77.3% → 77.3% | 0.000000 |
| reference | by_mission | sentinel-3a | October 2024 held out | 12 | cross | 22 → 22 | 2 → 2 | 9.1% → 9.1% | 0.000000 | 3 → 3 | 13.6% → 13.6% | 0.000000 |
| reference | by_mission | sentinel-3a | October 2024 held out | 24 | radial | 22 → 22 | 18 → 18 | 81.8% → 81.8% | 0.000000 | 20 → 20 | 90.9% → 90.9% | 0.000000 |
| reference | by_mission | sentinel-3a | October 2024 held out | 24 | in_track | 22 → 22 | 17 → 17 | 77.3% → 77.3% | 0.000000 | 19 → 19 | 86.4% → 86.4% | 0.000000 |
| reference | by_mission | sentinel-3a | October 2024 held out | 24 | cross | 22 → 22 | 2 → 2 | 9.1% → 9.1% | 0.000000 | 3 → 3 | 13.6% → 13.6% | 0.000000 |
| reference | by_mission | sentinel-3a | October 2024 held out | 36 | radial | 22 → 22 | 11 → 11 | 50.0% → 50.0% | 0.000000 | 12 → 12 | 54.5% → 54.5% | 0.000000 |
| reference | by_mission | sentinel-3a | October 2024 held out | 36 | in_track | 22 → 22 | 19 → 19 | 86.4% → 86.4% | 0.000000 | 21 → 21 | 95.5% → 95.5% | 0.000000 |
| reference | by_mission | sentinel-3a | October 2024 held out | 36 | cross | 22 → 22 | 5 → 5 | 22.7% → 22.7% | 0.000000 | 12 → 12 | 54.5% → 54.5% | 0.000000 |
| reference | by_mission | sentinel-3a | October 2024 held out | 48 | radial | 22 → 22 | 8 → 8 | 36.4% → 36.4% | 0.000000 | 19 → 19 | 86.4% → 86.4% | 0.000000 |
| reference | by_mission | sentinel-3a | October 2024 held out | 48 | in_track | 22 → 22 | 19 → 19 | 86.4% → 86.4% | 0.000000 | 21 → 21 | 95.5% → 95.5% | 0.000000 |
| reference | by_mission | sentinel-3a | October 2024 held out | 48 | cross | 22 → 22 | 13 → 13 | 59.1% → 59.1% | 0.000000 | 19 → 19 | 86.4% → 86.4% | 0.000000 |
| reference | by_mission | sentinel-3a | October 2024 held out | 72 | radial | 22 → 22 | 21 → 21 | 95.5% → 95.5% | 0.000000 | 21 → 21 | 95.5% → 95.5% | 0.000000 |
| reference | by_mission | sentinel-3a | October 2024 held out | 72 | in_track | 22 → 22 | 19 → 19 | 86.4% → 86.4% | 0.000000 | 21 → 21 | 95.5% → 95.5% | 0.000000 |
| reference | by_mission | sentinel-3a | October 2024 held out | 72 | cross | 22 → 22 | 11 → 11 | 50.0% → 50.0% | 0.000000 | 18 → 18 | 81.8% → 81.8% | 0.000000 |
| reference | by_mission | sentinel-3a | October 2024 held out | 96 | radial | 22 → 22 | 11 → 11 | 50.0% → 50.0% | 0.000000 | 21 → 21 | 95.5% → 95.5% | 0.000000 |
| reference | by_mission | sentinel-3a | October 2024 held out | 96 | in_track | 22 → 22 | 19 → 19 | 86.4% → 86.4% | 0.000000 | 21 → 21 | 95.5% → 95.5% | 0.000000 |
| reference | by_mission | sentinel-3a | October 2024 held out | 96 | cross | 22 → 22 | 20 → 20 | 90.9% → 90.9% | 0.000000 | 22 → 22 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | October 2024 held out | 120 | radial | 20 → 20 | 19 → 19 | 95.0% → 95.0% | 0.000000 | 19 → 20 | 95.0% → 100.0% | 5.000000 |
| reference | by_mission | sentinel-3a | October 2024 held out | 120 | in_track | 20 → 20 | 17 → 17 | 85.0% → 85.0% | 0.000000 | 19 → 19 | 95.0% → 95.0% | 0.000000 |
| reference | by_mission | sentinel-3a | October 2024 held out | 120 | cross | 20 → 20 | 16 → 16 | 80.0% → 80.0% | 0.000000 | 20 → 20 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | October 2024 held out | 144 | radial | 17 → 17 | 11 → 11 | 64.7% → 64.7% | 0.000000 | 16 → 17 | 94.1% → 100.0% | 5.882353 |
| reference | by_mission | sentinel-3a | October 2024 held out | 144 | in_track | 17 → 17 | 14 → 14 | 82.4% → 82.4% | 0.000000 | 16 → 16 | 94.1% → 94.1% | 0.000000 |
| reference | by_mission | sentinel-3a | October 2024 held out | 144 | cross | 17 → 17 | 17 → 17 | 100.0% → 100.0% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | October 2024 held out | 168 | radial | 12 → 12 | 12 → 12 | 100.0% → 100.0% | 0.000000 | 12 → 12 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | October 2024 held out | 168 | in_track | 12 → 12 | 12 → 12 | 100.0% → 100.0% | 0.000000 | 12 → 12 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | October 2024 held out | 168 | cross | 12 → 12 | 12 → 12 | 100.0% → 100.0% | 0.000000 | 12 → 12 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | April 2024 control | 6 | radial | 26 → 26 | 1 → 1 | 3.8% → 3.8% | 0.000000 | 5 → 5 | 19.2% → 19.2% | 0.000000 |
| reference | by_mission | sentinel-3a | April 2024 control | 6 | in_track | 26 → 26 | 7 → 7 | 26.9% → 26.9% | 0.000000 | 13 → 13 | 50.0% → 50.0% | 0.000000 |
| reference | by_mission | sentinel-3a | April 2024 control | 6 | cross | 26 → 26 | 9 → 9 | 34.6% → 34.6% | 0.000000 | 13 → 13 | 50.0% → 50.0% | 0.000000 |
| reference | by_mission | sentinel-3a | April 2024 control | 12 | radial | 25 → 25 | 4 → 4 | 16.0% → 16.0% | 0.000000 | 6 → 6 | 24.0% → 24.0% | 0.000000 |
| reference | by_mission | sentinel-3a | April 2024 control | 12 | in_track | 25 → 25 | 17 → 17 | 68.0% → 68.0% | 0.000000 | 24 → 24 | 96.0% → 96.0% | 0.000000 |
| reference | by_mission | sentinel-3a | April 2024 control | 12 | cross | 25 → 25 | 5 → 5 | 20.0% → 20.0% | 0.000000 | 8 → 8 | 32.0% → 32.0% | 0.000000 |
| reference | by_mission | sentinel-3a | April 2024 control | 24 | radial | 22 → 22 | 15 → 15 | 68.2% → 68.2% | 0.000000 | 19 → 19 | 86.4% → 86.4% | 0.000000 |
| reference | by_mission | sentinel-3a | April 2024 control | 24 | in_track | 22 → 22 | 17 → 17 | 77.3% → 77.3% | 0.000000 | 22 → 22 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | April 2024 control | 24 | cross | 22 → 22 | 4 → 4 | 18.2% → 18.2% | 0.000000 | 12 → 12 | 54.5% → 54.5% | 0.000000 |
| reference | by_mission | sentinel-3a | April 2024 control | 36 | radial | 20 → 20 | 12 → 12 | 60.0% → 60.0% | 0.000000 | 12 → 12 | 60.0% → 60.0% | 0.000000 |
| reference | by_mission | sentinel-3a | April 2024 control | 36 | in_track | 20 → 20 | 20 → 20 | 100.0% → 100.0% | 0.000000 | 20 → 20 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | April 2024 control | 36 | cross | 20 → 20 | 9 → 9 | 45.0% → 45.0% | 0.000000 | 18 → 18 | 90.0% → 90.0% | 0.000000 |
| reference | by_mission | sentinel-3a | April 2024 control | 48 | radial | 18 → 18 | 6 → 6 | 33.3% → 33.3% | 0.000000 | 15 → 15 | 83.3% → 83.3% | 0.000000 |
| reference | by_mission | sentinel-3a | April 2024 control | 48 | in_track | 18 → 18 | 18 → 18 | 100.0% → 100.0% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | April 2024 control | 48 | cross | 18 → 18 | 14 → 14 | 77.8% → 77.8% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | April 2024 control | 72 | radial | 14 → 14 | 13 → 13 | 92.9% → 92.9% | 0.000000 | 14 → 14 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | April 2024 control | 72 | in_track | 14 → 14 | 14 → 14 | 100.0% → 100.0% | 0.000000 | 14 → 14 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | April 2024 control | 72 | cross | 14 → 14 | 10 → 10 | 71.4% → 71.4% | 0.000000 | 13 → 13 | 92.9% → 92.9% | 0.000000 |
| reference | by_mission | sentinel-3a | April 2024 control | 96 | radial | 9 → 9 | 4 → 4 | 44.4% → 44.4% | 0.000000 | 9 → 9 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | April 2024 control | 96 | in_track | 9 → 9 | 9 → 9 | 100.0% → 100.0% | 0.000000 | 9 → 9 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | April 2024 control | 96 | cross | 9 → 9 | 7 → 7 | 77.8% → 77.8% | 0.000000 | 9 → 9 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | April 2024 control | 120 | radial | 8 → 8 | 8 → 8 | 100.0% → 100.0% | 0.000000 | 8 → 8 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | April 2024 control | 120 | in_track | 8 → 8 | 8 → 8 | 100.0% → 100.0% | 0.000000 | 8 → 8 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | April 2024 control | 120 | cross | 8 → 8 | 7 → 7 | 87.5% → 87.5% | 0.000000 | 8 → 8 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | April 2024 control | 144 | radial | 8 → 8 | 6 → 6 | 75.0% → 75.0% | 0.000000 | 8 → 8 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | April 2024 control | 144 | in_track | 8 → 8 | 8 → 8 | 100.0% → 100.0% | 0.000000 | 8 → 8 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | April 2024 control | 144 | cross | 8 → 8 | 6 → 6 | 75.0% → 75.0% | 0.000000 | 8 → 8 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | April 2024 control | 168 | radial | 8 → 8 | 8 → 8 | 100.0% → 100.0% | 0.000000 | 8 → 8 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | April 2024 control | 168 | in_track | 8 → 8 | 8 → 8 | 100.0% → 100.0% | 0.000000 | 8 → 8 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | April 2024 control | 168 | cross | 8 → 8 | 8 → 8 | 100.0% → 100.0% | 0.000000 | 8 → 8 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | May 2024 | 6 | radial | 27 → 27 | 1 → 1 | 3.7% → 3.7% | 0.000000 | 6 → 6 | 22.2% → 22.2% | 0.000000 |
| reference | by_mission | sentinel-3a | May 2024 | 6 | in_track | 27 → 27 | 9 → 9 | 33.3% → 33.3% | 0.000000 | 17 → 17 | 63.0% → 63.0% | 0.000000 |
| reference | by_mission | sentinel-3a | May 2024 | 6 | cross | 27 → 27 | 4 → 4 | 14.8% → 14.8% | 0.000000 | 11 → 11 | 40.7% → 40.7% | 0.000000 |
| reference | by_mission | sentinel-3a | May 2024 | 12 | radial | 25 → 25 | 3 → 3 | 12.0% → 12.0% | 0.000000 | 6 → 6 | 24.0% → 24.0% | 0.000000 |
| reference | by_mission | sentinel-3a | May 2024 | 12 | in_track | 25 → 25 | 19 → 19 | 76.0% → 76.0% | 0.000000 | 21 → 21 | 84.0% → 84.0% | 0.000000 |
| reference | by_mission | sentinel-3a | May 2024 | 12 | cross | 25 → 25 | 2 → 2 | 8.0% → 8.0% | 0.000000 | 5 → 5 | 20.0% → 20.0% | 0.000000 |
| reference | by_mission | sentinel-3a | May 2024 | 24 | radial | 23 → 23 | 17 → 17 | 73.9% → 73.9% | 0.000000 | 18 → 18 | 78.3% → 78.3% | 0.000000 |
| reference | by_mission | sentinel-3a | May 2024 | 24 | in_track | 23 → 23 | 19 → 19 | 82.6% → 82.6% | 0.000000 | 23 → 23 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | May 2024 | 24 | cross | 23 → 23 | 6 → 6 | 26.1% → 26.1% | 0.000000 | 11 → 11 | 47.8% → 47.8% | 0.000000 |
| reference | by_mission | sentinel-3a | May 2024 | 36 | radial | 20 → 20 | 12 → 12 | 60.0% → 60.0% | 0.000000 | 13 → 13 | 65.0% → 65.0% | 0.000000 |
| reference | by_mission | sentinel-3a | May 2024 | 36 | in_track | 20 → 20 | 20 → 20 | 100.0% → 100.0% | 0.000000 | 20 → 20 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | May 2024 | 36 | cross | 20 → 20 | 7 → 7 | 35.0% → 35.0% | 0.000000 | 14 → 14 | 70.0% → 70.0% | 0.000000 |
| reference | by_mission | sentinel-3a | May 2024 | 48 | radial | 18 → 18 | 4 → 4 | 22.2% → 22.2% | 0.000000 | 13 → 13 | 72.2% → 72.2% | 0.000000 |
| reference | by_mission | sentinel-3a | May 2024 | 48 | in_track | 18 → 18 | 18 → 18 | 100.0% → 100.0% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | May 2024 | 48 | cross | 18 → 18 | 8 → 8 | 44.4% → 44.4% | 0.000000 | 14 → 14 | 77.8% → 77.8% | 0.000000 |
| reference | by_mission | sentinel-3a | May 2024 | 72 | radial | 17 → 17 | 16 → 16 | 94.1% → 94.1% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | May 2024 | 72 | in_track | 17 → 17 | 17 → 17 | 100.0% → 100.0% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | May 2024 | 72 | cross | 17 → 17 | 9 → 9 | 52.9% → 52.9% | 0.000000 | 14 → 14 | 82.4% → 82.4% | 0.000000 |
| reference | by_mission | sentinel-3a | May 2024 | 96 | radial | 13 → 13 | 6 → 6 | 46.2% → 46.2% | 0.000000 | 13 → 13 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | May 2024 | 96 | in_track | 13 → 13 | 13 → 13 | 100.0% → 100.0% | 0.000000 | 13 → 13 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | May 2024 | 96 | cross | 13 → 13 | 4 → 4 | 30.8% → 30.8% | 0.000000 | 10 → 10 | 76.9% → 76.9% | 0.000000 |
| reference | by_mission | sentinel-3a | May 2024 | 120 | radial | 9 → 9 | 9 → 9 | 100.0% → 100.0% | 0.000000 | 9 → 9 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | May 2024 | 120 | in_track | 9 → 9 | 9 → 9 | 100.0% → 100.0% | 0.000000 | 9 → 9 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | May 2024 | 120 | cross | 9 → 9 | 6 → 6 | 66.7% → 66.7% | 0.000000 | 9 → 9 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | May 2024 | 144 | radial | 5 → 5 | 1 → 1 | 20.0% → 20.0% | 0.000000 | 5 → 5 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | May 2024 | 144 | in_track | 5 → 5 | 5 → 5 | 100.0% → 100.0% | 0.000000 | 5 → 5 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | May 2024 | 144 | cross | 5 → 5 | 1 → 1 | 20.0% → 20.0% | 0.000000 | 5 → 5 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3a | May 2024 | 168 | radial | 0 → 0 | 0 → 0 | — → — | — | 0 → 0 | — → — | — |
| reference | by_mission | sentinel-3a | May 2024 | 168 | in_track | 0 → 0 | 0 → 0 | — → — | — | 0 → 0 | — → — | — |
| reference | by_mission | sentinel-3a | May 2024 | 168 | cross | 0 → 0 | 0 → 0 | — → — | — | 0 → 0 | — → — | — |
| reference | by_mission | sentinel-3b | August 2024 held out | 6 | radial | 13 → 13 | 3 → 3 | 23.1% → 23.1% | 0.000000 | 4 → 4 | 30.8% → 30.8% | 0.000000 |
| reference | by_mission | sentinel-3b | August 2024 held out | 6 | in_track | 13 → 13 | 5 → 5 | 38.5% → 38.5% | 0.000000 | 9 → 9 | 69.2% → 69.2% | 0.000000 |
| reference | by_mission | sentinel-3b | August 2024 held out | 6 | cross | 13 → 13 | 1 → 1 | 7.7% → 7.7% | 0.000000 | 4 → 4 | 30.8% → 30.8% | 0.000000 |
| reference | by_mission | sentinel-3b | August 2024 held out | 12 | radial | 13 → 13 | 3 → 3 | 23.1% → 23.1% | 0.000000 | 3 → 3 | 23.1% → 23.1% | 0.000000 |
| reference | by_mission | sentinel-3b | August 2024 held out | 12 | in_track | 13 → 13 | 10 → 10 | 76.9% → 76.9% | 0.000000 | 12 → 12 | 92.3% → 92.3% | 0.000000 |
| reference | by_mission | sentinel-3b | August 2024 held out | 12 | cross | 13 → 13 | 3 → 3 | 23.1% → 23.1% | 0.000000 | 4 → 4 | 30.8% → 30.8% | 0.000000 |
| reference | by_mission | sentinel-3b | August 2024 held out | 24 | radial | 11 → 11 | 5 → 5 | 45.5% → 45.5% | 0.000000 | 8 → 8 | 72.7% → 72.7% | 0.000000 |
| reference | by_mission | sentinel-3b | August 2024 held out | 24 | in_track | 11 → 11 | 9 → 9 | 81.8% → 81.8% | 0.000000 | 11 → 11 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | August 2024 held out | 24 | cross | 11 → 11 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 2 → 2 | 18.2% → 18.2% | 0.000000 |
| reference | by_mission | sentinel-3b | August 2024 held out | 36 | radial | 10 → 10 | 8 → 8 | 80.0% → 80.0% | 0.000000 | 8 → 8 | 80.0% → 80.0% | 0.000000 |
| reference | by_mission | sentinel-3b | August 2024 held out | 36 | in_track | 10 → 10 | 10 → 10 | 100.0% → 100.0% | 0.000000 | 10 → 10 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | August 2024 held out | 36 | cross | 10 → 10 | 3 → 3 | 30.0% → 30.0% | 0.000000 | 9 → 9 | 90.0% → 90.0% | 0.000000 |
| reference | by_mission | sentinel-3b | August 2024 held out | 48 | radial | 9 → 9 | 4 → 4 | 44.4% → 44.4% | 0.000000 | 7 → 7 | 77.8% → 77.8% | 0.000000 |
| reference | by_mission | sentinel-3b | August 2024 held out | 48 | in_track | 9 → 9 | 9 → 9 | 100.0% → 100.0% | 0.000000 | 9 → 9 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | August 2024 held out | 48 | cross | 9 → 9 | 6 → 6 | 66.7% → 66.7% | 0.000000 | 8 → 8 | 88.9% → 88.9% | 0.000000 |
| reference | by_mission | sentinel-3b | August 2024 held out | 72 | radial | 7 → 7 | 7 → 7 | 100.0% → 100.0% | 0.000000 | 7 → 7 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | August 2024 held out | 72 | in_track | 7 → 7 | 7 → 7 | 100.0% → 100.0% | 0.000000 | 7 → 7 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | August 2024 held out | 72 | cross | 7 → 7 | 1 → 1 | 14.3% → 14.3% | 0.000000 | 6 → 6 | 85.7% → 85.7% | 0.000000 |
| reference | by_mission | sentinel-3b | August 2024 held out | 96 | radial | 5 → 5 | 4 → 4 | 80.0% → 80.0% | 0.000000 | 5 → 5 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | August 2024 held out | 96 | in_track | 5 → 5 | 5 → 5 | 100.0% → 100.0% | 0.000000 | 5 → 5 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | August 2024 held out | 96 | cross | 5 → 5 | 4 → 4 | 80.0% → 80.0% | 0.000000 | 5 → 5 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | August 2024 held out | 120 | radial | 2 → 2 | 2 → 2 | 100.0% → 100.0% | 0.000000 | 2 → 2 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | August 2024 held out | 120 | in_track | 2 → 2 | 2 → 2 | 100.0% → 100.0% | 0.000000 | 2 → 2 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | August 2024 held out | 120 | cross | 2 → 2 | 1 → 1 | 50.0% → 50.0% | 0.000000 | 2 → 2 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | August 2024 held out | 144 | radial | 0 → 0 | 0 → 0 | — → — | — | 0 → 0 | — → — | — |
| reference | by_mission | sentinel-3b | August 2024 held out | 144 | in_track | 0 → 0 | 0 → 0 | — → — | — | 0 → 0 | — → — | — |
| reference | by_mission | sentinel-3b | August 2024 held out | 144 | cross | 0 → 0 | 0 → 0 | — → — | — | 0 → 0 | — → — | — |
| reference | by_mission | sentinel-3b | August 2024 held out | 168 | radial | 0 → 0 | 0 → 0 | — → — | — | 0 → 0 | — → — | — |
| reference | by_mission | sentinel-3b | August 2024 held out | 168 | in_track | 0 → 0 | 0 → 0 | — → — | — | 0 → 0 | — → — | — |
| reference | by_mission | sentinel-3b | August 2024 held out | 168 | cross | 0 → 0 | 0 → 0 | — → — | — | 0 → 0 | — → — | — |
| reference | by_mission | sentinel-3b | October 2024 held out | 6 | radial | 12 → 12 | 2 → 3 | 16.7% → 25.0% | 8.333333 | 4 → 4 | 33.3% → 33.3% | 0.000000 |
| reference | by_mission | sentinel-3b | October 2024 held out | 6 | in_track | 12 → 12 | 7 → 7 | 58.3% → 58.3% | 0.000000 | 10 → 10 | 83.3% → 83.3% | 0.000000 |
| reference | by_mission | sentinel-3b | October 2024 held out | 6 | cross | 12 → 12 | 2 → 2 | 16.7% → 16.7% | 0.000000 | 2 → 2 | 16.7% → 16.7% | 0.000000 |
| reference | by_mission | sentinel-3b | October 2024 held out | 12 | radial | 11 → 11 | 3 → 3 | 27.3% → 27.3% | 0.000000 | 5 → 5 | 45.5% → 45.5% | 0.000000 |
| reference | by_mission | sentinel-3b | October 2024 held out | 12 | in_track | 11 → 11 | 7 → 7 | 63.6% → 63.6% | 0.000000 | 9 → 9 | 81.8% → 81.8% | 0.000000 |
| reference | by_mission | sentinel-3b | October 2024 held out | 12 | cross | 11 → 11 | 3 → 3 | 27.3% → 27.3% | 0.000000 | 3 → 3 | 27.3% → 27.3% | 0.000000 |
| reference | by_mission | sentinel-3b | October 2024 held out | 24 | radial | 11 → 11 | 6 → 6 | 54.5% → 54.5% | 0.000000 | 9 → 9 | 81.8% → 81.8% | 0.000000 |
| reference | by_mission | sentinel-3b | October 2024 held out | 24 | in_track | 11 → 11 | 9 → 9 | 81.8% → 81.8% | 0.000000 | 9 → 9 | 81.8% → 81.8% | 0.000000 |
| reference | by_mission | sentinel-3b | October 2024 held out | 24 | cross | 11 → 11 | 1 → 1 | 9.1% → 9.1% | 0.000000 | 3 → 3 | 27.3% → 27.3% | 0.000000 |
| reference | by_mission | sentinel-3b | October 2024 held out | 36 | radial | 9 → 9 | 1 → 1 | 11.1% → 11.1% | 0.000000 | 3 → 3 | 33.3% → 33.3% | 0.000000 |
| reference | by_mission | sentinel-3b | October 2024 held out | 36 | in_track | 9 → 9 | 7 → 7 | 77.8% → 77.8% | 0.000000 | 7 → 7 | 77.8% → 77.8% | 0.000000 |
| reference | by_mission | sentinel-3b | October 2024 held out | 36 | cross | 9 → 9 | 2 → 2 | 22.2% → 22.2% | 0.000000 | 7 → 7 | 77.8% → 77.8% | 0.000000 |
| reference | by_mission | sentinel-3b | October 2024 held out | 48 | radial | 8 → 8 | 6 → 6 | 75.0% → 75.0% | 0.000000 | 8 → 8 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | October 2024 held out | 48 | in_track | 8 → 8 | 7 → 7 | 87.5% → 87.5% | 0.000000 | 7 → 7 | 87.5% → 87.5% | 0.000000 |
| reference | by_mission | sentinel-3b | October 2024 held out | 48 | cross | 8 → 8 | 2 → 2 | 25.0% → 25.0% | 0.000000 | 6 → 6 | 75.0% → 75.0% | 0.000000 |
| reference | by_mission | sentinel-3b | October 2024 held out | 72 | radial | 6 → 6 | 4 → 4 | 66.7% → 66.7% | 0.000000 | 6 → 6 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | October 2024 held out | 72 | in_track | 6 → 6 | 6 → 6 | 100.0% → 100.0% | 0.000000 | 6 → 6 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | October 2024 held out | 72 | cross | 6 → 6 | 3 → 3 | 50.0% → 50.0% | 0.000000 | 4 → 4 | 66.7% → 66.7% | 0.000000 |
| reference | by_mission | sentinel-3b | October 2024 held out | 96 | radial | 4 → 4 | 2 → 2 | 50.0% → 50.0% | 0.000000 | 4 → 4 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | October 2024 held out | 96 | in_track | 4 → 4 | 4 → 4 | 100.0% → 100.0% | 0.000000 | 4 → 4 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | October 2024 held out | 96 | cross | 4 → 4 | 4 → 4 | 100.0% → 100.0% | 0.000000 | 4 → 4 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | October 2024 held out | 120 | radial | 4 → 4 | 4 → 4 | 100.0% → 100.0% | 0.000000 | 4 → 4 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | October 2024 held out | 120 | in_track | 4 → 4 | 4 → 4 | 100.0% → 100.0% | 0.000000 | 4 → 4 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | October 2024 held out | 120 | cross | 4 → 4 | 3 → 3 | 75.0% → 75.0% | 0.000000 | 4 → 4 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | October 2024 held out | 144 | radial | 4 → 4 | 3 → 3 | 75.0% → 75.0% | 0.000000 | 4 → 4 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | October 2024 held out | 144 | in_track | 4 → 4 | 4 → 4 | 100.0% → 100.0% | 0.000000 | 4 → 4 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | October 2024 held out | 144 | cross | 4 → 4 | 3 → 3 | 75.0% → 75.0% | 0.000000 | 4 → 4 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | October 2024 held out | 168 | radial | 4 → 4 | 4 → 4 | 100.0% → 100.0% | 0.000000 | 4 → 4 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | October 2024 held out | 168 | in_track | 4 → 4 | 4 → 4 | 100.0% → 100.0% | 0.000000 | 4 → 4 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | October 2024 held out | 168 | cross | 4 → 4 | 2 → 2 | 50.0% → 50.0% | 0.000000 | 3 → 3 | 75.0% → 75.0% | 0.000000 |
| reference | by_mission | sentinel-3b | April 2024 control | 6 | radial | 12 → 12 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | sentinel-3b | April 2024 control | 6 | in_track | 12 → 12 | 5 → 5 | 41.7% → 41.7% | 0.000000 | 11 → 11 | 91.7% → 91.7% | 0.000000 |
| reference | by_mission | sentinel-3b | April 2024 control | 6 | cross | 12 → 12 | 4 → 4 | 33.3% → 33.3% | 0.000000 | 5 → 5 | 41.7% → 41.7% | 0.000000 |
| reference | by_mission | sentinel-3b | April 2024 control | 12 | radial | 12 → 12 | 1 → 1 | 8.3% → 8.3% | 0.000000 | 1 → 1 | 8.3% → 8.3% | 0.000000 |
| reference | by_mission | sentinel-3b | April 2024 control | 12 | in_track | 12 → 12 | 11 → 11 | 91.7% → 91.7% | 0.000000 | 12 → 12 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | April 2024 control | 12 | cross | 12 → 12 | 1 → 1 | 8.3% → 8.3% | 0.000000 | 1 → 1 | 8.3% → 8.3% | 0.000000 |
| reference | by_mission | sentinel-3b | April 2024 control | 24 | radial | 11 → 11 | 7 → 7 | 63.6% → 63.6% | 0.000000 | 10 → 10 | 90.9% → 90.9% | 0.000000 |
| reference | by_mission | sentinel-3b | April 2024 control | 24 | in_track | 11 → 11 | 11 → 11 | 100.0% → 100.0% | 0.000000 | 11 → 11 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | April 2024 control | 24 | cross | 11 → 11 | 3 → 3 | 27.3% → 27.3% | 0.000000 | 6 → 6 | 54.5% → 54.5% | 0.000000 |
| reference | by_mission | sentinel-3b | April 2024 control | 36 | radial | 10 → 10 | 8 → 8 | 80.0% → 80.0% | 0.000000 | 8 → 8 | 80.0% → 80.0% | 0.000000 |
| reference | by_mission | sentinel-3b | April 2024 control | 36 | in_track | 10 → 10 | 10 → 10 | 100.0% → 100.0% | 0.000000 | 10 → 10 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | April 2024 control | 36 | cross | 10 → 10 | 5 → 5 | 50.0% → 50.0% | 0.000000 | 10 → 10 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | April 2024 control | 48 | radial | 9 → 9 | 2 → 2 | 22.2% → 22.2% | 0.000000 | 9 → 9 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | April 2024 control | 48 | in_track | 9 → 9 | 9 → 9 | 100.0% → 100.0% | 0.000000 | 9 → 9 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | April 2024 control | 48 | cross | 9 → 9 | 7 → 7 | 77.8% → 77.8% | 0.000000 | 9 → 9 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | April 2024 control | 72 | radial | 7 → 7 | 6 → 6 | 85.7% → 85.7% | 0.000000 | 7 → 7 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | April 2024 control | 72 | in_track | 7 → 7 | 7 → 7 | 100.0% → 100.0% | 0.000000 | 7 → 7 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | April 2024 control | 72 | cross | 7 → 7 | 2 → 2 | 28.6% → 28.6% | 0.000000 | 7 → 7 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | April 2024 control | 96 | radial | 5 → 5 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 5 → 5 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | April 2024 control | 96 | in_track | 5 → 5 | 5 → 5 | 100.0% → 100.0% | 0.000000 | 5 → 5 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | April 2024 control | 96 | cross | 5 → 5 | 4 → 4 | 80.0% → 80.0% | 0.000000 | 5 → 5 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | April 2024 control | 120 | radial | 3 → 3 | 3 → 3 | 100.0% → 100.0% | 0.000000 | 3 → 3 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | April 2024 control | 120 | in_track | 3 → 3 | 3 → 3 | 100.0% → 100.0% | 0.000000 | 3 → 3 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | April 2024 control | 120 | cross | 3 → 3 | 2 → 2 | 66.7% → 66.7% | 0.000000 | 3 → 3 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | April 2024 control | 144 | radial | 2 → 2 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 2 → 2 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | April 2024 control | 144 | in_track | 2 → 2 | 2 → 2 | 100.0% → 100.0% | 0.000000 | 2 → 2 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | April 2024 control | 144 | cross | 2 → 2 | 2 → 2 | 100.0% → 100.0% | 0.000000 | 2 → 2 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | April 2024 control | 168 | radial | 2 → 2 | 1 → 1 | 50.0% → 50.0% | 0.000000 | 2 → 2 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | April 2024 control | 168 | in_track | 2 → 2 | 2 → 2 | 100.0% → 100.0% | 0.000000 | 2 → 2 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | April 2024 control | 168 | cross | 2 → 2 | 2 → 2 | 100.0% → 100.0% | 0.000000 | 2 → 2 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | May 2024 | 6 | radial | 19 → 19 | 4 → 4 | 21.1% → 21.1% | 0.000000 | 5 → 5 | 26.3% → 26.3% | 0.000000 |
| reference | by_mission | sentinel-3b | May 2024 | 6 | in_track | 19 → 19 | 8 → 8 | 42.1% → 42.1% | 0.000000 | 18 → 18 | 94.7% → 94.7% | 0.000000 |
| reference | by_mission | sentinel-3b | May 2024 | 6 | cross | 19 → 19 | 1 → 1 | 5.3% → 5.3% | 0.000000 | 3 → 3 | 15.8% → 15.8% | 0.000000 |
| reference | by_mission | sentinel-3b | May 2024 | 12 | radial | 19 → 19 | 4 → 4 | 21.1% → 21.1% | 0.000000 | 6 → 6 | 31.6% → 31.6% | 0.000000 |
| reference | by_mission | sentinel-3b | May 2024 | 12 | in_track | 19 → 19 | 15 → 15 | 78.9% → 78.9% | 0.000000 | 17 → 17 | 89.5% → 89.5% | 0.000000 |
| reference | by_mission | sentinel-3b | May 2024 | 12 | cross | 19 → 19 | 4 → 4 | 21.1% → 21.1% | 0.000000 | 6 → 6 | 31.6% → 31.6% | 0.000000 |
| reference | by_mission | sentinel-3b | May 2024 | 24 | radial | 19 → 19 | 12 → 12 | 63.2% → 63.2% | 0.000000 | 14 → 14 | 73.7% → 73.7% | 0.000000 |
| reference | by_mission | sentinel-3b | May 2024 | 24 | in_track | 19 → 19 | 17 → 17 | 89.5% → 89.5% | 0.000000 | 18 → 18 | 94.7% → 94.7% | 0.000000 |
| reference | by_mission | sentinel-3b | May 2024 | 24 | cross | 19 → 19 | 2 → 2 | 10.5% → 10.5% | 0.000000 | 8 → 8 | 42.1% → 42.1% | 0.000000 |
| reference | by_mission | sentinel-3b | May 2024 | 36 | radial | 19 → 19 | 11 → 11 | 57.9% → 57.9% | 0.000000 | 13 → 13 | 68.4% → 68.4% | 0.000000 |
| reference | by_mission | sentinel-3b | May 2024 | 36 | in_track | 19 → 19 | 18 → 18 | 94.7% → 94.7% | 0.000000 | 18 → 18 | 94.7% → 94.7% | 0.000000 |
| reference | by_mission | sentinel-3b | May 2024 | 36 | cross | 19 → 19 | 14 → 14 | 73.7% → 73.7% | 0.000000 | 17 → 17 | 89.5% → 89.5% | 0.000000 |
| reference | by_mission | sentinel-3b | May 2024 | 48 | radial | 19 → 19 | 9 → 9 | 47.4% → 47.4% | 0.000000 | 17 → 17 | 89.5% → 89.5% | 0.000000 |
| reference | by_mission | sentinel-3b | May 2024 | 48 | in_track | 19 → 19 | 18 → 18 | 94.7% → 94.7% | 0.000000 | 18 → 18 | 94.7% → 94.7% | 0.000000 |
| reference | by_mission | sentinel-3b | May 2024 | 48 | cross | 19 → 19 | 14 → 14 | 73.7% → 73.7% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | May 2024 | 72 | radial | 17 → 17 | 16 → 16 | 94.1% → 94.1% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | May 2024 | 72 | in_track | 17 → 17 | 16 → 16 | 94.1% → 94.1% | 0.000000 | 16 → 16 | 94.1% → 94.1% | 0.000000 |
| reference | by_mission | sentinel-3b | May 2024 | 72 | cross | 17 → 17 | 9 → 9 | 52.9% → 52.9% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | May 2024 | 96 | radial | 14 → 14 | 8 → 8 | 57.1% → 57.1% | 0.000000 | 14 → 14 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | May 2024 | 96 | in_track | 14 → 14 | 14 → 14 | 100.0% → 100.0% | 0.000000 | 14 → 14 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | May 2024 | 96 | cross | 14 → 14 | 12 → 12 | 85.7% → 85.7% | 0.000000 | 14 → 14 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | May 2024 | 120 | radial | 12 → 12 | 11 → 11 | 91.7% → 91.7% | 0.000000 | 12 → 12 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | May 2024 | 120 | in_track | 12 → 12 | 12 → 12 | 100.0% → 100.0% | 0.000000 | 12 → 12 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | May 2024 | 120 | cross | 12 → 12 | 12 → 12 | 100.0% → 100.0% | 0.000000 | 12 → 12 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | May 2024 | 144 | radial | 9 → 9 | 4 → 4 | 44.4% → 44.4% | 0.000000 | 9 → 9 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | May 2024 | 144 | in_track | 9 → 9 | 9 → 9 | 100.0% → 100.0% | 0.000000 | 9 → 9 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | May 2024 | 144 | cross | 9 → 9 | 8 → 8 | 88.9% → 88.9% | 0.000000 | 9 → 9 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | May 2024 | 168 | radial | 6 → 6 | 6 → 6 | 100.0% → 100.0% | 0.000000 | 6 → 6 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | May 2024 | 168 | in_track | 6 → 6 | 6 → 6 | 100.0% → 100.0% | 0.000000 | 6 → 6 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-3b | May 2024 | 168 | cross | 6 → 6 | 6 → 6 | 100.0% → 100.0% | 0.000000 | 6 → 6 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | August 2024 held out | 6 | radial | 18 → 18 | 6 → 6 | 33.3% → 33.3% | 0.000000 | 9 → 9 | 50.0% → 50.0% | 0.000000 |
| reference | by_mission | sentinel-6a | August 2024 held out | 6 | in_track | 18 → 18 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | sentinel-6a | August 2024 held out | 6 | cross | 18 → 18 | 2 → 2 | 11.1% → 11.1% | 0.000000 | 5 → 5 | 27.8% → 27.8% | 0.000000 |
| reference | by_mission | sentinel-6a | August 2024 held out | 12 | radial | 18 → 18 | 1 → 1 | 5.6% → 5.6% | 0.000000 | 4 → 4 | 22.2% → 22.2% | 0.000000 |
| reference | by_mission | sentinel-6a | August 2024 held out | 12 | in_track | 18 → 18 | 1 → 1 | 5.6% → 5.6% | 0.000000 | 1 → 1 | 5.6% → 5.6% | 0.000000 |
| reference | by_mission | sentinel-6a | August 2024 held out | 12 | cross | 18 → 18 | 1 → 1 | 5.6% → 5.6% | 0.000000 | 6 → 6 | 33.3% → 33.3% | 0.000000 |
| reference | by_mission | sentinel-6a | August 2024 held out | 24 | radial | 18 → 18 | 4 → 4 | 22.2% → 22.2% | 0.000000 | 16 → 16 | 88.9% → 88.9% | 0.000000 |
| reference | by_mission | sentinel-6a | August 2024 held out | 24 | in_track | 18 → 18 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 1 → 1 | 5.6% → 5.6% | 0.000000 |
| reference | by_mission | sentinel-6a | August 2024 held out | 24 | cross | 18 → 18 | 1 → 1 | 5.6% → 5.6% | 0.000000 | 7 → 7 | 38.9% → 38.9% | 0.000000 |
| reference | by_mission | sentinel-6a | August 2024 held out | 36 | radial | 18 → 18 | 14 → 14 | 77.8% → 77.8% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | August 2024 held out | 36 | in_track | 18 → 18 | 1 → 1 | 5.6% → 5.6% | 0.000000 | 1 → 1 | 5.6% → 5.6% | 0.000000 |
| reference | by_mission | sentinel-6a | August 2024 held out | 36 | cross | 18 → 18 | 3 → 3 | 16.7% → 16.7% | 0.000000 | 7 → 7 | 38.9% → 38.9% | 0.000000 |
| reference | by_mission | sentinel-6a | August 2024 held out | 48 | radial | 18 → 18 | 4 → 4 | 22.2% → 22.2% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | August 2024 held out | 48 | in_track | 18 → 18 | 5 → 5 | 27.8% → 27.8% | 0.000000 | 7 → 7 | 38.9% → 38.9% | 0.000000 |
| reference | by_mission | sentinel-6a | August 2024 held out | 48 | cross | 18 → 18 | 6 → 6 | 33.3% → 33.3% | 0.000000 | 9 → 9 | 50.0% → 50.0% | 0.000000 |
| reference | by_mission | sentinel-6a | August 2024 held out | 72 | radial | 18 → 18 | 12 → 12 | 66.7% → 66.7% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | August 2024 held out | 72 | in_track | 18 → 18 | 5 → 5 | 27.8% → 27.8% | 0.000000 | 9 → 9 | 50.0% → 50.0% | 0.000000 |
| reference | by_mission | sentinel-6a | August 2024 held out | 72 | cross | 18 → 18 | 13 → 13 | 72.2% → 72.2% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | August 2024 held out | 96 | radial | 18 → 18 | 18 → 18 | 100.0% → 100.0% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | August 2024 held out | 96 | in_track | 18 → 18 | 2 → 2 | 11.1% → 11.1% | 0.000000 | 3 → 3 | 16.7% → 16.7% | 0.000000 |
| reference | by_mission | sentinel-6a | August 2024 held out | 96 | cross | 18 → 18 | 9 → 9 | 50.0% → 50.0% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | August 2024 held out | 120 | radial | 18 → 18 | 11 → 11 | 61.1% → 61.1% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | August 2024 held out | 120 | in_track | 18 → 18 | 1 → 1 | 5.6% → 5.6% | 0.000000 | 5 → 5 | 27.8% → 27.8% | 0.000000 |
| reference | by_mission | sentinel-6a | August 2024 held out | 120 | cross | 18 → 18 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | August 2024 held out | 144 | radial | 18 → 18 | 18 → 18 | 100.0% → 100.0% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | August 2024 held out | 144 | in_track | 18 → 18 | 8 → 8 | 44.4% → 44.4% | 0.000000 | 9 → 9 | 50.0% → 50.0% | 0.000000 |
| reference | by_mission | sentinel-6a | August 2024 held out | 144 | cross | 18 → 18 | 14 → 14 | 77.8% → 77.8% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | August 2024 held out | 168 | radial | 18 → 18 | 18 → 18 | 100.0% → 100.0% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | August 2024 held out | 168 | in_track | 18 → 18 | 7 → 7 | 38.9% → 38.9% | 0.000000 | 8 → 8 | 44.4% → 44.4% | 0.000000 |
| reference | by_mission | sentinel-6a | August 2024 held out | 168 | cross | 18 → 18 | 10 → 10 | 55.6% → 55.6% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | October 2024 held out | 6 | radial | 15 → 15 | 7 → 7 | 46.7% → 46.7% | 0.000000 | 15 → 15 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | October 2024 held out | 6 | in_track | 15 → 15 | 5 → 5 | 33.3% → 33.3% | 0.000000 | 5 → 5 | 33.3% → 33.3% | 0.000000 |
| reference | by_mission | sentinel-6a | October 2024 held out | 6 | cross | 15 → 15 | 4 → 4 | 26.7% → 26.7% | 0.000000 | 7 → 7 | 46.7% → 46.7% | 0.000000 |
| reference | by_mission | sentinel-6a | October 2024 held out | 12 | radial | 15 → 15 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 2 → 2 | 13.3% → 13.3% | 0.000000 |
| reference | by_mission | sentinel-6a | October 2024 held out | 12 | in_track | 15 → 15 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | sentinel-6a | October 2024 held out | 12 | cross | 15 → 15 | 3 → 3 | 20.0% → 20.0% | 0.000000 | 8 → 8 | 53.3% → 53.3% | 0.000000 |
| reference | by_mission | sentinel-6a | October 2024 held out | 24 | radial | 15 → 15 | 9 → 9 | 60.0% → 60.0% | 0.000000 | 15 → 15 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | October 2024 held out | 24 | in_track | 15 → 15 | 4 → 4 | 26.7% → 26.7% | 0.000000 | 9 → 9 | 60.0% → 60.0% | 0.000000 |
| reference | by_mission | sentinel-6a | October 2024 held out | 24 | cross | 15 → 15 | 6 → 6 | 40.0% → 40.0% | 0.000000 | 13 → 13 | 86.7% → 86.7% | 0.000000 |
| reference | by_mission | sentinel-6a | October 2024 held out | 36 | radial | 15 → 15 | 14 → 14 | 93.3% → 93.3% | 0.000000 | 15 → 15 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | October 2024 held out | 36 | in_track | 15 → 15 | 2 → 2 | 13.3% → 13.3% | 0.000000 | 7 → 7 | 46.7% → 46.7% | 0.000000 |
| reference | by_mission | sentinel-6a | October 2024 held out | 36 | cross | 15 → 15 | 5 → 5 | 33.3% → 33.3% | 0.000000 | 11 → 11 | 73.3% → 73.3% | 0.000000 |
| reference | by_mission | sentinel-6a | October 2024 held out | 48 | radial | 15 → 15 | 7 → 7 | 46.7% → 46.7% | 0.000000 | 15 → 15 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | October 2024 held out | 48 | in_track | 15 → 15 | 10 → 10 | 66.7% → 66.7% | 0.000000 | 15 → 15 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | October 2024 held out | 48 | cross | 15 → 15 | 6 → 6 | 40.0% → 40.0% | 0.000000 | 15 → 15 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | October 2024 held out | 72 | radial | 15 → 15 | 7 → 7 | 46.7% → 46.7% | 0.000000 | 15 → 15 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | October 2024 held out | 72 | in_track | 15 → 15 | 14 → 14 | 93.3% → 93.3% | 0.000000 | 15 → 15 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | October 2024 held out | 72 | cross | 15 → 15 | 12 → 12 | 80.0% → 80.0% | 0.000000 | 15 → 15 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | October 2024 held out | 96 | radial | 15 → 15 | 15 → 15 | 100.0% → 100.0% | 0.000000 | 15 → 15 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | October 2024 held out | 96 | in_track | 15 → 15 | 15 → 15 | 100.0% → 100.0% | 0.000000 | 15 → 15 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | October 2024 held out | 96 | cross | 15 → 15 | 15 → 15 | 100.0% → 100.0% | 0.000000 | 15 → 15 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | October 2024 held out | 120 | radial | 15 → 15 | 5 → 5 | 33.3% → 33.3% | 0.000000 | 15 → 15 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | October 2024 held out | 120 | in_track | 15 → 15 | 15 → 15 | 100.0% → 100.0% | 0.000000 | 15 → 15 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | October 2024 held out | 120 | cross | 15 → 15 | 7 → 7 | 46.7% → 46.7% | 0.000000 | 15 → 15 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | October 2024 held out | 144 | radial | 15 → 15 | 10 → 10 | 66.7% → 66.7% | 0.000000 | 15 → 15 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | October 2024 held out | 144 | in_track | 15 → 15 | 15 → 15 | 100.0% → 100.0% | 0.000000 | 15 → 15 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | October 2024 held out | 144 | cross | 15 → 15 | 14 → 14 | 93.3% → 93.3% | 0.000000 | 15 → 15 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | October 2024 held out | 168 | radial | 15 → 15 | 15 → 15 | 100.0% → 100.0% | 0.000000 | 15 → 15 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | October 2024 held out | 168 | in_track | 15 → 15 | 15 → 15 | 100.0% → 100.0% | 0.000000 | 15 → 15 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | October 2024 held out | 168 | cross | 15 → 15 | 15 → 15 | 100.0% → 100.0% | 0.000000 | 15 → 15 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | April 2024 control | 6 | radial | 18 → 18 | 6 → 6 | 33.3% → 33.3% | 0.000000 | 10 → 10 | 55.6% → 55.6% | 0.000000 |
| reference | by_mission | sentinel-6a | April 2024 control | 6 | in_track | 18 → 18 | 2 → 2 | 11.1% → 11.1% | 0.000000 | 4 → 4 | 22.2% → 22.2% | 0.000000 |
| reference | by_mission | sentinel-6a | April 2024 control | 6 | cross | 18 → 18 | 5 → 5 | 27.8% → 27.8% | 0.000000 | 10 → 10 | 55.6% → 55.6% | 0.000000 |
| reference | by_mission | sentinel-6a | April 2024 control | 12 | radial | 18 → 18 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 1 → 1 | 5.6% → 5.6% | 0.000000 |
| reference | by_mission | sentinel-6a | April 2024 control | 12 | in_track | 18 → 18 | 1 → 1 | 5.6% → 5.6% | 0.000000 | 1 → 1 | 5.6% → 5.6% | 0.000000 |
| reference | by_mission | sentinel-6a | April 2024 control | 12 | cross | 18 → 18 | 4 → 4 | 22.2% → 22.2% | 0.000000 | 6 → 6 | 33.3% → 33.3% | 0.000000 |
| reference | by_mission | sentinel-6a | April 2024 control | 24 | radial | 18 → 18 | 6 → 6 | 33.3% → 33.3% | 0.000000 | 15 → 15 | 83.3% → 83.3% | 0.000000 |
| reference | by_mission | sentinel-6a | April 2024 control | 24 | in_track | 18 → 18 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | sentinel-6a | April 2024 control | 24 | cross | 18 → 18 | 11 → 11 | 61.1% → 61.1% | 0.000000 | 16 → 16 | 88.9% → 88.9% | 0.000000 |
| reference | by_mission | sentinel-6a | April 2024 control | 36 | radial | 18 → 18 | 16 → 16 | 88.9% → 88.9% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | April 2024 control | 36 | in_track | 18 → 18 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | sentinel-6a | April 2024 control | 36 | cross | 18 → 18 | 13 → 13 | 72.2% → 72.2% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | April 2024 control | 48 | radial | 18 → 18 | 14 → 14 | 77.8% → 77.8% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | April 2024 control | 48 | in_track | 18 → 18 | 2 → 2 | 11.1% → 11.1% | 0.000000 | 4 → 4 | 22.2% → 22.2% | 0.000000 |
| reference | by_mission | sentinel-6a | April 2024 control | 48 | cross | 18 → 18 | 14 → 14 | 77.8% → 77.8% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | April 2024 control | 72 | radial | 18 → 18 | 18 → 18 | 100.0% → 100.0% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | April 2024 control | 72 | in_track | 18 → 18 | 1 → 1 | 5.6% → 5.6% | 0.000000 | 3 → 3 | 16.7% → 16.7% | 0.000000 |
| reference | by_mission | sentinel-6a | April 2024 control | 72 | cross | 18 → 18 | 10 → 10 | 55.6% → 55.6% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | April 2024 control | 96 | radial | 18 → 18 | 18 → 18 | 100.0% → 100.0% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | April 2024 control | 96 | in_track | 18 → 18 | 2 → 2 | 11.1% → 11.1% | 0.000000 | 3 → 3 | 16.7% → 16.7% | 0.000000 |
| reference | by_mission | sentinel-6a | April 2024 control | 96 | cross | 18 → 18 | 18 → 18 | 100.0% → 100.0% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | April 2024 control | 120 | radial | 18 → 18 | 16 → 16 | 88.9% → 88.9% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | April 2024 control | 120 | in_track | 18 → 18 | 2 → 2 | 11.1% → 11.1% | 0.000000 | 7 → 7 | 38.9% → 38.9% | 0.000000 |
| reference | by_mission | sentinel-6a | April 2024 control | 120 | cross | 18 → 18 | 1 → 1 | 5.6% → 5.6% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | April 2024 control | 144 | radial | 18 → 18 | 18 → 18 | 100.0% → 100.0% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | April 2024 control | 144 | in_track | 18 → 18 | 7 → 7 | 38.9% → 38.9% | 0.000000 | 13 → 13 | 72.2% → 72.2% | 0.000000 |
| reference | by_mission | sentinel-6a | April 2024 control | 144 | cross | 18 → 18 | 17 → 17 | 94.4% → 94.4% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | April 2024 control | 168 | radial | 18 → 18 | 18 → 18 | 100.0% → 100.0% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | April 2024 control | 168 | in_track | 18 → 18 | 6 → 6 | 33.3% → 33.3% | 0.000000 | 8 → 8 | 44.4% → 44.4% | 0.000000 |
| reference | by_mission | sentinel-6a | April 2024 control | 168 | cross | 18 → 18 | 18 → 18 | 100.0% → 100.0% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | May 2024 | 6 | radial | 15 → 15 | 5 → 5 | 33.3% → 33.3% | 0.000000 | 11 → 11 | 73.3% → 73.3% | 0.000000 |
| reference | by_mission | sentinel-6a | May 2024 | 6 | in_track | 15 → 15 | 4 → 4 | 26.7% → 26.7% | 0.000000 | 4 → 4 | 26.7% → 26.7% | 0.000000 |
| reference | by_mission | sentinel-6a | May 2024 | 6 | cross | 15 → 15 | 3 → 3 | 20.0% → 20.0% | 0.000000 | 5 → 5 | 33.3% → 33.3% | 0.000000 |
| reference | by_mission | sentinel-6a | May 2024 | 12 | radial | 15 → 15 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | sentinel-6a | May 2024 | 12 | in_track | 15 → 15 | 2 → 2 | 13.3% → 13.3% | 0.000000 | 4 → 4 | 26.7% → 26.7% | 0.000000 |
| reference | by_mission | sentinel-6a | May 2024 | 12 | cross | 15 → 15 | 3 → 3 | 20.0% → 20.0% | 0.000000 | 9 → 9 | 60.0% → 60.0% | 0.000000 |
| reference | by_mission | sentinel-6a | May 2024 | 24 | radial | 15 → 15 | 10 → 10 | 66.7% → 66.7% | 0.000000 | 14 → 14 | 93.3% → 93.3% | 0.000000 |
| reference | by_mission | sentinel-6a | May 2024 | 24 | in_track | 15 → 15 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | sentinel-6a | May 2024 | 24 | cross | 15 → 15 | 9 → 9 | 60.0% → 60.0% | 0.000000 | 15 → 15 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | May 2024 | 36 | radial | 15 → 15 | 15 → 15 | 100.0% → 100.0% | 0.000000 | 15 → 15 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | May 2024 | 36 | in_track | 15 → 15 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 3 → 3 | 20.0% → 20.0% | 0.000000 |
| reference | by_mission | sentinel-6a | May 2024 | 36 | cross | 15 → 15 | 8 → 8 | 53.3% → 53.3% | 0.000000 | 14 → 14 | 93.3% → 93.3% | 0.000000 |
| reference | by_mission | sentinel-6a | May 2024 | 48 | radial | 15 → 15 | 15 → 15 | 100.0% → 100.0% | 0.000000 | 15 → 15 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | May 2024 | 48 | in_track | 15 → 15 | 1 → 1 | 6.7% → 6.7% | 0.000000 | 1 → 1 | 6.7% → 6.7% | 0.000000 |
| reference | by_mission | sentinel-6a | May 2024 | 48 | cross | 15 → 15 | 2 → 2 | 13.3% → 13.3% | 0.000000 | 13 → 13 | 86.7% → 86.7% | 0.000000 |
| reference | by_mission | sentinel-6a | May 2024 | 72 | radial | 15 → 15 | 15 → 15 | 100.0% → 100.0% | 0.000000 | 15 → 15 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | May 2024 | 72 | in_track | 15 → 15 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | sentinel-6a | May 2024 | 72 | cross | 15 → 15 | 9 → 9 | 60.0% → 60.0% | 0.000000 | 15 → 15 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | May 2024 | 96 | radial | 15 → 15 | 15 → 15 | 100.0% → 100.0% | 0.000000 | 15 → 15 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | May 2024 | 96 | in_track | 15 → 15 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | sentinel-6a | May 2024 | 96 | cross | 15 → 15 | 15 → 15 | 100.0% → 100.0% | 0.000000 | 15 → 15 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | May 2024 | 120 | radial | 15 → 15 | 15 → 15 | 100.0% → 100.0% | 0.000000 | 15 → 15 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | May 2024 | 120 | in_track | 15 → 15 | 1 → 1 | 6.7% → 6.7% | 0.000000 | 3 → 3 | 20.0% → 20.0% | 0.000000 |
| reference | by_mission | sentinel-6a | May 2024 | 120 | cross | 15 → 15 | 6 → 6 | 40.0% → 40.0% | 0.000000 | 15 → 15 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | May 2024 | 144 | radial | 15 → 15 | 15 → 15 | 100.0% → 100.0% | 0.000000 | 15 → 15 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | May 2024 | 144 | in_track | 15 → 15 | 3 → 3 | 20.0% → 20.0% | 0.000000 | 6 → 6 | 40.0% → 40.0% | 0.000000 |
| reference | by_mission | sentinel-6a | May 2024 | 144 | cross | 15 → 15 | 15 → 15 | 100.0% → 100.0% | 0.000000 | 15 → 15 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | May 2024 | 168 | radial | 15 → 15 | 15 → 15 | 100.0% → 100.0% | 0.000000 | 15 → 15 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | sentinel-6a | May 2024 | 168 | in_track | 15 → 15 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 5 → 5 | 33.3% → 33.3% | 0.000000 |
| reference | by_mission | sentinel-6a | May 2024 | 168 | cross | 15 → 15 | 15 → 15 | 100.0% → 100.0% | 0.000000 | 15 → 15 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-a | August 2024 held out | 6 | radial | 19 → 19 | 3 → 3 | 15.8% → 15.8% | 0.000000 | 11 → 11 | 57.9% → 57.9% | 0.000000 |
| reference | by_mission | swarm-a | August 2024 held out | 6 | in_track | 19 → 19 | 3 → 3 | 15.8% → 15.8% | 0.000000 | 9 → 9 | 47.4% → 47.4% | 0.000000 |
| reference | by_mission | swarm-a | August 2024 held out | 6 | cross | 19 → 19 | 1 → 1 | 5.3% → 5.3% | 0.000000 | 1 → 1 | 5.3% → 5.3% | 0.000000 |
| reference | by_mission | swarm-a | August 2024 held out | 12 | radial | 19 → 19 | 8 → 8 | 42.1% → 42.1% | 0.000000 | 18 → 18 | 94.7% → 94.7% | 0.000000 |
| reference | by_mission | swarm-a | August 2024 held out | 12 | in_track | 19 → 19 | 5 → 5 | 26.3% → 26.3% | 0.000000 | 7 → 7 | 36.8% → 36.8% | 0.000000 |
| reference | by_mission | swarm-a | August 2024 held out | 12 | cross | 19 → 19 | 2 → 2 | 10.5% → 10.5% | 0.000000 | 2 → 2 | 10.5% → 10.5% | 0.000000 |
| reference | by_mission | swarm-a | August 2024 held out | 24 | radial | 19 → 19 | 17 → 17 | 89.5% → 89.5% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-a | August 2024 held out | 24 | in_track | 19 → 19 | 10 → 10 | 52.6% → 52.6% | 0.000000 | 13 → 13 | 68.4% → 68.4% | 0.000000 |
| reference | by_mission | swarm-a | August 2024 held out | 24 | cross | 19 → 19 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 1 → 1 | 5.3% → 5.3% | 0.000000 |
| reference | by_mission | swarm-a | August 2024 held out | 36 | radial | 19 → 19 | 12 → 12 | 63.2% → 63.2% | 0.000000 | 18 → 18 | 94.7% → 94.7% | 0.000000 |
| reference | by_mission | swarm-a | August 2024 held out | 36 | in_track | 19 → 19 | 8 → 8 | 42.1% → 42.1% | 0.000000 | 12 → 12 | 63.2% → 63.2% | 0.000000 |
| reference | by_mission | swarm-a | August 2024 held out | 36 | cross | 19 → 19 | 4 → 4 | 21.1% → 21.1% | 0.000000 | 7 → 7 | 36.8% → 36.8% | 0.000000 |
| reference | by_mission | swarm-a | August 2024 held out | 48 | radial | 19 → 19 | 12 → 12 | 63.2% → 63.2% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-a | August 2024 held out | 48 | in_track | 19 → 19 | 6 → 6 | 31.6% → 31.6% | 0.000000 | 8 → 8 | 42.1% → 42.1% | 0.000000 |
| reference | by_mission | swarm-a | August 2024 held out | 48 | cross | 19 → 19 | 3 → 3 | 15.8% → 15.8% | 0.000000 | 4 → 4 | 21.1% → 21.1% | 0.000000 |
| reference | by_mission | swarm-a | August 2024 held out | 72 | radial | 19 → 19 | 11 → 11 | 57.9% → 57.9% | 0.000000 | 17 → 17 | 89.5% → 89.5% | 0.000000 |
| reference | by_mission | swarm-a | August 2024 held out | 72 | in_track | 19 → 19 | 4 → 4 | 21.1% → 21.1% | 0.000000 | 7 → 7 | 36.8% → 36.8% | 0.000000 |
| reference | by_mission | swarm-a | August 2024 held out | 72 | cross | 19 → 19 | 3 → 3 | 15.8% → 15.8% | 0.000000 | 8 → 8 | 42.1% → 42.1% | 0.000000 |
| reference | by_mission | swarm-a | August 2024 held out | 96 | radial | 19 → 19 | 17 → 17 | 89.5% → 89.5% | 0.000000 | 17 → 17 | 89.5% → 89.5% | 0.000000 |
| reference | by_mission | swarm-a | August 2024 held out | 96 | in_track | 19 → 19 | 3 → 3 | 15.8% → 15.8% | 0.000000 | 7 → 7 | 36.8% → 36.8% | 0.000000 |
| reference | by_mission | swarm-a | August 2024 held out | 96 | cross | 19 → 19 | 2 → 2 | 10.5% → 10.5% | 0.000000 | 5 → 5 | 26.3% → 26.3% | 0.000000 |
| reference | by_mission | swarm-a | August 2024 held out | 120 | radial | 19 → 19 | 16 → 16 | 84.2% → 84.2% | 0.000000 | 17 → 17 | 89.5% → 89.5% | 0.000000 |
| reference | by_mission | swarm-a | August 2024 held out | 120 | in_track | 19 → 19 | 3 → 3 | 15.8% → 15.8% | 0.000000 | 6 → 6 | 31.6% → 31.6% | 0.000000 |
| reference | by_mission | swarm-a | August 2024 held out | 120 | cross | 19 → 19 | 2 → 2 | 10.5% → 10.5% | 0.000000 | 5 → 5 | 26.3% → 26.3% | 0.000000 |
| reference | by_mission | swarm-a | August 2024 held out | 144 | radial | 19 → 19 | 7 → 7 | 36.8% → 36.8% | 0.000000 | 16 → 16 | 84.2% → 84.2% | 0.000000 |
| reference | by_mission | swarm-a | August 2024 held out | 144 | in_track | 19 → 19 | 4 → 4 | 21.1% → 21.1% | 0.000000 | 7 → 7 | 36.8% → 36.8% | 0.000000 |
| reference | by_mission | swarm-a | August 2024 held out | 144 | cross | 19 → 19 | 9 → 9 | 47.4% → 47.4% | 0.000000 | 16 → 16 | 84.2% → 84.2% | 0.000000 |
| reference | by_mission | swarm-a | August 2024 held out | 168 | radial | 19 → 19 | 15 → 16 | 78.9% → 84.2% | 5.263158 | 16 → 16 | 84.2% → 84.2% | 0.000000 |
| reference | by_mission | swarm-a | August 2024 held out | 168 | in_track | 19 → 19 | 5 → 5 | 26.3% → 26.3% | 0.000000 | 7 → 7 | 36.8% → 36.8% | 0.000000 |
| reference | by_mission | swarm-a | August 2024 held out | 168 | cross | 19 → 19 | 4 → 4 | 21.1% → 21.1% | 0.000000 | 11 → 11 | 57.9% → 57.9% | 0.000000 |
| reference | by_mission | swarm-a | October 2024 held out | 6 | radial | 21 → 21 | 8 → 8 | 38.1% → 38.1% | 0.000000 | 16 → 16 | 76.2% → 76.2% | 0.000000 |
| reference | by_mission | swarm-a | October 2024 held out | 6 | in_track | 21 → 21 | 7 → 7 | 33.3% → 33.3% | 0.000000 | 15 → 15 | 71.4% → 71.4% | 0.000000 |
| reference | by_mission | swarm-a | October 2024 held out | 6 | cross | 21 → 21 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 2 → 2 | 9.5% → 9.5% | 0.000000 |
| reference | by_mission | swarm-a | October 2024 held out | 12 | radial | 21 → 21 | 1 → 1 | 4.8% → 4.8% | 0.000000 | 5 → 5 | 23.8% → 23.8% | 0.000000 |
| reference | by_mission | swarm-a | October 2024 held out | 12 | in_track | 21 → 21 | 8 → 8 | 38.1% → 38.1% | 0.000000 | 14 → 14 | 66.7% → 66.7% | 0.000000 |
| reference | by_mission | swarm-a | October 2024 held out | 12 | cross | 21 → 21 | 1 → 1 | 4.8% → 4.8% | 0.000000 | 2 → 2 | 9.5% → 9.5% | 0.000000 |
| reference | by_mission | swarm-a | October 2024 held out | 24 | radial | 21 → 21 | 10 → 10 | 47.6% → 47.6% | 0.000000 | 19 → 19 | 90.5% → 90.5% | 0.000000 |
| reference | by_mission | swarm-a | October 2024 held out | 24 | in_track | 21 → 21 | 11 → 11 | 52.4% → 52.4% | 0.000000 | 14 → 14 | 66.7% → 66.7% | 0.000000 |
| reference | by_mission | swarm-a | October 2024 held out | 24 | cross | 21 → 21 | 1 → 1 | 4.8% → 4.8% | 0.000000 | 1 → 1 | 4.8% → 4.8% | 0.000000 |
| reference | by_mission | swarm-a | October 2024 held out | 36 | radial | 21 → 21 | 1 → 1 | 4.8% → 4.8% | 0.000000 | 15 → 15 | 71.4% → 71.4% | 0.000000 |
| reference | by_mission | swarm-a | October 2024 held out | 36 | in_track | 21 → 21 | 11 → 11 | 52.4% → 52.4% | 0.000000 | 13 → 13 | 61.9% → 61.9% | 0.000000 |
| reference | by_mission | swarm-a | October 2024 held out | 36 | cross | 21 → 21 | 3 → 3 | 14.3% → 14.3% | 0.000000 | 4 → 4 | 19.0% → 19.0% | 0.000000 |
| reference | by_mission | swarm-a | October 2024 held out | 48 | radial | 21 → 21 | 19 → 19 | 90.5% → 90.5% | 0.000000 | 19 → 20 | 90.5% → 95.2% | 4.761905 |
| reference | by_mission | swarm-a | October 2024 held out | 48 | in_track | 21 → 21 | 11 → 11 | 52.4% → 52.4% | 0.000000 | 14 → 14 | 66.7% → 66.7% | 0.000000 |
| reference | by_mission | swarm-a | October 2024 held out | 48 | cross | 21 → 21 | 3 → 3 | 14.3% → 14.3% | 0.000000 | 4 → 4 | 19.0% → 19.0% | 0.000000 |
| reference | by_mission | swarm-a | October 2024 held out | 72 | radial | 21 → 21 | 12 → 12 | 57.1% → 57.1% | 0.000000 | 17 → 17 | 81.0% → 81.0% | 0.000000 |
| reference | by_mission | swarm-a | October 2024 held out | 72 | in_track | 21 → 21 | 10 → 10 | 47.6% → 47.6% | 0.000000 | 13 → 13 | 61.9% → 61.9% | 0.000000 |
| reference | by_mission | swarm-a | October 2024 held out | 72 | cross | 21 → 21 | 7 → 7 | 33.3% → 33.3% | 0.000000 | 10 → 10 | 47.6% → 47.6% | 0.000000 |
| reference | by_mission | swarm-a | October 2024 held out | 96 | radial | 18 → 18 | 14 → 16 | 77.8% → 88.9% | 11.111111 | 16 → 16 | 88.9% → 88.9% | 0.000000 |
| reference | by_mission | swarm-a | October 2024 held out | 96 | in_track | 18 → 18 | 10 → 10 | 55.6% → 55.6% | 0.000000 | 10 → 10 | 55.6% → 55.6% | 0.000000 |
| reference | by_mission | swarm-a | October 2024 held out | 96 | cross | 18 → 18 | 1 → 1 | 5.6% → 5.6% | 0.000000 | 3 → 3 | 16.7% → 16.7% | 0.000000 |
| reference | by_mission | swarm-a | October 2024 held out | 120 | radial | 14 → 14 | 10 → 10 | 71.4% → 71.4% | 0.000000 | 10 → 12 | 71.4% → 85.7% | 14.285714 |
| reference | by_mission | swarm-a | October 2024 held out | 120 | in_track | 14 → 14 | 10 → 10 | 71.4% → 71.4% | 0.000000 | 10 → 10 | 71.4% → 71.4% | 0.000000 |
| reference | by_mission | swarm-a | October 2024 held out | 120 | cross | 14 → 14 | 2 → 2 | 14.3% → 14.3% | 0.000000 | 4 → 4 | 28.6% → 28.6% | 0.000000 |
| reference | by_mission | swarm-a | October 2024 held out | 144 | radial | 12 → 12 | 9 → 9 | 75.0% → 75.0% | 0.000000 | 9 → 9 | 75.0% → 75.0% | 0.000000 |
| reference | by_mission | swarm-a | October 2024 held out | 144 | in_track | 12 → 12 | 9 → 9 | 75.0% → 75.0% | 0.000000 | 9 → 9 | 75.0% → 75.0% | 0.000000 |
| reference | by_mission | swarm-a | October 2024 held out | 144 | cross | 12 → 12 | 9 → 9 | 75.0% → 75.0% | 0.000000 | 10 → 10 | 83.3% → 83.3% | 0.000000 |
| reference | by_mission | swarm-a | October 2024 held out | 168 | radial | 10 → 10 | 7 → 7 | 70.0% → 70.0% | 0.000000 | 7 → 9 | 70.0% → 90.0% | 20.000000 |
| reference | by_mission | swarm-a | October 2024 held out | 168 | in_track | 10 → 10 | 7 → 7 | 70.0% → 70.0% | 0.000000 | 7 → 7 | 70.0% → 70.0% | 0.000000 |
| reference | by_mission | swarm-a | October 2024 held out | 168 | cross | 10 → 10 | 1 → 1 | 10.0% → 10.0% | 0.000000 | 5 → 5 | 50.0% → 50.0% | 0.000000 |
| reference | by_mission | swarm-a | April 2024 control | 6 | radial | 19 → 19 | 13 → 13 | 68.4% → 68.4% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-a | April 2024 control | 6 | in_track | 19 → 19 | 8 → 8 | 42.1% → 42.1% | 0.000000 | 12 → 12 | 63.2% → 63.2% | 0.000000 |
| reference | by_mission | swarm-a | April 2024 control | 6 | cross | 19 → 19 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | swarm-a | April 2024 control | 12 | radial | 19 → 19 | 12 → 12 | 63.2% → 63.2% | 0.000000 | 16 → 16 | 84.2% → 84.2% | 0.000000 |
| reference | by_mission | swarm-a | April 2024 control | 12 | in_track | 19 → 19 | 7 → 7 | 36.8% → 36.8% | 0.000000 | 11 → 11 | 57.9% → 57.9% | 0.000000 |
| reference | by_mission | swarm-a | April 2024 control | 12 | cross | 19 → 19 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | swarm-a | April 2024 control | 24 | radial | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-a | April 2024 control | 24 | in_track | 19 → 19 | 14 → 14 | 73.7% → 73.7% | 0.000000 | 18 → 18 | 94.7% → 94.7% | 0.000000 |
| reference | by_mission | swarm-a | April 2024 control | 24 | cross | 19 → 19 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 1 → 1 | 5.3% → 5.3% | 0.000000 |
| reference | by_mission | swarm-a | April 2024 control | 36 | radial | 19 → 19 | 12 → 12 | 63.2% → 63.2% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-a | April 2024 control | 36 | in_track | 19 → 19 | 16 → 16 | 84.2% → 84.2% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-a | April 2024 control | 36 | cross | 19 → 19 | 7 → 7 | 36.8% → 36.8% | 0.000000 | 10 → 10 | 52.6% → 52.6% | 0.000000 |
| reference | by_mission | swarm-a | April 2024 control | 48 | radial | 19 → 19 | 14 → 14 | 73.7% → 73.7% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-a | April 2024 control | 48 | in_track | 19 → 19 | 17 → 17 | 89.5% → 89.5% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-a | April 2024 control | 48 | cross | 19 → 19 | 3 → 3 | 15.8% → 15.8% | 0.000000 | 5 → 5 | 26.3% → 26.3% | 0.000000 |
| reference | by_mission | swarm-a | April 2024 control | 72 | radial | 19 → 19 | 12 → 12 | 63.2% → 63.2% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-a | April 2024 control | 72 | in_track | 19 → 19 | 18 → 18 | 94.7% → 94.7% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-a | April 2024 control | 72 | cross | 19 → 19 | 8 → 8 | 42.1% → 42.1% | 0.000000 | 14 → 14 | 73.7% → 73.7% | 0.000000 |
| reference | by_mission | swarm-a | April 2024 control | 96 | radial | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-a | April 2024 control | 96 | in_track | 19 → 19 | 18 → 18 | 94.7% → 94.7% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-a | April 2024 control | 96 | cross | 19 → 19 | 4 → 4 | 21.1% → 21.1% | 0.000000 | 8 → 8 | 42.1% → 42.1% | 0.000000 |
| reference | by_mission | swarm-a | April 2024 control | 120 | radial | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-a | April 2024 control | 120 | in_track | 19 → 19 | 18 → 18 | 94.7% → 94.7% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-a | April 2024 control | 120 | cross | 19 → 19 | 8 → 8 | 42.1% → 42.1% | 0.000000 | 17 → 17 | 89.5% → 89.5% | 0.000000 |
| reference | by_mission | swarm-a | April 2024 control | 144 | radial | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-a | April 2024 control | 144 | in_track | 19 → 19 | 17 → 17 | 89.5% → 89.5% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-a | April 2024 control | 144 | cross | 19 → 19 | 5 → 5 | 26.3% → 26.3% | 0.000000 | 12 → 12 | 63.2% → 63.2% | 0.000000 |
| reference | by_mission | swarm-a | April 2024 control | 168 | radial | 19 → 19 | 18 → 18 | 94.7% → 94.7% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-a | April 2024 control | 168 | in_track | 19 → 19 | 15 → 15 | 78.9% → 78.9% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-a | April 2024 control | 168 | cross | 19 → 19 | 5 → 5 | 26.3% → 26.3% | 0.000000 | 11 → 11 | 57.9% → 57.9% | 0.000000 |
| reference | by_mission | swarm-a | May 2024 | 6 | radial | 18 → 18 | 8 → 8 | 44.4% → 44.4% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-a | May 2024 | 6 | in_track | 18 → 18 | 6 → 6 | 33.3% → 33.3% | 0.000000 | 13 → 13 | 72.2% → 72.2% | 0.000000 |
| reference | by_mission | swarm-a | May 2024 | 6 | cross | 18 → 18 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | swarm-a | May 2024 | 12 | radial | 18 → 18 | 13 → 13 | 72.2% → 72.2% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-a | May 2024 | 12 | in_track | 18 → 18 | 7 → 7 | 38.9% → 38.9% | 0.000000 | 13 → 13 | 72.2% → 72.2% | 0.000000 |
| reference | by_mission | swarm-a | May 2024 | 12 | cross | 18 → 18 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | swarm-a | May 2024 | 24 | radial | 18 → 18 | 15 → 15 | 83.3% → 83.3% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-a | May 2024 | 24 | in_track | 18 → 18 | 11 → 11 | 61.1% → 61.1% | 0.000000 | 14 → 14 | 77.8% → 77.8% | 0.000000 |
| reference | by_mission | swarm-a | May 2024 | 24 | cross | 18 → 18 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | swarm-a | May 2024 | 36 | radial | 18 → 18 | 15 → 15 | 83.3% → 83.3% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-a | May 2024 | 36 | in_track | 18 → 18 | 14 → 14 | 77.8% → 77.8% | 0.000000 | 14 → 14 | 77.8% → 77.8% | 0.000000 |
| reference | by_mission | swarm-a | May 2024 | 36 | cross | 18 → 18 | 6 → 6 | 33.3% → 33.3% | 0.000000 | 9 → 9 | 50.0% → 50.0% | 0.000000 |
| reference | by_mission | swarm-a | May 2024 | 48 | radial | 18 → 18 | 10 → 10 | 55.6% → 55.6% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-a | May 2024 | 48 | in_track | 18 → 18 | 11 → 11 | 61.1% → 61.1% | 0.000000 | 14 → 14 | 77.8% → 77.8% | 0.000000 |
| reference | by_mission | swarm-a | May 2024 | 48 | cross | 18 → 18 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 3 → 3 | 16.7% → 16.7% | 0.000000 |
| reference | by_mission | swarm-a | May 2024 | 72 | radial | 18 → 18 | 14 → 14 | 77.8% → 77.8% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-a | May 2024 | 72 | in_track | 18 → 18 | 10 → 10 | 55.6% → 55.6% | 0.000000 | 12 → 12 | 66.7% → 66.7% | 0.000000 |
| reference | by_mission | swarm-a | May 2024 | 72 | cross | 18 → 18 | 10 → 10 | 55.6% → 55.6% | 0.000000 | 16 → 16 | 88.9% → 88.9% | 0.000000 |
| reference | by_mission | swarm-a | May 2024 | 96 | radial | 18 → 18 | 17 → 17 | 94.4% → 94.4% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-a | May 2024 | 96 | in_track | 18 → 18 | 8 → 8 | 44.4% → 44.4% | 0.000000 | 12 → 12 | 66.7% → 66.7% | 0.000000 |
| reference | by_mission | swarm-a | May 2024 | 96 | cross | 18 → 18 | 1 → 1 | 5.6% → 5.6% | 0.000000 | 1 → 1 | 5.6% → 5.6% | 0.000000 |
| reference | by_mission | swarm-a | May 2024 | 120 | radial | 18 → 18 | 16 → 16 | 88.9% → 88.9% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-a | May 2024 | 120 | in_track | 18 → 18 | 7 → 7 | 38.9% → 38.9% | 0.000000 | 13 → 13 | 72.2% → 72.2% | 0.000000 |
| reference | by_mission | swarm-a | May 2024 | 120 | cross | 18 → 18 | 13 → 13 | 72.2% → 72.2% | 0.000000 | 17 → 17 | 94.4% → 94.4% | 0.000000 |
| reference | by_mission | swarm-a | May 2024 | 144 | radial | 18 → 18 | 15 → 16 | 83.3% → 88.9% | 5.555556 | 16 → 18 | 88.9% → 100.0% | 11.111111 |
| reference | by_mission | swarm-a | May 2024 | 144 | in_track | 18 → 18 | 7 → 7 | 38.9% → 38.9% | 0.000000 | 13 → 13 | 72.2% → 72.2% | 0.000000 |
| reference | by_mission | swarm-a | May 2024 | 144 | cross | 18 → 18 | 14 → 14 | 77.8% → 77.8% | 0.000000 | 16 → 16 | 88.9% → 88.9% | 0.000000 |
| reference | by_mission | swarm-a | May 2024 | 168 | radial | 18 → 18 | 16 → 16 | 88.9% → 88.9% | 0.000000 | 16 → 18 | 88.9% → 100.0% | 11.111111 |
| reference | by_mission | swarm-a | May 2024 | 168 | in_track | 18 → 18 | 7 → 7 | 38.9% → 38.9% | 0.000000 | 16 → 16 | 88.9% → 88.9% | 0.000000 |
| reference | by_mission | swarm-a | May 2024 | 168 | cross | 18 → 18 | 3 → 3 | 16.7% → 16.7% | 0.000000 | 15 → 15 | 83.3% → 83.3% | 0.000000 |
| reference | by_mission | swarm-b | August 2024 held out | 6 | radial | 19 → 19 | 4 → 4 | 21.1% → 21.1% | 0.000000 | 18 → 18 | 94.7% → 94.7% | 0.000000 |
| reference | by_mission | swarm-b | August 2024 held out | 6 | in_track | 19 → 19 | 4 → 4 | 21.1% → 21.1% | 0.000000 | 7 → 7 | 36.8% → 36.8% | 0.000000 |
| reference | by_mission | swarm-b | August 2024 held out | 6 | cross | 19 → 19 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | swarm-b | August 2024 held out | 12 | radial | 19 → 19 | 17 → 17 | 89.5% → 89.5% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-b | August 2024 held out | 12 | in_track | 19 → 19 | 5 → 5 | 26.3% → 26.3% | 0.000000 | 10 → 10 | 52.6% → 52.6% | 0.000000 |
| reference | by_mission | swarm-b | August 2024 held out | 12 | cross | 19 → 19 | 2 → 2 | 10.5% → 10.5% | 0.000000 | 7 → 7 | 36.8% → 36.8% | 0.000000 |
| reference | by_mission | swarm-b | August 2024 held out | 24 | radial | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-b | August 2024 held out | 24 | in_track | 19 → 19 | 10 → 10 | 52.6% → 52.6% | 0.000000 | 16 → 16 | 84.2% → 84.2% | 0.000000 |
| reference | by_mission | swarm-b | August 2024 held out | 24 | cross | 19 → 19 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 1 → 1 | 5.3% → 5.3% | 0.000000 |
| reference | by_mission | swarm-b | August 2024 held out | 36 | radial | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-b | August 2024 held out | 36 | in_track | 19 → 19 | 9 → 9 | 47.4% → 47.4% | 0.000000 | 13 → 13 | 68.4% → 68.4% | 0.000000 |
| reference | by_mission | swarm-b | August 2024 held out | 36 | cross | 19 → 19 | 1 → 1 | 5.3% → 5.3% | 0.000000 | 1 → 1 | 5.3% → 5.3% | 0.000000 |
| reference | by_mission | swarm-b | August 2024 held out | 48 | radial | 19 → 19 | 11 → 11 | 57.9% → 57.9% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-b | August 2024 held out | 48 | in_track | 19 → 19 | 10 → 10 | 52.6% → 52.6% | 0.000000 | 12 → 12 | 63.2% → 63.2% | 0.000000 |
| reference | by_mission | swarm-b | August 2024 held out | 48 | cross | 19 → 19 | 13 → 13 | 68.4% → 68.4% | 0.000000 | 17 → 17 | 89.5% → 89.5% | 0.000000 |
| reference | by_mission | swarm-b | August 2024 held out | 72 | radial | 19 → 19 | 17 → 17 | 89.5% → 89.5% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-b | August 2024 held out | 72 | in_track | 19 → 19 | 4 → 4 | 21.1% → 21.1% | 0.000000 | 10 → 10 | 52.6% → 52.6% | 0.000000 |
| reference | by_mission | swarm-b | August 2024 held out | 72 | cross | 19 → 19 | 7 → 7 | 36.8% → 36.8% | 0.000000 | 10 → 10 | 52.6% → 52.6% | 0.000000 |
| reference | by_mission | swarm-b | August 2024 held out | 96 | radial | 19 → 19 | 18 → 18 | 94.7% → 94.7% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-b | August 2024 held out | 96 | in_track | 19 → 19 | 3 → 3 | 15.8% → 15.8% | 0.000000 | 6 → 6 | 31.6% → 31.6% | 0.000000 |
| reference | by_mission | swarm-b | August 2024 held out | 96 | cross | 19 → 19 | 11 → 11 | 57.9% → 57.9% | 0.000000 | 18 → 18 | 94.7% → 94.7% | 0.000000 |
| reference | by_mission | swarm-b | August 2024 held out | 120 | radial | 19 → 19 | 9 → 9 | 47.4% → 47.4% | 0.000000 | 18 → 18 | 94.7% → 94.7% | 0.000000 |
| reference | by_mission | swarm-b | August 2024 held out | 120 | in_track | 19 → 19 | 4 → 4 | 21.1% → 21.1% | 0.000000 | 5 → 5 | 26.3% → 26.3% | 0.000000 |
| reference | by_mission | swarm-b | August 2024 held out | 120 | cross | 19 → 19 | 10 → 10 | 52.6% → 52.6% | 0.000000 | 13 → 13 | 68.4% → 68.4% | 0.000000 |
| reference | by_mission | swarm-b | August 2024 held out | 144 | radial | 19 → 19 | 16 → 16 | 84.2% → 84.2% | 0.000000 | 18 → 18 | 94.7% → 94.7% | 0.000000 |
| reference | by_mission | swarm-b | August 2024 held out | 144 | in_track | 19 → 19 | 4 → 4 | 21.1% → 21.1% | 0.000000 | 5 → 5 | 26.3% → 26.3% | 0.000000 |
| reference | by_mission | swarm-b | August 2024 held out | 144 | cross | 19 → 19 | 9 → 9 | 47.4% → 47.4% | 0.000000 | 17 → 17 | 89.5% → 89.5% | 0.000000 |
| reference | by_mission | swarm-b | August 2024 held out | 168 | radial | 19 → 19 | 18 → 18 | 94.7% → 94.7% | 0.000000 | 18 → 18 | 94.7% → 94.7% | 0.000000 |
| reference | by_mission | swarm-b | August 2024 held out | 168 | in_track | 19 → 19 | 4 → 4 | 21.1% → 21.1% | 0.000000 | 5 → 5 | 26.3% → 26.3% | 0.000000 |
| reference | by_mission | swarm-b | August 2024 held out | 168 | cross | 19 → 19 | 9 → 9 | 47.4% → 47.4% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-b | October 2024 held out | 6 | radial | 19 → 19 | 12 → 12 | 63.2% → 63.2% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-b | October 2024 held out | 6 | in_track | 19 → 19 | 4 → 4 | 21.1% → 21.1% | 0.000000 | 12 → 12 | 63.2% → 63.2% | 0.000000 |
| reference | by_mission | swarm-b | October 2024 held out | 6 | cross | 19 → 19 | 1 → 1 | 5.3% → 5.3% | 0.000000 | 3 → 3 | 15.8% → 15.8% | 0.000000 |
| reference | by_mission | swarm-b | October 2024 held out | 12 | radial | 19 → 19 | 10 → 10 | 52.6% → 52.6% | 0.000000 | 10 → 10 | 52.6% → 52.6% | 0.000000 |
| reference | by_mission | swarm-b | October 2024 held out | 12 | in_track | 19 → 19 | 3 → 3 | 15.8% → 15.8% | 0.000000 | 10 → 10 | 52.6% → 52.6% | 0.000000 |
| reference | by_mission | swarm-b | October 2024 held out | 12 | cross | 19 → 19 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 1 → 1 | 5.3% → 5.3% | 0.000000 |
| reference | by_mission | swarm-b | October 2024 held out | 24 | radial | 19 → 19 | 18 → 18 | 94.7% → 94.7% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-b | October 2024 held out | 24 | in_track | 19 → 19 | 9 → 9 | 47.4% → 47.4% | 0.000000 | 14 → 14 | 73.7% → 73.7% | 0.000000 |
| reference | by_mission | swarm-b | October 2024 held out | 24 | cross | 19 → 19 | 4 → 4 | 21.1% → 21.1% | 0.000000 | 7 → 7 | 36.8% → 36.8% | 0.000000 |
| reference | by_mission | swarm-b | October 2024 held out | 36 | radial | 19 → 19 | 17 → 17 | 89.5% → 89.5% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-b | October 2024 held out | 36 | in_track | 19 → 19 | 8 → 8 | 42.1% → 42.1% | 0.000000 | 12 → 12 | 63.2% → 63.2% | 0.000000 |
| reference | by_mission | swarm-b | October 2024 held out | 36 | cross | 19 → 19 | 5 → 5 | 26.3% → 26.3% | 0.000000 | 6 → 6 | 31.6% → 31.6% | 0.000000 |
| reference | by_mission | swarm-b | October 2024 held out | 48 | radial | 19 → 19 | 13 → 13 | 68.4% → 68.4% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-b | October 2024 held out | 48 | in_track | 19 → 19 | 8 → 8 | 42.1% → 42.1% | 0.000000 | 14 → 14 | 73.7% → 73.7% | 0.000000 |
| reference | by_mission | swarm-b | October 2024 held out | 48 | cross | 19 → 19 | 6 → 6 | 31.6% → 31.6% | 0.000000 | 7 → 7 | 36.8% → 36.8% | 0.000000 |
| reference | by_mission | swarm-b | October 2024 held out | 72 | radial | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-b | October 2024 held out | 72 | in_track | 19 → 19 | 8 → 8 | 42.1% → 42.1% | 0.000000 | 14 → 14 | 73.7% → 73.7% | 0.000000 |
| reference | by_mission | swarm-b | October 2024 held out | 72 | cross | 19 → 19 | 10 → 10 | 52.6% → 52.6% | 0.000000 | 18 → 18 | 94.7% → 94.7% | 0.000000 |
| reference | by_mission | swarm-b | October 2024 held out | 96 | radial | 19 → 19 | 14 → 14 | 73.7% → 73.7% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-b | October 2024 held out | 96 | in_track | 19 → 19 | 13 → 13 | 68.4% → 68.4% | 0.000000 | 14 → 14 | 73.7% → 73.7% | 0.000000 |
| reference | by_mission | swarm-b | October 2024 held out | 96 | cross | 19 → 19 | 5 → 5 | 26.3% → 26.3% | 0.000000 | 9 → 9 | 47.4% → 47.4% | 0.000000 |
| reference | by_mission | swarm-b | October 2024 held out | 120 | radial | 19 → 19 | 14 → 14 | 73.7% → 73.7% | 0.000000 | 15 → 15 | 78.9% → 78.9% | 0.000000 |
| reference | by_mission | swarm-b | October 2024 held out | 120 | in_track | 19 → 19 | 13 → 13 | 68.4% → 68.4% | 0.000000 | 14 → 14 | 73.7% → 73.7% | 0.000000 |
| reference | by_mission | swarm-b | October 2024 held out | 120 | cross | 19 → 19 | 13 → 13 | 68.4% → 68.4% | 0.000000 | 16 → 16 | 84.2% → 84.2% | 0.000000 |
| reference | by_mission | swarm-b | October 2024 held out | 144 | radial | 17 → 17 | 12 → 12 | 70.6% → 70.6% | 0.000000 | 14 → 15 | 82.4% → 88.2% | 5.882353 |
| reference | by_mission | swarm-b | October 2024 held out | 144 | in_track | 17 → 17 | 11 → 11 | 64.7% → 64.7% | 0.000000 | 12 → 12 | 70.6% → 70.6% | 0.000000 |
| reference | by_mission | swarm-b | October 2024 held out | 144 | cross | 17 → 17 | 9 → 9 | 52.9% → 52.9% | 0.000000 | 16 → 16 | 94.1% → 94.1% | 0.000000 |
| reference | by_mission | swarm-b | October 2024 held out | 168 | radial | 15 → 15 | 12 → 12 | 80.0% → 80.0% | 0.000000 | 12 → 13 | 80.0% → 86.7% | 6.666667 |
| reference | by_mission | swarm-b | October 2024 held out | 168 | in_track | 15 → 15 | 11 → 11 | 73.3% → 73.3% | 0.000000 | 12 → 12 | 80.0% → 80.0% | 0.000000 |
| reference | by_mission | swarm-b | October 2024 held out | 168 | cross | 15 → 15 | 6 → 6 | 40.0% → 40.0% | 0.000000 | 13 → 13 | 86.7% → 86.7% | 0.000000 |
| reference | by_mission | swarm-b | April 2024 control | 6 | radial | 19 → 19 | 13 → 13 | 68.4% → 68.4% | 0.000000 | 17 → 17 | 89.5% → 89.5% | 0.000000 |
| reference | by_mission | swarm-b | April 2024 control | 6 | in_track | 19 → 19 | 7 → 7 | 36.8% → 36.8% | 0.000000 | 12 → 12 | 63.2% → 63.2% | 0.000000 |
| reference | by_mission | swarm-b | April 2024 control | 6 | cross | 19 → 19 | 1 → 1 | 5.3% → 5.3% | 0.000000 | 1 → 1 | 5.3% → 5.3% | 0.000000 |
| reference | by_mission | swarm-b | April 2024 control | 12 | radial | 19 → 19 | 12 → 12 | 63.2% → 63.2% | 0.000000 | 17 → 17 | 89.5% → 89.5% | 0.000000 |
| reference | by_mission | swarm-b | April 2024 control | 12 | in_track | 19 → 19 | 4 → 4 | 21.1% → 21.1% | 0.000000 | 10 → 10 | 52.6% → 52.6% | 0.000000 |
| reference | by_mission | swarm-b | April 2024 control | 12 | cross | 19 → 19 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | swarm-b | April 2024 control | 24 | radial | 19 → 19 | 16 → 16 | 84.2% → 84.2% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-b | April 2024 control | 24 | in_track | 19 → 19 | 15 → 15 | 78.9% → 78.9% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-b | April 2024 control | 24 | cross | 19 → 19 | 1 → 1 | 5.3% → 5.3% | 0.000000 | 3 → 3 | 15.8% → 15.8% | 0.000000 |
| reference | by_mission | swarm-b | April 2024 control | 36 | radial | 19 → 19 | 17 → 17 | 89.5% → 89.5% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-b | April 2024 control | 36 | in_track | 19 → 19 | 15 → 15 | 78.9% → 78.9% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-b | April 2024 control | 36 | cross | 19 → 19 | 3 → 3 | 15.8% → 15.8% | 0.000000 | 5 → 5 | 26.3% → 26.3% | 0.000000 |
| reference | by_mission | swarm-b | April 2024 control | 48 | radial | 19 → 19 | 16 → 16 | 84.2% → 84.2% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-b | April 2024 control | 48 | in_track | 19 → 19 | 18 → 18 | 94.7% → 94.7% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-b | April 2024 control | 48 | cross | 19 → 19 | 1 → 1 | 5.3% → 5.3% | 0.000000 | 3 → 3 | 15.8% → 15.8% | 0.000000 |
| reference | by_mission | swarm-b | April 2024 control | 72 | radial | 19 → 19 | 12 → 12 | 63.2% → 63.2% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-b | April 2024 control | 72 | in_track | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-b | April 2024 control | 72 | cross | 19 → 19 | 11 → 11 | 57.9% → 57.9% | 0.000000 | 15 → 15 | 78.9% → 78.9% | 0.000000 |
| reference | by_mission | swarm-b | April 2024 control | 96 | radial | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-b | April 2024 control | 96 | in_track | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-b | April 2024 control | 96 | cross | 19 → 19 | 6 → 6 | 31.6% → 31.6% | 0.000000 | 10 → 10 | 52.6% → 52.6% | 0.000000 |
| reference | by_mission | swarm-b | April 2024 control | 120 | radial | 19 → 19 | 15 → 15 | 78.9% → 78.9% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-b | April 2024 control | 120 | in_track | 19 → 19 | 16 → 16 | 84.2% → 84.2% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-b | April 2024 control | 120 | cross | 19 → 19 | 8 → 8 | 42.1% → 42.1% | 0.000000 | 15 → 15 | 78.9% → 78.9% | 0.000000 |
| reference | by_mission | swarm-b | April 2024 control | 144 | radial | 19 → 19 | 18 → 18 | 94.7% → 94.7% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-b | April 2024 control | 144 | in_track | 19 → 19 | 15 → 15 | 78.9% → 78.9% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-b | April 2024 control | 144 | cross | 19 → 19 | 14 → 14 | 73.7% → 73.7% | 0.000000 | 17 → 17 | 89.5% → 89.5% | 0.000000 |
| reference | by_mission | swarm-b | April 2024 control | 168 | radial | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-b | April 2024 control | 168 | in_track | 19 → 19 | 14 → 14 | 73.7% → 73.7% | 0.000000 | 18 → 18 | 94.7% → 94.7% | 0.000000 |
| reference | by_mission | swarm-b | April 2024 control | 168 | cross | 19 → 19 | 7 → 7 | 36.8% → 36.8% | 0.000000 | 17 → 17 | 89.5% → 89.5% | 0.000000 |
| reference | by_mission | swarm-b | May 2024 | 6 | radial | 19 → 19 | 6 → 6 | 31.6% → 31.6% | 0.000000 | 15 → 15 | 78.9% → 78.9% | 0.000000 |
| reference | by_mission | swarm-b | May 2024 | 6 | in_track | 19 → 19 | 2 → 2 | 10.5% → 10.5% | 0.000000 | 10 → 10 | 52.6% → 52.6% | 0.000000 |
| reference | by_mission | swarm-b | May 2024 | 6 | cross | 19 → 19 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 1 → 1 | 5.3% → 5.3% | 0.000000 |
| reference | by_mission | swarm-b | May 2024 | 12 | radial | 19 → 19 | 8 → 8 | 42.1% → 42.1% | 0.000000 | 15 → 15 | 78.9% → 78.9% | 0.000000 |
| reference | by_mission | swarm-b | May 2024 | 12 | in_track | 19 → 19 | 7 → 7 | 36.8% → 36.8% | 0.000000 | 12 → 12 | 63.2% → 63.2% | 0.000000 |
| reference | by_mission | swarm-b | May 2024 | 12 | cross | 19 → 19 | 1 → 1 | 5.3% → 5.3% | 0.000000 | 3 → 3 | 15.8% → 15.8% | 0.000000 |
| reference | by_mission | swarm-b | May 2024 | 24 | radial | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-b | May 2024 | 24 | in_track | 19 → 19 | 13 → 13 | 68.4% → 68.4% | 0.000000 | 15 → 15 | 78.9% → 78.9% | 0.000000 |
| reference | by_mission | swarm-b | May 2024 | 24 | cross | 19 → 19 | 2 → 2 | 10.5% → 10.5% | 0.000000 | 2 → 2 | 10.5% → 10.5% | 0.000000 |
| reference | by_mission | swarm-b | May 2024 | 36 | radial | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-b | May 2024 | 36 | in_track | 19 → 19 | 14 → 14 | 73.7% → 73.7% | 0.000000 | 14 → 14 | 73.7% → 73.7% | 0.000000 |
| reference | by_mission | swarm-b | May 2024 | 36 | cross | 19 → 19 | 2 → 2 | 10.5% → 10.5% | 0.000000 | 3 → 3 | 15.8% → 15.8% | 0.000000 |
| reference | by_mission | swarm-b | May 2024 | 48 | radial | 19 → 19 | 13 → 13 | 68.4% → 68.4% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-b | May 2024 | 48 | in_track | 19 → 19 | 13 → 13 | 68.4% → 68.4% | 0.000000 | 14 → 14 | 73.7% → 73.7% | 0.000000 |
| reference | by_mission | swarm-b | May 2024 | 48 | cross | 19 → 19 | 5 → 5 | 26.3% → 26.3% | 0.000000 | 6 → 6 | 31.6% → 31.6% | 0.000000 |
| reference | by_mission | swarm-b | May 2024 | 72 | radial | 19 → 19 | 10 → 10 | 52.6% → 52.6% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-b | May 2024 | 72 | in_track | 19 → 19 | 9 → 9 | 47.4% → 47.4% | 0.000000 | 12 → 12 | 63.2% → 63.2% | 0.000000 |
| reference | by_mission | swarm-b | May 2024 | 72 | cross | 19 → 19 | 8 → 8 | 42.1% → 42.1% | 0.000000 | 16 → 16 | 84.2% → 84.2% | 0.000000 |
| reference | by_mission | swarm-b | May 2024 | 96 | radial | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-b | May 2024 | 96 | in_track | 19 → 19 | 8 → 8 | 42.1% → 42.1% | 0.000000 | 12 → 12 | 63.2% → 63.2% | 0.000000 |
| reference | by_mission | swarm-b | May 2024 | 96 | cross | 19 → 19 | 6 → 6 | 31.6% → 31.6% | 0.000000 | 16 → 16 | 84.2% → 84.2% | 0.000000 |
| reference | by_mission | swarm-b | May 2024 | 120 | radial | 19 → 19 | 14 → 14 | 73.7% → 73.7% | 0.000000 | 17 → 19 | 89.5% → 100.0% | 10.526316 |
| reference | by_mission | swarm-b | May 2024 | 120 | in_track | 19 → 19 | 5 → 5 | 26.3% → 26.3% | 0.000000 | 12 → 12 | 63.2% → 63.2% | 0.000000 |
| reference | by_mission | swarm-b | May 2024 | 120 | cross | 19 → 19 | 8 → 8 | 42.1% → 42.1% | 0.000000 | 18 → 18 | 94.7% → 94.7% | 0.000000 |
| reference | by_mission | swarm-b | May 2024 | 144 | radial | 19 → 19 | 17 → 17 | 89.5% → 89.5% | 0.000000 | 17 → 17 | 89.5% → 89.5% | 0.000000 |
| reference | by_mission | swarm-b | May 2024 | 144 | in_track | 19 → 19 | 6 → 6 | 31.6% → 31.6% | 0.000000 | 12 → 12 | 63.2% → 63.2% | 0.000000 |
| reference | by_mission | swarm-b | May 2024 | 144 | cross | 19 → 19 | 16 → 16 | 84.2% → 84.2% | 0.000000 | 18 → 18 | 94.7% → 94.7% | 0.000000 |
| reference | by_mission | swarm-b | May 2024 | 168 | radial | 19 → 19 | 17 → 17 | 89.5% → 89.5% | 0.000000 | 17 → 19 | 89.5% → 100.0% | 10.526316 |
| reference | by_mission | swarm-b | May 2024 | 168 | in_track | 19 → 19 | 6 → 6 | 31.6% → 31.6% | 0.000000 | 14 → 14 | 73.7% → 73.7% | 0.000000 |
| reference | by_mission | swarm-b | May 2024 | 168 | cross | 19 → 19 | 10 → 10 | 52.6% → 52.6% | 0.000000 | 17 → 17 | 89.5% → 89.5% | 0.000000 |
| reference | by_mission | swarm-c | August 2024 held out | 6 | radial | 19 → 19 | 4 → 4 | 21.1% → 21.1% | 0.000000 | 10 → 10 | 52.6% → 52.6% | 0.000000 |
| reference | by_mission | swarm-c | August 2024 held out | 6 | in_track | 19 → 19 | 4 → 4 | 21.1% → 21.1% | 0.000000 | 8 → 8 | 42.1% → 42.1% | 0.000000 |
| reference | by_mission | swarm-c | August 2024 held out | 6 | cross | 19 → 19 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | swarm-c | August 2024 held out | 12 | radial | 19 → 19 | 10 → 10 | 52.6% → 52.6% | 0.000000 | 17 → 17 | 89.5% → 89.5% | 0.000000 |
| reference | by_mission | swarm-c | August 2024 held out | 12 | in_track | 19 → 19 | 3 → 3 | 15.8% → 15.8% | 0.000000 | 7 → 7 | 36.8% → 36.8% | 0.000000 |
| reference | by_mission | swarm-c | August 2024 held out | 12 | cross | 19 → 19 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 1 → 1 | 5.3% → 5.3% | 0.000000 |
| reference | by_mission | swarm-c | August 2024 held out | 24 | radial | 19 → 19 | 16 → 16 | 84.2% → 84.2% | 0.000000 | 18 → 18 | 94.7% → 94.7% | 0.000000 |
| reference | by_mission | swarm-c | August 2024 held out | 24 | in_track | 19 → 19 | 9 → 9 | 47.4% → 47.4% | 0.000000 | 14 → 14 | 73.7% → 73.7% | 0.000000 |
| reference | by_mission | swarm-c | August 2024 held out | 24 | cross | 19 → 19 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 1 → 1 | 5.3% → 5.3% | 0.000000 |
| reference | by_mission | swarm-c | August 2024 held out | 36 | radial | 19 → 19 | 14 → 14 | 73.7% → 73.7% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-c | August 2024 held out | 36 | in_track | 19 → 19 | 8 → 8 | 42.1% → 42.1% | 0.000000 | 11 → 11 | 57.9% → 57.9% | 0.000000 |
| reference | by_mission | swarm-c | August 2024 held out | 36 | cross | 19 → 19 | 4 → 4 | 21.1% → 21.1% | 0.000000 | 8 → 8 | 42.1% → 42.1% | 0.000000 |
| reference | by_mission | swarm-c | August 2024 held out | 48 | radial | 19 → 19 | 10 → 10 | 52.6% → 52.6% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-c | August 2024 held out | 48 | in_track | 19 → 19 | 6 → 6 | 31.6% → 31.6% | 0.000000 | 10 → 10 | 52.6% → 52.6% | 0.000000 |
| reference | by_mission | swarm-c | August 2024 held out | 48 | cross | 19 → 19 | 3 → 3 | 15.8% → 15.8% | 0.000000 | 5 → 5 | 26.3% → 26.3% | 0.000000 |
| reference | by_mission | swarm-c | August 2024 held out | 72 | radial | 19 → 19 | 12 → 12 | 63.2% → 63.2% | 0.000000 | 17 → 17 | 89.5% → 89.5% | 0.000000 |
| reference | by_mission | swarm-c | August 2024 held out | 72 | in_track | 19 → 19 | 5 → 5 | 26.3% → 26.3% | 0.000000 | 9 → 9 | 47.4% → 47.4% | 0.000000 |
| reference | by_mission | swarm-c | August 2024 held out | 72 | cross | 19 → 19 | 3 → 3 | 15.8% → 15.8% | 0.000000 | 9 → 9 | 47.4% → 47.4% | 0.000000 |
| reference | by_mission | swarm-c | August 2024 held out | 96 | radial | 19 → 19 | 17 → 17 | 89.5% → 89.5% | 0.000000 | 17 → 17 | 89.5% → 89.5% | 0.000000 |
| reference | by_mission | swarm-c | August 2024 held out | 96 | in_track | 19 → 19 | 4 → 4 | 21.1% → 21.1% | 0.000000 | 8 → 8 | 42.1% → 42.1% | 0.000000 |
| reference | by_mission | swarm-c | August 2024 held out | 96 | cross | 19 → 19 | 2 → 2 | 10.5% → 10.5% | 0.000000 | 6 → 6 | 31.6% → 31.6% | 0.000000 |
| reference | by_mission | swarm-c | August 2024 held out | 120 | radial | 19 → 19 | 15 → 15 | 78.9% → 78.9% | 0.000000 | 17 → 17 | 89.5% → 89.5% | 0.000000 |
| reference | by_mission | swarm-c | August 2024 held out | 120 | in_track | 19 → 19 | 5 → 5 | 26.3% → 26.3% | 0.000000 | 7 → 7 | 36.8% → 36.8% | 0.000000 |
| reference | by_mission | swarm-c | August 2024 held out | 120 | cross | 19 → 19 | 2 → 2 | 10.5% → 10.5% | 0.000000 | 7 → 7 | 36.8% → 36.8% | 0.000000 |
| reference | by_mission | swarm-c | August 2024 held out | 144 | radial | 19 → 19 | 7 → 7 | 36.8% → 36.8% | 0.000000 | 16 → 16 | 84.2% → 84.2% | 0.000000 |
| reference | by_mission | swarm-c | August 2024 held out | 144 | in_track | 19 → 19 | 5 → 5 | 26.3% → 26.3% | 0.000000 | 7 → 7 | 36.8% → 36.8% | 0.000000 |
| reference | by_mission | swarm-c | August 2024 held out | 144 | cross | 19 → 19 | 9 → 9 | 47.4% → 47.4% | 0.000000 | 16 → 16 | 84.2% → 84.2% | 0.000000 |
| reference | by_mission | swarm-c | August 2024 held out | 168 | radial | 19 → 19 | 15 → 16 | 78.9% → 84.2% | 5.263158 | 16 → 16 | 84.2% → 84.2% | 0.000000 |
| reference | by_mission | swarm-c | August 2024 held out | 168 | in_track | 19 → 19 | 6 → 6 | 31.6% → 31.6% | 0.000000 | 7 → 7 | 36.8% → 36.8% | 0.000000 |
| reference | by_mission | swarm-c | August 2024 held out | 168 | cross | 19 → 19 | 3 → 3 | 15.8% → 15.8% | 0.000000 | 11 → 11 | 57.9% → 57.9% | 0.000000 |
| reference | by_mission | swarm-c | October 2024 held out | 6 | radial | 21 → 21 | 9 → 9 | 42.9% → 42.9% | 0.000000 | 16 → 16 | 76.2% → 76.2% | 0.000000 |
| reference | by_mission | swarm-c | October 2024 held out | 6 | in_track | 21 → 21 | 8 → 8 | 38.1% → 38.1% | 0.000000 | 19 → 19 | 90.5% → 90.5% | 0.000000 |
| reference | by_mission | swarm-c | October 2024 held out | 6 | cross | 21 → 21 | 1 → 1 | 4.8% → 4.8% | 0.000000 | 2 → 2 | 9.5% → 9.5% | 0.000000 |
| reference | by_mission | swarm-c | October 2024 held out | 12 | radial | 21 → 21 | 2 → 2 | 9.5% → 9.5% | 0.000000 | 5 → 5 | 23.8% → 23.8% | 0.000000 |
| reference | by_mission | swarm-c | October 2024 held out | 12 | in_track | 21 → 21 | 9 → 9 | 42.9% → 42.9% | 0.000000 | 14 → 14 | 66.7% → 66.7% | 0.000000 |
| reference | by_mission | swarm-c | October 2024 held out | 12 | cross | 21 → 21 | 2 → 2 | 9.5% → 9.5% | 0.000000 | 3 → 3 | 14.3% → 14.3% | 0.000000 |
| reference | by_mission | swarm-c | October 2024 held out | 24 | radial | 21 → 21 | 10 → 10 | 47.6% → 47.6% | 0.000000 | 20 → 20 | 95.2% → 95.2% | 0.000000 |
| reference | by_mission | swarm-c | October 2024 held out | 24 | in_track | 21 → 21 | 11 → 11 | 52.4% → 52.4% | 0.000000 | 14 → 14 | 66.7% → 66.7% | 0.000000 |
| reference | by_mission | swarm-c | October 2024 held out | 24 | cross | 21 → 21 | 2 → 2 | 9.5% → 9.5% | 0.000000 | 3 → 3 | 14.3% → 14.3% | 0.000000 |
| reference | by_mission | swarm-c | October 2024 held out | 36 | radial | 21 → 21 | 2 → 2 | 9.5% → 9.5% | 0.000000 | 14 → 14 | 66.7% → 66.7% | 0.000000 |
| reference | by_mission | swarm-c | October 2024 held out | 36 | in_track | 21 → 21 | 11 → 11 | 52.4% → 52.4% | 0.000000 | 13 → 13 | 61.9% → 61.9% | 0.000000 |
| reference | by_mission | swarm-c | October 2024 held out | 36 | cross | 21 → 21 | 3 → 3 | 14.3% → 14.3% | 0.000000 | 6 → 6 | 28.6% → 28.6% | 0.000000 |
| reference | by_mission | swarm-c | October 2024 held out | 48 | radial | 21 → 21 | 19 → 19 | 90.5% → 90.5% | 0.000000 | 19 → 19 | 90.5% → 90.5% | 0.000000 |
| reference | by_mission | swarm-c | October 2024 held out | 48 | in_track | 21 → 21 | 10 → 10 | 47.6% → 47.6% | 0.000000 | 13 → 13 | 61.9% → 61.9% | 0.000000 |
| reference | by_mission | swarm-c | October 2024 held out | 48 | cross | 21 → 21 | 3 → 3 | 14.3% → 14.3% | 0.000000 | 4 → 4 | 19.0% → 19.0% | 0.000000 |
| reference | by_mission | swarm-c | October 2024 held out | 72 | radial | 21 → 21 | 12 → 12 | 57.1% → 57.1% | 0.000000 | 16 → 16 | 76.2% → 76.2% | 0.000000 |
| reference | by_mission | swarm-c | October 2024 held out | 72 | in_track | 21 → 21 | 9 → 9 | 42.9% → 42.9% | 0.000000 | 13 → 13 | 61.9% → 61.9% | 0.000000 |
| reference | by_mission | swarm-c | October 2024 held out | 72 | cross | 21 → 21 | 7 → 7 | 33.3% → 33.3% | 0.000000 | 11 → 11 | 52.4% → 52.4% | 0.000000 |
| reference | by_mission | swarm-c | October 2024 held out | 96 | radial | 21 → 21 | 15 → 17 | 71.4% → 81.0% | 9.523810 | 19 → 19 | 90.5% → 90.5% | 0.000000 |
| reference | by_mission | swarm-c | October 2024 held out | 96 | in_track | 21 → 21 | 9 → 9 | 42.9% → 42.9% | 0.000000 | 13 → 13 | 61.9% → 61.9% | 0.000000 |
| reference | by_mission | swarm-c | October 2024 held out | 96 | cross | 21 → 21 | 1 → 1 | 4.8% → 4.8% | 0.000000 | 5 → 5 | 23.8% → 23.8% | 0.000000 |
| reference | by_mission | swarm-c | October 2024 held out | 120 | radial | 21 → 21 | 14 → 14 | 66.7% → 66.7% | 0.000000 | 14 → 16 | 66.7% → 76.2% | 9.523810 |
| reference | by_mission | swarm-c | October 2024 held out | 120 | in_track | 21 → 21 | 11 → 11 | 52.4% → 52.4% | 0.000000 | 13 → 13 | 61.9% → 61.9% | 0.000000 |
| reference | by_mission | swarm-c | October 2024 held out | 120 | cross | 21 → 21 | 4 → 4 | 19.0% → 19.0% | 0.000000 | 6 → 6 | 28.6% → 28.6% | 0.000000 |
| reference | by_mission | swarm-c | October 2024 held out | 144 | radial | 21 → 21 | 12 → 12 | 57.1% → 57.1% | 0.000000 | 13 → 14 | 61.9% → 66.7% | 4.761905 |
| reference | by_mission | swarm-c | October 2024 held out | 144 | in_track | 21 → 21 | 11 → 11 | 52.4% → 52.4% | 0.000000 | 13 → 13 | 61.9% → 61.9% | 0.000000 |
| reference | by_mission | swarm-c | October 2024 held out | 144 | cross | 21 → 21 | 11 → 11 | 52.4% → 52.4% | 0.000000 | 15 → 15 | 71.4% → 71.4% | 0.000000 |
| reference | by_mission | swarm-c | October 2024 held out | 168 | radial | 21 → 21 | 14 → 14 | 66.7% → 66.7% | 0.000000 | 14 → 14 | 66.7% → 66.7% | 0.000000 |
| reference | by_mission | swarm-c | October 2024 held out | 168 | in_track | 21 → 21 | 10 → 10 | 47.6% → 47.6% | 0.000000 | 13 → 13 | 61.9% → 61.9% | 0.000000 |
| reference | by_mission | swarm-c | October 2024 held out | 168 | cross | 21 → 21 | 4 → 4 | 19.0% → 19.0% | 0.000000 | 9 → 9 | 42.9% → 42.9% | 0.000000 |
| reference | by_mission | swarm-c | April 2024 control | 6 | radial | 19 → 19 | 15 → 15 | 78.9% → 78.9% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-c | April 2024 control | 6 | in_track | 19 → 19 | 13 → 13 | 68.4% → 68.4% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-c | April 2024 control | 6 | cross | 19 → 19 | 1 → 1 | 5.3% → 5.3% | 0.000000 | 1 → 1 | 5.3% → 5.3% | 0.000000 |
| reference | by_mission | swarm-c | April 2024 control | 12 | radial | 19 → 19 | 12 → 12 | 63.2% → 63.2% | 0.000000 | 16 → 16 | 84.2% → 84.2% | 0.000000 |
| reference | by_mission | swarm-c | April 2024 control | 12 | in_track | 19 → 19 | 10 → 10 | 52.6% → 52.6% | 0.000000 | 13 → 13 | 68.4% → 68.4% | 0.000000 |
| reference | by_mission | swarm-c | April 2024 control | 12 | cross | 19 → 19 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 1 → 1 | 5.3% → 5.3% | 0.000000 |
| reference | by_mission | swarm-c | April 2024 control | 24 | radial | 19 → 19 | 18 → 18 | 94.7% → 94.7% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-c | April 2024 control | 24 | in_track | 19 → 19 | 18 → 18 | 94.7% → 94.7% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-c | April 2024 control | 24 | cross | 19 → 19 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | swarm-c | April 2024 control | 36 | radial | 19 → 19 | 11 → 11 | 57.9% → 57.9% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-c | April 2024 control | 36 | in_track | 19 → 19 | 17 → 17 | 89.5% → 89.5% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-c | April 2024 control | 36 | cross | 19 → 19 | 8 → 8 | 42.1% → 42.1% | 0.000000 | 10 → 10 | 52.6% → 52.6% | 0.000000 |
| reference | by_mission | swarm-c | April 2024 control | 48 | radial | 19 → 19 | 13 → 13 | 68.4% → 68.4% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-c | April 2024 control | 48 | in_track | 19 → 19 | 18 → 18 | 94.7% → 94.7% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-c | April 2024 control | 48 | cross | 19 → 19 | 2 → 2 | 10.5% → 10.5% | 0.000000 | 5 → 5 | 26.3% → 26.3% | 0.000000 |
| reference | by_mission | swarm-c | April 2024 control | 72 | radial | 19 → 19 | 11 → 11 | 57.9% → 57.9% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-c | April 2024 control | 72 | in_track | 19 → 19 | 17 → 17 | 89.5% → 89.5% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-c | April 2024 control | 72 | cross | 19 → 19 | 8 → 8 | 42.1% → 42.1% | 0.000000 | 13 → 13 | 68.4% → 68.4% | 0.000000 |
| reference | by_mission | swarm-c | April 2024 control | 96 | radial | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-c | April 2024 control | 96 | in_track | 19 → 19 | 18 → 18 | 94.7% → 94.7% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-c | April 2024 control | 96 | cross | 19 → 19 | 4 → 4 | 21.1% → 21.1% | 0.000000 | 7 → 7 | 36.8% → 36.8% | 0.000000 |
| reference | by_mission | swarm-c | April 2024 control | 120 | radial | 19 → 19 | 16 → 16 | 84.2% → 84.2% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-c | April 2024 control | 120 | in_track | 19 → 19 | 18 → 18 | 94.7% → 94.7% | 0.000000 | 18 → 18 | 94.7% → 94.7% | 0.000000 |
| reference | by_mission | swarm-c | April 2024 control | 120 | cross | 19 → 19 | 7 → 7 | 36.8% → 36.8% | 0.000000 | 17 → 17 | 89.5% → 89.5% | 0.000000 |
| reference | by_mission | swarm-c | April 2024 control | 144 | radial | 19 → 19 | 17 → 17 | 89.5% → 89.5% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-c | April 2024 control | 144 | in_track | 19 → 19 | 16 → 16 | 84.2% → 84.2% | 0.000000 | 18 → 18 | 94.7% → 94.7% | 0.000000 |
| reference | by_mission | swarm-c | April 2024 control | 144 | cross | 19 → 19 | 6 → 6 | 31.6% → 31.6% | 0.000000 | 13 → 13 | 68.4% → 68.4% | 0.000000 |
| reference | by_mission | swarm-c | April 2024 control | 168 | radial | 19 → 19 | 18 → 18 | 94.7% → 94.7% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-c | April 2024 control | 168 | in_track | 19 → 19 | 11 → 11 | 57.9% → 57.9% | 0.000000 | 18 → 18 | 94.7% → 94.7% | 0.000000 |
| reference | by_mission | swarm-c | April 2024 control | 168 | cross | 19 → 19 | 4 → 4 | 21.1% → 21.1% | 0.000000 | 12 → 12 | 63.2% → 63.2% | 0.000000 |
| reference | by_mission | swarm-c | May 2024 | 6 | radial | 17 → 17 | 6 → 6 | 35.3% → 35.3% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-c | May 2024 | 6 | in_track | 17 → 17 | 10 → 10 | 58.8% → 58.8% | 0.000000 | 13 → 13 | 76.5% → 76.5% | 0.000000 |
| reference | by_mission | swarm-c | May 2024 | 6 | cross | 17 → 17 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | swarm-c | May 2024 | 12 | radial | 17 → 17 | 13 → 13 | 76.5% → 76.5% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-c | May 2024 | 12 | in_track | 17 → 17 | 10 → 10 | 58.8% → 58.8% | 0.000000 | 16 → 16 | 94.1% → 94.1% | 0.000000 |
| reference | by_mission | swarm-c | May 2024 | 12 | cross | 17 → 17 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | swarm-c | May 2024 | 24 | radial | 17 → 17 | 15 → 15 | 88.2% → 88.2% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-c | May 2024 | 24 | in_track | 17 → 17 | 12 → 12 | 70.6% → 70.6% | 0.000000 | 14 → 14 | 82.4% → 82.4% | 0.000000 |
| reference | by_mission | swarm-c | May 2024 | 24 | cross | 17 → 17 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | swarm-c | May 2024 | 36 | radial | 17 → 17 | 14 → 14 | 82.4% → 82.4% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-c | May 2024 | 36 | in_track | 17 → 17 | 13 → 13 | 76.5% → 76.5% | 0.000000 | 13 → 13 | 76.5% → 76.5% | 0.000000 |
| reference | by_mission | swarm-c | May 2024 | 36 | cross | 17 → 17 | 4 → 4 | 23.5% → 23.5% | 0.000000 | 8 → 8 | 47.1% → 47.1% | 0.000000 |
| reference | by_mission | swarm-c | May 2024 | 48 | radial | 17 → 17 | 10 → 10 | 58.8% → 58.8% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-c | May 2024 | 48 | in_track | 17 → 17 | 12 → 12 | 70.6% → 70.6% | 0.000000 | 13 → 13 | 76.5% → 76.5% | 0.000000 |
| reference | by_mission | swarm-c | May 2024 | 48 | cross | 17 → 17 | 1 → 1 | 5.9% → 5.9% | 0.000000 | 3 → 3 | 17.6% → 17.6% | 0.000000 |
| reference | by_mission | swarm-c | May 2024 | 72 | radial | 17 → 17 | 14 → 14 | 82.4% → 82.4% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-c | May 2024 | 72 | in_track | 17 → 17 | 9 → 9 | 52.9% → 52.9% | 0.000000 | 11 → 11 | 64.7% → 64.7% | 0.000000 |
| reference | by_mission | swarm-c | May 2024 | 72 | cross | 17 → 17 | 11 → 11 | 64.7% → 64.7% | 0.000000 | 16 → 16 | 94.1% → 94.1% | 0.000000 |
| reference | by_mission | swarm-c | May 2024 | 96 | radial | 17 → 17 | 16 → 16 | 94.1% → 94.1% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-c | May 2024 | 96 | in_track | 17 → 17 | 8 → 8 | 47.1% → 47.1% | 0.000000 | 11 → 11 | 64.7% → 64.7% | 0.000000 |
| reference | by_mission | swarm-c | May 2024 | 96 | cross | 17 → 17 | 1 → 1 | 5.9% → 5.9% | 0.000000 | 1 → 1 | 5.9% → 5.9% | 0.000000 |
| reference | by_mission | swarm-c | May 2024 | 120 | radial | 17 → 17 | 15 → 15 | 88.2% → 88.2% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swarm-c | May 2024 | 120 | in_track | 17 → 17 | 6 → 6 | 35.3% → 35.3% | 0.000000 | 11 → 11 | 64.7% → 64.7% | 0.000000 |
| reference | by_mission | swarm-c | May 2024 | 120 | cross | 17 → 17 | 13 → 13 | 76.5% → 76.5% | 0.000000 | 16 → 16 | 94.1% → 94.1% | 0.000000 |
| reference | by_mission | swarm-c | May 2024 | 144 | radial | 17 → 17 | 14 → 15 | 82.4% → 88.2% | 5.882353 | 15 → 17 | 88.2% → 100.0% | 11.764706 |
| reference | by_mission | swarm-c | May 2024 | 144 | in_track | 17 → 17 | 6 → 6 | 35.3% → 35.3% | 0.000000 | 11 → 11 | 64.7% → 64.7% | 0.000000 |
| reference | by_mission | swarm-c | May 2024 | 144 | cross | 17 → 17 | 13 → 13 | 76.5% → 76.5% | 0.000000 | 16 → 16 | 94.1% → 94.1% | 0.000000 |
| reference | by_mission | swarm-c | May 2024 | 168 | radial | 17 → 17 | 15 → 15 | 88.2% → 88.2% | 0.000000 | 15 → 16 | 88.2% → 94.1% | 5.882353 |
| reference | by_mission | swarm-c | May 2024 | 168 | in_track | 17 → 17 | 6 → 6 | 35.3% → 35.3% | 0.000000 | 13 → 13 | 76.5% → 76.5% | 0.000000 |
| reference | by_mission | swarm-c | May 2024 | 168 | cross | 17 → 17 | 2 → 2 | 11.8% → 11.8% | 0.000000 | 14 → 14 | 82.4% → 82.4% | 0.000000 |
| reference | by_mission | swot | August 2024 held out | 6 | radial | 17 → 17 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | swot | August 2024 held out | 6 | in_track | 17 → 17 | 2 → 2 | 11.8% → 11.8% | 0.000000 | 5 → 5 | 29.4% → 29.4% | 0.000000 |
| reference | by_mission | swot | August 2024 held out | 6 | cross | 17 → 17 | 10 → 10 | 58.8% → 58.8% | 0.000000 | 16 → 16 | 94.1% → 94.1% | 0.000000 |
| reference | by_mission | swot | August 2024 held out | 12 | radial | 17 → 17 | 1 → 1 | 5.9% → 5.9% | 0.000000 | 1 → 1 | 5.9% → 5.9% | 0.000000 |
| reference | by_mission | swot | August 2024 held out | 12 | in_track | 17 → 17 | 2 → 2 | 11.8% → 11.8% | 0.000000 | 8 → 8 | 47.1% → 47.1% | 0.000000 |
| reference | by_mission | swot | August 2024 held out | 12 | cross | 17 → 17 | 4 → 4 | 23.5% → 23.5% | 0.000000 | 6 → 6 | 35.3% → 35.3% | 0.000000 |
| reference | by_mission | swot | August 2024 held out | 24 | radial | 17 → 17 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | swot | August 2024 held out | 24 | in_track | 17 → 17 | 13 → 13 | 76.5% → 76.5% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swot | August 2024 held out | 24 | cross | 17 → 17 | 6 → 6 | 35.3% → 35.3% | 0.000000 | 10 → 10 | 58.8% → 58.8% | 0.000000 |
| reference | by_mission | swot | August 2024 held out | 36 | radial | 17 → 17 | 1 → 1 | 5.9% → 5.9% | 0.000000 | 4 → 4 | 23.5% → 23.5% | 0.000000 |
| reference | by_mission | swot | August 2024 held out | 36 | in_track | 17 → 17 | 14 → 14 | 82.4% → 82.4% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swot | August 2024 held out | 36 | cross | 17 → 17 | 13 → 13 | 76.5% → 76.5% | 0.000000 | 16 → 16 | 94.1% → 94.1% | 0.000000 |
| reference | by_mission | swot | August 2024 held out | 48 | radial | 17 → 17 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | swot | August 2024 held out | 48 | in_track | 17 → 17 | 17 → 17 | 100.0% → 100.0% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swot | August 2024 held out | 48 | cross | 17 → 17 | 9 → 9 | 52.9% → 52.9% | 0.000000 | 10 → 10 | 58.8% → 58.8% | 0.000000 |
| reference | by_mission | swot | August 2024 held out | 72 | radial | 17 → 17 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | swot | August 2024 held out | 72 | in_track | 17 → 17 | 17 → 17 | 100.0% → 100.0% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swot | August 2024 held out | 72 | cross | 17 → 17 | 10 → 10 | 58.8% → 58.8% | 0.000000 | 11 → 11 | 64.7% → 64.7% | 0.000000 |
| reference | by_mission | swot | August 2024 held out | 96 | radial | 17 → 17 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 1 → 1 | 5.9% → 5.9% | 0.000000 |
| reference | by_mission | swot | August 2024 held out | 96 | in_track | 17 → 17 | 17 → 17 | 100.0% → 100.0% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swot | August 2024 held out | 96 | cross | 17 → 17 | 10 → 10 | 58.8% → 58.8% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swot | August 2024 held out | 120 | radial | 17 → 17 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 2 → 2 | 11.8% → 11.8% | 0.000000 |
| reference | by_mission | swot | August 2024 held out | 120 | in_track | 17 → 17 | 17 → 17 | 100.0% → 100.0% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swot | August 2024 held out | 120 | cross | 17 → 17 | 10 → 10 | 58.8% → 58.8% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swot | August 2024 held out | 144 | radial | 17 → 17 | 1 → 1 | 5.9% → 5.9% | 0.000000 | 1 → 1 | 5.9% → 5.9% | 0.000000 |
| reference | by_mission | swot | August 2024 held out | 144 | in_track | 17 → 17 | 17 → 17 | 100.0% → 100.0% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swot | August 2024 held out | 144 | cross | 17 → 17 | 10 → 10 | 58.8% → 58.8% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swot | August 2024 held out | 168 | radial | 17 → 17 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 3 → 3 | 17.6% → 17.6% | 0.000000 |
| reference | by_mission | swot | August 2024 held out | 168 | in_track | 17 → 17 | 17 → 17 | 100.0% → 100.0% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swot | August 2024 held out | 168 | cross | 17 → 17 | 10 → 10 | 58.8% → 58.8% | 0.000000 | 17 → 17 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swot | October 2024 held out | 6 | radial | 17 → 17 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | swot | October 2024 held out | 6 | in_track | 17 → 17 | 1 → 1 | 5.9% → 5.9% | 0.000000 | 6 → 6 | 35.3% → 35.3% | 0.000000 |
| reference | by_mission | swot | October 2024 held out | 6 | cross | 17 → 17 | 3 → 3 | 17.6% → 17.6% | 0.000000 | 7 → 7 | 41.2% → 41.2% | 0.000000 |
| reference | by_mission | swot | October 2024 held out | 12 | radial | 16 → 16 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | swot | October 2024 held out | 12 | in_track | 16 → 16 | 4 → 4 | 25.0% → 25.0% | 0.000000 | 6 → 6 | 37.5% → 37.5% | 0.000000 |
| reference | by_mission | swot | October 2024 held out | 12 | cross | 16 → 16 | 2 → 2 | 12.5% → 12.5% | 0.000000 | 3 → 3 | 18.8% → 18.8% | 0.000000 |
| reference | by_mission | swot | October 2024 held out | 24 | radial | 15 → 15 | 1 → 1 | 6.7% → 6.7% | 0.000000 | 1 → 1 | 6.7% → 6.7% | 0.000000 |
| reference | by_mission | swot | October 2024 held out | 24 | in_track | 15 → 15 | 8 → 8 | 53.3% → 53.3% | 0.000000 | 14 → 14 | 93.3% → 93.3% | 0.000000 |
| reference | by_mission | swot | October 2024 held out | 24 | cross | 15 → 15 | 3 → 3 | 20.0% → 20.0% | 0.000000 | 7 → 7 | 46.7% → 46.7% | 0.000000 |
| reference | by_mission | swot | October 2024 held out | 36 | radial | 13 → 13 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | swot | October 2024 held out | 36 | in_track | 13 → 13 | 12 → 12 | 92.3% → 92.3% | 0.000000 | 12 → 12 | 92.3% → 92.3% | 0.000000 |
| reference | by_mission | swot | October 2024 held out | 36 | cross | 13 → 13 | 7 → 7 | 53.8% → 53.8% | 0.000000 | 12 → 12 | 92.3% → 92.3% | 0.000000 |
| reference | by_mission | swot | October 2024 held out | 48 | radial | 12 → 12 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 1 → 1 | 8.3% → 8.3% | 0.000000 |
| reference | by_mission | swot | October 2024 held out | 48 | in_track | 12 → 12 | 11 → 11 | 91.7% → 91.7% | 0.000000 | 11 → 11 | 91.7% → 91.7% | 0.000000 |
| reference | by_mission | swot | October 2024 held out | 48 | cross | 12 → 12 | 7 → 7 | 58.3% → 58.3% | 0.000000 | 8 → 8 | 66.7% → 66.7% | 0.000000 |
| reference | by_mission | swot | October 2024 held out | 72 | radial | 9 → 9 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 2 → 2 | 22.2% → 22.2% | 0.000000 |
| reference | by_mission | swot | October 2024 held out | 72 | in_track | 9 → 9 | 8 → 8 | 88.9% → 88.9% | 0.000000 | 8 → 8 | 88.9% → 88.9% | 0.000000 |
| reference | by_mission | swot | October 2024 held out | 72 | cross | 9 → 9 | 5 → 5 | 55.6% → 55.6% | 0.000000 | 6 → 6 | 66.7% → 66.7% | 0.000000 |
| reference | by_mission | swot | October 2024 held out | 96 | radial | 6 → 6 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 3 → 3 | 50.0% → 50.0% | 0.000000 |
| reference | by_mission | swot | October 2024 held out | 96 | in_track | 6 → 6 | 6 → 6 | 100.0% → 100.0% | 0.000000 | 6 → 6 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swot | October 2024 held out | 96 | cross | 6 → 6 | 3 → 3 | 50.0% → 50.0% | 0.000000 | 4 → 4 | 66.7% → 66.7% | 0.000000 |
| reference | by_mission | swot | October 2024 held out | 120 | radial | 3 → 3 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 1 → 1 | 33.3% → 33.3% | 0.000000 |
| reference | by_mission | swot | October 2024 held out | 120 | in_track | 3 → 3 | 3 → 3 | 100.0% → 100.0% | 0.000000 | 3 → 3 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swot | October 2024 held out | 120 | cross | 3 → 3 | 1 → 1 | 33.3% → 33.3% | 0.000000 | 2 → 2 | 66.7% → 66.7% | 0.000000 |
| reference | by_mission | swot | October 2024 held out | 144 | radial | 1 → 1 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | swot | October 2024 held out | 144 | in_track | 1 → 1 | 1 → 1 | 100.0% → 100.0% | 0.000000 | 1 → 1 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swot | October 2024 held out | 144 | cross | 1 → 1 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 1 → 1 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swot | October 2024 held out | 168 | radial | 1 → 1 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | swot | October 2024 held out | 168 | in_track | 1 → 1 | 1 → 1 | 100.0% → 100.0% | 0.000000 | 1 → 1 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swot | October 2024 held out | 168 | cross | 1 → 1 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 1 → 1 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swot | April 2024 control | 6 | radial | 21 → 21 | 1 → 1 | 4.8% → 4.8% | 0.000000 | 1 → 1 | 4.8% → 4.8% | 0.000000 |
| reference | by_mission | swot | April 2024 control | 6 | in_track | 21 → 21 | 2 → 2 | 9.5% → 9.5% | 0.000000 | 9 → 9 | 42.9% → 42.9% | 0.000000 |
| reference | by_mission | swot | April 2024 control | 6 | cross | 21 → 21 | 4 → 4 | 19.0% → 19.0% | 0.000000 | 13 → 13 | 61.9% → 61.9% | 0.000000 |
| reference | by_mission | swot | April 2024 control | 12 | radial | 21 → 21 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | swot | April 2024 control | 12 | in_track | 21 → 21 | 11 → 11 | 52.4% → 52.4% | 0.000000 | 14 → 14 | 66.7% → 66.7% | 0.000000 |
| reference | by_mission | swot | April 2024 control | 12 | cross | 21 → 21 | 3 → 3 | 14.3% → 14.3% | 0.000000 | 5 → 5 | 23.8% → 23.8% | 0.000000 |
| reference | by_mission | swot | April 2024 control | 24 | radial | 21 → 21 | 3 → 3 | 14.3% → 14.3% | 0.000000 | 6 → 6 | 28.6% → 28.6% | 0.000000 |
| reference | by_mission | swot | April 2024 control | 24 | in_track | 21 → 21 | 10 → 10 | 47.6% → 47.6% | 0.000000 | 21 → 21 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swot | April 2024 control | 24 | cross | 21 → 21 | 13 → 13 | 61.9% → 61.9% | 0.000000 | 21 → 21 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swot | April 2024 control | 36 | radial | 21 → 21 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | swot | April 2024 control | 36 | in_track | 21 → 21 | 20 → 20 | 95.2% → 95.2% | 0.000000 | 21 → 21 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swot | April 2024 control | 36 | cross | 21 → 21 | 14 → 14 | 66.7% → 66.7% | 0.000000 | 20 → 20 | 95.2% → 95.2% | 0.000000 |
| reference | by_mission | swot | April 2024 control | 48 | radial | 21 → 21 | 5 → 5 | 23.8% → 23.8% | 0.000000 | 6 → 6 | 28.6% → 28.6% | 0.000000 |
| reference | by_mission | swot | April 2024 control | 48 | in_track | 21 → 21 | 21 → 21 | 100.0% → 100.0% | 0.000000 | 21 → 21 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swot | April 2024 control | 48 | cross | 21 → 21 | 14 → 14 | 66.7% → 66.7% | 0.000000 | 21 → 21 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swot | April 2024 control | 72 | radial | 21 → 21 | 5 → 5 | 23.8% → 23.8% | 0.000000 | 5 → 5 | 23.8% → 23.8% | 0.000000 |
| reference | by_mission | swot | April 2024 control | 72 | in_track | 21 → 21 | 21 → 21 | 100.0% → 100.0% | 0.000000 | 21 → 21 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swot | April 2024 control | 72 | cross | 21 → 21 | 13 → 13 | 61.9% → 61.9% | 0.000000 | 21 → 21 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swot | April 2024 control | 96 | radial | 21 → 21 | 4 → 4 | 19.0% → 19.0% | 0.000000 | 8 → 8 | 38.1% → 38.1% | 0.000000 |
| reference | by_mission | swot | April 2024 control | 96 | in_track | 21 → 21 | 21 → 21 | 100.0% → 100.0% | 0.000000 | 21 → 21 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swot | April 2024 control | 96 | cross | 21 → 21 | 10 → 10 | 47.6% → 47.6% | 0.000000 | 21 → 21 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swot | April 2024 control | 120 | radial | 21 → 21 | 5 → 5 | 23.8% → 23.8% | 0.000000 | 13 → 13 | 61.9% → 61.9% | 0.000000 |
| reference | by_mission | swot | April 2024 control | 120 | in_track | 21 → 21 | 21 → 21 | 100.0% → 100.0% | 0.000000 | 21 → 21 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swot | April 2024 control | 120 | cross | 21 → 21 | 9 → 9 | 42.9% → 42.9% | 0.000000 | 21 → 21 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swot | April 2024 control | 144 | radial | 21 → 21 | 6 → 6 | 28.6% → 28.6% | 0.000000 | 14 → 14 | 66.7% → 66.7% | 0.000000 |
| reference | by_mission | swot | April 2024 control | 144 | in_track | 21 → 21 | 21 → 21 | 100.0% → 100.0% | 0.000000 | 21 → 21 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swot | April 2024 control | 144 | cross | 21 → 21 | 6 → 6 | 28.6% → 28.6% | 0.000000 | 21 → 21 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swot | April 2024 control | 168 | radial | 20 → 20 | 8 → 8 | 40.0% → 40.0% | 0.000000 | 18 → 18 | 90.0% → 90.0% | 0.000000 |
| reference | by_mission | swot | April 2024 control | 168 | in_track | 20 → 20 | 20 → 20 | 100.0% → 100.0% | 0.000000 | 20 → 20 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swot | April 2024 control | 168 | cross | 20 → 20 | 3 → 3 | 15.0% → 15.0% | 0.000000 | 20 → 20 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swot | May 2024 | 6 | radial | 19 → 19 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | swot | May 2024 | 6 | in_track | 19 → 19 | 4 → 4 | 21.1% → 21.1% | 0.000000 | 6 → 6 | 31.6% → 31.6% | 0.000000 |
| reference | by_mission | swot | May 2024 | 6 | cross | 19 → 19 | 1 → 1 | 5.3% → 5.3% | 0.000000 | 7 → 7 | 36.8% → 36.8% | 0.000000 |
| reference | by_mission | swot | May 2024 | 12 | radial | 19 → 19 | 1 → 1 | 5.3% → 5.3% | 0.000000 | 2 → 2 | 10.5% → 10.5% | 0.000000 |
| reference | by_mission | swot | May 2024 | 12 | in_track | 19 → 19 | 7 → 7 | 36.8% → 36.8% | 0.000000 | 11 → 11 | 57.9% → 57.9% | 0.000000 |
| reference | by_mission | swot | May 2024 | 12 | cross | 19 → 19 | 5 → 5 | 26.3% → 26.3% | 0.000000 | 12 → 12 | 63.2% → 63.2% | 0.000000 |
| reference | by_mission | swot | May 2024 | 24 | radial | 19 → 19 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | swot | May 2024 | 24 | in_track | 19 → 19 | 14 → 14 | 73.7% → 73.7% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swot | May 2024 | 24 | cross | 19 → 19 | 10 → 10 | 52.6% → 52.6% | 0.000000 | 14 → 14 | 73.7% → 73.7% | 0.000000 |
| reference | by_mission | swot | May 2024 | 36 | radial | 19 → 19 | 3 → 3 | 15.8% → 15.8% | 0.000000 | 4 → 4 | 21.1% → 21.1% | 0.000000 |
| reference | by_mission | swot | May 2024 | 36 | in_track | 19 → 19 | 14 → 14 | 73.7% → 73.7% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swot | May 2024 | 36 | cross | 19 → 19 | 13 → 13 | 68.4% → 68.4% | 0.000000 | 18 → 18 | 94.7% → 94.7% | 0.000000 |
| reference | by_mission | swot | May 2024 | 48 | radial | 19 → 19 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | swot | May 2024 | 48 | in_track | 19 → 19 | 18 → 18 | 94.7% → 94.7% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swot | May 2024 | 48 | cross | 19 → 19 | 13 → 13 | 68.4% → 68.4% | 0.000000 | 14 → 14 | 73.7% → 73.7% | 0.000000 |
| reference | by_mission | swot | May 2024 | 72 | radial | 19 → 19 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | swot | May 2024 | 72 | in_track | 19 → 19 | 18 → 18 | 94.7% → 94.7% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swot | May 2024 | 72 | cross | 19 → 19 | 12 → 12 | 63.2% → 63.2% | 0.000000 | 14 → 14 | 73.7% → 73.7% | 0.000000 |
| reference | by_mission | swot | May 2024 | 96 | radial | 19 → 19 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | swot | May 2024 | 96 | in_track | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swot | May 2024 | 96 | cross | 19 → 19 | 6 → 6 | 31.6% → 31.6% | 0.000000 | 16 → 16 | 84.2% → 84.2% | 0.000000 |
| reference | by_mission | swot | May 2024 | 120 | radial | 19 → 19 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | swot | May 2024 | 120 | in_track | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swot | May 2024 | 120 | cross | 19 → 19 | 4 → 4 | 21.1% → 21.1% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swot | May 2024 | 144 | radial | 19 → 19 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | swot | May 2024 | 144 | in_track | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swot | May 2024 | 144 | cross | 19 → 19 | 4 → 4 | 21.1% → 21.1% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swot | May 2024 | 168 | radial | 19 → 19 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| reference | by_mission | swot | May 2024 | 168 | in_track | 19 → 19 | 19 → 19 | 100.0% → 100.0% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| reference | by_mission | swot | May 2024 | 168 | cross | 19 → 19 | 5 → 5 | 26.3% → 26.3% | 0.000000 | 19 → 19 | 100.0% → 100.0% | 0.000000 |
| september | by_band | 1000-1400 km | September 2024 replay | 6 | radial | 133 → 133 | 43 → 43 | 32.3% → 32.3% | 0.000000 | 90 → 90 | 67.7% → 67.7% | 0.000000 |
| september | by_band | 1000-1400 km | September 2024 replay | 6 | in_track | 133 → 133 | 14 → 14 | 10.5% → 10.5% | 0.000000 | 27 → 27 | 20.3% → 20.3% | 0.000000 |
| september | by_band | 1000-1400 km | September 2024 replay | 6 | cross | 133 → 133 | 29 → 29 | 21.8% → 21.8% | 0.000000 | 62 → 62 | 46.6% → 46.6% | 0.000000 |
| september | by_band | 1000-1400 km | September 2024 replay | 12 | radial | 131 → 131 | 4 → 4 | 3.1% → 3.1% | 0.000000 | 8 → 8 | 6.1% → 6.1% | 0.000000 |
| september | by_band | 1000-1400 km | September 2024 replay | 12 | in_track | 131 → 131 | 21 → 21 | 16.0% → 16.0% | 0.000000 | 31 → 31 | 23.7% → 23.7% | 0.000000 |
| september | by_band | 1000-1400 km | September 2024 replay | 12 | cross | 131 → 131 | 22 → 22 | 16.8% → 16.8% | 0.000000 | 47 → 47 | 35.9% → 35.9% | 0.000000 |
| september | by_band | 1000-1400 km | September 2024 replay | 24 | radial | 131 → 131 | 48 → 48 | 36.6% → 36.6% | 0.000000 | 92 → 92 | 70.2% → 70.2% | 0.000000 |
| september | by_band | 1000-1400 km | September 2024 replay | 24 | in_track | 131 → 131 | 33 → 33 | 25.2% → 25.2% | 0.000000 | 70 → 70 | 53.4% → 53.4% | 0.000000 |
| september | by_band | 1000-1400 km | September 2024 replay | 24 | cross | 131 → 131 | 35 → 35 | 26.7% → 26.7% | 0.000000 | 90 → 90 | 68.7% → 68.7% | 0.000000 |
| september | by_band | 1000-1400 km | September 2024 replay | 36 | radial | 130 → 130 | 107 → 107 | 82.3% → 82.3% | 0.000000 | 130 → 130 | 100.0% → 100.0% | 0.000000 |
| september | by_band | 1000-1400 km | September 2024 replay | 36 | in_track | 130 → 130 | 47 → 47 | 36.2% → 36.2% | 0.000000 | 78 → 78 | 60.0% → 60.0% | 0.000000 |
| september | by_band | 1000-1400 km | September 2024 replay | 36 | cross | 130 → 130 | 47 → 47 | 36.2% → 36.2% | 0.000000 | 84 → 84 | 64.6% → 64.6% | 0.000000 |
| september | by_band | 1000-1400 km | September 2024 replay | 48 | radial | 129 → 129 | 54 → 54 | 41.9% → 41.9% | 0.000000 | 129 → 129 | 100.0% → 100.0% | 0.000000 |
| september | by_band | 1000-1400 km | September 2024 replay | 48 | in_track | 129 → 129 | 76 → 76 | 58.9% → 58.9% | 0.000000 | 83 → 83 | 64.3% → 64.3% | 0.000000 |
| september | by_band | 1000-1400 km | September 2024 replay | 48 | cross | 129 → 129 | 24 → 24 | 18.6% → 18.6% | 0.000000 | 103 → 103 | 79.8% → 79.8% | 0.000000 |
| september | by_band | 1000-1400 km | September 2024 replay | 72 | radial | 127 → 127 | 84 → 84 | 66.1% → 66.1% | 0.000000 | 113 → 113 | 89.0% → 89.0% | 0.000000 |
| september | by_band | 1000-1400 km | September 2024 replay | 72 | in_track | 127 → 127 | 83 → 83 | 65.4% → 65.4% | 0.000000 | 85 → 85 | 66.9% → 66.9% | 0.000000 |
| september | by_band | 1000-1400 km | September 2024 replay | 72 | cross | 127 → 127 | 98 → 98 | 77.2% → 77.2% | 0.000000 | 127 → 127 | 100.0% → 100.0% | 0.000000 |
| september | by_band | 1000-1400 km | September 2024 replay | 96 | radial | 122 → 122 | 122 → 122 | 100.0% → 100.0% | 0.000000 | 122 → 122 | 100.0% → 100.0% | 0.000000 |
| september | by_band | 1000-1400 km | September 2024 replay | 96 | in_track | 122 → 122 | 77 → 77 | 63.1% → 63.1% | 0.000000 | 77 → 77 | 63.1% → 63.1% | 0.000000 |
| september | by_band | 1000-1400 km | September 2024 replay | 96 | cross | 122 → 122 | 84 → 84 | 68.9% → 68.9% | 0.000000 | 122 → 122 | 100.0% → 100.0% | 0.000000 |
| september | by_band | 1000-1400 km | September 2024 replay | 120 | radial | 118 → 118 | 74 → 74 | 62.7% → 62.7% | 0.000000 | 118 → 118 | 100.0% → 100.0% | 0.000000 |
| september | by_band | 1000-1400 km | September 2024 replay | 120 | in_track | 118 → 118 | 72 → 72 | 61.0% → 61.0% | 0.000000 | 80 → 80 | 67.8% → 67.8% | 0.000000 |
| september | by_band | 1000-1400 km | September 2024 replay | 120 | cross | 118 → 118 | 19 → 19 | 16.1% → 16.1% | 0.000000 | 118 → 118 | 100.0% → 100.0% | 0.000000 |
| september | by_band | 1000-1400 km | September 2024 replay | 144 | radial | 113 → 113 | 79 → 79 | 69.9% → 69.9% | 0.000000 | 113 → 113 | 100.0% → 100.0% | 0.000000 |
| september | by_band | 1000-1400 km | September 2024 replay | 144 | in_track | 113 → 113 | 83 → 83 | 73.5% → 73.5% | 0.000000 | 93 → 93 | 82.3% → 82.3% | 0.000000 |
| september | by_band | 1000-1400 km | September 2024 replay | 144 | cross | 113 → 113 | 113 → 113 | 100.0% → 100.0% | 0.000000 | 113 → 113 | 100.0% → 100.0% | 0.000000 |
| september | by_band | 1000-1400 km | September 2024 replay | 168 | radial | 106 → 106 | 106 → 106 | 100.0% → 100.0% | 0.000000 | 106 → 106 | 100.0% → 100.0% | 0.000000 |
| september | by_band | 1000-1400 km | September 2024 replay | 168 | in_track | 106 → 106 | 72 → 72 | 67.9% → 67.9% | 0.000000 | 84 → 84 | 79.2% → 79.2% | 0.000000 |
| september | by_band | 1000-1400 km | September 2024 replay | 168 | cross | 106 → 106 | 73 → 73 | 68.9% → 68.9% | 0.000000 | 106 → 106 | 100.0% → 100.0% | 0.000000 |
| september | by_band | 400-600 km | September 2024 replay | 6 | radial | 373 → 373 | 117 → 117 | 31.4% → 31.4% | 0.000000 | 248 → 248 | 66.5% → 66.5% | 0.000000 |
| september | by_band | 400-600 km | September 2024 replay | 6 | in_track | 373 → 373 | 72 → 72 | 19.3% → 19.3% | 0.000000 | 168 → 168 | 45.0% → 45.0% | 0.000000 |
| september | by_band | 400-600 km | September 2024 replay | 6 | cross | 373 → 373 | 12 → 12 | 3.2% → 3.2% | 0.000000 | 31 → 31 | 8.3% → 8.3% | 0.000000 |
| september | by_band | 400-600 km | September 2024 replay | 12 | radial | 373 → 373 | 130 → 130 | 34.9% → 34.9% | 0.000000 | 180 → 180 | 48.3% → 48.3% | 0.000000 |
| september | by_band | 400-600 km | September 2024 replay | 12 | in_track | 373 → 373 | 90 → 90 | 24.1% → 24.1% | 0.000000 | 179 → 179 | 48.0% → 48.0% | 0.000000 |
| september | by_band | 400-600 km | September 2024 replay | 12 | cross | 373 → 373 | 13 → 13 | 3.5% → 3.5% | 0.000000 | 24 → 24 | 6.4% → 6.4% | 0.000000 |
| september | by_band | 400-600 km | September 2024 replay | 24 | radial | 370 → 370 | 238 → 238 | 64.3% → 64.3% | 0.000000 | 361 → 361 | 97.6% → 97.6% | 0.000000 |
| september | by_band | 400-600 km | September 2024 replay | 24 | in_track | 370 → 370 | 259 → 259 | 70.0% → 70.0% | 0.000000 | 325 → 325 | 87.8% → 87.8% | 0.000000 |
| september | by_band | 400-600 km | September 2024 replay | 24 | cross | 370 → 370 | 13 → 13 | 3.5% → 3.5% | 0.000000 | 35 → 35 | 9.5% → 9.5% | 0.000000 |
| september | by_band | 400-600 km | September 2024 replay | 36 | radial | 370 → 370 | 168 → 168 | 45.4% → 45.4% | 0.000000 | 339 → 339 | 91.6% → 91.6% | 0.000000 |
| september | by_band | 400-600 km | September 2024 replay | 36 | in_track | 370 → 370 | 300 → 300 | 81.1% → 81.1% | 0.000000 | 342 → 342 | 92.4% → 92.4% | 0.000000 |
| september | by_band | 400-600 km | September 2024 replay | 36 | cross | 370 → 370 | 42 → 42 | 11.4% → 11.4% | 0.000000 | 98 → 98 | 26.5% → 26.5% | 0.000000 |
| september | by_band | 400-600 km | September 2024 replay | 48 | radial | 368 → 368 | 302 → 302 | 82.1% → 82.1% | 0.000000 | 368 → 368 | 100.0% → 100.0% | 0.000000 |
| september | by_band | 400-600 km | September 2024 replay | 48 | in_track | 368 → 368 | 300 → 300 | 81.5% → 81.5% | 0.000000 | 345 → 345 | 93.8% → 93.8% | 0.000000 |
| september | by_band | 400-600 km | September 2024 replay | 48 | cross | 368 → 368 | 30 → 30 | 8.2% → 8.2% | 0.000000 | 69 → 69 | 18.8% → 18.8% | 0.000000 |
| september | by_band | 400-600 km | September 2024 replay | 72 | radial | 365 → 365 | 253 → 253 | 69.3% → 69.3% | 0.000000 | 362 → 362 | 99.2% → 99.2% | 0.000000 |
| september | by_band | 400-600 km | September 2024 replay | 72 | in_track | 365 → 365 | 300 → 300 | 82.2% → 82.2% | 0.000000 | 344 → 344 | 94.2% → 94.2% | 0.000000 |
| september | by_band | 400-600 km | September 2024 replay | 72 | cross | 365 → 365 | 83 → 83 | 22.7% → 22.7% | 0.000000 | 151 → 151 | 41.4% → 41.4% | 0.000000 |
| september | by_band | 400-600 km | September 2024 replay | 96 | radial | 362 → 362 | 349 → 349 | 96.4% → 96.4% | 0.000000 | 360 → 360 | 99.4% → 99.4% | 0.000000 |
| september | by_band | 400-600 km | September 2024 replay | 96 | in_track | 362 → 362 | 295 → 295 | 81.5% → 81.5% | 0.000000 | 341 → 341 | 94.2% → 94.2% | 0.000000 |
| september | by_band | 400-600 km | September 2024 replay | 96 | cross | 362 → 362 | 80 → 80 | 22.1% → 22.1% | 0.000000 | 144 → 144 | 39.8% → 39.8% | 0.000000 |
| september | by_band | 400-600 km | September 2024 replay | 120 | radial | 360 → 360 | 267 → 267 | 74.2% → 74.2% | 0.000000 | 354 → 354 | 98.3% → 98.3% | 0.000000 |
| september | by_band | 400-600 km | September 2024 replay | 120 | in_track | 360 → 360 | 301 → 301 | 83.6% → 83.6% | 0.000000 | 340 → 340 | 94.4% → 94.4% | 0.000000 |
| september | by_band | 400-600 km | September 2024 replay | 120 | cross | 360 → 360 | 110 → 110 | 30.6% → 30.6% | 0.000000 | 181 → 181 | 50.3% → 50.3% | 0.000000 |
| september | by_band | 400-600 km | September 2024 replay | 144 | radial | 358 → 358 | 323 → 326 | 90.2% → 91.1% | 0.837989 | 344 → 347 | 96.1% → 96.9% | 0.837989 |
| september | by_band | 400-600 km | September 2024 replay | 144 | in_track | 358 → 358 | 303 → 303 | 84.6% → 84.6% | 0.000000 | 338 → 338 | 94.4% → 94.4% | 0.000000 |
| september | by_band | 400-600 km | September 2024 replay | 144 | cross | 358 → 358 | 114 → 114 | 31.8% → 31.8% | 0.000000 | 197 → 197 | 55.0% → 55.0% | 0.000000 |
| september | by_band | 400-600 km | September 2024 replay | 168 | radial | 355 → 355 | 319 → 321 | 89.9% → 90.4% | 0.563380 | 342 → 347 | 96.3% → 97.7% | 1.408451 |
| september | by_band | 400-600 km | September 2024 replay | 168 | in_track | 355 → 355 | 296 → 296 | 83.4% → 83.4% | 0.000000 | 330 → 330 | 93.0% → 93.0% | 0.000000 |
| september | by_band | 400-600 km | September 2024 replay | 168 | cross | 355 → 355 | 137 → 137 | 38.6% → 38.6% | 0.000000 | 227 → 227 | 63.9% → 63.9% | 0.000000 |
| september | by_band | 600-750 km | September 2024 replay | 6 | radial | 62 → 62 | 45 → 45 | 72.6% → 72.6% | 0.000000 | 60 → 60 | 96.8% → 96.8% | 0.000000 |
| september | by_band | 600-750 km | September 2024 replay | 6 | in_track | 62 → 62 | 33 → 33 | 53.2% → 53.2% | 0.000000 | 59 → 59 | 95.2% → 95.2% | 0.000000 |
| september | by_band | 600-750 km | September 2024 replay | 6 | cross | 62 → 62 | 4 → 4 | 6.5% → 6.5% | 0.000000 | 6 → 6 | 9.7% → 9.7% | 0.000000 |
| september | by_band | 600-750 km | September 2024 replay | 12 | radial | 62 → 62 | 14 → 14 | 22.6% → 22.6% | 0.000000 | 31 → 31 | 50.0% → 50.0% | 0.000000 |
| september | by_band | 600-750 km | September 2024 replay | 12 | in_track | 62 → 62 | 53 → 53 | 85.5% → 85.5% | 0.000000 | 60 → 60 | 96.8% → 96.8% | 0.000000 |
| september | by_band | 600-750 km | September 2024 replay | 12 | cross | 62 → 62 | 4 → 4 | 6.5% → 6.5% | 0.000000 | 5 → 5 | 8.1% → 8.1% | 0.000000 |
| september | by_band | 600-750 km | September 2024 replay | 24 | radial | 59 → 59 | 22 → 22 | 37.3% → 37.3% | 0.000000 | 53 → 53 | 89.8% → 89.8% | 0.000000 |
| september | by_band | 600-750 km | September 2024 replay | 24 | in_track | 59 → 59 | 56 → 56 | 94.9% → 94.9% | 0.000000 | 59 → 59 | 100.0% → 100.0% | 0.000000 |
| september | by_band | 600-750 km | September 2024 replay | 24 | cross | 59 → 59 | 3 → 3 | 5.1% → 5.1% | 0.000000 | 7 → 7 | 11.9% → 11.9% | 0.000000 |
| september | by_band | 600-750 km | September 2024 replay | 36 | radial | 58 → 58 | 55 → 55 | 94.8% → 94.8% | 0.000000 | 58 → 58 | 100.0% → 100.0% | 0.000000 |
| september | by_band | 600-750 km | September 2024 replay | 36 | in_track | 58 → 58 | 57 → 57 | 98.3% → 98.3% | 0.000000 | 58 → 58 | 100.0% → 100.0% | 0.000000 |
| september | by_band | 600-750 km | September 2024 replay | 36 | cross | 58 → 58 | 1 → 1 | 1.7% → 1.7% | 0.000000 | 4 → 4 | 6.9% → 6.9% | 0.000000 |
| september | by_band | 600-750 km | September 2024 replay | 48 | radial | 54 → 54 | 27 → 27 | 50.0% → 50.0% | 0.000000 | 54 → 54 | 100.0% → 100.0% | 0.000000 |
| september | by_band | 600-750 km | September 2024 replay | 48 | in_track | 54 → 54 | 54 → 54 | 100.0% → 100.0% | 0.000000 | 54 → 54 | 100.0% → 100.0% | 0.000000 |
| september | by_band | 600-750 km | September 2024 replay | 48 | cross | 54 → 54 | 4 → 4 | 7.4% → 7.4% | 0.000000 | 8 → 8 | 14.8% → 14.8% | 0.000000 |
| september | by_band | 600-750 km | September 2024 replay | 72 | radial | 52 → 52 | 34 → 34 | 65.4% → 65.4% | 0.000000 | 52 → 52 | 100.0% → 100.0% | 0.000000 |
| september | by_band | 600-750 km | September 2024 replay | 72 | in_track | 52 → 52 | 52 → 52 | 100.0% → 100.0% | 0.000000 | 52 → 52 | 100.0% → 100.0% | 0.000000 |
| september | by_band | 600-750 km | September 2024 replay | 72 | cross | 52 → 52 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 1 → 1 | 1.9% → 1.9% | 0.000000 |
| september | by_band | 600-750 km | September 2024 replay | 96 | radial | 51 → 51 | 32 → 32 | 62.7% → 62.7% | 0.000000 | 51 → 51 | 100.0% → 100.0% | 0.000000 |
| september | by_band | 600-750 km | September 2024 replay | 96 | in_track | 51 → 51 | 50 → 50 | 98.0% → 98.0% | 0.000000 | 51 → 51 | 100.0% → 100.0% | 0.000000 |
| september | by_band | 600-750 km | September 2024 replay | 96 | cross | 51 → 51 | 7 → 7 | 13.7% → 13.7% | 0.000000 | 11 → 11 | 21.6% → 21.6% | 0.000000 |
| september | by_band | 600-750 km | September 2024 replay | 120 | radial | 49 → 49 | 39 → 39 | 79.6% → 79.6% | 0.000000 | 49 → 49 | 100.0% → 100.0% | 0.000000 |
| september | by_band | 600-750 km | September 2024 replay | 120 | in_track | 49 → 49 | 49 → 49 | 100.0% → 100.0% | 0.000000 | 49 → 49 | 100.0% → 100.0% | 0.000000 |
| september | by_band | 600-750 km | September 2024 replay | 120 | cross | 49 → 49 | 1 → 1 | 2.0% → 2.0% | 0.000000 | 4 → 4 | 8.2% → 8.2% | 0.000000 |
| september | by_band | 600-750 km | September 2024 replay | 144 | radial | 47 → 47 | 47 → 47 | 100.0% → 100.0% | 0.000000 | 47 → 47 | 100.0% → 100.0% | 0.000000 |
| september | by_band | 600-750 km | September 2024 replay | 144 | in_track | 47 → 47 | 46 → 46 | 97.9% → 97.9% | 0.000000 | 47 → 47 | 100.0% → 100.0% | 0.000000 |
| september | by_band | 600-750 km | September 2024 replay | 144 | cross | 47 → 47 | 3 → 3 | 6.4% → 6.4% | 0.000000 | 11 → 11 | 23.4% → 23.4% | 0.000000 |
| september | by_band | 600-750 km | September 2024 replay | 168 | radial | 45 → 45 | 45 → 45 | 100.0% → 100.0% | 0.000000 | 45 → 45 | 100.0% → 100.0% | 0.000000 |
| september | by_band | 600-750 km | September 2024 replay | 168 | in_track | 45 → 45 | 44 → 44 | 97.8% → 97.8% | 0.000000 | 45 → 45 | 100.0% → 100.0% | 0.000000 |
| september | by_band | 600-750 km | September 2024 replay | 168 | cross | 45 → 45 | 1 → 1 | 2.2% → 2.2% | 0.000000 | 3 → 3 | 6.7% → 6.7% | 0.000000 |
| september | by_band | 750-850 km | September 2024 replay | 6 | radial | 245 → 245 | 21 → 21 | 8.6% → 8.6% | 0.000000 | 57 → 57 | 23.3% → 23.3% | 0.000000 |
| september | by_band | 750-850 km | September 2024 replay | 6 | in_track | 245 → 245 | 60 → 60 | 24.5% → 24.5% | 0.000000 | 118 → 118 | 48.2% → 48.2% | 0.000000 |
| september | by_band | 750-850 km | September 2024 replay | 6 | cross | 245 → 245 | 24 → 24 | 9.8% → 9.8% | 0.000000 | 45 → 45 | 18.4% → 18.4% | 0.000000 |
| september | by_band | 750-850 km | September 2024 replay | 12 | radial | 238 → 238 | 27 → 27 | 11.3% → 11.3% | 0.000000 | 49 → 49 | 20.6% → 20.6% | 0.000000 |
| september | by_band | 750-850 km | September 2024 replay | 12 | in_track | 238 → 238 | 127 → 127 | 53.4% → 53.4% | 0.000000 | 182 → 182 | 76.5% → 76.5% | 0.000000 |
| september | by_band | 750-850 km | September 2024 replay | 12 | cross | 238 → 238 | 16 → 16 | 6.7% → 6.7% | 0.000000 | 27 → 27 | 11.3% → 11.3% | 0.000000 |
| september | by_band | 750-850 km | September 2024 replay | 24 | radial | 226 → 226 | 157 → 157 | 69.5% → 69.5% | 0.000000 | 196 → 196 | 86.7% → 86.7% | 0.000000 |
| september | by_band | 750-850 km | September 2024 replay | 24 | in_track | 226 → 226 | 152 → 152 | 67.3% → 67.3% | 0.000000 | 204 → 204 | 90.3% → 90.3% | 0.000000 |
| september | by_band | 750-850 km | September 2024 replay | 24 | cross | 226 → 226 | 16 → 16 | 7.1% → 7.1% | 0.000000 | 39 → 39 | 17.3% → 17.3% | 0.000000 |
| september | by_band | 750-850 km | September 2024 replay | 36 | radial | 218 → 218 | 105 → 105 | 48.2% → 48.2% | 0.000000 | 133 → 133 | 61.0% → 61.0% | 0.000000 |
| september | by_band | 750-850 km | September 2024 replay | 36 | in_track | 218 → 218 | 170 → 170 | 78.0% → 78.0% | 0.000000 | 197 → 197 | 90.4% → 90.4% | 0.000000 |
| september | by_band | 750-850 km | September 2024 replay | 36 | cross | 218 → 218 | 42 → 42 | 19.3% → 19.3% | 0.000000 | 91 → 91 | 41.7% → 41.7% | 0.000000 |
| september | by_band | 750-850 km | September 2024 replay | 48 | radial | 209 → 209 | 79 → 79 | 37.8% → 37.8% | 0.000000 | 172 → 172 | 82.3% → 82.3% | 0.000000 |
| september | by_band | 750-850 km | September 2024 replay | 48 | in_track | 209 → 209 | 176 → 176 | 84.2% → 84.2% | 0.000000 | 205 → 205 | 98.1% → 98.1% | 0.000000 |
| september | by_band | 750-850 km | September 2024 replay | 48 | cross | 209 → 209 | 71 → 71 | 34.0% → 34.0% | 0.000000 | 124 → 124 | 59.3% → 59.3% | 0.000000 |
| september | by_band | 750-850 km | September 2024 replay | 72 | radial | 194 → 194 | 155 → 155 | 79.9% → 79.9% | 0.000000 | 194 → 194 | 100.0% → 100.0% | 0.000000 |
| september | by_band | 750-850 km | September 2024 replay | 72 | in_track | 194 → 194 | 175 → 175 | 90.2% → 90.2% | 0.000000 | 191 → 191 | 98.5% → 98.5% | 0.000000 |
| september | by_band | 750-850 km | September 2024 replay | 72 | cross | 194 → 194 | 49 → 49 | 25.3% → 25.3% | 0.000000 | 98 → 98 | 50.5% → 50.5% | 0.000000 |
| september | by_band | 750-850 km | September 2024 replay | 96 | radial | 179 → 179 | 126 → 126 | 70.4% → 70.4% | 0.000000 | 179 → 179 | 100.0% → 100.0% | 0.000000 |
| september | by_band | 750-850 km | September 2024 replay | 96 | in_track | 179 → 179 | 165 → 165 | 92.2% → 92.2% | 0.000000 | 176 → 176 | 98.3% → 98.3% | 0.000000 |
| september | by_band | 750-850 km | September 2024 replay | 96 | cross | 179 → 179 | 93 → 93 | 52.0% → 52.0% | 0.000000 | 117 → 117 | 65.4% → 65.4% | 0.000000 |
| september | by_band | 750-850 km | September 2024 replay | 120 | radial | 166 → 166 | 161 → 161 | 97.0% → 97.0% | 0.000000 | 166 → 166 | 100.0% → 100.0% | 0.000000 |
| september | by_band | 750-850 km | September 2024 replay | 120 | in_track | 166 → 166 | 149 → 149 | 89.8% → 89.8% | 0.000000 | 163 → 163 | 98.2% → 98.2% | 0.000000 |
| september | by_band | 750-850 km | September 2024 replay | 120 | cross | 166 → 166 | 54 → 54 | 32.5% → 32.5% | 0.000000 | 108 → 108 | 65.1% → 65.1% | 0.000000 |
| september | by_band | 750-850 km | September 2024 replay | 144 | radial | 151 → 151 | 95 → 95 | 62.9% → 62.9% | 0.000000 | 151 → 151 | 100.0% → 100.0% | 0.000000 |
| september | by_band | 750-850 km | September 2024 replay | 144 | in_track | 151 → 151 | 130 → 130 | 86.1% → 86.1% | 0.000000 | 147 → 147 | 97.4% → 97.4% | 0.000000 |
| september | by_band | 750-850 km | September 2024 replay | 144 | cross | 151 → 151 | 83 → 83 | 55.0% → 55.0% | 0.000000 | 125 → 125 | 82.8% → 82.8% | 0.000000 |
| september | by_band | 750-850 km | September 2024 replay | 168 | radial | 137 → 137 | 137 → 137 | 100.0% → 100.0% | 0.000000 | 137 → 137 | 100.0% → 100.0% | 0.000000 |
| september | by_band | 750-850 km | September 2024 replay | 168 | in_track | 137 → 137 | 106 → 106 | 77.4% → 77.4% | 0.000000 | 129 → 129 | 94.2% → 94.2% | 0.000000 |
| september | by_band | 750-850 km | September 2024 replay | 168 | cross | 137 → 137 | 65 → 65 | 47.4% → 47.4% | 0.000000 | 97 → 97 | 70.8% → 70.8% | 0.000000 |
| september | by_band | 850-1000 km | September 2024 replay | 6 | radial | 327 → 327 | 23 → 23 | 7.0% → 7.0% | 0.000000 | 53 → 53 | 16.2% → 16.2% | 0.000000 |
| september | by_band | 850-1000 km | September 2024 replay | 6 | in_track | 327 → 327 | 54 → 54 | 16.5% → 16.5% | 0.000000 | 115 → 115 | 35.2% → 35.2% | 0.000000 |
| september | by_band | 850-1000 km | September 2024 replay | 6 | cross | 327 → 327 | 81 → 81 | 24.8% → 24.8% | 0.000000 | 141 → 141 | 43.1% → 43.1% | 0.000000 |
| september | by_band | 850-1000 km | September 2024 replay | 12 | radial | 325 → 325 | 66 → 66 | 20.3% → 20.3% | 0.000000 | 94 → 94 | 28.9% → 28.9% | 0.000000 |
| september | by_band | 850-1000 km | September 2024 replay | 12 | in_track | 325 → 325 | 60 → 60 | 18.5% → 18.5% | 0.000000 | 104 → 104 | 32.0% → 32.0% | 0.000000 |
| september | by_band | 850-1000 km | September 2024 replay | 12 | cross | 325 → 325 | 81 → 81 | 24.9% → 24.9% | 0.000000 | 132 → 132 | 40.6% → 40.6% | 0.000000 |
| september | by_band | 850-1000 km | September 2024 replay | 24 | radial | 322 → 322 | 130 → 130 | 40.4% → 40.4% | 0.000000 | 201 → 201 | 62.4% → 62.4% | 0.000000 |
| september | by_band | 850-1000 km | September 2024 replay | 24 | in_track | 322 → 322 | 154 → 154 | 47.8% → 47.8% | 0.000000 | 243 → 243 | 75.5% → 75.5% | 0.000000 |
| september | by_band | 850-1000 km | September 2024 replay | 24 | cross | 322 → 322 | 116 → 116 | 36.0% → 36.0% | 0.000000 | 222 → 222 | 68.9% → 68.9% | 0.000000 |
| september | by_band | 850-1000 km | September 2024 replay | 36 | radial | 319 → 319 | 192 → 192 | 60.2% → 60.2% | 0.000000 | 250 → 250 | 78.4% → 78.4% | 0.000000 |
| september | by_band | 850-1000 km | September 2024 replay | 36 | in_track | 319 → 319 | 255 → 255 | 79.9% → 79.9% | 0.000000 | 302 → 302 | 94.7% → 94.7% | 0.000000 |
| september | by_band | 850-1000 km | September 2024 replay | 36 | cross | 319 → 319 | 134 → 134 | 42.0% → 42.0% | 0.000000 | 231 → 231 | 72.4% → 72.4% | 0.000000 |
| september | by_band | 850-1000 km | September 2024 replay | 48 | radial | 315 → 315 | 191 → 191 | 60.6% → 60.6% | 0.000000 | 255 → 255 | 81.0% → 81.0% | 0.000000 |
| september | by_band | 850-1000 km | September 2024 replay | 48 | in_track | 315 → 315 | 291 → 291 | 92.4% → 92.4% | 0.000000 | 313 → 313 | 99.4% → 99.4% | 0.000000 |
| september | by_band | 850-1000 km | September 2024 replay | 48 | cross | 315 → 315 | 129 → 129 | 41.0% → 41.0% | 0.000000 | 270 → 270 | 85.7% → 85.7% | 0.000000 |
| september | by_band | 850-1000 km | September 2024 replay | 72 | radial | 308 → 308 | 139 → 139 | 45.1% → 45.1% | 0.000000 | 248 → 248 | 80.5% → 80.5% | 0.000000 |
| september | by_band | 850-1000 km | September 2024 replay | 72 | in_track | 308 → 308 | 307 → 307 | 99.7% → 99.7% | 0.000000 | 308 → 308 | 100.0% → 100.0% | 0.000000 |
| september | by_band | 850-1000 km | September 2024 replay | 72 | cross | 308 → 308 | 159 → 159 | 51.6% → 51.6% | 0.000000 | 301 → 301 | 97.7% → 97.7% | 0.000000 |
| september | by_band | 850-1000 km | September 2024 replay | 96 | radial | 301 → 301 | 216 → 216 | 71.8% → 71.8% | 0.000000 | 247 → 247 | 82.1% → 82.1% | 0.000000 |
| september | by_band | 850-1000 km | September 2024 replay | 96 | in_track | 301 → 301 | 301 → 301 | 100.0% → 100.0% | 0.000000 | 301 → 301 | 100.0% → 100.0% | 0.000000 |
| september | by_band | 850-1000 km | September 2024 replay | 96 | cross | 301 → 301 | 272 → 272 | 90.4% → 90.4% | 0.000000 | 301 → 301 | 100.0% → 100.0% | 0.000000 |
| september | by_band | 850-1000 km | September 2024 replay | 120 | radial | 294 → 294 | 238 → 238 | 81.0% → 81.0% | 0.000000 | 251 → 251 | 85.4% → 85.4% | 0.000000 |
| september | by_band | 850-1000 km | September 2024 replay | 120 | in_track | 294 → 294 | 294 → 294 | 100.0% → 100.0% | 0.000000 | 294 → 294 | 100.0% → 100.0% | 0.000000 |
| september | by_band | 850-1000 km | September 2024 replay | 120 | cross | 294 → 294 | 174 → 174 | 59.2% → 59.2% | 0.000000 | 294 → 294 | 100.0% → 100.0% | 0.000000 |
| september | by_band | 850-1000 km | September 2024 replay | 144 | radial | 287 → 287 | 127 → 127 | 44.3% → 44.3% | 0.000000 | 253 → 253 | 88.2% → 88.2% | 0.000000 |
| september | by_band | 850-1000 km | September 2024 replay | 144 | in_track | 287 → 287 | 287 → 287 | 100.0% → 100.0% | 0.000000 | 287 → 287 | 100.0% → 100.0% | 0.000000 |
| september | by_band | 850-1000 km | September 2024 replay | 144 | cross | 287 → 287 | 93 → 93 | 32.4% → 32.4% | 0.000000 | 287 → 287 | 100.0% → 100.0% | 0.000000 |
| september | by_band | 850-1000 km | September 2024 replay | 168 | radial | 281 → 281 | 228 → 228 | 81.1% → 81.1% | 0.000000 | 252 → 253 | 89.7% → 90.0% | 0.355872 |
| september | by_band | 850-1000 km | September 2024 replay | 168 | in_track | 281 → 281 | 281 → 281 | 100.0% → 100.0% | 0.000000 | 281 → 281 | 100.0% → 100.0% | 0.000000 |
| september | by_band | 850-1000 km | September 2024 replay | 168 | cross | 281 → 281 | 266 → 266 | 94.7% → 94.7% | 0.000000 | 281 → 281 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | cryosat-2 | September 2024 replay | 6 | radial | 62 → 62 | 45 → 45 | 72.6% → 72.6% | 0.000000 | 60 → 60 | 96.8% → 96.8% | 0.000000 |
| september | by_mission | cryosat-2 | September 2024 replay | 6 | in_track | 62 → 62 | 33 → 33 | 53.2% → 53.2% | 0.000000 | 59 → 59 | 95.2% → 95.2% | 0.000000 |
| september | by_mission | cryosat-2 | September 2024 replay | 6 | cross | 62 → 62 | 4 → 4 | 6.5% → 6.5% | 0.000000 | 6 → 6 | 9.7% → 9.7% | 0.000000 |
| september | by_mission | cryosat-2 | September 2024 replay | 12 | radial | 62 → 62 | 14 → 14 | 22.6% → 22.6% | 0.000000 | 31 → 31 | 50.0% → 50.0% | 0.000000 |
| september | by_mission | cryosat-2 | September 2024 replay | 12 | in_track | 62 → 62 | 53 → 53 | 85.5% → 85.5% | 0.000000 | 60 → 60 | 96.8% → 96.8% | 0.000000 |
| september | by_mission | cryosat-2 | September 2024 replay | 12 | cross | 62 → 62 | 4 → 4 | 6.5% → 6.5% | 0.000000 | 5 → 5 | 8.1% → 8.1% | 0.000000 |
| september | by_mission | cryosat-2 | September 2024 replay | 24 | radial | 59 → 59 | 22 → 22 | 37.3% → 37.3% | 0.000000 | 53 → 53 | 89.8% → 89.8% | 0.000000 |
| september | by_mission | cryosat-2 | September 2024 replay | 24 | in_track | 59 → 59 | 56 → 56 | 94.9% → 94.9% | 0.000000 | 59 → 59 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | cryosat-2 | September 2024 replay | 24 | cross | 59 → 59 | 3 → 3 | 5.1% → 5.1% | 0.000000 | 7 → 7 | 11.9% → 11.9% | 0.000000 |
| september | by_mission | cryosat-2 | September 2024 replay | 36 | radial | 58 → 58 | 55 → 55 | 94.8% → 94.8% | 0.000000 | 58 → 58 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | cryosat-2 | September 2024 replay | 36 | in_track | 58 → 58 | 57 → 57 | 98.3% → 98.3% | 0.000000 | 58 → 58 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | cryosat-2 | September 2024 replay | 36 | cross | 58 → 58 | 1 → 1 | 1.7% → 1.7% | 0.000000 | 4 → 4 | 6.9% → 6.9% | 0.000000 |
| september | by_mission | cryosat-2 | September 2024 replay | 48 | radial | 54 → 54 | 27 → 27 | 50.0% → 50.0% | 0.000000 | 54 → 54 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | cryosat-2 | September 2024 replay | 48 | in_track | 54 → 54 | 54 → 54 | 100.0% → 100.0% | 0.000000 | 54 → 54 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | cryosat-2 | September 2024 replay | 48 | cross | 54 → 54 | 4 → 4 | 7.4% → 7.4% | 0.000000 | 8 → 8 | 14.8% → 14.8% | 0.000000 |
| september | by_mission | cryosat-2 | September 2024 replay | 72 | radial | 52 → 52 | 34 → 34 | 65.4% → 65.4% | 0.000000 | 52 → 52 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | cryosat-2 | September 2024 replay | 72 | in_track | 52 → 52 | 52 → 52 | 100.0% → 100.0% | 0.000000 | 52 → 52 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | cryosat-2 | September 2024 replay | 72 | cross | 52 → 52 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 1 → 1 | 1.9% → 1.9% | 0.000000 |
| september | by_mission | cryosat-2 | September 2024 replay | 96 | radial | 51 → 51 | 32 → 32 | 62.7% → 62.7% | 0.000000 | 51 → 51 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | cryosat-2 | September 2024 replay | 96 | in_track | 51 → 51 | 50 → 50 | 98.0% → 98.0% | 0.000000 | 51 → 51 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | cryosat-2 | September 2024 replay | 96 | cross | 51 → 51 | 7 → 7 | 13.7% → 13.7% | 0.000000 | 11 → 11 | 21.6% → 21.6% | 0.000000 |
| september | by_mission | cryosat-2 | September 2024 replay | 120 | radial | 49 → 49 | 39 → 39 | 79.6% → 79.6% | 0.000000 | 49 → 49 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | cryosat-2 | September 2024 replay | 120 | in_track | 49 → 49 | 49 → 49 | 100.0% → 100.0% | 0.000000 | 49 → 49 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | cryosat-2 | September 2024 replay | 120 | cross | 49 → 49 | 1 → 1 | 2.0% → 2.0% | 0.000000 | 4 → 4 | 8.2% → 8.2% | 0.000000 |
| september | by_mission | cryosat-2 | September 2024 replay | 144 | radial | 47 → 47 | 47 → 47 | 100.0% → 100.0% | 0.000000 | 47 → 47 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | cryosat-2 | September 2024 replay | 144 | in_track | 47 → 47 | 46 → 46 | 97.9% → 97.9% | 0.000000 | 47 → 47 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | cryosat-2 | September 2024 replay | 144 | cross | 47 → 47 | 3 → 3 | 6.4% → 6.4% | 0.000000 | 11 → 11 | 23.4% → 23.4% | 0.000000 |
| september | by_mission | cryosat-2 | September 2024 replay | 168 | radial | 45 → 45 | 45 → 45 | 100.0% → 100.0% | 0.000000 | 45 → 45 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | cryosat-2 | September 2024 replay | 168 | in_track | 45 → 45 | 44 → 44 | 97.8% → 97.8% | 0.000000 | 45 → 45 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | cryosat-2 | September 2024 replay | 168 | cross | 45 → 45 | 1 → 1 | 2.2% → 2.2% | 0.000000 | 3 → 3 | 6.7% → 6.7% | 0.000000 |
| september | by_mission | gracefo-c | September 2024 replay | 6 | radial | 76 → 76 | 37 → 37 | 48.7% → 48.7% | 0.000000 | 58 → 58 | 76.3% → 76.3% | 0.000000 |
| september | by_mission | gracefo-c | September 2024 replay | 6 | in_track | 76 → 76 | 9 → 9 | 11.8% → 11.8% | 0.000000 | 19 → 19 | 25.0% → 25.0% | 0.000000 |
| september | by_mission | gracefo-c | September 2024 replay | 6 | cross | 76 → 76 | 1 → 1 | 1.3% → 1.3% | 0.000000 | 4 → 4 | 5.3% → 5.3% | 0.000000 |
| september | by_mission | gracefo-c | September 2024 replay | 12 | radial | 76 → 76 | 26 → 26 | 34.2% → 34.2% | 0.000000 | 36 → 36 | 47.4% → 47.4% | 0.000000 |
| september | by_mission | gracefo-c | September 2024 replay | 12 | in_track | 76 → 76 | 14 → 14 | 18.4% → 18.4% | 0.000000 | 30 → 30 | 39.5% → 39.5% | 0.000000 |
| september | by_mission | gracefo-c | September 2024 replay | 12 | cross | 76 → 76 | 3 → 3 | 3.9% → 3.9% | 0.000000 | 4 → 4 | 5.3% → 5.3% | 0.000000 |
| september | by_mission | gracefo-c | September 2024 replay | 24 | radial | 76 → 76 | 45 → 45 | 59.2% → 59.2% | 0.000000 | 76 → 76 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | gracefo-c | September 2024 replay | 24 | in_track | 76 → 76 | 53 → 53 | 69.7% → 69.7% | 0.000000 | 68 → 68 | 89.5% → 89.5% | 0.000000 |
| september | by_mission | gracefo-c | September 2024 replay | 24 | cross | 76 → 76 | 3 → 3 | 3.9% → 3.9% | 0.000000 | 6 → 6 | 7.9% → 7.9% | 0.000000 |
| september | by_mission | gracefo-c | September 2024 replay | 36 | radial | 76 → 76 | 30 → 30 | 39.5% → 39.5% | 0.000000 | 72 → 72 | 94.7% → 94.7% | 0.000000 |
| september | by_mission | gracefo-c | September 2024 replay | 36 | in_track | 76 → 76 | 62 → 62 | 81.6% → 81.6% | 0.000000 | 71 → 71 | 93.4% → 93.4% | 0.000000 |
| september | by_mission | gracefo-c | September 2024 replay | 36 | cross | 76 → 76 | 4 → 4 | 5.3% → 5.3% | 0.000000 | 17 → 17 | 22.4% → 22.4% | 0.000000 |
| september | by_mission | gracefo-c | September 2024 replay | 48 | radial | 76 → 76 | 55 → 55 | 72.4% → 72.4% | 0.000000 | 76 → 76 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | gracefo-c | September 2024 replay | 48 | in_track | 76 → 76 | 62 → 62 | 81.6% → 81.6% | 0.000000 | 72 → 72 | 94.7% → 94.7% | 0.000000 |
| september | by_mission | gracefo-c | September 2024 replay | 48 | cross | 76 → 76 | 4 → 4 | 5.3% → 5.3% | 0.000000 | 11 → 11 | 14.5% → 14.5% | 0.000000 |
| september | by_mission | gracefo-c | September 2024 replay | 72 | radial | 76 → 76 | 51 → 51 | 67.1% → 67.1% | 0.000000 | 76 → 76 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | gracefo-c | September 2024 replay | 72 | in_track | 76 → 76 | 64 → 64 | 84.2% → 84.2% | 0.000000 | 72 → 72 | 94.7% → 94.7% | 0.000000 |
| september | by_mission | gracefo-c | September 2024 replay | 72 | cross | 76 → 76 | 7 → 7 | 9.2% → 9.2% | 0.000000 | 12 → 12 | 15.8% → 15.8% | 0.000000 |
| september | by_mission | gracefo-c | September 2024 replay | 96 | radial | 76 → 76 | 73 → 73 | 96.1% → 96.1% | 0.000000 | 76 → 76 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | gracefo-c | September 2024 replay | 96 | in_track | 76 → 76 | 64 → 64 | 84.2% → 84.2% | 0.000000 | 72 → 72 | 94.7% → 94.7% | 0.000000 |
| september | by_mission | gracefo-c | September 2024 replay | 96 | cross | 76 → 76 | 12 → 12 | 15.8% → 15.8% | 0.000000 | 20 → 20 | 26.3% → 26.3% | 0.000000 |
| september | by_mission | gracefo-c | September 2024 replay | 120 | radial | 76 → 76 | 36 → 36 | 47.4% → 47.4% | 0.000000 | 76 → 76 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | gracefo-c | September 2024 replay | 120 | in_track | 76 → 76 | 65 → 65 | 85.5% → 85.5% | 0.000000 | 72 → 72 | 94.7% → 94.7% | 0.000000 |
| september | by_mission | gracefo-c | September 2024 replay | 120 | cross | 76 → 76 | 28 → 28 | 36.8% → 36.8% | 0.000000 | 43 → 43 | 56.6% → 56.6% | 0.000000 |
| september | by_mission | gracefo-c | September 2024 replay | 144 | radial | 76 → 76 | 72 → 72 | 94.7% → 94.7% | 0.000000 | 74 → 74 | 97.4% → 97.4% | 0.000000 |
| september | by_mission | gracefo-c | September 2024 replay | 144 | in_track | 76 → 76 | 66 → 66 | 86.8% → 86.8% | 0.000000 | 72 → 72 | 94.7% → 94.7% | 0.000000 |
| september | by_mission | gracefo-c | September 2024 replay | 144 | cross | 76 → 76 | 10 → 10 | 13.2% → 13.2% | 0.000000 | 19 → 19 | 25.0% → 25.0% | 0.000000 |
| september | by_mission | gracefo-c | September 2024 replay | 168 | radial | 76 → 76 | 63 → 63 | 82.9% → 82.9% | 0.000000 | 73 → 73 | 96.1% → 96.1% | 0.000000 |
| september | by_mission | gracefo-c | September 2024 replay | 168 | in_track | 76 → 76 | 65 → 65 | 85.5% → 85.5% | 0.000000 | 72 → 72 | 94.7% → 94.7% | 0.000000 |
| september | by_mission | gracefo-c | September 2024 replay | 168 | cross | 76 → 76 | 29 → 29 | 38.2% → 38.2% | 0.000000 | 49 → 49 | 64.5% → 64.5% | 0.000000 |
| september | by_mission | gracefo-d | September 2024 replay | 6 | radial | 73 → 73 | 34 → 34 | 46.6% → 46.6% | 0.000000 | 56 → 56 | 76.7% → 76.7% | 0.000000 |
| september | by_mission | gracefo-d | September 2024 replay | 6 | in_track | 73 → 73 | 11 → 11 | 15.1% → 15.1% | 0.000000 | 22 → 22 | 30.1% → 30.1% | 0.000000 |
| september | by_mission | gracefo-d | September 2024 replay | 6 | cross | 73 → 73 | 1 → 1 | 1.4% → 1.4% | 0.000000 | 4 → 4 | 5.5% → 5.5% | 0.000000 |
| september | by_mission | gracefo-d | September 2024 replay | 12 | radial | 73 → 73 | 21 → 21 | 28.8% → 28.8% | 0.000000 | 31 → 31 | 42.5% → 42.5% | 0.000000 |
| september | by_mission | gracefo-d | September 2024 replay | 12 | in_track | 73 → 73 | 14 → 14 | 19.2% → 19.2% | 0.000000 | 32 → 32 | 43.8% → 43.8% | 0.000000 |
| september | by_mission | gracefo-d | September 2024 replay | 12 | cross | 73 → 73 | 3 → 3 | 4.1% → 4.1% | 0.000000 | 5 → 5 | 6.8% → 6.8% | 0.000000 |
| september | by_mission | gracefo-d | September 2024 replay | 24 | radial | 70 → 70 | 43 → 43 | 61.4% → 61.4% | 0.000000 | 70 → 70 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | gracefo-d | September 2024 replay | 24 | in_track | 70 → 70 | 51 → 51 | 72.9% → 72.9% | 0.000000 | 64 → 64 | 91.4% → 91.4% | 0.000000 |
| september | by_mission | gracefo-d | September 2024 replay | 24 | cross | 70 → 70 | 1 → 1 | 1.4% → 1.4% | 0.000000 | 8 → 8 | 11.4% → 11.4% | 0.000000 |
| september | by_mission | gracefo-d | September 2024 replay | 36 | radial | 70 → 70 | 29 → 29 | 41.4% → 41.4% | 0.000000 | 68 → 68 | 97.1% → 97.1% | 0.000000 |
| september | by_mission | gracefo-d | September 2024 replay | 36 | in_track | 70 → 70 | 60 → 60 | 85.7% → 85.7% | 0.000000 | 66 → 66 | 94.3% → 94.3% | 0.000000 |
| september | by_mission | gracefo-d | September 2024 replay | 36 | cross | 70 → 70 | 6 → 6 | 8.6% → 8.6% | 0.000000 | 16 → 16 | 22.9% → 22.9% | 0.000000 |
| september | by_mission | gracefo-d | September 2024 replay | 48 | radial | 68 → 68 | 48 → 48 | 70.6% → 70.6% | 0.000000 | 68 → 68 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | gracefo-d | September 2024 replay | 48 | in_track | 68 → 68 | 58 → 58 | 85.3% → 85.3% | 0.000000 | 65 → 65 | 95.6% → 95.6% | 0.000000 |
| september | by_mission | gracefo-d | September 2024 replay | 48 | cross | 68 → 68 | 5 → 5 | 7.4% → 7.4% | 0.000000 | 12 → 12 | 17.6% → 17.6% | 0.000000 |
| september | by_mission | gracefo-d | September 2024 replay | 72 | radial | 65 → 65 | 42 → 42 | 64.6% → 64.6% | 0.000000 | 65 → 65 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | gracefo-d | September 2024 replay | 72 | in_track | 65 → 65 | 56 → 56 | 86.2% → 86.2% | 0.000000 | 62 → 62 | 95.4% → 95.4% | 0.000000 |
| september | by_mission | gracefo-d | September 2024 replay | 72 | cross | 65 → 65 | 6 → 6 | 9.2% → 9.2% | 0.000000 | 10 → 10 | 15.4% → 15.4% | 0.000000 |
| september | by_mission | gracefo-d | September 2024 replay | 96 | radial | 62 → 62 | 60 → 60 | 96.8% → 96.8% | 0.000000 | 62 → 62 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | gracefo-d | September 2024 replay | 96 | in_track | 62 → 62 | 53 → 53 | 85.5% → 85.5% | 0.000000 | 59 → 59 | 95.2% → 95.2% | 0.000000 |
| september | by_mission | gracefo-d | September 2024 replay | 96 | cross | 62 → 62 | 8 → 8 | 12.9% → 12.9% | 0.000000 | 17 → 17 | 27.4% → 27.4% | 0.000000 |
| september | by_mission | gracefo-d | September 2024 replay | 120 | radial | 60 → 60 | 29 → 29 | 48.3% → 48.3% | 0.000000 | 60 → 60 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | gracefo-d | September 2024 replay | 120 | in_track | 60 → 60 | 52 → 52 | 86.7% → 86.7% | 0.000000 | 58 → 58 | 96.7% → 96.7% | 0.000000 |
| september | by_mission | gracefo-d | September 2024 replay | 120 | cross | 60 → 60 | 22 → 22 | 36.7% → 36.7% | 0.000000 | 33 → 33 | 55.0% → 55.0% | 0.000000 |
| september | by_mission | gracefo-d | September 2024 replay | 144 | radial | 58 → 58 | 56 → 56 | 96.6% → 96.6% | 0.000000 | 56 → 56 | 96.6% → 96.6% | 0.000000 |
| september | by_mission | gracefo-d | September 2024 replay | 144 | in_track | 58 → 58 | 49 → 49 | 84.5% → 84.5% | 0.000000 | 56 → 56 | 96.6% → 96.6% | 0.000000 |
| september | by_mission | gracefo-d | September 2024 replay | 144 | cross | 58 → 58 | 8 → 8 | 13.8% → 13.8% | 0.000000 | 15 → 15 | 25.9% → 25.9% | 0.000000 |
| september | by_mission | gracefo-d | September 2024 replay | 168 | radial | 55 → 55 | 46 → 46 | 83.6% → 83.6% | 0.000000 | 53 → 53 | 96.4% → 96.4% | 0.000000 |
| september | by_mission | gracefo-d | September 2024 replay | 168 | in_track | 55 → 55 | 45 → 45 | 81.8% → 81.8% | 0.000000 | 52 → 52 | 94.5% → 94.5% | 0.000000 |
| september | by_mission | gracefo-d | September 2024 replay | 168 | cross | 55 → 55 | 17 → 17 | 30.9% → 30.9% | 0.000000 | 29 → 29 | 52.7% → 52.7% | 0.000000 |
| september | by_mission | hy-2c | September 2024 replay | 6 | radial | 127 → 127 | 12 → 12 | 9.4% → 9.4% | 0.000000 | 29 → 29 | 22.8% → 22.8% | 0.000000 |
| september | by_mission | hy-2c | September 2024 replay | 6 | in_track | 127 → 127 | 34 → 34 | 26.8% → 26.8% | 0.000000 | 65 → 65 | 51.2% → 51.2% | 0.000000 |
| september | by_mission | hy-2c | September 2024 replay | 6 | cross | 127 → 127 | 33 → 33 | 26.0% → 26.0% | 0.000000 | 59 → 59 | 46.5% → 46.5% | 0.000000 |
| september | by_mission | hy-2c | September 2024 replay | 12 | radial | 126 → 126 | 29 → 29 | 23.0% → 23.0% | 0.000000 | 42 → 42 | 33.3% → 33.3% | 0.000000 |
| september | by_mission | hy-2c | September 2024 replay | 12 | in_track | 126 → 126 | 23 → 23 | 18.3% → 18.3% | 0.000000 | 46 → 46 | 36.5% → 36.5% | 0.000000 |
| september | by_mission | hy-2c | September 2024 replay | 12 | cross | 126 → 126 | 37 → 37 | 29.4% → 29.4% | 0.000000 | 61 → 61 | 48.4% → 48.4% | 0.000000 |
| september | by_mission | hy-2c | September 2024 replay | 24 | radial | 124 → 124 | 58 → 58 | 46.8% → 46.8% | 0.000000 | 96 → 96 | 77.4% → 77.4% | 0.000000 |
| september | by_mission | hy-2c | September 2024 replay | 24 | in_track | 124 → 124 | 97 → 97 | 78.2% → 78.2% | 0.000000 | 124 → 124 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | hy-2c | September 2024 replay | 24 | cross | 124 → 124 | 37 → 37 | 29.8% → 29.8% | 0.000000 | 84 → 84 | 67.7% → 67.7% | 0.000000 |
| september | by_mission | hy-2c | September 2024 replay | 36 | radial | 122 → 122 | 82 → 82 | 67.2% → 67.2% | 0.000000 | 122 → 122 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | hy-2c | September 2024 replay | 36 | in_track | 122 → 122 | 116 → 116 | 95.1% → 95.1% | 0.000000 | 122 → 122 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | hy-2c | September 2024 replay | 36 | cross | 122 → 122 | 48 → 48 | 39.3% → 39.3% | 0.000000 | 88 → 88 | 72.1% → 72.1% | 0.000000 |
| september | by_mission | hy-2c | September 2024 replay | 48 | radial | 119 → 119 | 90 → 90 | 75.6% → 75.6% | 0.000000 | 119 → 119 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | hy-2c | September 2024 replay | 48 | in_track | 119 → 119 | 119 → 119 | 100.0% → 100.0% | 0.000000 | 119 → 119 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | hy-2c | September 2024 replay | 48 | cross | 119 → 119 | 37 → 37 | 31.1% → 31.1% | 0.000000 | 95 → 95 | 79.8% → 79.8% | 0.000000 |
| september | by_mission | hy-2c | September 2024 replay | 72 | radial | 114 → 114 | 55 → 55 | 48.2% → 48.2% | 0.000000 | 110 → 110 | 96.5% → 96.5% | 0.000000 |
| september | by_mission | hy-2c | September 2024 replay | 72 | in_track | 114 → 114 | 114 → 114 | 100.0% → 100.0% | 0.000000 | 114 → 114 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | hy-2c | September 2024 replay | 72 | cross | 114 → 114 | 58 → 58 | 50.9% → 50.9% | 0.000000 | 114 → 114 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | hy-2c | September 2024 replay | 96 | radial | 109 → 109 | 82 → 82 | 75.2% → 75.2% | 0.000000 | 109 → 109 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | hy-2c | September 2024 replay | 96 | in_track | 109 → 109 | 109 → 109 | 100.0% → 100.0% | 0.000000 | 109 → 109 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | hy-2c | September 2024 replay | 96 | cross | 109 → 109 | 106 → 106 | 97.2% → 97.2% | 0.000000 | 109 → 109 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | hy-2c | September 2024 replay | 120 | radial | 104 → 104 | 104 → 104 | 100.0% → 100.0% | 0.000000 | 104 → 104 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | hy-2c | September 2024 replay | 120 | in_track | 104 → 104 | 104 → 104 | 100.0% → 100.0% | 0.000000 | 104 → 104 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | hy-2c | September 2024 replay | 120 | cross | 104 → 104 | 60 → 60 | 57.7% → 57.7% | 0.000000 | 104 → 104 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | hy-2c | September 2024 replay | 144 | radial | 100 → 100 | 40 → 40 | 40.0% → 40.0% | 0.000000 | 100 → 100 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | hy-2c | September 2024 replay | 144 | in_track | 100 → 100 | 100 → 100 | 100.0% → 100.0% | 0.000000 | 100 → 100 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | hy-2c | September 2024 replay | 144 | cross | 100 → 100 | 41 → 41 | 41.0% → 41.0% | 0.000000 | 100 → 100 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | hy-2c | September 2024 replay | 168 | radial | 96 → 96 | 92 → 92 | 95.8% → 95.8% | 0.000000 | 96 → 96 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | hy-2c | September 2024 replay | 168 | in_track | 96 → 96 | 96 → 96 | 100.0% → 100.0% | 0.000000 | 96 → 96 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | hy-2c | September 2024 replay | 168 | cross | 96 → 96 | 96 → 96 | 100.0% → 100.0% | 0.000000 | 96 → 96 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | hy-2d | September 2024 replay | 6 | radial | 128 → 128 | 10 → 10 | 7.8% → 7.8% | 0.000000 | 20 → 20 | 15.6% → 15.6% | 0.000000 |
| september | by_mission | hy-2d | September 2024 replay | 6 | in_track | 128 → 128 | 7 → 7 | 5.5% → 5.5% | 0.000000 | 15 → 15 | 11.7% → 11.7% | 0.000000 |
| september | by_mission | hy-2d | September 2024 replay | 6 | cross | 128 → 128 | 35 → 35 | 27.3% → 27.3% | 0.000000 | 55 → 55 | 43.0% → 43.0% | 0.000000 |
| september | by_mission | hy-2d | September 2024 replay | 12 | radial | 128 → 128 | 37 → 37 | 28.9% → 28.9% | 0.000000 | 52 → 52 | 40.6% → 40.6% | 0.000000 |
| september | by_mission | hy-2d | September 2024 replay | 12 | in_track | 128 → 128 | 5 → 5 | 3.9% → 3.9% | 0.000000 | 9 → 9 | 7.0% → 7.0% | 0.000000 |
| september | by_mission | hy-2d | September 2024 replay | 12 | cross | 128 → 128 | 27 → 27 | 21.1% → 21.1% | 0.000000 | 45 → 45 | 35.2% → 35.2% | 0.000000 |
| september | by_mission | hy-2d | September 2024 replay | 24 | radial | 128 → 128 | 70 → 70 | 54.7% → 54.7% | 0.000000 | 100 → 100 | 78.1% → 78.1% | 0.000000 |
| september | by_mission | hy-2d | September 2024 replay | 24 | in_track | 128 → 128 | 17 → 17 | 13.3% → 13.3% | 0.000000 | 51 → 51 | 39.8% → 39.8% | 0.000000 |
| september | by_mission | hy-2d | September 2024 replay | 24 | cross | 128 → 128 | 34 → 34 | 26.6% → 26.6% | 0.000000 | 79 → 79 | 61.7% → 61.7% | 0.000000 |
| september | by_mission | hy-2d | September 2024 replay | 36 | radial | 128 → 128 | 110 → 110 | 85.9% → 85.9% | 0.000000 | 128 → 128 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | hy-2d | September 2024 replay | 36 | in_track | 128 → 128 | 70 → 70 | 54.7% → 54.7% | 0.000000 | 111 → 111 | 86.7% → 86.7% | 0.000000 |
| september | by_mission | hy-2d | September 2024 replay | 36 | cross | 128 → 128 | 56 → 56 | 43.8% → 43.8% | 0.000000 | 96 → 96 | 75.0% → 75.0% | 0.000000 |
| september | by_mission | hy-2d | September 2024 replay | 48 | radial | 128 → 128 | 95 → 95 | 74.2% → 74.2% | 0.000000 | 128 → 128 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | hy-2d | September 2024 replay | 48 | in_track | 128 → 128 | 104 → 104 | 81.2% → 81.2% | 0.000000 | 126 → 126 | 98.4% → 98.4% | 0.000000 |
| september | by_mission | hy-2d | September 2024 replay | 48 | cross | 128 → 128 | 37 → 37 | 28.9% → 28.9% | 0.000000 | 109 → 109 | 85.2% → 85.2% | 0.000000 |
| september | by_mission | hy-2d | September 2024 replay | 72 | radial | 128 → 128 | 77 → 77 | 60.2% → 60.2% | 0.000000 | 128 → 128 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | hy-2d | September 2024 replay | 72 | in_track | 128 → 128 | 127 → 127 | 99.2% → 99.2% | 0.000000 | 128 → 128 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | hy-2d | September 2024 replay | 72 | cross | 128 → 128 | 46 → 46 | 35.9% → 35.9% | 0.000000 | 121 → 121 | 94.5% → 94.5% | 0.000000 |
| september | by_mission | hy-2d | September 2024 replay | 96 | radial | 128 → 128 | 128 → 128 | 100.0% → 100.0% | 0.000000 | 128 → 128 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | hy-2d | September 2024 replay | 96 | in_track | 128 → 128 | 128 → 128 | 100.0% → 100.0% | 0.000000 | 128 → 128 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | hy-2d | September 2024 replay | 96 | cross | 128 → 128 | 113 → 113 | 88.3% → 88.3% | 0.000000 | 128 → 128 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | hy-2d | September 2024 replay | 120 | radial | 128 → 128 | 128 → 128 | 100.0% → 100.0% | 0.000000 | 128 → 128 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | hy-2d | September 2024 replay | 120 | in_track | 128 → 128 | 128 → 128 | 100.0% → 100.0% | 0.000000 | 128 → 128 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | hy-2d | September 2024 replay | 120 | cross | 128 → 128 | 63 → 63 | 49.2% → 49.2% | 0.000000 | 128 → 128 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | hy-2d | September 2024 replay | 144 | radial | 128 → 128 | 81 → 81 | 63.3% → 63.3% | 0.000000 | 128 → 128 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | hy-2d | September 2024 replay | 144 | in_track | 128 → 128 | 128 → 128 | 100.0% → 100.0% | 0.000000 | 128 → 128 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | hy-2d | September 2024 replay | 144 | cross | 128 → 128 | 4 → 4 | 3.1% → 3.1% | 0.000000 | 128 → 128 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | hy-2d | September 2024 replay | 168 | radial | 128 → 128 | 128 → 128 | 100.0% → 100.0% | 0.000000 | 128 → 128 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | hy-2d | September 2024 replay | 168 | in_track | 128 → 128 | 128 → 128 | 100.0% → 100.0% | 0.000000 | 128 → 128 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | hy-2d | September 2024 replay | 168 | cross | 128 → 128 | 127 → 127 | 99.2% → 99.2% | 0.000000 | 128 → 128 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | jason-3 | September 2024 replay | 6 | radial | 76 → 76 | 26 → 26 | 34.2% → 34.2% | 0.000000 | 47 → 47 | 61.8% → 61.8% | 0.000000 |
| september | by_mission | jason-3 | September 2024 replay | 6 | in_track | 76 → 76 | 10 → 10 | 13.2% → 13.2% | 0.000000 | 22 → 22 | 28.9% → 28.9% | 0.000000 |
| september | by_mission | jason-3 | September 2024 replay | 6 | cross | 76 → 76 | 10 → 10 | 13.2% → 13.2% | 0.000000 | 27 → 27 | 35.5% → 35.5% | 0.000000 |
| september | by_mission | jason-3 | September 2024 replay | 12 | radial | 76 → 76 | 4 → 4 | 5.3% → 5.3% | 0.000000 | 8 → 8 | 10.5% → 10.5% | 0.000000 |
| september | by_mission | jason-3 | September 2024 replay | 12 | in_track | 76 → 76 | 18 → 18 | 23.7% → 23.7% | 0.000000 | 27 → 27 | 35.5% → 35.5% | 0.000000 |
| september | by_mission | jason-3 | September 2024 replay | 12 | cross | 76 → 76 | 10 → 10 | 13.2% → 13.2% | 0.000000 | 16 → 16 | 21.1% → 21.1% | 0.000000 |
| september | by_mission | jason-3 | September 2024 replay | 24 | radial | 76 → 76 | 26 → 26 | 34.2% → 34.2% | 0.000000 | 48 → 48 | 63.2% → 63.2% | 0.000000 |
| september | by_mission | jason-3 | September 2024 replay | 24 | in_track | 76 → 76 | 32 → 32 | 42.1% → 42.1% | 0.000000 | 69 → 69 | 90.8% → 90.8% | 0.000000 |
| september | by_mission | jason-3 | September 2024 replay | 24 | cross | 76 → 76 | 20 → 20 | 26.3% → 26.3% | 0.000000 | 45 → 45 | 59.2% → 59.2% | 0.000000 |
| september | by_mission | jason-3 | September 2024 replay | 36 | radial | 76 → 76 | 64 → 64 | 84.2% → 84.2% | 0.000000 | 76 → 76 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | jason-3 | September 2024 replay | 36 | in_track | 76 → 76 | 46 → 46 | 60.5% → 60.5% | 0.000000 | 76 → 76 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | jason-3 | September 2024 replay | 36 | cross | 76 → 76 | 29 → 29 | 38.2% → 38.2% | 0.000000 | 47 → 47 | 61.8% → 61.8% | 0.000000 |
| september | by_mission | jason-3 | September 2024 replay | 48 | radial | 76 → 76 | 21 → 21 | 27.6% → 27.6% | 0.000000 | 76 → 76 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | jason-3 | September 2024 replay | 48 | in_track | 76 → 76 | 74 → 74 | 97.4% → 97.4% | 0.000000 | 76 → 76 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | jason-3 | September 2024 replay | 48 | cross | 76 → 76 | 15 → 15 | 19.7% → 19.7% | 0.000000 | 60 → 60 | 78.9% → 78.9% | 0.000000 |
| september | by_mission | jason-3 | September 2024 replay | 72 | radial | 75 → 75 | 37 → 37 | 49.3% → 49.3% | 0.000000 | 61 → 61 | 81.3% → 81.3% | 0.000000 |
| september | by_mission | jason-3 | September 2024 replay | 72 | in_track | 75 → 75 | 75 → 75 | 100.0% → 100.0% | 0.000000 | 75 → 75 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | jason-3 | September 2024 replay | 72 | cross | 75 → 75 | 56 → 56 | 74.7% → 74.7% | 0.000000 | 75 → 75 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | jason-3 | September 2024 replay | 96 | radial | 72 → 72 | 72 → 72 | 100.0% → 100.0% | 0.000000 | 72 → 72 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | jason-3 | September 2024 replay | 96 | in_track | 72 → 72 | 72 → 72 | 100.0% → 100.0% | 0.000000 | 72 → 72 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | jason-3 | September 2024 replay | 96 | cross | 72 → 72 | 48 → 48 | 66.7% → 66.7% | 0.000000 | 72 → 72 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | jason-3 | September 2024 replay | 120 | radial | 69 → 69 | 36 → 36 | 52.2% → 52.2% | 0.000000 | 69 → 69 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | jason-3 | September 2024 replay | 120 | in_track | 69 → 69 | 69 → 69 | 100.0% → 100.0% | 0.000000 | 69 → 69 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | jason-3 | September 2024 replay | 120 | cross | 69 → 69 | 11 → 11 | 15.9% → 15.9% | 0.000000 | 69 → 69 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | jason-3 | September 2024 replay | 144 | radial | 67 → 67 | 38 → 38 | 56.7% → 56.7% | 0.000000 | 67 → 67 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | jason-3 | September 2024 replay | 144 | in_track | 67 → 67 | 67 → 67 | 100.0% → 100.0% | 0.000000 | 67 → 67 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | jason-3 | September 2024 replay | 144 | cross | 67 → 67 | 67 → 67 | 100.0% → 100.0% | 0.000000 | 67 → 67 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | jason-3 | September 2024 replay | 168 | radial | 63 → 63 | 63 → 63 | 100.0% → 100.0% | 0.000000 | 63 → 63 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | jason-3 | September 2024 replay | 168 | in_track | 63 → 63 | 63 → 63 | 100.0% → 100.0% | 0.000000 | 63 → 63 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | jason-3 | September 2024 replay | 168 | cross | 63 → 63 | 42 → 42 | 66.7% → 66.7% | 0.000000 | 63 → 63 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | saral | September 2024 replay | 6 | radial | 73 → 73 | 4 → 4 | 5.5% → 5.5% | 0.000000 | 22 → 22 | 30.1% → 30.1% | 0.000000 |
| september | by_mission | saral | September 2024 replay | 6 | in_track | 73 → 73 | 12 → 12 | 16.4% → 16.4% | 0.000000 | 19 → 19 | 26.0% → 26.0% | 0.000000 |
| september | by_mission | saral | September 2024 replay | 6 | cross | 73 → 73 | 4 → 4 | 5.5% → 5.5% | 0.000000 | 6 → 6 | 8.2% → 8.2% | 0.000000 |
| september | by_mission | saral | September 2024 replay | 12 | radial | 73 → 73 | 2 → 2 | 2.7% → 2.7% | 0.000000 | 5 → 5 | 6.8% → 6.8% | 0.000000 |
| september | by_mission | saral | September 2024 replay | 12 | in_track | 73 → 73 | 15 → 15 | 20.5% → 20.5% | 0.000000 | 28 → 28 | 38.4% → 38.4% | 0.000000 |
| september | by_mission | saral | September 2024 replay | 12 | cross | 73 → 73 | 4 → 4 | 5.5% → 5.5% | 0.000000 | 5 → 5 | 6.8% → 6.8% | 0.000000 |
| september | by_mission | saral | September 2024 replay | 24 | radial | 73 → 73 | 52 → 52 | 71.2% → 71.2% | 0.000000 | 73 → 73 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | saral | September 2024 replay | 24 | in_track | 73 → 73 | 32 → 32 | 43.8% → 43.8% | 0.000000 | 55 → 55 | 75.3% → 75.3% | 0.000000 |
| september | by_mission | saral | September 2024 replay | 24 | cross | 73 → 73 | 2 → 2 | 2.7% → 2.7% | 0.000000 | 6 → 6 | 8.2% → 8.2% | 0.000000 |
| september | by_mission | saral | September 2024 replay | 36 | radial | 73 → 73 | 27 → 27 | 37.0% → 37.0% | 0.000000 | 39 → 39 | 53.4% → 53.4% | 0.000000 |
| september | by_mission | saral | September 2024 replay | 36 | in_track | 73 → 73 | 29 → 29 | 39.7% → 39.7% | 0.000000 | 52 → 52 | 71.2% → 71.2% | 0.000000 |
| september | by_mission | saral | September 2024 replay | 36 | cross | 73 → 73 | 18 → 18 | 24.7% → 24.7% | 0.000000 | 28 → 28 | 38.4% → 38.4% | 0.000000 |
| september | by_mission | saral | September 2024 replay | 48 | radial | 73 → 73 | 33 → 33 | 45.2% → 45.2% | 0.000000 | 67 → 67 | 91.8% → 91.8% | 0.000000 |
| september | by_mission | saral | September 2024 replay | 48 | in_track | 73 → 73 | 41 → 41 | 56.2% → 56.2% | 0.000000 | 69 → 69 | 94.5% → 94.5% | 0.000000 |
| september | by_mission | saral | September 2024 replay | 48 | cross | 73 → 73 | 7 → 7 | 9.6% → 9.6% | 0.000000 | 16 → 16 | 21.9% → 21.9% | 0.000000 |
| september | by_mission | saral | September 2024 replay | 72 | radial | 73 → 73 | 38 → 38 | 52.1% → 52.1% | 0.000000 | 73 → 73 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | saral | September 2024 replay | 72 | in_track | 73 → 73 | 54 → 54 | 74.0% → 74.0% | 0.000000 | 70 → 70 | 95.9% → 95.9% | 0.000000 |
| september | by_mission | saral | September 2024 replay | 72 | cross | 73 → 73 | 14 → 14 | 19.2% → 19.2% | 0.000000 | 26 → 26 | 35.6% → 35.6% | 0.000000 |
| september | by_mission | saral | September 2024 replay | 96 | radial | 73 → 73 | 73 → 73 | 100.0% → 100.0% | 0.000000 | 73 → 73 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | saral | September 2024 replay | 96 | in_track | 73 → 73 | 59 → 59 | 80.8% → 80.8% | 0.000000 | 70 → 70 | 95.9% → 95.9% | 0.000000 |
| september | by_mission | saral | September 2024 replay | 96 | cross | 73 → 73 | 13 → 13 | 17.8% → 17.8% | 0.000000 | 24 → 24 | 32.9% → 32.9% | 0.000000 |
| september | by_mission | saral | September 2024 replay | 120 | radial | 73 → 73 | 68 → 68 | 93.2% → 93.2% | 0.000000 | 73 → 73 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | saral | September 2024 replay | 120 | in_track | 73 → 73 | 56 → 56 | 76.7% → 76.7% | 0.000000 | 70 → 70 | 95.9% → 95.9% | 0.000000 |
| september | by_mission | saral | September 2024 replay | 120 | cross | 73 → 73 | 9 → 9 | 12.3% → 12.3% | 0.000000 | 20 → 20 | 27.4% → 27.4% | 0.000000 |
| september | by_mission | saral | September 2024 replay | 144 | radial | 73 → 73 | 46 → 46 | 63.0% → 63.0% | 0.000000 | 73 → 73 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | saral | September 2024 replay | 144 | in_track | 73 → 73 | 52 → 52 | 71.2% → 71.2% | 0.000000 | 69 → 69 | 94.5% → 94.5% | 0.000000 |
| september | by_mission | saral | September 2024 replay | 144 | cross | 73 → 73 | 23 → 23 | 31.5% → 31.5% | 0.000000 | 50 → 50 | 68.5% → 68.5% | 0.000000 |
| september | by_mission | saral | September 2024 replay | 168 | radial | 73 → 73 | 73 → 73 | 100.0% → 100.0% | 0.000000 | 73 → 73 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | saral | September 2024 replay | 168 | in_track | 73 → 73 | 42 → 42 | 57.5% → 57.5% | 0.000000 | 65 → 65 | 89.0% → 89.0% | 0.000000 |
| september | by_mission | saral | September 2024 replay | 168 | cross | 73 → 73 | 17 → 17 | 23.3% → 23.3% | 0.000000 | 33 → 33 | 45.2% → 45.2% | 0.000000 |
| september | by_mission | sentinel-3a | September 2024 replay | 6 | radial | 121 → 121 | 5 → 5 | 4.1% → 4.1% | 0.000000 | 17 → 17 | 14.0% → 14.0% | 0.000000 |
| september | by_mission | sentinel-3a | September 2024 replay | 6 | in_track | 121 → 121 | 21 → 21 | 17.4% → 17.4% | 0.000000 | 56 → 56 | 46.3% → 46.3% | 0.000000 |
| september | by_mission | sentinel-3a | September 2024 replay | 6 | cross | 121 → 121 | 13 → 13 | 10.7% → 10.7% | 0.000000 | 30 → 30 | 24.8% → 24.8% | 0.000000 |
| september | by_mission | sentinel-3a | September 2024 replay | 12 | radial | 116 → 116 | 15 → 15 | 12.9% → 12.9% | 0.000000 | 26 → 26 | 22.4% → 22.4% | 0.000000 |
| september | by_mission | sentinel-3a | September 2024 replay | 12 | in_track | 116 → 116 | 72 → 72 | 62.1% → 62.1% | 0.000000 | 107 → 107 | 92.2% → 92.2% | 0.000000 |
| september | by_mission | sentinel-3a | September 2024 replay | 12 | cross | 116 → 116 | 7 → 7 | 6.0% → 6.0% | 0.000000 | 16 → 16 | 13.8% → 13.8% | 0.000000 |
| september | by_mission | sentinel-3a | September 2024 replay | 24 | radial | 109 → 109 | 81 → 81 | 74.3% → 74.3% | 0.000000 | 89 → 89 | 81.7% → 81.7% | 0.000000 |
| september | by_mission | sentinel-3a | September 2024 replay | 24 | in_track | 109 → 109 | 79 → 79 | 72.5% → 72.5% | 0.000000 | 106 → 106 | 97.2% → 97.2% | 0.000000 |
| september | by_mission | sentinel-3a | September 2024 replay | 24 | cross | 109 → 109 | 10 → 10 | 9.2% → 9.2% | 0.000000 | 26 → 26 | 23.9% → 23.9% | 0.000000 |
| september | by_mission | sentinel-3a | September 2024 replay | 36 | radial | 103 → 103 | 59 → 59 | 57.3% → 57.3% | 0.000000 | 70 → 70 | 68.0% → 68.0% | 0.000000 |
| september | by_mission | sentinel-3a | September 2024 replay | 36 | in_track | 103 → 103 | 101 → 101 | 98.1% → 98.1% | 0.000000 | 103 → 103 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | sentinel-3a | September 2024 replay | 36 | cross | 103 → 103 | 18 → 18 | 17.5% → 17.5% | 0.000000 | 44 → 44 | 42.7% → 42.7% | 0.000000 |
| september | by_mission | sentinel-3a | September 2024 replay | 48 | radial | 98 → 98 | 31 → 31 | 31.6% → 31.6% | 0.000000 | 76 → 76 | 77.6% → 77.6% | 0.000000 |
| september | by_mission | sentinel-3a | September 2024 replay | 48 | in_track | 98 → 98 | 97 → 97 | 99.0% → 99.0% | 0.000000 | 98 → 98 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | sentinel-3a | September 2024 replay | 48 | cross | 98 → 98 | 42 → 42 | 42.9% → 42.9% | 0.000000 | 76 → 76 | 77.6% → 77.6% | 0.000000 |
| september | by_mission | sentinel-3a | September 2024 replay | 72 | radial | 89 → 89 | 87 → 87 | 97.8% → 97.8% | 0.000000 | 89 → 89 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | sentinel-3a | September 2024 replay | 72 | in_track | 89 → 89 | 89 → 89 | 100.0% → 100.0% | 0.000000 | 89 → 89 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | sentinel-3a | September 2024 replay | 72 | cross | 89 → 89 | 26 → 26 | 29.2% → 29.2% | 0.000000 | 53 → 53 | 59.6% → 59.6% | 0.000000 |
| september | by_mission | sentinel-3a | September 2024 replay | 96 | radial | 80 → 80 | 39 → 39 | 48.8% → 48.8% | 0.000000 | 80 → 80 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | sentinel-3a | September 2024 replay | 96 | in_track | 80 → 80 | 80 → 80 | 100.0% → 100.0% | 0.000000 | 80 → 80 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | sentinel-3a | September 2024 replay | 96 | cross | 80 → 80 | 58 → 58 | 72.5% → 72.5% | 0.000000 | 69 → 69 | 86.2% → 86.2% | 0.000000 |
| september | by_mission | sentinel-3a | September 2024 replay | 120 | radial | 73 → 73 | 73 → 73 | 100.0% → 100.0% | 0.000000 | 73 → 73 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | sentinel-3a | September 2024 replay | 120 | in_track | 73 → 73 | 73 → 73 | 100.0% → 100.0% | 0.000000 | 73 → 73 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | sentinel-3a | September 2024 replay | 120 | cross | 73 → 73 | 34 → 34 | 46.6% → 46.6% | 0.000000 | 69 → 69 | 94.5% → 94.5% | 0.000000 |
| september | by_mission | sentinel-3a | September 2024 replay | 144 | radial | 60 → 60 | 36 → 36 | 60.0% → 60.0% | 0.000000 | 60 → 60 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | sentinel-3a | September 2024 replay | 144 | in_track | 60 → 60 | 60 → 60 | 100.0% → 100.0% | 0.000000 | 60 → 60 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | sentinel-3a | September 2024 replay | 144 | cross | 60 → 60 | 46 → 46 | 76.7% → 76.7% | 0.000000 | 57 → 57 | 95.0% → 95.0% | 0.000000 |
| september | by_mission | sentinel-3a | September 2024 replay | 168 | radial | 50 → 50 | 50 → 50 | 100.0% → 100.0% | 0.000000 | 50 → 50 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | sentinel-3a | September 2024 replay | 168 | in_track | 50 → 50 | 50 → 50 | 100.0% → 100.0% | 0.000000 | 50 → 50 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | sentinel-3a | September 2024 replay | 168 | cross | 50 → 50 | 37 → 37 | 74.0% → 74.0% | 0.000000 | 50 → 50 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | sentinel-3b | September 2024 replay | 6 | radial | 51 → 51 | 12 → 12 | 23.5% → 23.5% | 0.000000 | 18 → 18 | 35.3% → 35.3% | 0.000000 |
| september | by_mission | sentinel-3b | September 2024 replay | 6 | in_track | 51 → 51 | 27 → 27 | 52.9% → 52.9% | 0.000000 | 43 → 43 | 84.3% → 84.3% | 0.000000 |
| september | by_mission | sentinel-3b | September 2024 replay | 6 | cross | 51 → 51 | 7 → 7 | 13.7% → 13.7% | 0.000000 | 9 → 9 | 17.6% → 17.6% | 0.000000 |
| september | by_mission | sentinel-3b | September 2024 replay | 12 | radial | 49 → 49 | 10 → 10 | 20.4% → 20.4% | 0.000000 | 18 → 18 | 36.7% → 36.7% | 0.000000 |
| september | by_mission | sentinel-3b | September 2024 replay | 12 | in_track | 49 → 49 | 40 → 40 | 81.6% → 81.6% | 0.000000 | 47 → 47 | 95.9% → 95.9% | 0.000000 |
| september | by_mission | sentinel-3b | September 2024 replay | 12 | cross | 49 → 49 | 5 → 5 | 10.2% → 10.2% | 0.000000 | 6 → 6 | 12.2% → 12.2% | 0.000000 |
| september | by_mission | sentinel-3b | September 2024 replay | 24 | radial | 44 → 44 | 24 → 24 | 54.5% → 54.5% | 0.000000 | 34 → 34 | 77.3% → 77.3% | 0.000000 |
| september | by_mission | sentinel-3b | September 2024 replay | 24 | in_track | 44 → 44 | 41 → 41 | 93.2% → 93.2% | 0.000000 | 43 → 43 | 97.7% → 97.7% | 0.000000 |
| september | by_mission | sentinel-3b | September 2024 replay | 24 | cross | 44 → 44 | 4 → 4 | 9.1% → 9.1% | 0.000000 | 7 → 7 | 15.9% → 15.9% | 0.000000 |
| september | by_mission | sentinel-3b | September 2024 replay | 36 | radial | 42 → 42 | 19 → 19 | 45.2% → 45.2% | 0.000000 | 24 → 24 | 57.1% → 57.1% | 0.000000 |
| september | by_mission | sentinel-3b | September 2024 replay | 36 | in_track | 42 → 42 | 40 → 40 | 95.2% → 95.2% | 0.000000 | 42 → 42 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | sentinel-3b | September 2024 replay | 36 | cross | 42 → 42 | 6 → 6 | 14.3% → 14.3% | 0.000000 | 19 → 19 | 45.2% → 45.2% | 0.000000 |
| september | by_mission | sentinel-3b | September 2024 replay | 48 | radial | 38 → 38 | 15 → 15 | 39.5% → 39.5% | 0.000000 | 29 → 29 | 76.3% → 76.3% | 0.000000 |
| september | by_mission | sentinel-3b | September 2024 replay | 48 | in_track | 38 → 38 | 38 → 38 | 100.0% → 100.0% | 0.000000 | 38 → 38 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | sentinel-3b | September 2024 replay | 48 | cross | 38 → 38 | 22 → 22 | 57.9% → 57.9% | 0.000000 | 32 → 32 | 84.2% → 84.2% | 0.000000 |
| september | by_mission | sentinel-3b | September 2024 replay | 72 | radial | 32 → 32 | 30 → 30 | 93.8% → 93.8% | 0.000000 | 32 → 32 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | sentinel-3b | September 2024 replay | 72 | in_track | 32 → 32 | 32 → 32 | 100.0% → 100.0% | 0.000000 | 32 → 32 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | sentinel-3b | September 2024 replay | 72 | cross | 32 → 32 | 9 → 9 | 28.1% → 28.1% | 0.000000 | 19 → 19 | 59.4% → 59.4% | 0.000000 |
| september | by_mission | sentinel-3b | September 2024 replay | 96 | radial | 26 → 26 | 14 → 14 | 53.8% → 53.8% | 0.000000 | 26 → 26 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | sentinel-3b | September 2024 replay | 96 | in_track | 26 → 26 | 26 → 26 | 100.0% → 100.0% | 0.000000 | 26 → 26 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | sentinel-3b | September 2024 replay | 96 | cross | 26 → 26 | 22 → 22 | 84.6% → 84.6% | 0.000000 | 24 → 24 | 92.3% → 92.3% | 0.000000 |
| september | by_mission | sentinel-3b | September 2024 replay | 120 | radial | 20 → 20 | 20 → 20 | 100.0% → 100.0% | 0.000000 | 20 → 20 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | sentinel-3b | September 2024 replay | 120 | in_track | 20 → 20 | 20 → 20 | 100.0% → 100.0% | 0.000000 | 20 → 20 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | sentinel-3b | September 2024 replay | 120 | cross | 20 → 20 | 11 → 11 | 55.0% → 55.0% | 0.000000 | 19 → 19 | 95.0% → 95.0% | 0.000000 |
| september | by_mission | sentinel-3b | September 2024 replay | 144 | radial | 18 → 18 | 13 → 13 | 72.2% → 72.2% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | sentinel-3b | September 2024 replay | 144 | in_track | 18 → 18 | 18 → 18 | 100.0% → 100.0% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | sentinel-3b | September 2024 replay | 144 | cross | 18 → 18 | 14 → 14 | 77.8% → 77.8% | 0.000000 | 18 → 18 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | sentinel-3b | September 2024 replay | 168 | radial | 14 → 14 | 14 → 14 | 100.0% → 100.0% | 0.000000 | 14 → 14 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | sentinel-3b | September 2024 replay | 168 | in_track | 14 → 14 | 14 → 14 | 100.0% → 100.0% | 0.000000 | 14 → 14 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | sentinel-3b | September 2024 replay | 168 | cross | 14 → 14 | 11 → 11 | 78.6% → 78.6% | 0.000000 | 14 → 14 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | sentinel-6a | September 2024 replay | 6 | radial | 57 → 57 | 17 → 17 | 29.8% → 29.8% | 0.000000 | 43 → 43 | 75.4% → 75.4% | 0.000000 |
| september | by_mission | sentinel-6a | September 2024 replay | 6 | in_track | 57 → 57 | 4 → 4 | 7.0% → 7.0% | 0.000000 | 5 → 5 | 8.8% → 8.8% | 0.000000 |
| september | by_mission | sentinel-6a | September 2024 replay | 6 | cross | 57 → 57 | 19 → 19 | 33.3% → 33.3% | 0.000000 | 35 → 35 | 61.4% → 61.4% | 0.000000 |
| september | by_mission | sentinel-6a | September 2024 replay | 12 | radial | 55 → 55 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| september | by_mission | sentinel-6a | September 2024 replay | 12 | in_track | 55 → 55 | 3 → 3 | 5.5% → 5.5% | 0.000000 | 4 → 4 | 7.3% → 7.3% | 0.000000 |
| september | by_mission | sentinel-6a | September 2024 replay | 12 | cross | 55 → 55 | 12 → 12 | 21.8% → 21.8% | 0.000000 | 31 → 31 | 56.4% → 56.4% | 0.000000 |
| september | by_mission | sentinel-6a | September 2024 replay | 24 | radial | 55 → 55 | 22 → 22 | 40.0% → 40.0% | 0.000000 | 44 → 44 | 80.0% → 80.0% | 0.000000 |
| september | by_mission | sentinel-6a | September 2024 replay | 24 | in_track | 55 → 55 | 1 → 1 | 1.8% → 1.8% | 0.000000 | 1 → 1 | 1.8% → 1.8% | 0.000000 |
| september | by_mission | sentinel-6a | September 2024 replay | 24 | cross | 55 → 55 | 15 → 15 | 27.3% → 27.3% | 0.000000 | 45 → 45 | 81.8% → 81.8% | 0.000000 |
| september | by_mission | sentinel-6a | September 2024 replay | 36 | radial | 54 → 54 | 43 → 43 | 79.6% → 79.6% | 0.000000 | 54 → 54 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | sentinel-6a | September 2024 replay | 36 | in_track | 54 → 54 | 1 → 1 | 1.9% → 1.9% | 0.000000 | 2 → 2 | 3.7% → 3.7% | 0.000000 |
| september | by_mission | sentinel-6a | September 2024 replay | 36 | cross | 54 → 54 | 18 → 18 | 33.3% → 33.3% | 0.000000 | 37 → 37 | 68.5% → 68.5% | 0.000000 |
| september | by_mission | sentinel-6a | September 2024 replay | 48 | radial | 53 → 53 | 33 → 33 | 62.3% → 62.3% | 0.000000 | 53 → 53 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | sentinel-6a | September 2024 replay | 48 | in_track | 53 → 53 | 2 → 2 | 3.8% → 3.8% | 0.000000 | 7 → 7 | 13.2% → 13.2% | 0.000000 |
| september | by_mission | sentinel-6a | September 2024 replay | 48 | cross | 53 → 53 | 9 → 9 | 17.0% → 17.0% | 0.000000 | 43 → 43 | 81.1% → 81.1% | 0.000000 |
| september | by_mission | sentinel-6a | September 2024 replay | 72 | radial | 52 → 52 | 47 → 47 | 90.4% → 90.4% | 0.000000 | 52 → 52 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | sentinel-6a | September 2024 replay | 72 | in_track | 52 → 52 | 8 → 8 | 15.4% → 15.4% | 0.000000 | 10 → 10 | 19.2% → 19.2% | 0.000000 |
| september | by_mission | sentinel-6a | September 2024 replay | 72 | cross | 52 → 52 | 42 → 42 | 80.8% → 80.8% | 0.000000 | 52 → 52 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | sentinel-6a | September 2024 replay | 96 | radial | 50 → 50 | 50 → 50 | 100.0% → 100.0% | 0.000000 | 50 → 50 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | sentinel-6a | September 2024 replay | 96 | in_track | 50 → 50 | 5 → 5 | 10.0% → 10.0% | 0.000000 | 5 → 5 | 10.0% → 10.0% | 0.000000 |
| september | by_mission | sentinel-6a | September 2024 replay | 96 | cross | 50 → 50 | 36 → 36 | 72.0% → 72.0% | 0.000000 | 50 → 50 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | sentinel-6a | September 2024 replay | 120 | radial | 49 → 49 | 38 → 38 | 77.6% → 77.6% | 0.000000 | 49 → 49 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | sentinel-6a | September 2024 replay | 120 | in_track | 49 → 49 | 3 → 3 | 6.1% → 6.1% | 0.000000 | 11 → 11 | 22.4% → 22.4% | 0.000000 |
| september | by_mission | sentinel-6a | September 2024 replay | 120 | cross | 49 → 49 | 8 → 8 | 16.3% → 16.3% | 0.000000 | 49 → 49 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | sentinel-6a | September 2024 replay | 144 | radial | 46 → 46 | 41 → 41 | 89.1% → 89.1% | 0.000000 | 46 → 46 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | sentinel-6a | September 2024 replay | 144 | in_track | 46 → 46 | 16 → 16 | 34.8% → 34.8% | 0.000000 | 26 → 26 | 56.5% → 56.5% | 0.000000 |
| september | by_mission | sentinel-6a | September 2024 replay | 144 | cross | 46 → 46 | 46 → 46 | 100.0% → 100.0% | 0.000000 | 46 → 46 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | sentinel-6a | September 2024 replay | 168 | radial | 43 → 43 | 43 → 43 | 100.0% → 100.0% | 0.000000 | 43 → 43 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | sentinel-6a | September 2024 replay | 168 | in_track | 43 → 43 | 9 → 9 | 20.9% → 20.9% | 0.000000 | 21 → 21 | 48.8% → 48.8% | 0.000000 |
| september | by_mission | sentinel-6a | September 2024 replay | 168 | cross | 43 → 43 | 31 → 31 | 72.1% → 72.1% | 0.000000 | 43 → 43 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | swarm-a | September 2024 replay | 6 | radial | 75 → 75 | 10 → 10 | 13.3% → 13.3% | 0.000000 | 38 → 38 | 50.7% → 50.7% | 0.000000 |
| september | by_mission | swarm-a | September 2024 replay | 6 | in_track | 75 → 75 | 19 → 19 | 25.3% → 25.3% | 0.000000 | 54 → 54 | 72.0% → 72.0% | 0.000000 |
| september | by_mission | swarm-a | September 2024 replay | 6 | cross | 75 → 75 | 2 → 2 | 2.7% → 2.7% | 0.000000 | 5 → 5 | 6.7% → 6.7% | 0.000000 |
| september | by_mission | swarm-a | September 2024 replay | 12 | radial | 75 → 75 | 22 → 22 | 29.3% → 29.3% | 0.000000 | 32 → 32 | 42.7% → 42.7% | 0.000000 |
| september | by_mission | swarm-a | September 2024 replay | 12 | in_track | 75 → 75 | 26 → 26 | 34.7% → 34.7% | 0.000000 | 43 → 43 | 57.3% → 57.3% | 0.000000 |
| september | by_mission | swarm-a | September 2024 replay | 12 | cross | 75 → 75 | 1 → 1 | 1.3% → 1.3% | 0.000000 | 1 → 1 | 1.3% → 1.3% | 0.000000 |
| september | by_mission | swarm-a | September 2024 replay | 24 | radial | 75 → 75 | 38 → 38 | 50.7% → 50.7% | 0.000000 | 70 → 70 | 93.3% → 93.3% | 0.000000 |
| september | by_mission | swarm-a | September 2024 replay | 24 | in_track | 75 → 75 | 59 → 59 | 78.7% → 78.7% | 0.000000 | 69 → 69 | 92.0% → 92.0% | 0.000000 |
| september | by_mission | swarm-a | September 2024 replay | 24 | cross | 75 → 75 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 3 → 3 | 4.0% → 4.0% | 0.000000 |
| september | by_mission | swarm-a | September 2024 replay | 36 | radial | 75 → 75 | 15 → 15 | 20.0% → 20.0% | 0.000000 | 63 → 63 | 84.0% → 84.0% | 0.000000 |
| september | by_mission | swarm-a | September 2024 replay | 36 | in_track | 75 → 75 | 64 → 64 | 85.3% → 85.3% | 0.000000 | 69 → 69 | 92.0% → 92.0% | 0.000000 |
| september | by_mission | swarm-a | September 2024 replay | 36 | cross | 75 → 75 | 11 → 11 | 14.7% → 14.7% | 0.000000 | 25 → 25 | 33.3% → 33.3% | 0.000000 |
| september | by_mission | swarm-a | September 2024 replay | 48 | radial | 75 → 75 | 72 → 72 | 96.0% → 96.0% | 0.000000 | 75 → 75 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | swarm-a | September 2024 replay | 48 | in_track | 75 → 75 | 62 → 62 | 82.7% → 82.7% | 0.000000 | 70 → 70 | 93.3% → 93.3% | 0.000000 |
| september | by_mission | swarm-a | September 2024 replay | 48 | cross | 75 → 75 | 3 → 3 | 4.0% → 4.0% | 0.000000 | 3 → 3 | 4.0% → 4.0% | 0.000000 |
| september | by_mission | swarm-a | September 2024 replay | 72 | radial | 75 → 75 | 38 → 38 | 50.7% → 50.7% | 0.000000 | 73 → 73 | 97.3% → 97.3% | 0.000000 |
| september | by_mission | swarm-a | September 2024 replay | 72 | in_track | 75 → 75 | 60 → 60 | 80.0% → 80.0% | 0.000000 | 71 → 71 | 94.7% → 94.7% | 0.000000 |
| september | by_mission | swarm-a | September 2024 replay | 72 | cross | 75 → 75 | 24 → 24 | 32.0% → 32.0% | 0.000000 | 39 → 39 | 52.0% → 52.0% | 0.000000 |
| september | by_mission | swarm-a | September 2024 replay | 96 | radial | 75 → 75 | 72 → 72 | 96.0% → 96.0% | 0.000000 | 74 → 74 | 98.7% → 98.7% | 0.000000 |
| september | by_mission | swarm-a | September 2024 replay | 96 | in_track | 75 → 75 | 60 → 60 | 80.0% → 80.0% | 0.000000 | 71 → 71 | 94.7% → 94.7% | 0.000000 |
| september | by_mission | swarm-a | September 2024 replay | 96 | cross | 75 → 75 | 15 → 15 | 20.0% → 20.0% | 0.000000 | 25 → 25 | 33.3% → 33.3% | 0.000000 |
| september | by_mission | swarm-a | September 2024 replay | 120 | radial | 75 → 75 | 72 → 72 | 96.0% → 96.0% | 0.000000 | 73 → 73 | 97.3% → 97.3% | 0.000000 |
| september | by_mission | swarm-a | September 2024 replay | 120 | in_track | 75 → 75 | 61 → 61 | 81.3% → 81.3% | 0.000000 | 71 → 71 | 94.7% → 94.7% | 0.000000 |
| september | by_mission | swarm-a | September 2024 replay | 120 | cross | 75 → 75 | 10 → 10 | 13.3% → 13.3% | 0.000000 | 21 → 21 | 28.0% → 28.0% | 0.000000 |
| september | by_mission | swarm-a | September 2024 replay | 144 | radial | 75 → 75 | 61 → 62 | 81.3% → 82.7% | 1.333333 | 71 → 72 | 94.7% → 96.0% | 1.333333 |
| september | by_mission | swarm-a | September 2024 replay | 144 | in_track | 75 → 75 | 63 → 63 | 84.0% → 84.0% | 0.000000 | 71 → 71 | 94.7% → 94.7% | 0.000000 |
| september | by_mission | swarm-a | September 2024 replay | 144 | cross | 75 → 75 | 22 → 22 | 29.3% → 29.3% | 0.000000 | 49 → 49 | 65.3% → 65.3% | 0.000000 |
| september | by_mission | swarm-a | September 2024 replay | 168 | radial | 75 → 75 | 71 → 72 | 94.7% → 96.0% | 1.333333 | 72 → 73 | 96.0% → 97.3% | 1.333333 |
| september | by_mission | swarm-a | September 2024 replay | 168 | in_track | 75 → 75 | 62 → 62 | 82.7% → 82.7% | 0.000000 | 69 → 69 | 92.0% → 92.0% | 0.000000 |
| september | by_mission | swarm-a | September 2024 replay | 168 | cross | 75 → 75 | 21 → 21 | 28.0% → 28.0% | 0.000000 | 38 → 38 | 50.7% → 50.7% | 0.000000 |
| september | by_mission | swarm-b | September 2024 replay | 6 | radial | 75 → 75 | 24 → 24 | 32.0% → 32.0% | 0.000000 | 55 → 55 | 73.3% → 73.3% | 0.000000 |
| september | by_mission | swarm-b | September 2024 replay | 6 | in_track | 75 → 75 | 11 → 11 | 14.7% → 14.7% | 0.000000 | 20 → 20 | 26.7% → 26.7% | 0.000000 |
| september | by_mission | swarm-b | September 2024 replay | 6 | cross | 75 → 75 | 5 → 5 | 6.7% → 6.7% | 0.000000 | 10 → 10 | 13.3% → 13.3% | 0.000000 |
| september | by_mission | swarm-b | September 2024 replay | 12 | radial | 75 → 75 | 40 → 40 | 53.3% → 53.3% | 0.000000 | 48 → 48 | 64.0% → 64.0% | 0.000000 |
| september | by_mission | swarm-b | September 2024 replay | 12 | in_track | 75 → 75 | 8 → 8 | 10.7% → 10.7% | 0.000000 | 22 → 22 | 29.3% → 29.3% | 0.000000 |
| september | by_mission | swarm-b | September 2024 replay | 12 | cross | 75 → 75 | 6 → 6 | 8.0% → 8.0% | 0.000000 | 10 → 10 | 13.3% → 13.3% | 0.000000 |
| september | by_mission | swarm-b | September 2024 replay | 24 | radial | 75 → 75 | 72 → 72 | 96.0% → 96.0% | 0.000000 | 75 → 75 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | swarm-b | September 2024 replay | 24 | in_track | 75 → 75 | 34 → 34 | 45.3% → 45.3% | 0.000000 | 56 → 56 | 74.7% → 74.7% | 0.000000 |
| september | by_mission | swarm-b | September 2024 replay | 24 | cross | 75 → 75 | 7 → 7 | 9.3% → 9.3% | 0.000000 | 13 → 13 | 17.3% → 17.3% | 0.000000 |
| september | by_mission | swarm-b | September 2024 replay | 36 | radial | 75 → 75 | 72 → 72 | 96.0% → 96.0% | 0.000000 | 75 → 75 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | swarm-b | September 2024 replay | 36 | in_track | 75 → 75 | 50 → 50 | 66.7% → 66.7% | 0.000000 | 66 → 66 | 88.0% → 88.0% | 0.000000 |
| september | by_mission | swarm-b | September 2024 replay | 36 | cross | 75 → 75 | 8 → 8 | 10.7% → 10.7% | 0.000000 | 18 → 18 | 24.0% → 24.0% | 0.000000 |
| september | by_mission | swarm-b | September 2024 replay | 48 | radial | 75 → 75 | 53 → 53 | 70.7% → 70.7% | 0.000000 | 75 → 75 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | swarm-b | September 2024 replay | 48 | in_track | 75 → 75 | 56 → 56 | 74.7% → 74.7% | 0.000000 | 66 → 66 | 88.0% → 88.0% | 0.000000 |
| september | by_mission | swarm-b | September 2024 replay | 48 | cross | 75 → 75 | 16 → 16 | 21.3% → 21.3% | 0.000000 | 41 → 41 | 54.7% → 54.7% | 0.000000 |
| september | by_mission | swarm-b | September 2024 replay | 72 | radial | 75 → 75 | 74 → 74 | 98.7% → 98.7% | 0.000000 | 75 → 75 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | swarm-b | September 2024 replay | 72 | in_track | 75 → 75 | 58 → 58 | 77.3% → 77.3% | 0.000000 | 68 → 68 | 90.7% → 90.7% | 0.000000 |
| september | by_mission | swarm-b | September 2024 replay | 72 | cross | 75 → 75 | 23 → 23 | 30.7% → 30.7% | 0.000000 | 53 → 53 | 70.7% → 70.7% | 0.000000 |
| september | by_mission | swarm-b | September 2024 replay | 96 | radial | 75 → 75 | 71 → 71 | 94.7% → 94.7% | 0.000000 | 75 → 75 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | swarm-b | September 2024 replay | 96 | in_track | 75 → 75 | 57 → 57 | 76.0% → 76.0% | 0.000000 | 68 → 68 | 90.7% → 90.7% | 0.000000 |
| september | by_mission | swarm-b | September 2024 replay | 96 | cross | 75 → 75 | 35 → 35 | 46.7% → 46.7% | 0.000000 | 60 → 60 | 80.0% → 80.0% | 0.000000 |
| september | by_mission | swarm-b | September 2024 replay | 120 | radial | 75 → 75 | 58 → 58 | 77.3% → 77.3% | 0.000000 | 72 → 72 | 96.0% → 96.0% | 0.000000 |
| september | by_mission | swarm-b | September 2024 replay | 120 | in_track | 75 → 75 | 61 → 61 | 81.3% → 81.3% | 0.000000 | 68 → 68 | 90.7% → 90.7% | 0.000000 |
| september | by_mission | swarm-b | September 2024 replay | 120 | cross | 75 → 75 | 44 → 44 | 58.7% → 58.7% | 0.000000 | 66 → 66 | 88.0% → 88.0% | 0.000000 |
| september | by_mission | swarm-b | September 2024 replay | 144 | radial | 75 → 75 | 71 → 71 | 94.7% → 94.7% | 0.000000 | 72 → 73 | 96.0% → 97.3% | 1.333333 |
| september | by_mission | swarm-b | September 2024 replay | 144 | in_track | 75 → 75 | 61 → 61 | 81.3% → 81.3% | 0.000000 | 68 → 68 | 90.7% → 90.7% | 0.000000 |
| september | by_mission | swarm-b | September 2024 replay | 144 | cross | 75 → 75 | 52 → 52 | 69.3% → 69.3% | 0.000000 | 71 → 71 | 94.7% → 94.7% | 0.000000 |
| september | by_mission | swarm-b | September 2024 replay | 168 | radial | 75 → 75 | 68 → 68 | 90.7% → 90.7% | 0.000000 | 72 → 75 | 96.0% → 100.0% | 4.000000 |
| september | by_mission | swarm-b | September 2024 replay | 168 | in_track | 75 → 75 | 60 → 60 | 80.0% → 80.0% | 0.000000 | 67 → 67 | 89.3% → 89.3% | 0.000000 |
| september | by_mission | swarm-b | September 2024 replay | 168 | cross | 75 → 75 | 51 → 51 | 68.0% → 68.0% | 0.000000 | 75 → 75 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | swarm-c | September 2024 replay | 6 | radial | 74 → 74 | 12 → 12 | 16.2% → 16.2% | 0.000000 | 41 → 41 | 55.4% → 55.4% | 0.000000 |
| september | by_mission | swarm-c | September 2024 replay | 6 | in_track | 74 → 74 | 22 → 22 | 29.7% → 29.7% | 0.000000 | 53 → 53 | 71.6% → 71.6% | 0.000000 |
| september | by_mission | swarm-c | September 2024 replay | 6 | cross | 74 → 74 | 3 → 3 | 4.1% → 4.1% | 0.000000 | 8 → 8 | 10.8% → 10.8% | 0.000000 |
| september | by_mission | swarm-c | September 2024 replay | 12 | radial | 74 → 74 | 21 → 21 | 28.4% → 28.4% | 0.000000 | 33 → 33 | 44.6% → 44.6% | 0.000000 |
| september | by_mission | swarm-c | September 2024 replay | 12 | in_track | 74 → 74 | 28 → 28 | 37.8% → 37.8% | 0.000000 | 52 → 52 | 70.3% → 70.3% | 0.000000 |
| september | by_mission | swarm-c | September 2024 replay | 12 | cross | 74 → 74 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 4 → 4 | 5.4% → 5.4% | 0.000000 |
| september | by_mission | swarm-c | September 2024 replay | 24 | radial | 74 → 74 | 40 → 40 | 54.1% → 54.1% | 0.000000 | 70 → 70 | 94.6% → 94.6% | 0.000000 |
| september | by_mission | swarm-c | September 2024 replay | 24 | in_track | 74 → 74 | 62 → 62 | 83.8% → 83.8% | 0.000000 | 68 → 68 | 91.9% → 91.9% | 0.000000 |
| september | by_mission | swarm-c | September 2024 replay | 24 | cross | 74 → 74 | 2 → 2 | 2.7% → 2.7% | 0.000000 | 5 → 5 | 6.8% → 6.8% | 0.000000 |
| september | by_mission | swarm-c | September 2024 replay | 36 | radial | 74 → 74 | 22 → 22 | 29.7% → 29.7% | 0.000000 | 61 → 61 | 82.4% → 82.4% | 0.000000 |
| september | by_mission | swarm-c | September 2024 replay | 36 | in_track | 74 → 74 | 64 → 64 | 86.5% → 86.5% | 0.000000 | 70 → 70 | 94.6% → 94.6% | 0.000000 |
| september | by_mission | swarm-c | September 2024 replay | 36 | cross | 74 → 74 | 13 → 13 | 17.6% → 17.6% | 0.000000 | 22 → 22 | 29.7% → 29.7% | 0.000000 |
| september | by_mission | swarm-c | September 2024 replay | 48 | radial | 74 → 74 | 74 → 74 | 100.0% → 100.0% | 0.000000 | 74 → 74 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | swarm-c | September 2024 replay | 48 | in_track | 74 → 74 | 62 → 62 | 83.8% → 83.8% | 0.000000 | 72 → 72 | 97.3% → 97.3% | 0.000000 |
| september | by_mission | swarm-c | September 2024 replay | 48 | cross | 74 → 74 | 2 → 2 | 2.7% → 2.7% | 0.000000 | 2 → 2 | 2.7% → 2.7% | 0.000000 |
| september | by_mission | swarm-c | September 2024 replay | 72 | radial | 74 → 74 | 48 → 48 | 64.9% → 64.9% | 0.000000 | 73 → 73 | 98.6% → 98.6% | 0.000000 |
| september | by_mission | swarm-c | September 2024 replay | 72 | in_track | 74 → 74 | 62 → 62 | 83.8% → 83.8% | 0.000000 | 71 → 71 | 95.9% → 95.9% | 0.000000 |
| september | by_mission | swarm-c | September 2024 replay | 72 | cross | 74 → 74 | 23 → 23 | 31.1% → 31.1% | 0.000000 | 37 → 37 | 50.0% → 50.0% | 0.000000 |
| september | by_mission | swarm-c | September 2024 replay | 96 | radial | 74 → 74 | 73 → 73 | 98.6% → 98.6% | 0.000000 | 73 → 73 | 98.6% → 98.6% | 0.000000 |
| september | by_mission | swarm-c | September 2024 replay | 96 | in_track | 74 → 74 | 61 → 61 | 82.4% → 82.4% | 0.000000 | 71 → 71 | 95.9% → 95.9% | 0.000000 |
| september | by_mission | swarm-c | September 2024 replay | 96 | cross | 74 → 74 | 10 → 10 | 13.5% → 13.5% | 0.000000 | 22 → 22 | 29.7% → 29.7% | 0.000000 |
| september | by_mission | swarm-c | September 2024 replay | 120 | radial | 74 → 74 | 72 → 72 | 97.3% → 97.3% | 0.000000 | 73 → 73 | 98.6% → 98.6% | 0.000000 |
| september | by_mission | swarm-c | September 2024 replay | 120 | in_track | 74 → 74 | 62 → 62 | 83.8% → 83.8% | 0.000000 | 71 → 71 | 95.9% → 95.9% | 0.000000 |
| september | by_mission | swarm-c | September 2024 replay | 120 | cross | 74 → 74 | 6 → 6 | 8.1% → 8.1% | 0.000000 | 18 → 18 | 24.3% → 24.3% | 0.000000 |
| september | by_mission | swarm-c | September 2024 replay | 144 | radial | 74 → 74 | 63 → 65 | 85.1% → 87.8% | 2.702703 | 71 → 72 | 95.9% → 97.3% | 1.351351 |
| september | by_mission | swarm-c | September 2024 replay | 144 | in_track | 74 → 74 | 64 → 64 | 86.5% → 86.5% | 0.000000 | 71 → 71 | 95.9% → 95.9% | 0.000000 |
| september | by_mission | swarm-c | September 2024 replay | 144 | cross | 74 → 74 | 22 → 22 | 29.7% → 29.7% | 0.000000 | 43 → 43 | 58.1% → 58.1% | 0.000000 |
| september | by_mission | swarm-c | September 2024 replay | 168 | radial | 74 → 74 | 71 → 72 | 95.9% → 97.3% | 1.351351 | 72 → 73 | 97.3% → 98.6% | 1.351351 |
| september | by_mission | swarm-c | September 2024 replay | 168 | in_track | 74 → 74 | 64 → 64 | 86.5% → 86.5% | 0.000000 | 70 → 70 | 94.6% → 94.6% | 0.000000 |
| september | by_mission | swarm-c | September 2024 replay | 168 | cross | 74 → 74 | 19 → 19 | 25.7% → 25.7% | 0.000000 | 36 → 36 | 48.6% → 48.6% | 0.000000 |
| september | by_mission | swot | September 2024 replay | 6 | radial | 72 → 72 | 1 → 1 | 1.4% → 1.4% | 0.000000 | 4 → 4 | 5.6% → 5.6% | 0.000000 |
| september | by_mission | swot | September 2024 replay | 6 | in_track | 72 → 72 | 13 → 13 | 18.1% → 18.1% | 0.000000 | 35 → 35 | 48.6% → 48.6% | 0.000000 |
| september | by_mission | swot | September 2024 replay | 6 | cross | 72 → 72 | 13 → 13 | 18.1% → 18.1% | 0.000000 | 27 → 27 | 37.5% → 37.5% | 0.000000 |
| september | by_mission | swot | September 2024 replay | 12 | radial | 71 → 71 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| september | by_mission | swot | September 2024 replay | 12 | in_track | 71 → 71 | 32 → 32 | 45.1% → 45.1% | 0.000000 | 49 → 49 | 69.0% → 69.0% | 0.000000 |
| september | by_mission | swot | September 2024 replay | 12 | cross | 71 → 71 | 17 → 17 | 23.9% → 23.9% | 0.000000 | 26 → 26 | 36.6% → 36.6% | 0.000000 |
| september | by_mission | swot | September 2024 replay | 24 | radial | 70 → 70 | 2 → 2 | 2.9% → 2.9% | 0.000000 | 5 → 5 | 7.1% → 7.1% | 0.000000 |
| september | by_mission | swot | September 2024 replay | 24 | in_track | 70 → 70 | 40 → 40 | 57.1% → 57.1% | 0.000000 | 68 → 68 | 97.1% → 97.1% | 0.000000 |
| september | by_mission | swot | September 2024 replay | 24 | cross | 70 → 70 | 45 → 45 | 64.3% → 64.3% | 0.000000 | 59 → 59 | 84.3% → 84.3% | 0.000000 |
| september | by_mission | swot | September 2024 replay | 36 | radial | 69 → 69 | 0 → 0 | 0.0% → 0.0% | 0.000000 | 0 → 0 | 0.0% → 0.0% | 0.000000 |
| september | by_mission | swot | September 2024 replay | 36 | in_track | 69 → 69 | 69 → 69 | 100.0% → 100.0% | 0.000000 | 69 → 69 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | swot | September 2024 replay | 36 | cross | 69 → 69 | 30 → 30 | 43.5% → 43.5% | 0.000000 | 47 → 47 | 68.1% → 68.1% | 0.000000 |
| september | by_mission | swot | September 2024 replay | 48 | radial | 68 → 68 | 6 → 6 | 8.8% → 8.8% | 0.000000 | 8 → 8 | 11.8% → 11.8% | 0.000000 |
| september | by_mission | swot | September 2024 replay | 48 | in_track | 68 → 68 | 68 → 68 | 100.0% → 100.0% | 0.000000 | 68 → 68 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | swot | September 2024 replay | 48 | cross | 68 → 68 | 55 → 55 | 80.9% → 80.9% | 0.000000 | 66 → 66 | 97.1% → 97.1% | 0.000000 |
| september | by_mission | swot | September 2024 replay | 72 | radial | 66 → 66 | 7 → 7 | 10.6% → 10.6% | 0.000000 | 10 → 10 | 15.2% → 15.2% | 0.000000 |
| september | by_mission | swot | September 2024 replay | 72 | in_track | 66 → 66 | 66 → 66 | 100.0% → 100.0% | 0.000000 | 66 → 66 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | swot | September 2024 replay | 72 | cross | 66 → 66 | 55 → 55 | 83.3% → 83.3% | 0.000000 | 66 → 66 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | swot | September 2024 replay | 96 | radial | 64 → 64 | 6 → 6 | 9.4% → 9.4% | 0.000000 | 10 → 10 | 15.6% → 15.6% | 0.000000 |
| september | by_mission | swot | September 2024 replay | 96 | in_track | 64 → 64 | 64 → 64 | 100.0% → 100.0% | 0.000000 | 64 → 64 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | swot | September 2024 replay | 96 | cross | 64 → 64 | 53 → 53 | 82.8% → 82.8% | 0.000000 | 64 → 64 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | swot | September 2024 replay | 120 | radial | 62 → 62 | 6 → 6 | 9.7% → 9.7% | 0.000000 | 19 → 19 | 30.6% → 30.6% | 0.000000 |
| september | by_mission | swot | September 2024 replay | 120 | in_track | 62 → 62 | 62 → 62 | 100.0% → 100.0% | 0.000000 | 62 → 62 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | swot | September 2024 replay | 120 | cross | 62 → 62 | 51 → 51 | 82.3% → 82.3% | 0.000000 | 62 → 62 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | swot | September 2024 replay | 144 | radial | 59 → 59 | 6 → 6 | 10.2% → 10.2% | 0.000000 | 25 → 25 | 42.4% → 42.4% | 0.000000 |
| september | by_mission | swot | September 2024 replay | 144 | in_track | 59 → 59 | 59 → 59 | 100.0% → 100.0% | 0.000000 | 59 → 59 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | swot | September 2024 replay | 144 | cross | 59 → 59 | 48 → 48 | 81.4% → 81.4% | 0.000000 | 59 → 59 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | swot | September 2024 replay | 168 | radial | 57 → 57 | 8 → 8 | 14.0% → 14.0% | 0.000000 | 28 → 29 | 49.1% → 50.9% | 1.754386 |
| september | by_mission | swot | September 2024 replay | 168 | in_track | 57 → 57 | 57 → 57 | 100.0% → 100.0% | 0.000000 | 57 → 57 | 100.0% → 100.0% | 0.000000 |
| september | by_mission | swot | September 2024 replay | 168 | cross | 57 → 57 | 43 → 43 | 75.4% → 75.4% | 0.000000 | 57 → 57 | 100.0% → 100.0% | 0.000000 |
