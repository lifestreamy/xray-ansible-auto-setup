"""Package smoke test: importable and reports a version."""

from xrayvpn import __version__


def test_version_string() -> None:
    assert isinstance(__version__, str)
    assert __version__.count(".") >= 1