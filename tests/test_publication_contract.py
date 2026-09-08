"""The paper and coverage correction must remain bound to the stored evidence."""

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_publication_invariants  # noqa: E402
import publication_assets  # noqa: E402
import publication_text  # noqa: E402
import render_paper_v2  # noqa: E402
import render_public_claims  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def restore_publication_inputs():
    publication_assets.restore_required(root=ROOT)


def evidence():
    path = ROOT / "docs/assets/benchmark-v2.json"
    return json.loads(path.read_text(encoding="utf-8")), hashlib.sha256(path.read_bytes()).hexdigest()


def test_v21_changes_no_v2_table_substitution_or_other_paper_text():
    result = check_publication_invariants.check(ROOT)
    assert result["diff_count"] == 0, result["differences"]


def test_distributable_evidence_has_no_private_identifiers_or_embedded_provider_payload():
    import re

    data, _ = evidence()
    contact = json.loads((ROOT / "docs/publication-metadata.json").read_text())["email"].split("@")[0]
    text = json.dumps(data)
    assert contact.lower() not in text.lower()
    assert re.search(r"(?i)(?<![\w])[a-z]:[\\\\/]|/Users/|/home/|DESKTOP-[a-z0-9]+", text) is None

    def visit(value):
        if isinstance(value, dict):
            assert "raw_path" not in value and "raw_file" not in value
            assert not {"NORAD_CAT_ID", "EPOCH"} <= value.keys()
            for key, item in value.items():
                if key in {"site", "measured_metrics"} or (key == "manoeuvres_recorded" and item is not None):
                    assert set(item) == {"source_identifier", "content_sha256"}
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(data)


def test_paper_has_only_bound_figures_and_matches_current_evidence():
    data, digest = evidence()
    template = (ROOT / "docs/paper.template.md").read_text(encoding="utf-8")
    paper = (ROOT / "docs/paper.md").read_text(encoding="utf-8")
    tables = {k: publication_text.display_windows(v, data) for k, v in render_paper_v2.paper_tables(data).items()}
    publication_text.validate_numeric_prose(template, paper, data, tables, digest)
    with pytest.raises(ValueError, match="Literal figure"):
        publication_text.validate_numeric_prose(template + "\nAn error of 987654321 km.", paper, data, tables, digest)
    with pytest.raises(ValueError, match="differs"):
        publication_text.validate_numeric_prose(template, paper.replace("km", "987654321 km", 1), data, tables, digest)
    with pytest.raises(KeyError):
        publication_text.render_template("{{absent/figure}}", data, tables, digest)


def test_covariance_amendment_recomputes_only_sigmas_and_component_membership():
    data, _ = evidence()
    directory = ROOT / "data/validation/covariance-basis-correction-2026-09-08"
    for population, source in (
        ("reference", directory / "reference-original.parquet"),
        ("september", ROOT / "data/validation/locked-september-2024/locked_trials.parquet"),
    ):
        original = pd.read_parquet(source)
        corrected = pd.read_parquet(directory / f"{population}-trials.parquet")
        bases = np.load(directory / f"{population}-bases.npz")
        # Independently pass through Cartesian coordinates, not the production helper.
        b, t = bases["source"], bases["target"]
        sigmas = ["sigma_r_km", "sigma_i_km", "sigma_c_km"]
        diagonal = original[sigmas].to_numpy() ** 2
        cartesian = np.einsum("nji,nj,njk->nik", b, diagonal, b)
        truth = np.einsum("nij,njk,nlk->nil", t, cartesian, t)
        expected = np.sqrt(np.diagonal(truth, axis1=-2, axis2=-1))
        # Cartesian expansion subtracts large rotated variances for thin axes.
        np.testing.assert_allclose(corrected[sigmas], expected, rtol=1e-10, atol=1e-10, equal_nan=True)
        flags = [f"{c}_inside_{s}s" for c in ("radial", "in_track", "cross") for s in (1, 2)]
        for index, component in enumerate(("radial", "in_track", "cross")):
            for multiple in (1, 2):
                np.testing.assert_array_equal(
                    corrected[f"{component}_inside_{multiple}s"],
                    np.abs(corrected[f"{component}_km"]) <= multiple * expected[:, index],
                )
        pd.testing.assert_frame_equal(original.drop(columns=sigmas + flags), corrected.drop(columns=sigmas + flags))
        amendment = data["covariance_basis_correction"][population]
        assert amendment["horizons_unchanged"]
        assert amendment["n_coverage_cells_changed"] == sum(c["coverage_changed"] for c in amendment["cells"])
        assert all(c["component"] == "radial" for c in amendment["cells"] if c["coverage_changed"])


