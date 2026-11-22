"""The NCTB-aligned passages really contain the words and units they claim to practise."""

import subprocess
import sys
from pathlib import Path

from app.evaluation.dataset import load_seed_passages


def test_textbook_passages_are_seeded():
    codes = load_seed_passages()
    assert all(f"T{i:02d}" in codes for i in range(1, 13))


def test_curriculum_targets_present():
    root = Path(__file__).resolve().parent.parent
    r = subprocess.run([sys.executable, "-m", "scripts.curriculum_evidence", "--check"], cwd=root,
                       capture_output=True, text=True, encoding="utf-8", env={**__import__("os").environ,
                                                                             "PYTHONIOENCODING": "utf-8"})
    assert r.returncode == 0, r.stdout + r.stderr
