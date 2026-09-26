"""Keep reviewed screenshots reproducible without replacing them in CI."""

from pathlib import Path

from PIL import Image, ImageStat

from scripts.capture_docs_screenshots import CAPTURES, capture_all


def test_workflow_gallery_capture_smoke(run_streamlit, tmp_path: Path) -> None:
    written = capture_all(
        f"http://localhost:{run_streamlit}", tmp_path, gallery_only=True
    )
    expected = {
        item.filename for item in CAPTURES if item.scene.startswith("workflow-")
    }
    assert {path.name for path in written} == expected
    assert len(written) == 5
    for path in written:
        with Image.open(path) as image:
            assert image.width >= 450
            assert image.height >= 300
            assert max(ImageStat.Stat(image.convert("RGB")).stddev) > 10
            assert path.stat().st_size < 300_000
