from pathlib import Path

__version__ = "0.1.0"

# The checkout holding config/, data/ and this package; the package runs from
# an editable install, so its source sits at src/harnessing_honesty/.
REPO_ROOT = Path(__file__).resolve().parents[2]
