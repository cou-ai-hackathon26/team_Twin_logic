"""Pre-generate the model readings for every passage (normal and slow) while online,
so "Listen first" works offline in class.

    python -m scripts.pregen_tts
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.models import Passage  # noqa: E402
from app.services import tts  # noqa: E402


async def main() -> None:
    with SessionLocal() as db:
        passages = [(p.id, p.text, p.language or "bn") for p in db.scalars(select(Passage))]
    ok = fail = 0
    for pid, text, lang in passages:
        for slow in (False, True):
            try:
                await tts.speak(text, lang, slow)
                ok += 1
            except Exception as e:  # noqa: BLE001
                fail += 1
                print(f"passage {pid} slow={slow}: {e}")
    print(f"done: {ok} ready, {fail} failed ({len(passages)} passages)")


if __name__ == "__main__":
    asyncio.run(main())
