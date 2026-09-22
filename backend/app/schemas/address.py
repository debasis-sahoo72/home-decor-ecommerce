"""India-only address input; serviceability is checked separately at checkout."""

import re
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AddressInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    full_name: str = Field(min_length=2, max_length=100)
    phone: str = Field(min_length=10, max_length=20)
    line1: str = Field(min_length=5, max_length=200)
    line2: str | None = Field(default=None, max_length=200)
    landmark: str | None = Field(default=None, max_length=200)
    city: str = Field(min_length=2, max_length=100)
    state: str = Field(min_length=2, max_length=100)
    country: Literal["IN"] = "IN"
    pincode: str = Field(pattern=r"^[1-9][0-9]{5}$")
    is_default: bool = Field(default=False, strict=True)

    @field_validator("phone")
    @classmethod
    def phone_number(cls, value):
        if not re.fullmatch(r"[+0-9 ()-]+", value):
            raise ValueError("Enter a valid Indian mobile number.")
        digits = re.sub(r"[ ()-]", "", value)
        if digits.startswith("+91"):
            digits = digits[3:]
        if not re.fullmatch(r"[6-9][0-9]{9}", digits):
            raise ValueError("Enter a 10-digit Indian mobile number, optionally prefixed with +91.")
        return "+91" + digits

    @field_validator("full_name", "line1", "line2", "landmark", "city", "state")
    @classmethod
    def clean_text(cls, value):
        if value is not None and any(ord(c) < 32 or ord(c) == 127 for c in value):
            raise ValueError("Control characters are not allowed.")
        return value or None


class AddressPublic(BaseModel):
    id: UUID
    full_name: str
    phone: str
    line1: str
    line2: str | None
    landmark: str | None
    city: str
    state: str
    country: str
    pincode: str
    is_default: bool
