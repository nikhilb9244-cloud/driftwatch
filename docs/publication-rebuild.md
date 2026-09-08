# Rebuilding the publication

## Dated completeness and provenance correction: 2026-09-08

Release `paper-2026-09-v2.1` repairs omitted project artefacts and removes private provenance and embedded provider records from the distributable evidence. It does not rescore the benchmark. The [correction record](assets/publication-correction-v2.1.json) gives the original and corrected evidence hashes. The [asset ledger](assets/publication-assets-v2.1.json) maps every retained path to its original and replacement SHA-256, including unchanged files. Original v2 provenance hashes in the tables identify historical bytes; resolve them through this disclosed ledger when checking a scrubbed replacement. The original v2 tag and Git history remain unchanged.

The 24 project-generated files omitted from v2 are individual release assets. The derived-artefact archive also contains the complete distributable input inventory, including reference trials, covariance bases, radio curves and cases, frozen-result metadata, training eligibility records and both rejected learned-propagator checkpoints. `SHA256SUMS` covers the release assets; the ledger additionally verifies each archive member. Provider raw snapshots are excluded.

Local paths are made relative where the repository location is known. Private external locations and execution references are replaced by identifiers and hashes. Copied provider payloads, source descriptions and record inventories are replaced by source identifiers and content hashes; computed residuals, UTC comparison endpoints, coverage counts, conventions and statistical results are retained. Content hashes of JSON values use UTF-8 JSON with sorted keys, no optional whitespace and unescaped Unicode. File hashes always refer to exact file bytes. The author's public contact remains in publication metadata and the paper, with a hash-bound scalar reference in the evidence object.

## Restore and verify a clean clone

Install the complete environment, including the learned-propagator extra. Run from the checkout root:

```powershell
uv sync --all-groups --extra dsgp4
uv run python scripts/publication_assets.py --all
uv run python scripts/render_publication.py --check
uv run python scripts/render_public_claims.py --check
uv run python scripts/check_publication_invariants.py
uv run pytest --junitxml=output/publication-checks/pytest.xml
uv run python scripts/check_test_count.py output/publication-checks/pytest.xml
```

The publication-contract tests restore their required assets automatically when absent. The loader locates the release by repository ID and tag, downloads its content-addressed archive, verifies the archive hash and size, then checks each selected member before installing it. Missing or inaccessible assets fail with the asset name, required hash and release archive name. Existing files with the wrong hash fail explicitly; they are not silently trusted or overwritten. `data/`, `output/` and caches remain ignored by Git.

For a pre-publication rehearsal only, `DRIFTWATCH_ASSET_MIRROR` can point to an HTTP server serving the exact staged archive. The same archive/member hashes are required. Such a rehearsal is recorded separately from a fresh-clone run against the published release; a local working copy containing old evidence is not a clean-clone test.

The [v2 invariant baseline](assets/publication-invariants-v2.json) records 52 published table blocks and 107 existing scalar substitutions. The invariant check also compares the complete paper body after removing only the dated availability addition and restoring the original evidence hash. It must report zero differences. The test-count guard compares completed tests with fresh collection and rejects a truncated suite.

## Regenerate the rendered publication

The sentences are authored in `docs/paper.template.md`. Figures are explicit scalar substitutions; the renderer does not compose sentences. `docs/assets/benchmark-v2.json` is the scientific evidence object. The correction's date, hashes and assigned DOI are in `docs/assets/publication-correction-v2.1.json`, separately from the frozen measurements so assigning a DOI does not change the scientific evidence hash.

```powershell
uv run python scripts/render_publication.py
uv run python scripts/render_public_claims.py
uv run python scripts/check_publication_invariants.py
```

The claims manifest continues to identify the v2 scientific measurements. Its evidence hash follows the scrubbed object; result hashes, methods, populations, denominators, censoring and permitted numerical wording remain unchanged. The root README horizon section is rendered from that manifest and has a dedicated publication-contract test.

