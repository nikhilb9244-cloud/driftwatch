# Rebuilding the publication

The reader-facing paper is authored in `docs/paper.template.md`. Edit its sentences there; use scalar evidence substitutions for figures. The renderer inserts values and tables, and does not compose the paper's sentences. Author identifiers and retained protocol links are in `docs/publication-metadata.json`. `docs/assets/benchmark-v2.json` is the evidence object; the paper carries the hash of its exact bytes.

The covariance amendment uses only the retained offline inputs. The original predicted-RIC covariance is transported into truth RIC at each comparison time, preserving the stored residuals and exclusions. The original reference trials, both sets of bases and the corrected trials are retained in `data/validation/covariance-basis-correction-2026-09-08/`. The dated correction page and CSV include every cell, including unchanged cells. The September primary result and frozen experiment files are preserved; its displayed secondary component coverage uses a separately identified amendment.

To rebuild the evidence and all publication tables from the retained inputs, run from the repository root:

Install the complete validation environment with `uv sync --all-groups --extra dsgp4`. CI installs that extra as well: without it, the learned-propagator module is skipped and the test-count guard correctly rejects the incomplete inventory.

```powershell
uv run --offline python scripts/render_paper_v2.py --dsgp4 data/validation/dsgp4_evaluation.json --dsgp4-pairs data/validation/dsgp4_paired_comparisons.csv --dsgp4-audit output/referee/dsgp4_correction_audit.json --radio data/radio/horizon.json --radio-tracks data/radio/track_benchmark_v2_complete/radio_track_summary.json --locked data/validation/locked-september-2024/locked_experiment.json
uv run --offline python scripts/render_public_claims.py
uv run --offline python scripts/render_public_claims.py --check
uv run --offline pytest --junitxml=output/publication-review-2026-09-08/pytest.xml
uv run --offline python scripts/check_test_count.py output/publication-review-2026-09-08/pytest.xml
```

The covariance reconstruction itself is reproducible with `uv run --offline python scripts/correct_covariance_basis.py`. It starts from write-once pre-correction archives and never overwrites the frozen September experiment. Rebuilding that amendment changes its execution timestamp and downstream hashes; follow it with both publication commands above.

The public claims manifest records a result hash, method, population, denominator, reference type, censoring and permitted wording for each claim. Its renderer owns the marked README and roadmap result regions, current findings/reference/calibration/applicability pages, and the Python and browser applicability text. The publication tests reject a stale consumer, a changed bound input or source, an unbound numeric figure in paper prose, or a paper differing from its authored template. The test-count check also verifies that pytest reached the end of the collected suite.

The root README's horizon section is rendered from `docs/assets/claims-v2.json`. The publication-contract suite explicitly checks its v2 low-altitude brackets, the May 600-750 km result passing through 168 hours, and the October 600-750 km bracket of 96/120 hours.

Build the paper PDF from the rendered Markdown with `python scripts/build_paper_pdf.py --font-dir C:/Windows/Fonts` in an environment containing ReportLab. The builder embeds the supplied Times New Roman font files and resolves repository links against the release tag. For the PDF containing the assigned DOI, pass `--repository-ref` with the immutable DOI metadata commit so its evidence link resolves to the exact object whose hash it displays. It does not generate prose. On another operating system, supply a directory with the same licensed font files. Render every page with Poppler and inspect the tables, references and page boundaries before attaching the PDF to the release.

The current September status pages are generated from the frozen protocol, separately bound attestation, first-access marker and completion metadata. The original method Markdown is retained byte-for-byte in `docs/archive/september-2024-protocol-frozen.md`. The original pre-access audit was a check at freezing time; it is not a claim that current edited source files still have the frozen source hashes. The original numerical audit applies to the preserved experiment, while the later covariance amendment has separate transport checks.

The author authorised the final edits and deposition on 2026-09-08 after reviewing the rewritten paper. The release tag is `paper-2026-09-v2`. Zenodo assigns its version DOI after the GitHub release; the subsequent DOI metadata commit and rebuilt PDF are identified in the release notes without moving the published tag. No outreach is authorised by the README consistency check.
