"""Deploy the committed code (git HEAD) to the Hugging Face Space.

    backend/.venv/Scripts/python deploy/push_space.py [owner/space]

Only files tracked by git are uploaded, so the live demo is always built from
the repository. The Space README gets the YAML header Spaces needs, followed by
the project README.
"""

from __future__ import annotations

import io
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parent.parent
SPACE = sys.argv[1] if len(sys.argv) > 1 else "safu58/porabondhu"
HEADER = """---
title: PoraBondhu AI
emoji: 📖
colorFrom: green
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
short_description: Bangla reading diagnostician for primary teachers
---

"""


def main() -> None:
    sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    archive = subprocess.check_output(["git", "archive", "--format=tar", "HEAD"], cwd=ROOT)
    with tempfile.TemporaryDirectory() as tmp:
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(tmp)
        readme = Path(tmp, "README.md")
        readme.write_text(HEADER + readme.read_text(encoding="utf-8"), encoding="utf-8")
        api = HfApi()
        api.create_repo(SPACE, repo_type="space", space_sdk="docker", exist_ok=True, private=False)
        api.upload_folder(folder_path=tmp, repo_id=SPACE, repo_type="space", delete_patterns="*",
                          commit_message=f"Deploy {sha} from GitHub main")
    print(f"Deployed {sha} to https://huggingface.co/spaces/{SPACE}")


if __name__ == "__main__":
    main()
