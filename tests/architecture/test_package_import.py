import subprocess
import sys

# A fresh interpreter: the fit tests load pandas through gpboost.
CHECK = """
import sys
import harnessing_honesty
assert harnessing_honesty.__version__ == "0.1.0"
assert not {"gpboost", "pandas", "streamlit"} & set(sys.modules)
"""


def test_package_import_is_lightweight() -> None:
    subprocess.run([sys.executable, "-c", CHECK], check=True)
