from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session

from app.api.dependencies import current_user, session_csrf
from app.db import get_session
from app.services.addresses import lock_owner

router = APIRouter(prefix="/account/notifications", tags=["notification preferences"])


class Preferences(BaseModel):
    model_config = ConfigDict(extra="forbid")
    whatsapp_enabled: bool = Field(strict=True)
    whatsapp_phone: str | None = Field(default=None, pattern=r"^\+[1-9][0-9]{7,14}$")

    @model_validator(mode="after")
    def require_phone(self):
        if self.whatsapp_enabled and not self.whatsapp_phone:
            raise ValueError("Provide your WhatsApp number with country code")
        return self


def view(user, settings):
    return dict(
        whatsapp_enabled=user.whatsapp_opted_in_at is not None,
        whatsapp_phone=user.whatsapp_phone,
        whatsapp_available=settings.whatsapp_notifications_enabled,
    )


@router.get("")
def get_preferences(request: Request, response: Response, user=Depends(current_user)):
    response.headers["Cache-Control"] = "no-store"
    return view(user, request.app.state.settings)


@router.put("", dependencies=[Depends(session_csrf)])
def update_preferences(
    data: Preferences,
    request: Request,
    response: Response,
    user=Depends(current_user),
    db: Session = Depends(get_session),
):
    lock_owner(db, user.id)
    if data.whatsapp_enabled:
        if user.whatsapp_phone != data.whatsapp_phone or user.whatsapp_opted_in_at is None:
            user.whatsapp_opted_in_at = datetime.now(timezone.utc)
        user.whatsapp_phone = data.whatsapp_phone
    else:
        user.whatsapp_phone = None
        user.whatsapp_opted_in_at = None
    db.commit()
    response.headers["Cache-Control"] = "no-store"
    return view(user, request.app.state.settings)
