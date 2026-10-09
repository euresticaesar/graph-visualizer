import json
import os
from pathlib import Path

import pytest
from PySide6.QtCore import QRect
from PySide6.QtGui import QImage
from render_reference import cases, fingerprint, reference_font, render_case

REFERENCES = Path(__file__).parent / "fixtures/render"


@pytest.fixture
def controlled_font(qapp):
    with reference_font():
        yield


@pytest.mark.parametrize(
    "case_name",
    ["astar_adaptive", "matrix_highlights", "negative_cycle", "long_ids_dark", "colorblind_focus"],
)
def test_slide_render_regions_match_reviewed_references(controlled_font, tmp_path, case_name):
    manifest = json.loads((REFERENCES / "manifest.json").read_text())
    actual_environment = fingerprint()
    if actual_environment != manifest["environment"]:
        message = (
            "La referencia requiere las mismas métricas de fuente y versión Qt; "
            "las pruebas de integridad y geometría siguen activas. "
            f"Esperado: {manifest['environment']}; actual: {actual_environment}."
        )
        if os.environ.get("GV_REQUIRE_RENDER_REFERENCES") == "1":
            pytest.fail(message)
        pytest.skip(message)
    case = next(case for case in cases() if case[0] == case_name)
    actual, regions = render_case(case)
    record = manifest["cases"][case_name]
    expected = QImage(str(REFERENCES / record["file"]))
    assert not expected.isNull() and actual.size() == expected.size()
    assert regions == record["regions"]
    for number, region in enumerate(regions):
        rect = QRect(*region)
        a = actual.copy(rect).convertToFormat(QImage.Format.Format_RGBA8888)
        b = expected.copy(rect).convertToFormat(QImage.Format.Format_RGBA8888)
        left, right = a.constBits().tobytes(), b.constBits().tobytes()
        difference = sum(abs(x - y) for x, y in zip(left, right, strict=True)) / len(left)
        if difference > 2:
            actual.save(str(tmp_path / f"{case_name}-actual.png"))
        assert difference <= 2, f"Región {number} cambió ({difference:.2f}); revisa {tmp_path}"
