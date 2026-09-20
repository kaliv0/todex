import shutil
from pathlib import Path

import pytest

from todex.extractor import Extractor

TESTDATA = Path(__file__).parent / "testdata"


@pytest.fixture
def sample(tmp_path: Path) -> Path:
    # copy the sample project tree into an isolated temp dir."""
    dest = tmp_path / "project"
    shutil.copytree(TESTDATA, dest)

    # NB: paths matching ignore rules never land in git — materialize them for the scan.
    # testdata/.gitignore: vendor/, skip_me.py vs repo .gitignore: .venv/
    (dest / "skip_me.py").write_text("# TODO: skip\n", encoding="utf-8")

    vendor = dest / "vendor"
    vendor.mkdir(exist_ok=True)
    (vendor / "lib.py").write_text("# TODO: vendored\n", encoding="utf-8")

    venv = dest / ".venv"
    venv.mkdir(exist_ok=True)
    (venv / "x.py").write_text("# TODO: venv\n", encoding="utf-8")

    return dest


@pytest.fixture
def out(sample: Path) -> Path:
    return sample / "out.txt"


@pytest.fixture
def run():
    def _run(path: Path, out: Path, **kwargs) -> str:
        Extractor(path=path, out=str(out), **kwargs).run()
        return out.read_text(encoding="utf-8") if out.is_file() else ""

    return _run
