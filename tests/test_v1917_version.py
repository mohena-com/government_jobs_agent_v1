from pathlib import Path


def test_workspace_version_is_1918():
    assert Path("VERSION").read_text(encoding="utf-8").strip() == "1.9.20"
