"""Text-to-speech for any logged-in user: hear a passage or a single word read correctly."""

from __future__ import annotations

import re
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ..auth import current_user
from ..services import tts

router = APIRouter(prefix="/api/tts", dependencies=[Depends(current_user)])


class SpeakIn(BaseModel):
    text: str = Field(min_length=1, max_length=tts.MAX_CHARS)
    lang: Literal["bn", "en"] = "bn"
    slow: bool = False


@router.post("")
async def speak(body: SpeakIn) -> dict:
    try:
        res = await tts.speak(body.text, body.lang, body.slow)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    except tts.TTSUnavailable as e:
        raise HTTPException(503, str(e)) from e
    return {"url": f"/api/tts/{res['key']}.mp3", "words": res["words"]}


@router.get("/{key}.mp3")
def audio(key: str):
    if not re.fullmatch(r"[0-9a-f]{20}", key):
        raise HTTPException(404, "Not found")
    p = tts.audio_path(key)
    if not p.exists():
        raise HTTPException(404, "Not found")
    return FileResponse(p, media_type="audio/mpeg", headers={"Cache-Control": "private, max-age=86400"})
