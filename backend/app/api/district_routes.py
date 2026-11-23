"""District view: counts per school only (see app/services/district.py for the privacy rules)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..auth import require_district
from ..db import get_db
from ..services import district

router = APIRouter(prefix="/api/district", dependencies=[Depends(require_district)])


@router.get("/summary")
def district_summary(db: Session = Depends(get_db)) -> dict:
    return district.summary(db)


@router.get("/summary.csv")
def district_summary_csv(db: Session = Depends(get_db)) -> Response:
    body = "﻿" + district.summary_csv(district.summary(db))  # BOM so Excel reads Bangla correctly
    return Response(body, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="porabondhu_district_summary.csv"'})
