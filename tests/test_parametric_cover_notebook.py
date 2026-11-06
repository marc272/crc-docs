"""The parametric cover notebook keeps portable saved outputs and states its setup."""

import base64
import struct
from pathlib import Path

import nbformat

NOTEBOOK = Path("notebooks/parametric_cover_design.ipynb")


def _read():
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    nbformat.validate(notebook)
    return notebook


def _source(notebook):
    return "\n".join(cell.source for cell in notebook.cells)


def _printed(notebook):
    return "\n".join(
        output.text
        for cell in notebook.cells
        if cell.cell_type == "code"
        for output in cell.outputs
        if output.output_type == "stream" and output.name == "stdout"
    )


def test_parametric_notebook_has_portable_executed_outputs():
    notebook = _read()
    code = [cell for cell in notebook.cells if cell.cell_type == "code"]
    assert [cell.execution_count for cell in code] == list(range(1, len(code) + 1))
    outputs = [output for cell in code for output in cell.outputs]
    assert not any(output.output_type == "error" for output in outputs)
    assert not notebook.metadata.get("widgets")
    figures = [
        output.data
        for output in outputs
        if "application/vnd.plotly.v1+json" in output.get("data", {})
    ]
    assert len(figures) >= 4
    for figure in figures:
        image = base64.b64decode(figure["image/png"])
        assert image.startswith(b"\x89PNG\r\n\x1a\n")
        width, height = struct.unpack(">II", image[16:24])
        assert width >= 600 and height >= 300


def test_parametric_notebook_reads_the_public_release_or_a_stated_local_file():
    source = _source(_read())
    assert 'RELEASE = "ssp585-global-2026-10-20-v1"' in source
    assert "HazardDataset.crc_open(source=SOURCE, release=RELEASE)" in source
    assert ".ensure_materialized()" in source
    assert 'os.environ.get("CRC_PARAMETRIC_CURVES")' in source
    assert "HazardDataset.local(curves_path)" in source
    assert "raise FileNotFoundError(" in source
    assert "Curves come from" in _printed(_read())


def test_parametric_notebook_designs_and_compares_out_of_sample():
    source = _source(_read())
    assert "ParametricPlan.for_evaluation(request" in source
    assert ".monte_carlo(" in source and "FreshDraws(" in source
    for family in ("LinearPayout(", "StepPayout(", "PiecewiseLinearPayout("):
        assert family in source
    for objective in ("MSE()", "ExpectedUncovered()", "WeightedCVaR("):
        assert objective in source
    assert "budget=Budget(" in source
    assert 'pc.equal(table["split"], "out_of_sample")' in source


def test_parametric_notebook_states_its_setup_and_the_data_licence():
    notebook = _read()
    source, printed = _source(notebook), _printed(notebook)
    assert "print(setup_text(result.metadata))" in source
    assert "Basis: annual, one draw is one year." in printed
    assert "the leakage check passed" in printed
    assert "Basis risk: impact noise" in printed
    assert "Source: " in printed and "licence CC-BY-NC-4.0" in printed
    assert "CC BY-NC 4.0" in source
    assert "Riskthinking.AI bias-corrected climate distributions" in source


def test_parametric_notebook_checks_the_module_without_importing_it():
    setup = next(cell.source for cell in _read().cells if "REQUIREMENTS =" in cell.source)
    assert "crc-sdk[geometry,parametric]" in setup
    assert '"parametric" / "__init__.py"' in setup
    assert '"highspy"' in setup
    assert "import crc_sdk" not in setup


def test_saved_outputs_say_which_source_they_come_from():
    notebook = _read()
    printed = _printed(notebook)
    note = "About the saved outputs of this copy." in _source(notebook)
    from_local_file = "Curves come from a local canonical file" in printed
    from_release = "Curves come from the public CRC Open release" in printed
    assert from_local_file != from_release
    # Outputs refreshed from the public release drop the note about a local file.
    assert note == from_local_file