The historical `render_paper_v2.py` build path and `correct_covariance_basis.py` reconstruct the original analysis from retained scientific inputs. They are not the v2.1 presentation-only rebuild command: rerunning a scientific build updates execution provenance and would need a new, separately validated record. The covariance contract independently transports the retained covariance bases and recomputes component membership while checking residuals and exclusions remain fixed. The September completion contract resolves disclosed scrubbed replacements without pretending their hashes equal the frozen original hashes.

Build the PDF in an environment with ReportLab and the licensed Times New Roman fonts:

```powershell
python scripts/build_paper_pdf.py --output output/pdf/paper-2026-09-v2.1.pdf --font-dir "$env:WINDIR/Fonts"
```

On another operating system, supply the same licensed fonts through `--font-dir`. Render every page with Poppler and inspect tables, references and page boundaries. After DOI assignment, use `--repository-ref` with the immutable DOI metadata commit when rebuilding the final PDF. The tag is not moved after publication.

## Provider inputs: exact-snapshot recovery

The following three provider-authored snapshots are fetched from their original sources and verified by the hashes below. None is attached to v2.1. Retrieval times are the original local acquisition observations, not inferred publication times.

| Local snapshot | Source identifier | Original retrieval UTC | Required file SHA-256 |
| --- | --- | --- | --- |
| `output/referee/ids-events.html` | [IDS event table](https://ids-doris.org/user-corner/table-of-all-events.html) | 2026-09-08T09:03:13.983454+00:00 | `7355031aeddc6f37a54e4280f32c2440f1eed2343f988f76f85372d4930e07c4` |
| `output/referee/s3a.man` | [SentiWiki Sentinel-3A history](https://sentiwiki.copernicus.eu/__attachments/a_3556c4aa440be245bf6ab6ff367525e46a101dff5bf0260c41dafc40897e15bd/s3a.man?cb=28d779e3ae310d45dcf55248702ec2a8) | 2026-09-08T09:03:33.393132+00:00 | `b907b21903c5367013efd1948e346d0e9aa72a478f197b170670fc31f7045705` |
| `output/referee/s3b.man` | [SentiWiki Sentinel-3B history](https://sentiwiki.copernicus.eu/__attachments/a_adc1553d599e66e4c320b7b54488fb13217012408df5bc8c5dc0334ca3ab93d9/s3b.man?cb=951072114b0a8c6b993353b8b7913d93) | 2026-09-08T09:03:33.759239+00:00 | `51f7c3cab1c67559cfb7882a1d062172f73aa19ddbb82a4b8df4213faeef9cce` |

Obtain the files under the provider's access and use terms. If a current URL no longer serves the recorded bytes, request that specific historical snapshot through an authorised provider route. Check SHA-256 before parsing. A newer event table is not interchangeable with the frozen snapshot. Preserve matching bytes locally under the ignored path; do not commit or attach them. If the recorded hash cannot be recovered, report the input as unavailable and do not claim exact raw-source reconstruction. The providers' continued availability of these historical bytes is not established by these instructions.

The parser in `src/driftwatch/storm/manoeuvre_records.py` interprets IDS event times as TAI and Sentinel-3 NAPEOS history times as UTC. Preserve those declarations when reconstructing UTC intervals. The parsed GRACE products have a separate retention limitation: the original transport archives were deleted by the historical loader. The supporting manifests identify retained parsed products but do not restore raw archive bytes. Other provider products and their access conditions are documented in the [data-source record](data-sources.md).

SentiWiki's [terms](https://sentiwiki.copernicus.eu/web/terms-and-conditions) restrict redistribution without written authorisation. IDS requests attribution in its [citation guidance](https://ids-doris.org/resources/articles/citation.html); its incomplete [legal notice](https://ids-doris.org/legal-notice.html) does not establish redistribution permission. The IDS snapshot remains withheld rather than being treated as licensed for redistribution. These sources were checked on 2026-09-08.

The author authorised this dated correction and deposition on 2026-09-08. No outreach is authorised by the release or by passing the README consistency check.
