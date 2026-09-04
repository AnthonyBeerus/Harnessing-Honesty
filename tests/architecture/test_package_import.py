import sys


def test_package_import_is_lightweight() -> None:
    import harnessing_honesty

    assert harnessing_honesty.__version__ == "0.1.0"
    assert "pandas" not in sys.modules
    assert "streamlit" not in sys.modules