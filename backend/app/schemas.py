from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .assessment.types import STATUSES


class ClassroomIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    grade: int = Field(ge=1, le=5)
    school: str | None = Field(default=None, max_length=160)


class StudentIn(BaseModel):
    code: str = Field(min_length=1, max_length=40)
    nickname: str | None = Field(default=None, max_length=60)


class StudentsBulkIn(BaseModel):
    count: int = Field(ge=1, le=120)
    prefix: str = Field(default="Roll ", max_length=20)
    start: int = Field(default=1, ge=0)


class StudentPatch(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=40)
    nickname: str | None = Field(default=None, max_length=60)
    active: bool | None = None


class PassageIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    grade: int = Field(ge=1, le=5)
    language: Literal["bn", "en"] = "bn"
    text: str = Field(min_length=1, max_length=5000)


class PassagePatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    grade: int | None = Field(default=None, ge=1, le=5)
    text: str | None = Field(default=None, min_length=1, max_length=5000)
    active: bool | None = None


class MarkPatch(BaseModel):
    teacher_status: str | None = None  # null resets to the system decision

    def validated(self) -> str | None:
        if self.teacher_status is not None and self.teacher_status not in STATUSES:
            raise ValueError(f"teacher_status must be one of {STATUSES}")
        return self.teacher_status


class FinalizeIn(BaseModel):
    keep_audio: bool = False


class VariantIn(BaseModel):
    word: str = Field(min_length=1, max_length=200)
    variant: str = Field(min_length=1, max_length=200)
    note: str | None = Field(default=None, max_length=200)


class AnalyzeIn(BaseModel):
    text: str = Field(min_length=1, max_length=5000)


class DiffIn(BaseModel):
    expected: str = Field(min_length=1, max_length=200)
    heard: str = Field(default="", max_length=200)


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=60)
    password: str = Field(min_length=1, max_length=200)
    role: Literal["teacher", "student"] | None = None  # the login tab used; checked against the account


class AccountIn(BaseModel):
    username: str = Field(min_length=3, max_length=60, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=4, max_length=200)


class PasswordIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=4, max_length=200)