def test_frozen_september_result_bytes_remain_bound_to_completion_manifest():
    folder = ROOT / "data/validation/locked-september-2024"
    manifest = json.loads((folder / "completion-manifest.json").read_text())
    for name in ("locked_trials.parquet", "locked_experiment.json"):
        relative = (folder / name).relative_to(ROOT).as_posix()
        assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == publication_assets.effective_hash(
            relative, manifest["files"][name], root=ROOT
        )


def test_publication_inputs_and_method_sources_match_the_bound_hashes():
    data, _ = evidence()
    for source in data["inputs"] + data["source_code"]:
        expected = publication_assets.effective_hash(source["path"], source["sha256"], root=ROOT)
        assert hashlib.sha256((ROOT / source["path"]).read_bytes()).hexdigest() == expected, source["path"]
    frozen = ROOT / data["publication"]["frozen_protocol_markdown_path"]
    assert hashlib.sha256(frozen.read_bytes()).hexdigest() == data["publication"]["frozen_protocol_markdown_sha256"]
    status = (ROOT / "docs/protocols/2026-09-08-september-2024.md").read_text(encoding="utf-8")
    assert "**Execution completed" in status and "remains pending" not in status


def test_all_generated_tables_match_the_canonical_object():
    data, _ = evidence()
    for name, text in {**render_paper_v2.render(data), **render_paper_v2.basis_correction_outputs(data)}.items():
        assert (ROOT / name).read_text(encoding="utf-8") == text.strip() + "\n", name


def test_public_claims_bind_result_hashes_denominators_and_rendered_consumers():
    data, digest = evidence()
    manifest = json.loads((ROOT / "docs/assets/claims-v2.json").read_text(encoding="utf-8"))
    assert manifest == render_public_claims.build_manifest(data, digest)
    for record in manifest["claims"]:
        value = data
        for key in record["result_path"].split("/"):
            value = value[key]
        assert record["result_hash"] == render_public_claims.sha(value)
        assert all(
            record[key]
            for key in (
                "method_version",
                "population",
                "denominator",
                "reference_type",
                "censoring_state",
                "permitted_wording",
            )
        )
    for name, text in render_public_claims.render(manifest).items():
        assert (ROOT / name).read_text(encoding="utf-8") == text, name
    from driftwatch import claims
    from driftwatch.export import report

    assert report.HORIZON_HEADLINE == claims.wording("horizon_overview")
    assert report.STORM_CALIBRATION_NOTE == claims.wording("consistency")
    assert "claims.generated" in (ROOT / "web/src/scenarios.ts").read_text()


def test_root_readme_horizons_render_from_manifest_with_v2_brackets():
    manifest = json.loads((ROOT / "docs/assets/claims-v2.json").read_text(encoding="utf-8"))
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert readme == render_public_claims.render(manifest)["README.md"]
    section = readme.split("<!-- BEGIN CLAIMS:horizons -->", 1)[1].split("<!-- END CLAIMS:horizons -->", 1)[0]
    expected = {
        ("400-600 km", "April 2024 control"): "120 h pass / 144 h fail",
        ("400-600 km", "May 2024"): "48 h pass / 72 h fail",
        ("400-600 km", "August 2024 held out"): "48 h pass / 72 h fail",
        ("400-600 km", "October 2024 held out"): "24 h pass / 36 h fail",
        ("600-750 km", "May 2024"): "passes through the longest tested lead (168 h)",
        ("600-750 km", "October 2024 held out"): "96 h pass / 120 h fail",
    }
    for (band, window), bracket in expected.items():
        assert f"| {band} | {window} | {bracket} |" in section
    assert "696" not in section and "719" not in section


def test_paper_horizon_order_and_restored_publication_sections():
    data, _ = evidence()
    paper = (ROOT / "docs/paper.md").read_text(encoding="utf-8")
    table = render_paper_v2.paper_tables(data)["horizons"]
    bands = [int(line.split("|")[1].strip().split("-")[0]) for line in table.splitlines()[2:]]
    assert bands == sorted(bands)
    appendix = paper.split("## Assurance appendix\n", 1)[1].split("\n## ", 1)[0]
    assert len([line for line in appendix.splitlines() if line.startswith("|")]) == 8
    assert paper.index("## Corrections and reproducibility") < paper.index("## Assurance appendix")
    for heading in ("Acknowledgements", "Data and code availability", "References"):
        assert f"## {heading}\n" in paper
    assert "SARAO supplied nothing and has not been consulted." in paper
    assert "Sentinel-3A on 2024-09-18" in paper
    assert "1.037 km prediction error against 0.708 km" in paper
