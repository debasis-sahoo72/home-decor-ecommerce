from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.dependencies import current_user, session_csrf
from app.db import get_session
from app.schemas.address import AddressInput, AddressPublic
from app.services import addresses

router = APIRouter(prefix="/addresses", tags=["customer addresses"])


@router.get("", response_model=list[AddressPublic])
def listing(user=Depends(current_user), db: Session = Depends(get_session)):
    return addresses.listing(db, user.id)


@router.get("/{address_id}", response_model=AddressPublic)
def detail(address_id: UUID, user=Depends(current_user), db: Session = Depends(get_session)):
    return addresses.view(addresses.owned(db, user.id, address_id))


@router.post(
    "", response_model=AddressPublic, status_code=201, dependencies=[Depends(session_csrf)]
)
def add(data: AddressInput, user=Depends(current_user), db: Session = Depends(get_session)):
    return addresses.save(db, user.id, data)


@router.put("/{address_id}", response_model=AddressPublic, dependencies=[Depends(session_csrf)])
def edit(
    address_id: UUID,
    data: AddressInput,
    user=Depends(current_user),
    db: Session = Depends(get_session),
):
    return addresses.save(db, user.id, data, address_id)


@router.post(
    "/{address_id}/default", response_model=AddressPublic, dependencies=[Depends(session_csrf)]
)
def default(address_id: UUID, user=Depends(current_user), db: Session = Depends(get_session)):
    return addresses.set_default(db, user.id, address_id)


@router.delete("/{address_id}", status_code=204, dependencies=[Depends(session_csrf)])
def remove(address_id: UUID, user=Depends(current_user), db: Session = Depends(get_session)):
    addresses.remove(db, user.id, address_id)
    return Response(status_code=204)
