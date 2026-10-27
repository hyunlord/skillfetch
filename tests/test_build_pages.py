"""scripts/build_pages.py: the Pages site holds the galleries and an index, nothing else."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location(
        "build_pages", ROOT / "scripts" / "build_pages.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_site_is_galleries_and_index(tmp_path):
    pages = _load()
    e2e = tmp_path / "e2e"
    for stage in ("stage13", "stage14"):
        (e2e / stage / "gallery").mkdir(parents=True)
        (e2e / stage / "gallery" / f"{stage}-gallery.html").write_text("<html>g</html>")
        (e2e / stage / "gallery" / "build.py").write_text("x")  # not deployed
        (e2e / stage / "report.md").write_text("x")  # not deployed
    out = tmp_path / "_site"
    written = pages.build(out, e2e)
    files = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
    assert files == ["index.html", "stage13/stage13-gallery.html", "stage14/stage14-gallery.html"]
    assert len(written) == 3
    index = (out / "index.html").read_text()
    assert 'href="stage13/stage13-gallery.html"' in index and "§26" in index
    assert 'href="stage14/stage14-gallery.html"' in index and "§28" in index


def test_the_real_galleries_are_found():
    names = {p.relative_to(ROOT).as_posix() for p in _load().galleries()}
    assert "evals/e2e/stage13/gallery/stage13-gallery.html" in names
    assert "evals/e2e/stage14/gallery/stage14-gallery.html" in names
